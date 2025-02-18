# Asteroid Streak Analysis Pipeline for ZTF Observations

![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![Astronomy](https://img.shields.io/badge/Astronomy-Data%20Analysis-orange)
![License](https://img.shields.io/badge/License-MIT-green)

Advanced pipeline for analyzing asteroid streaks in Zwicky Transient Facility (ZTF) difference images, combining JPL Horizons ephemeris data with observational metadata from IPAC's MOST tool.

## 🌠 Project Overview

This final stage in our asteroid analysis pipeline:
1. Calculates predicted streak trajectories using JPL Horizons data
2. Generates science-ready cutouts from ZTF difference images
3. Visualizes motion through oriented aperture markers
4. Highlights ephemeris-vs-observation discrepancies

![Example Cutout](../FWHMEndPoints/cutouts/K11M00U/ztf_20220623205451_000578_zr_c07_o_q4_scimrefdiffimg_cutout.png)

## ⚙️ Installation

```bash
pip install astroquery astropy matplotlib numpy
```

## 🏃‍♂️ Usage

1. **Run Pipeline** (requires output from previous stages)
```bash
python streak_analyzer.py
```

2. **Monitor Output**
```
Found 142 asteroid metadata files to process

🛰 Processing: K22S00C (mostoutput/K22S00C/OB1.../observation_images)
RA Rate: 12.34"/min | Dec Rate: -8.76"/min
Created: cutouts/K22S00C/ZTFJ20230105..._cutout.png
```

## 📂 Output Structure

```
cutouts/
└── K22S00C/
    ├── ZTFJ202301050000_cutout.png
    └── ZTFJ202301050030_cutout.png
```

Each PNG contains:
- Start/end markers (green circle/red square)
- Predicted streak path (yellow dashed line)
- FWHM-scaled apertures (magenta boxes)
- Key observational parameters

## 🔍 Key Technical Features

### 1. Ephemeris-Based Streak Prediction
```python
# Calculate endpoint coordinates (30s exposure)
delta_ra = (ra_rate * 0.5) / 3600  # "/min -> degrees
delta_dec = (dec_rate * 0.5) / 3600
ra_end = ra_start + delta_ra
dec_end = dec_start + delta_dec
```

### 2. Adaptive Cutout Sizing
```python
# Auto-expand based on predicted motion
dx = abs(start_px[0] - end_px[0])
dy = abs(start_px[1] - end_px[1])
size = max(dx, dy) * 1.5 + 50
```

### 3. FWHM-Scaled Apertures
```python
# Convert seeing to pixels
pixel_scale = wcs.proj_plane_pixel_scales().mean().to(u.arcsec)
fwhm_pixels = seeing / pixel_scale

# Create rotated rectangles
rotation = np.array([[np.cos(theta), -np.sin(theta)],
                   [np.sin(theta), np.cos(theta)]])
```

## 🧩 Observed Discrepancies (Case Study)

### Asteroid K22S00C - 2023-01-05 Observation

| Parameter          | JPL Prediction      | MOST Observed      | Difference       |
|--------------------|---------------------|--------------------|------------------|
| RA (deg)           | 322.157100          | 322.178967         | Δ0.021867°       |
| Dec (deg)          | -17.671880          | -17.721018         | Δ-0.049138°      |
| **Angular Separation** |                   |                   | **192" (3.2')**  |

**Implications:**
- Predicted positions often outside standard cutouts
- Systematic offset suggests ephemeris inaccuracy
- MOST positions match actual image content

## ❓ Critical Open Questions

1. **MOST Position Determination**
   - Does MOST use ephemeris predictions or image detection?
   - Why the consistent ~3' offset from JPL predictions?

2. **Ephemeris Accuracy**
   - Are there unmodeled orbital perturbations?
   - How does timing accuracy affect positions?

3. **Observation Methodology**
   - Should we prioritize MOST positions for cutouts?
   - How to reconcile ephemeris vs observed positions?

## 📊 Technical Specifications

### FWHM Calculation
```python
# From header seeing (arcsec) to pixels
fwhm_arcsec = header['SEEING']  # Typically 1.5-2.5"
pixel_scale = 1.0" # ZTF plate scale
fwhm_pixels = fwhm_arcsec / pixel_scale
```

### Aperture Placement
- Oriented along predicted motion vector
- Width = FWHM diameter
- Spaced every FWHM distance along streak

![Aperture Diagram](https://via.placeholder.com/400x200.png/000000/FFFFFF?text=FWHM-Spaced+Apertures+Along+Streak)

## 🚀 Current Approach and Challenges

### Current Methodology
We are proceeding with extrapolating the MOST RA/Dec positions using the RA/Dec rates derived from JPL Horizons. This approach provides:
- Consistent reference frame with observed positions
- Better alignment with actual image content
- More reliable cutout placement

### Known Issues
1. **Ephemeris Query Discrepancies**
   - Direct ephemeris queries at shutter open/close times yield positions significantly offset from observations
   - Potential causes:
     - Unmodeled non-gravitational forces
     - Timing synchronization issues
     - Reference frame differences

2. **Rate Extrapolation Limitations**
   - Linear extrapolation assumes constant motion
   - Near-Earth Asteroids (NEAs) may exhibit:
     - Non-linear motion due to proximity
     - Apparent curvature in streaks
     - Rapidly changing rates

3. **Photometric Challenges**
   - Curved streaks require specialized analysis:
     - Adaptive aperture shapes
     - Motion-dependent PSF modeling
     - Trailed source photometry techniques

## 🔮 Future Directions

1. **Ephemeris Analysis**
   - Investigate timing and reference frame effects
   - Compare with alternative ephemeris services

2. **Motion Modeling**
   - Implement higher-order motion models
   - Develop curved streak detection

3. **Photometric Methods**
   - Explore trailed source photometry
   - Develop adaptive aperture techniques

## 📜 License

This project is licensed under the [MIT License](../LICENSE.md).

## 🙏 Acknowledgements

- JPL Horizons team for ephemeris service
- ZTF Collaboration for public data access
- IPAC for maintaining MOST tool