"""
Download real representative 2023 NYC 311 service requests from NYC Open Data.
"""

import requests
import json
from pathlib import Path


def download_sample():
    target_dir = Path(__file__).resolve().parent / "data"
    target_dir.mkdir(parents=True, exist_ok=True)
    target_file = target_dir / "nyc311_sample_2023.json"

    url = "https://data.cityofnewyork.us/resource/erm2-nwe9.json"
    
    # Query across different months of 2023 to capture seasonal distribution
    all_records = []
    periods = [
        ("2023-01-15T00:00:00", "2023-01-16T12:00:00"),
        ("2023-04-15T00:00:00", "2023-04-16T12:00:00"),
        ("2023-07-15T00:00:00", "2023-07-16T12:00:00"),
        ("2023-10-15T00:00:00", "2023-10-16T12:00:00")
    ]
    
    print("Fetching NYC 311 2023 records across seasons from NYC Open Data...")
    for start, end in periods:
        query = f"created_date >= '{start}' AND created_date <= '{end}'"
        params = {"$where": query, "$limit": 1500}
        try:
            r = requests.get(url, params=params, timeout=25)
            if r.status_code == 200:
                batch = r.json()
                all_records.extend(batch)
                print(f"Fetched {len(batch)} records for period {start[:10]}")
            else:
                print(f"Warning: HTTP {r.status_code} for period {start}")
        except Exception as e:
            print(f"Network error on {start}: {e}")

    if all_records:
        with open(target_file, "w", encoding="utf-8") as f:
            json.dump(all_records, f)
        print(f"Saved total of {len(all_records)} real 2023 NYC 311 records to {target_file}")
    else:
        print("Failed to download records.")


if __name__ == "__main__":
    download_sample()
