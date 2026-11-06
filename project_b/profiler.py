"""
Data Profiler for Real 2023 NYC 311 Service Requests.
Task 1: Profile the raw data. Find and document the quality problems that already exist
in the 2023 data, with counts, percentages, and concrete examples.
"""

import json
import re
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime


# Valid NYC ZIP code prefixes and Borough associations
# Manhattan: 100xx - 102xx
# Staten Island: 103xx
# Bronx: 104xx
# Brooklyn: 112xx
# Queens: 110xx, 111xx, 113xx, 114xx, 116xx
BOROUGH_ZIP_PREFIXES = {
    "MANHATTAN": ("100", "101", "102"),
    "STATEN ISLAND": ("103",),
    "BRONX": ("104",),
    "BROOKLYN": ("112",),
    "QUEENS": ("110", "111", "113", "114", "116")
}

NYC_BOUNDS = {
    "lat_min": 40.49,
    "lat_max": 40.92,
    "lon_min": -74.26,
    "lon_max": -73.68
}


class NYC311Profiler:
    """Profiles raw 2023 NYC 311 dataset for intrinsic data anomalies."""

    def __init__(self, data_path: Path):
        self.data_path = data_path
        with open(data_path, "r", encoding="utf-8") as f:
            self.records = json.load(f)
        self.total_records = len(self.records)

    def run_profiling(self) -> Dict[str, Any]:
        """Perform comprehensive profiling across all dimensions."""
        profile = {
            "total_records": self.total_records,
            "columns": list(self.records[0].keys()) if self.records else [],
            "issues": {}
        }

        # Issue 1: Missing Critical Fields (Nulls)
        missing_fields = {
            "incident_zip": 0,
            "latitude": 0,
            "longitude": 0,
            "resolution_description": 0,
            "closed_date": 0,
            "descriptor": 0
        }
        for r in self.records:
            for k in missing_fields:
                if not r.get(k):
                    missing_fields[k] += 1

        profile["issues"]["missing_fields"] = {
            "counts": missing_fields,
            "percentages": {k: round((v / self.total_records) * 100.0, 2) for k, v in missing_fields.items()}
        }

        # Issue 2: Closed Date Earlier than Created Date
        temporal_inversions = []
        for r in self.records:
            c_date_str = r.get("created_date")
            cl_date_str = r.get("closed_date")
            if c_date_str and cl_date_str:
                try:
                    c_dt = datetime.fromisoformat(c_date_str.replace("Z", ""))
                    cl_dt = datetime.fromisoformat(cl_date_str.replace("Z", ""))
                    if cl_dt < c_dt:
                        temporal_inversions.append({
                            "unique_key": r.get("unique_key"),
                            "agency": r.get("agency"),
                            "created_date": c_date_str,
                            "closed_date": cl_date_str,
                            "delta_seconds": (cl_dt - c_dt).total_seconds()
                        })
                except Exception:
                    pass

        profile["issues"]["closed_earlier_than_created"] = {
            "count": len(temporal_inversions),
            "percentage": round((len(temporal_inversions) / self.total_records) * 100.0, 4),
            "examples": temporal_inversions[:5]
        }

        # Issue 3: Unspecified Borough
        unspecified_boroughs = [r for r in self.records if (r.get("borough") or "").upper() in ["UNSPECIFIED", "", "UNKNOWN"]]
        profile["issues"]["unspecified_borough"] = {
            "count": len(unspecified_boroughs),
            "percentage": round((len(unspecified_boroughs) / self.total_records) * 100.0, 2),
            "examples": [
                {"unique_key": r.get("unique_key"), "complaint_type": r.get("complaint_type"), "borough": r.get("borough")}
                for r in unspecified_boroughs[:5]
            ]
        }

        # Issue 4: ZIP Code Inconsistent with Borough
        zip_borough_mismatches = []
        for r in self.records:
            b = (r.get("borough") or "").upper()
            z = str(r.get("incident_zip") or "").strip()
            if len(z) == 5 and z.isdigit() and b in BOROUGH_ZIP_PREFIXES:
                valid_prefixes = BOROUGH_ZIP_PREFIXES[b]
                if not any(z.startswith(p) for p in valid_prefixes):
                    zip_borough_mismatches.append({
                        "unique_key": r.get("unique_key"),
                        "borough": b,
                        "incident_zip": z,
                        "expected_prefixes": valid_prefixes
                    })

        profile["issues"]["zip_borough_inconsistency"] = {
            "count": len(zip_borough_mismatches),
            "percentage": round((len(zip_borough_mismatches) / self.total_records) * 100.0, 3),
            "examples": zip_borough_mismatches[:5]
        }

        # Issue 5: Coordinates Missing or Outside NYC Bounding Box
        geo_anomalies = []
        for r in self.records:
            lat = r.get("latitude")
            lon = r.get("longitude")
            if lat and lon:
                try:
                    f_lat = float(lat)
                    f_lon = float(lon)
                    # Check if coordinates are outside NYC box or swapped
                    is_outside = not (NYC_BOUNDS["lat_min"] <= f_lat <= NYC_BOUNDS["lat_max"] and
                                     NYC_BOUNDS["lon_min"] <= f_lon <= NYC_BOUNDS["lon_max"])
                    if is_outside:
                        geo_anomalies.append({
                            "unique_key": r.get("unique_key"),
                            "latitude": f_lat,
                            "longitude": f_lon,
                            "anomaly": "Out of NYC bounds or inverted"
                        })
                except ValueError:
                    geo_anomalies.append({
                        "unique_key": r.get("unique_key"),
                        "latitude": lat,
                        "longitude": lon,
                        "anomaly": "Non-numeric coordinate string"
                    })

        profile["issues"]["geo_coordinate_anomalies"] = {
            "count": len(geo_anomalies),
            "percentage": round((len(geo_anomalies) / self.total_records) * 100.0, 3),
            "examples": geo_anomalies[:5]
        }

        # Issue 6: PII in Free-Text Fields (Phone Numbers & Email Addresses)
        phone_regex = re.compile(r"\b(?:\+?1[-.]?)?\(?[2-9]\d{2}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")
        email_regex = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")
        pii_leaks = []
        for r in self.records:
            combined_text = f"{r.get('descriptor', '')} {r.get('resolution_description', '')}"
            phone_matches = phone_regex.findall(combined_text)
            email_matches = email_regex.findall(combined_text)
            if phone_matches or email_matches:
                pii_leaks.append({
                    "unique_key": r.get("unique_key"),
                    "agency": r.get("agency"),
                    "phones_found": phone_matches,
                    "emails_found": email_matches,
                    "text_snippet": combined_text[:120]
                })

        profile["issues"]["pii_in_free_text"] = {
            "count": len(pii_leaks),
            "percentage": round((len(pii_leaks) / self.total_records) * 100.0, 3),
            "examples": pii_leaks[:5]
        }

        # Issue 7: Resolution Description Contradicting Status
        # e.g. status == "Closed" but text indicates pending/in-progress
        status_contradictions = []
        pending_keywords = ["pending inspection", "in progress", "has been scheduled for", "under investigation", "assigned to", "will be inspected"]
        for r in self.records:
            st = (r.get("status") or "").strip().lower()
            res_desc = (r.get("resolution_description") or "").lower()
            if st == "closed":
                if any(kw in res_desc for kw in pending_keywords):
                    status_contradictions.append({
                        "unique_key": r.get("unique_key"),
                        "status": r.get("status"),
                        "resolution_description": r.get("resolution_description")[:140]
                    })

        profile["issues"]["status_resolution_contradiction"] = {
            "count": len(status_contradictions),
            "percentage": round((len(status_contradictions) / self.total_records) * 100.0, 3),
            "examples": status_contradictions[:5]
        }

        # Issue 8: Exact and Near Duplicates
        seen_keys = set()
        exact_dups = 0
        for r in self.records:
            k = r.get("unique_key")
            if k in seen_keys:
                exact_dups += 1
            else:
                seen_keys.add(k)

        profile["issues"]["exact_duplicates"] = {
            "count": exact_dups,
            "percentage": round((exact_dups / self.total_records) * 100.0, 4)
        }

        return profile


