# Asteroid Motion Cutout Generator (JPL Horizons Enhanced)

**Improved version** using JPL Horizons for accurate asteroid endpoint calculation

## Key Improvements Over Previous Version

This version significantly improves trajectory accuracy by:
1. **JPL Horizons Query for End Position**  
   Instead of extrapolating using RA/Dec rates from the MOST file:
   - Queries JPL Horizons **at observation end time** (`obs_time + 30s`)
   - Gets **true calculated position** from ephemerides
   - Handles **curved trajectories** and non-linear motion

2. **Start Position Preservation**  
   - Uses original MOST file RA/Dec as start point (no query)
   - Maintains consistency with initial detection data

3. **Visualization Enhancements**  
   - More accurate motion trails with rotated FWHM rectangles
   - Direct comparison between extrapolated vs JPL-calculated paths

## Workflow Overview

1. **Input Processing**  
   - Scan `mostoutput/` for asteroid metadata (`*.fits.fz.txt`)

2. **JPL Horizons Integration**  
   - For each observation:
     - Parse observation time from metadata
     - Calculate end time: `obs_time + 30s exposure`
     - Query Horizons for exact RA/Dec at end time

3. **Cutout Generation**  
   - Create FITS cutout containing full trajectory:
     - Auto-expanding size based on start/end separation
     - WCS-preserved outputs

4. **Enhanced Visualization**  
   - Generate PNG with:
     - Start (green) and JPL-calculated end (red) markers
     - Motion path line
     - Rotated FWHM rectangles showing expected positions
     - Key metadata overlay

## Key Features

| Feature | Description |
|---------|-------------|
| **JPL Accuracy** | Endpoints from Horizons instead of linear extrapolation |
| **Dynamic Cutouts** | Automatic size adjustment for long trails |
| **FWHM Motion Trail** | Rotated rectangles showing expected positions every FWHM |
| **Multi-Output** | FITS cutouts + PNG visuals + metadata TXT |
| **Error Handling** | Skip corrupted files with clear error logging |

## Usage

### Requirements
```bash
pip install astroquery astropy matplotlib numpy