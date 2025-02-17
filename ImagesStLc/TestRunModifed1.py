import os
import subprocess
import time
from bs4 import BeautifulSoup
import requests
from datetime import datetime, timedelta

# Configuration constants
ASTEROID_LIST = "asteroids.txt"
BASE_URL = "https://irsa.ipac.caltech.edu/cgi-bin/MOST/nph-most"
OUTPUT_DIR = "mostoutput"
DELAY_SECONDS = 5
EPHEM_STEP = "0.25"
MAX_GAP_DAYS = 1  # Maximum allowed gap between consecutive observations

def parse_asteroid_dates():
    asteroid_windows = {}
    with open(ASTEROID_LIST, 'r') as f:
        for line in f:
            parts = line.strip().split(',')
            if len(parts) < 2:
                continue
            name = parts[0].strip()
            date_str = parts[1].strip().split()[0]  # Get date part only
            
            try:
                dt = datetime.strptime(date_str, "%Y-%b-%d")
            except ValueError:
                print(f"⚠️ Skipping invalid date format: {date_str}")
                continue
            
            if name not in asteroid_windows:
                asteroid_windows[name] = []
            asteroid_windows[name].append(dt)

    # Group dates into consecutive observation windows
    for name in asteroid_windows:
        sorted_dates = sorted(asteroid_windows[name])
        groups = []
        current_group = []
        
        for dt in sorted_dates:
            if not current_group:
                current_group.append(dt)
            else:
                last_dt = current_group[-1]
                delta = (dt - last_dt).days
                if delta <= MAX_GAP_DAYS:
                    current_group.append(dt)
                else:
                    groups.append(current_group)
                    current_group = [dt]
        if current_group:
            groups.append(current_group)
        
        # Convert groups to (start, end) tuples
        asteroid_windows[name] = [
            (
                min(group).strftime("%Y-%m-%d"),
                max(group).strftime("%Y-%m-%d")
            ) 
            for group in groups
        ]
    
    return asteroid_windows

def fetch_asteroid_data(asteroid_name, obs_begin, obs_end, run_number):
    # Create run-specific directory
    run_id = f"OB{run_number}_{obs_begin.replace('-', '')}_{obs_end.replace('-', '')}"
    asteroid_dir = os.path.join(OUTPUT_DIR, asteroid_name.replace(" ", "_"), run_id)
    os.makedirs(asteroid_dir, exist_ok=True)
    
    output_file = os.path.join(asteroid_dir, f"{asteroid_name.replace(' ', '_')}_{run_id}.html")
    
    # Format dates for URL
    url_begin = obs_begin.replace("-", "+")
    url_end = obs_end.replace("-", "+")
    
    url = (f"{BASE_URL}?catalog=ztf"
           f"&input_type=name_input"
           f"&obj_name={asteroid_name}"
           f"&obs_begin={url_begin}"
           f"&obs_end={url_end}"
           f"&ephem_step={EPHEM_STEP}"
           f"&output_mode=Regular")
    
    cmd = ["curl", "-s", "-o", output_file, url]
    
    try:
        subprocess.run(cmd, check=True)
        print(f"✅ Successfully downloaded HTML for {asteroid_name} ({obs_begin} to {obs_end})")
        return output_file
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to fetch data for {asteroid_name}: {e}")
        return None

def process_html_file(html_file, asteroid_name):
    print(f"\n🔍 Parsing HTML file: {html_file}")
    try:
        with open(html_file, 'r', encoding='utf-8') as f:
            html_content = f.read()
    except Exception as e:
        print(f"❌ Error reading HTML file: {e}")
        return []

    soup = BeautifulSoup(html_content, 'html.parser')
    data_entries = []
    
    for row in soup.find_all('tr')[2:]:  # Skip header rows
        tds = row.find_all('td')
        if len(tds) < 13:
            continue
            
        link = tds[0].find('a')
        if not link or 'sciimg.fits' not in link.get('href', ''):
            continue
            
        href = link['href']
        entry = {
            'href': href,
            'filename': tds[2].text.strip(),
            'date_obs': tds[3].text.strip(),
            'time_obs': tds[4].text.strip(),
            'mjd_obs': tds[5].text.strip(),
            'ra_obj': tds[6].text.strip(),
            'dec_obj': tds[7].text.strip(),
            'r': tds[8].text.strip(),
            'delta': tds[9].text.strip(),
            'dist_ctr': tds[10].text.strip(),
            'phase': tds[11].text.strip(),
            'vmag': tds[12].text.strip()
        }
        data_entries.append(entry)
    
    print(f"📊 Found {len(data_entries)} valid entries in HTML")
    return data_entries

def download_modified_files(data_entries, asteroid_name, run_id):
    # Create observation images directory inside the run directory
    asteroid_dir = os.path.join(OUTPUT_DIR, asteroid_name.replace(" ", "_"), run_id, "observation_images")
    os.makedirs(asteroid_dir, exist_ok=True)
    
    for entry in data_entries:
        modified_url = entry['href'].replace('sciimg.fits', 'scimrefdiffimg.fits.fz')
        filename = os.path.basename(modified_url)
        file_path = os.path.join(asteroid_dir, filename)
        txt_path = os.path.join(asteroid_dir, f"{filename}.txt")
        
        if os.path.exists(file_path) and os.path.exists(txt_path):
            print(f"⏩ Skipping existing files for {filename}")
            continue
            
        # Download FITS file
        try:
            print(f"\n⬇️ Downloading {filename}...")
            start_time = time.time()
            response = requests.get(modified_url, stream=True)
            response.raise_for_status()
            
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            print(f"✅ Downloaded {filename} ({time.time()-start_time:.1f}s)")
        except Exception as e:
            print(f"❌ Failed to download {filename}: {e}")
            continue
            
        # Save metadata
        try:
            with open(txt_path, 'w') as f:
                metadata = f"""File: {entry['filename']}
Observation Date: {entry['date_obs']}
Observation Time: {entry['time_obs']}
MJD: {entry['mjd_obs']}
RA: {entry['ra_obj']}
Dec: {entry['dec_obj']}
r (AU): {entry['r']}
Delta (AU): {entry['delta']}
Distance Center: {entry['dist_ctr']}
Phase: {entry['phase']}
Vmag: {entry['vmag']}
"""
                f.write(metadata)
            print(f"📝 Saved metadata to {filename}.txt")
        except Exception as e:
            print(f"⚠️ Failed to save metadata: {e}")
        
        time.sleep(1)  # Rate limiting

def process_asteroids():
    asteroid_windows = parse_asteroid_dates()
    
    for asteroid_name, observation_runs in asteroid_windows.items():
        print(f"\n🛰️ Processing asteroid: {asteroid_name}")
        
        for run_idx, (obs_begin, obs_end) in enumerate(observation_runs, 1):
            print(f"📅 Processing observation run {run_idx}: {obs_begin} to {obs_end}")
            
            run_id = f"OB{run_idx}_{obs_begin.replace('-', '')}_{obs_end.replace('-', '')}"
            html_file = fetch_asteroid_data(asteroid_name, obs_begin, obs_end, run_idx)
            
            if html_file:
                entries = process_html_file(html_file, asteroid_name)
                if entries:
                    download_modified_files(entries, asteroid_name, run_id)
                else:
                    print(f"⚠️ No downloadable content found for {asteroid_name} in this run")
            time.sleep(DELAY_SECONDS)

if __name__ == "__main__":
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print("🚀 Starting asteroid data processing...")
    process_asteroids()
    print("\n🎉 All processing completed!")