def print_profile_report(profile: Dict[str, Any]):
    print("="*80)
    print("NYC 311 2023 RAW DATA QUALITY PROFILE REPORT")
    print("="*80)
    print(f"Total Records Analyzed: {profile['total_records']:,}")
    print(f"Total Columns: {len(profile['columns'])}\n")
    
    print("--- 1. Missing Critical Fields ---")
    for field, pct in profile["issues"]["missing_fields"]["percentages"].items():
        cnt = profile["issues"]["missing_fields"]["counts"][field]
        print(f"  • {field:<24}: {cnt:>5} nulls ({pct:>6.2f}%)")

    print("\n--- 2. Real Quality Deficiencies Discovered in Raw 2023 Data ---")
    for issue_key, data in profile["issues"].items():
        if issue_key == "missing_fields":
            continue
        cnt = data.get("count", 0)
        pct = data.get("percentage", 0.0)
        title = issue_key.replace("_", " ").title()
        print(f"\n[Issue: {title}]")
        print(f"  Count: {cnt:,} occurrences ({pct}%)")
        examples = data.get("examples", [])
        if examples:
            print("  Concrete Raw Data Examples:")
            for ex in examples[:2]:
                print(f"    - {ex}")
    print("="*80)


if __name__ == "__main__":
    data_file = Path(__file__).resolve().parent / "data" / "nyc311_sample_2023.json"
    if not data_file.exists():
        print(f"Error: {data_file} not found. Run download_data.py first.")
    else:
        profiler = NYC311Profiler(data_file)
        results = profiler.run_profiling()
        print_profile_report(results)
        # Save output
        with open(Path(__file__).resolve().parent / "raw_profile_report.json", "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)
