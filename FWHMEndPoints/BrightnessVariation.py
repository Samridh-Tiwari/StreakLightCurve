import os
from glob import glob
from astroquery.jplhorizons import Horizons
from astropy.time import Time
from astropy.io import fits
from astropy.wcs import WCS
import matplotlib.pyplot as plt
from astropy.nddata import Cutout2D
import numpy as np
from astropy.visualization import ZScaleInterval
from matplotlib.patches import Polygon, Rectangle
from astropy import units as u
from scipy.ndimage import rotate

# Configuration
LOCATION = "I41"  # ZTF observatory code
CUTOUT_SIZE = 100  # Default cutout size in pixels (will auto-expand if needed)
CUTOUTS_DIR = "cutouts"  # Main output directory for all cutouts

def create_cutout(fits_path, ra_start, dec_start, ra_end, dec_end, asteroid_id, obs_utc, v_mag):
    try:
        with fits.open(fits_path) as hdul:
            # Handle different HDU scenarios
            if len(hdul) > 1:
                hdu = hdul[1]
            else:
                hdu = hdul[0]

            # Handle 3D data and singleton dimensions
            data = hdu.data.squeeze()
            if data.ndim != 2:
                raise ValueError(f"Invalid data shape {data.shape} - expected 2D array")

            # Create 2D celestial WCS
            header = hdu.header
            wcs = WCS(header).celestial

            # Convert coordinates to pixel positions
            start_px = wcs.all_world2pix([[ra_start, dec_start]], 0)[0]
            end_px = wcs.all_world2pix([[ra_end, dec_end]], 0)[0]
            
            # Calculate required cutout size
            dx = abs(start_px[0] - end_px[0])
            dy = abs(start_px[1] - end_px[1])
            size = max(dx, dy) * 1.5 + 50
            size = max(size, CUTOUT_SIZE)
            
            # Use midpoint for cutout center
            center_x = (start_px[0] + end_px[0]) / 2
            center_y = (start_px[1] + end_px[1]) / 2
            
            # Create cutout
            cutout = Cutout2D(data, position=(center_x, center_y), 
                            size=(size, size), wcs=wcs, mode='partial')
            
            # --- Save FITS cutout ---
            # Prepare header with updated WCS
            new_header = header.copy()
            new_header.update(cutout.wcs.to_header())
            new_header['NAXIS1'] = cutout.data.shape[1]
            new_header['NAXIS2'] = cutout.data.shape[0]
            
            # Remove singleton dimensions if present
            for key in ['NAXIS3', 'NAXIS4']:
                if key in new_header:
                    del new_header[key]
            
            # Create output directory
            output_dir = os.path.join(CUTOUTS_DIR, asteroid_id)
            os.makedirs(output_dir, exist_ok=True)
            
            # Save FITS file
            base_name = os.path.basename(fits_path).replace('.fits.fz', '')
            fits_output_path = os.path.join(output_dir, f"{base_name}_cutout.fits")
            fits.PrimaryHDU(data=cutout.data, header=new_header).writeto(fits_output_path, overwrite=True)
            print(f"Saved FITS: {fits_output_path}")
            
            # --- Create visualization ---
            # Get positions in cutout coordinates
            start_cutout = cutout.to_cutout_position(start_px)
            end_cutout = cutout.to_cutout_position(end_px)
            
            # Create figure with subplots
            fig = plt.figure(figsize=(15, 8))
            gs = fig.add_gridspec(2, 2, width_ratios=[3, 1], height_ratios=[3, 1])
            ax1 = fig.add_subplot(gs[0, 0], projection=cutout.wcs)
            ax2 = fig.add_subplot(gs[0, 1])
            ax3 = fig.add_subplot(gs[1, :])
            
            # --- Main Image with Custom Scaling ---
            # Get FWHM and maglim from header
            seeing_hdu = next(h for h in hdul if 'SEEING' in h.header)
            maglim = next(h.header['MAGLIM'] for h in hdul if 'MAGLIM' in h.header)
            
            # Calculate FWHM in pixels
            fwhm_arcsec = seeing_hdu.header['SEEING']
            pixel_scale = np.mean([abs(scale.to(u.arcsec).value) 
                                 for scale in wcs.proj_plane_pixel_scales()])
            fwhm_pixels = fwhm_arcsec / pixel_scale

            # Calculate motion parameters
            dx_px = end_cutout[0] - start_cutout[0]
            dy_px = end_cutout[1] - start_cutout[1]
            distance = np.hypot(dx_px, dy_px)
            theta = np.arctan2(dy_px, dx_px)
            
            # Create mask along the streak
            length = distance
            width = fwhm_pixels * 2  # 2xFWHM width
            mask = np.zeros(cutout.data.shape, dtype=bool)
            
            # Create rotated rectangle mask
            y, x = np.indices(cutout.data.shape)
            cx = (start_cutout[0] + end_cutout[0])/2
            cy = (start_cutout[1] + end_cutout[1])/2
            
            # Rotate coordinates to streak's frame
            dx = x - cx
            dy = y - cy
            rot_x = dx * np.cos(theta) + dy * np.sin(theta)
            rot_y = -dx * np.sin(theta) + dy * np.cos(theta)
            
            # Create mask
            mask = (np.abs(rot_x) < length/2) & (np.abs(rot_y) < width/2)
            
            # Calculate statistics
            streak_data = cutout.data[mask]
            median = np.median(streak_data)
            std = np.std(streak_data)
            vmin = median - 2*std
            vmax = median + 2*std
            
            # Plot main image with custom scaling
            im = ax1.imshow(cutout.data, cmap='gray', vmin=vmin, vmax=vmax, origin='lower')
            fig.colorbar(im, ax=ax1, label='ADU (Median ±2σ)')
            
            # --- Zoomed Streak View ---
            # Rotate and crop the streak
            rotated = rotate(cutout.data, np.degrees(theta), reshape=False)
            crop_size = int(fwhm_pixels * 4)
            cy_rot, cx_rot = rotated.shape[0]//2, rotated.shape[1]//2
            zoom = rotated[cy_rot-crop_size:cy_rot+crop_size, cx_rot-crop_size:cx_rot+crop_size]
            
            ax2.imshow(zoom, cmap='gray', origin='lower')
            ax2.set_title('Rotated Streak View')
            ax2.axis('off')
            
            # --- Brightness Profile ---
            # Sample along the streak
            num_points = 100
            x_points = np.linspace(start_cutout[0], end_cutout[0], num_points)
            y_points = np.linspace(start_cutout[1], end_cutout[1], num_points)
            profile = [cutout.data[int(y), int(x)] for x,y in zip(x_points, y_points)]
            
            # Convert to arcseconds from start
            distances = np.linspace(0, distance*pixel_scale, num_points)
            
            ax3.plot(distances, profile, 'w-', linewidth=1)
            ax3.fill_between(distances, 
                           [p - std for p in profile],
                           [p + std for p in profile],
                           color='magenta', alpha=0.3)
            ax3.set_xlabel('Distance along streak (arcsec)')
            ax3.set_ylabel('Brightness (ADU)')
            ax3.set_title('Brightness Profile with 1σ Range')
            ax3.grid(color='0.5', linestyle=':', alpha=0.5)
            
            # --- Annotations and Markers ---
            # Plot markers and polygons (from original code)
            start_coord = cutout.wcs.pixel_to_world(*start_cutout)
            end_coord = cutout.wcs.pixel_to_world(*end_cutout)
            
            ax1.plot(start_coord.ra.deg, start_coord.dec.deg, 'o',
                    color='lime', markersize=12, label='Start',
                    transform=ax1.get_transform('world'))
            ax1.plot(end_coord.ra.deg, end_coord.dec.deg, 's',
                    color='red', markersize=12, label='End',
                    transform=ax1.get_transform('world'))
            
            # Add statistics annotation
            stats_text = (f"Median: {median:.1f} ADU\n"
                        f"1σ: ±{std:.1f} ADU\n"
                        f"Range: {vmin:.1f}-{vmax:.1f}")
            ax1.text(0.05, 0.95, stats_text, transform=ax1.transAxes,
                    color='white', fontsize=10, va='top',
                    bbox=dict(facecolor='black', alpha=0.7))

            # Prepare metadata text
            text = (f"Asteroid: {asteroid_id}\n"
                    f"Observation Time: {obs_utc}\n"
                    f"Vmag: {v_mag:.2f}\n"
                    f"Mag Limit: {maglim:.2f}\n"
                    f"FWHM: {fwhm_arcsec:.2f}\"\n"
                    f"Start: {ra_start:.6f}, {dec_start:.6f}\n"
                    f"End: {ra_end:.6f}, {dec_end:.6f}")

            # Save metadata to text file
            txt_output_path = os.path.join(output_dir, f"{base_name}_cutout.txt")
            with open(txt_output_path, 'w') as f:
                f.write(text)
            print(f"Saved metadata: {txt_output_path}")

            # Save PNG output
            png_output_path = os.path.join(output_dir, f"{base_name}_cutout.png")
            plt.savefig(png_output_path, bbox_inches='tight', facecolor='black', dpi=150)
            plt.close()
            print(f"Created visualization: {png_output_path}")
            
    except Exception as e:
        print(f"ERROR in {fits_path}: {str(e)}")

