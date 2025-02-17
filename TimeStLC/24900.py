import requests
from astroquery.jplhorizons import Horizons
from datetime import datetime
import time

# Constants
MPC_URL = "https://www.minorplanetcenter.net/iau/MPCORB/NEA.txt"
START_DATE = "2018-01-01"  # Observation start date
END_DATE = "2025-01-01"  # Observation end date
LOCATION = "500"  # Geocentric location (@500 for Earth)
CHUNK_START = 24900  # Start index for this chunk
CHUNK_END = 26900  # End index for this chunk
CHUNK_FILE = f"valid_asteroids_{CHUNK_START}_to_{CHUNK_END}.txt"  # Chunk-specific file
MASTER_FILE = "all_valid_asteroids.txt"  # Central master file

def fetch_asteroid_ids(mpc_url):
    """Fetch asteroid IDs from the MPC NEA catalog"""
    try:
        response = requests.get(mpc_url)
        response.raise_for_status()
        return [line[:7].strip() for line in response.text.splitlines() if len(line) >= 7]
    except Exception as e:
        print(f"Error fetching MPC data: {e}")
        return []

def check_conditions(asteroid_id, location, start_date, end_date):
    """Return valid observations with detailed parameters"""
    valid_observations = []
    try:
        obj = Horizons(
            id=asteroid_id,
            location=location,
            epochs={'start': start_date, 'stop': end_date, 'step': '1d'}
        )
        eph = obj.ephemerides()
        
        for row in eph:
            v_mag = row["V"]
            timestamp = row["datetime_str"]
            
            # Convert rates from arcsec/hr to arcsec/min
            ra_rate = row["RA_rate"] / 60
            dec_rate = row["DEC_rate"] / 60
            motion_rate = (ra_rate**2 + dec_rate**2)**0.5  # Total motion rate
            
            if v_mag < 20 and motion_rate > 10:
                valid_observations.append({
                    'timestamp': timestamp,
                    'v_mag': v_mag,
                    'ra_rate': ra_rate,
                    'dec_rate': dec_rate,
                    'motion_rate': motion_rate
                })
                
    except Exception as e:
        pass  # Suppress individual query errors
    
    return valid_observations

def main():
    """Main processing function with enhanced data recording"""
    asteroid_ids = fetch_asteroid_ids(MPC_URL)
    if not asteroid_ids:
        print("No asteroid IDs fetched.")
        return

    chunk_ids = asteroid_ids[CHUNK_START:CHUNK_END]
    print(f"Processing {len(chunk_ids)} asteroids from {CHUNK_START} to {CHUNK_END}")

    with open(CHUNK_FILE, "w") as chunk_file, open(MASTER_FILE, "a") as master_file:
        # Write headers
        header = "Asteroid_ID,Timestamp,V_Mag,RA_Rate(\"/min),DEC_Rate(\"/min),Motion_Rate(\"/min)\n"
        chunk_file.write(header)
        
        for asteroid_id in chunk_ids:
            observations = check_conditions(asteroid_id, LOCATION, START_DATE, END_DATE)
            
            for obs in observations:
                data_line = (
                    f"{asteroid_id},"
                    f"{obs['timestamp']},"
                    f"{obs['v_mag']:.2f},"
                    f"{obs['ra_rate']:.2f},"
                    f"{obs['dec_rate']:.2f},"
                    f"{obs['motion_rate']:.2f}\n"
                )
                
                # Write to both files
                chunk_file.write(data_line)
                master_file.write(data_line)
                
                # Print to console
                print(f"Valid observation: {data_line.strip()}")

    print(f"Processing complete. Data saved to {CHUNK_FILE} and {MASTER_FILE}")

if __name__ == "__main__":
    main()