# [Keep process_asteroid_motion and main functions unchanged from previous version]
# ... (Rest of the code remains identical to the previous implementation)
# [Keep process_asteroid_motion and main functions unchanged from previous version]
# ... (Rest of the code remains identical to the previous implementation)
def process_asteroid_motion(txt_path, asteroid_id):
    try:
        # Read existing metadata
        with open(txt_path, 'r') as f:
            lines = f.readlines()
        
        # Parse metadata
        metadata = {
            'obs_date': None,
            'obs_time': None,
            'ra_start': None,
            'dec_start': None,
            'fits_filename': None,
            'v_mag': None
        }
        
        for line in lines:
            line = line.strip()
            if line.startswith("Observation Date:"):
                metadata['obs_date'] = line.split(":", 1)[1].strip()
            elif line.startswith("Observation Time:"):
                metadata['obs_time'] = line.split(":", 1)[1].strip()
            elif line.startswith("RA:"):
                metadata['ra_start'] = float(line.split(":", 1)[1].strip())
            elif line.startswith("Dec:"):
                metadata['dec_start'] = float(line.split(":", 1)[1].strip())
            elif line.startswith("File:"):
                metadata['fits_filename'] = line.split(":", 1)[1].strip()
            elif line.startswith("Vmag:"):
                metadata['v_mag'] = float(line.split(":", 1)[1].strip())

        # Validate required fields
        required_fields = ['obs_date', 'obs_time', 'ra_start', 'dec_start', 'fits_filename', 'v_mag']
        missing = [k for k in required_fields if metadata[k] is None]
        if missing:
            print(f"Skipping {txt_path} - missing fields: {', '.join(missing)}")
            return

        # Combine observation time
        obs_utc = f"{metadata['obs_date']} {metadata['obs_time']}"
        
        # Query Horizons for exact end position
        try:
            t = Time(obs_utc, format='iso', scale='utc')
            t_end = t + 30 * u.second  # 30 second exposure
            
            obj = Horizons(id=asteroid_id, location=LOCATION, epochs=t_end.jd)
            eph = obj.ephemerides()
            
            if len(eph) == 0:
                print(f"No Horizons data for {txt_path}")
                return
                
            data = eph[0]
            ra_end = data['RA']
            dec_end = data['DEC']
            
            # Prepare new metadata entries
            new_entries = [
                f"\n# Asteroid motion calculations",
                f"RA End (deg): {ra_end:.6f}",
                f"Dec End (deg): {dec_end:.6f}",
                f"Exposure (s): 30.0"
            ]
            
            # Update text file
            with open(txt_path, 'a') as f:
                f.write("\n".join(new_entries))
            
            # Terminal display
            print(f"\nProcessed: {os.path.basename(metadata['fits_filename'])}")
            print(f"Observation Time: {obs_utc}")
            print(f"Start RA/Dec: {metadata['ra_start']:.6f}, {metadata['dec_start']:.6f}")
            print(f"End RA/Dec: {ra_end:.6f}, {dec_end:.6f}")
            delta_ra = (ra_end - metadata['ra_start']) * 3600
            delta_dec = (dec_end - metadata['dec_start']) * 3600
            print(f"Total displacement: {delta_ra:.2f}\" RA, {delta_dec:.2f}\" Dec\n")
            
            # Create cutout visualization
            fits_filename = metadata['fits_filename'].replace('sciimg.fits', 'scimrefdiffimg.fits.fz')
            fits_path = os.path.join(os.path.dirname(txt_path), fits_filename)
            
            if os.path.exists(fits_path):
                create_cutout(
                    fits_path=fits_path,
                    ra_start=metadata['ra_start'],
                    dec_start=metadata['dec_start'],
                    ra_end=ra_end,
                    dec_end=dec_end,
                    asteroid_id=asteroid_id,
                    obs_utc=obs_utc,
                    v_mag=metadata['v_mag']
                )
            else:
                print(f"FITS file not found: {fits_path}")
            
        except Exception as e:
            print(f"Horizons query failed for {txt_path}: {str(e)}")
            
    except Exception as e:
        print(f"Error processing {txt_path}: {str(e)}")

def main():
    # Create main output directory if needed
    os.makedirs(CUTOUTS_DIR, exist_ok=True)
    
    # Find all FITS metadata files under 'mostoutput' directory
    metadata_files = glob(os.path.join('mostoutput', '**', '*.fits.fz.txt'), recursive=True)
    
    if not metadata_files:
        print("No metadata files found (*.fits.fz.txt)")
        return
    
    print(f"Found {len(metadata_files)} asteroid metadata files to process\n")
    
    for txt_path in metadata_files:
        # Extract asteroid ID from directory structure
        parts = os.path.normpath(txt_path).split(os.sep)
        try:
            # Locate 'mostoutput' in the path
            idx = parts.index('mostoutput')
            asteroid_id = parts[idx + 1]
        except (ValueError, IndexError):
            print(f"Skipping {txt_path} - could not determine asteroid ID")
            continue
        
        process_asteroid_motion(txt_path, asteroid_id)

if __name__ == "__main__":
    main()