"""
Corruption Injector for NYC 311 Service Requests.
Task 2: Inject each of the 12 specified problem types into clean batches at a controlled rate,
producing annotated ground truth for detector evaluation.
"""

import copy
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple


class CorruptionInjector:
    """Injects 12 synthetic corruption patterns into NYC 311 data batches."""

    def __init__(self, seed: int = 42):
        random.seed(seed)

    def inject(self, clean_batch: List[Dict[str, Any]], problem_type: str, rate: float = 0.05) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Injects a specific problem type into a clean batch at the specified rate.
        Returns:
          corrupted_batch: List of records with corruptions applied
          ground_truth: List of annotations containing record index, key, and corruption type
        """
        data = copy.deepcopy(clean_batch)
        n = len(data)
        corrupted_indices = sorted(random.sample(range(n), max(1, int(n * rate))))
        ground_truth = []

        if problem_type == "renamed_or_dropped_column":
            # Problem a: Rename 'complaint_type' to 'c_type' or drop 'incident_zip'
            drop_col = "incident_zip"
            rename_col = ("complaint_type", "c_type")
            for idx in corrupted_indices:
                rec = data[idx]
                if drop_col in rec:
                    del rec[drop_col]
                if rename_col[0] in rec:
                    rec[rename_col[1]] = rec.pop(rename_col[0])
                ground_truth.append({
                    "row_index": idx,
                    "unique_key": rec.get("unique_key"),
                    "problem_type": "renamed_or_dropped_column",
                    "details": f"Dropped {drop_col}, renamed {rename_col[0]} -> {rename_col[1]}"
                })

        elif problem_type == "column_type_change":
            # Problem b: Numbers arriving as strings, or floats as unparsed objects
            for idx in corrupted_indices:
                rec = data[idx]
                if "latitude" in rec and rec["latitude"]:
                    rec["latitude"] = str(rec["latitude"]) + "_STR"
                if "unique_key" in rec:
                    rec["unique_key"] = {"raw_id": rec["unique_key"]}
                ground_truth.append({
                    "row_index": idx,
                    "unique_key": str(rec.get("unique_key")),
                    "problem_type": "column_type_change",
                    "details": "latitude corrupted to string with suffix, unique_key boxed into dict"
                })

        elif problem_type == "date_format_switch":
            # Problem c: Date format switch partway through batch (ISO -> MM/DD/YYYY hh:mm:ss AM/PM)
            switch_point = n // 2
            corrupted_indices = list(range(switch_point, n))
            for idx in corrupted_indices:
                rec = data[idx]
                c_date = rec.get("created_date")
                if c_date:
                    try:
                        dt = datetime.fromisoformat(c_date.replace("Z", ""))
                        rec["created_date"] = dt.strftime("%m/%d/%Y %I:%M:%S %p")
                        ground_truth.append({
                            "row_index": idx,
                            "unique_key": rec.get("unique_key"),
                            "problem_type": "date_format_switch",
                            "details": f"Switched ISO to US date string: {rec['created_date']}"
                        })
                    except Exception:
                        pass

        elif problem_type == "lat_lon_swapped":
            # Problem d: Latitude and longitude swapped
            for idx in corrupted_indices:
                rec = data[idx]
                if rec.get("latitude") and rec.get("longitude"):
                    lat = rec["latitude"]
                    lon = rec["longitude"]
                    rec["latitude"] = lon
                    rec["longitude"] = lat
                    ground_truth.append({
                        "row_index": idx,
                        "unique_key": rec.get("unique_key"),
                        "problem_type": "lat_lon_swapped",
                        "details": f"Swapped lat ({lat}) with lon ({lon})"
                    })

        elif problem_type == "exact_duplicates":
            # Problem e: Exact duplicates (clone existing records)
            dup_records = []
            for idx in corrupted_indices:
                rec_copy = copy.deepcopy(data[idx])
                dup_records.append(rec_copy)
                ground_truth.append({
                    "row_index": len(data) + len(dup_records) - 1,
                    "unique_key": rec_copy.get("unique_key"),
                    "problem_type": "exact_duplicates",
                    "details": f"Exact copy of row {idx} (key: {rec_copy.get('unique_key')})"
                })
            data.extend(dup_records)

        elif problem_type == "near_duplicates":
            # Problem f: Near-duplicates (same request, slightly altered timestamp or minor text typo)
            near_dup_records = []
            for idx in corrupted_indices:
                rec_copy = copy.deepcopy(data[idx])
                # Shift created_date by 45 seconds
                c_date = rec_copy.get("created_date")
                if c_date:
                    try:
                        dt = datetime.fromisoformat(c_date.replace("Z", ""))
                        rec_copy["created_date"] = (dt + timedelta(seconds=45)).isoformat()
                    except Exception:
                        pass
                # Slight modification in descriptor
                rec_copy["descriptor"] = (rec_copy.get("descriptor") or "") + " (urgent follow-up)"
                rec_copy["unique_key"] = str(int(rec_copy.get("unique_key", 10000000)) + 999999)
                near_dup_records.append(rec_copy)
                ground_truth.append({
                    "row_index": len(data) + len(near_dup_records) - 1,
                    "unique_key": rec_copy.get("unique_key"),
                    "problem_type": "near_duplicates",
                    "details": f"Near duplicate of row {idx} with timestamp shifted by 45s"
                })
            data.extend(near_dup_records)

        elif problem_type == "null_spike":
            # Problem g: Null spike in one agency's records (e.g. NYPD suddenly missing incident_zip)
            target_agency = "NYPD"
            spike_indices = [i for i, r in enumerate(data) if r.get("agency") == target_agency]
            corrupted_subset = random.sample(spike_indices, min(len(spike_indices), int(len(spike_indices) * 0.85)))
            for idx in corrupted_subset:
                data[idx]["incident_zip"] = None
                ground_truth.append({
                    "row_index": idx,
                    "unique_key": data[idx].get("unique_key"),
                    "problem_type": "null_spike",
                    "details": f"Injected null incident_zip for agency {target_agency}"
                })

        elif problem_type == "closed_earlier_than_created":
            # Problem h: Closed date earlier than created date
            for idx in corrupted_indices:
                rec = data[idx]
                c_date = rec.get("created_date")
                if c_date:
                    try:
                        dt = datetime.fromisoformat(c_date.replace("Z", ""))
                        rec["closed_date"] = (dt - timedelta(hours=3)).isoformat()
                        rec["status"] = "Closed"
                        ground_truth.append({
                            "row_index": idx,
                            "unique_key": rec.get("unique_key"),
                            "problem_type": "closed_earlier_than_created",
                            "details": f"Closed date ({rec['closed_date']}) is 3 hours before created date ({c_date})"
                        })
                    except Exception:
                        pass

        elif problem_type == "zip_inconsistent_with_borough":
            # Problem i: ZIP code inconsistent with borough
            # E.g. Manhattan record assigned Brooklyn zip 11201 or Bronx zip 10451
            mismatches = {"MANHATTAN": "11201", "BROOKLYN": "10001", "QUEENS": "10451", "BRONX": "11101", "STATEN ISLAND": "10025"}
            for idx in corrupted_indices:
                rec = data[idx]
                borough = (rec.get("borough") or "MANHATTAN").upper()
                alien_zip = mismatches.get(borough, "11201")
                rec["incident_zip"] = alien_zip
                ground_truth.append({
                    "row_index": idx,
                    "unique_key": rec.get("unique_key"),
                    "problem_type": "zip_inconsistent_with_borough",
                    "details": f"Assigned alien ZIP {alien_zip} to borough {borough}"
                })

        elif problem_type == "complaint_inconsistent_with_descriptor":
            # Problem j: Complaint Type inconsistent with Descriptor
            # E.g. Noise - Residential paired with Pothole or Sewer Backup
            mismatched_descriptors = [
                ("Noise - Residential", "Pothole in roadway near pedestrian crosswalk"),
                ("Street Condition", "Loud music / party coming from apartment 4B"),
                ("Water System", "Feral cat colony in abandoned garage"),
                ("Rodent", "Illegal parking blocking commercial fire hydrant")
            ]
            for idx in corrupted_indices:
                rec = data[idx]
                c_type, desc = random.choice(mismatched_descriptors)
                rec["complaint_type"] = c_type
                rec["descriptor"] = desc
                ground_truth.append({
                    "row_index": idx,
                    "unique_key": rec.get("unique_key"),
                    "problem_type": "complaint_inconsistent_with_descriptor",
                    "details": f"Semantic mismatch: Complaint Type '{c_type}' with Descriptor '{desc}'"
                })

        elif problem_type == "resolution_contradicting_status":
            # Problem k: Resolution Description contradicting Status
            contradicting_resolutions = [
                "The complaint has been forwarded to the local precinct and is actively pending inspection.",
                "Case is open and under investigation by city engineers. No action taken yet.",
                "Assigned to field team for emergency repair scheduled next week."
            ]
            for idx in corrupted_indices:
                rec = data[idx]
                rec["status"] = "Closed"
                rec["resolution_description"] = random.choice(contradicting_resolutions)
                ground_truth.append({
                    "row_index": idx,
                    "unique_key": rec.get("unique_key"),
                    "problem_type": "resolution_contradicting_status",
                    "details": f"Status is 'Closed' but resolution states: '{rec['resolution_description']}'"
                })

        elif problem_type == "personal_data_in_free_text":
            # Problem l: Personal data (phone numbers, emails, full personal names) inside free-text
            pii_templates = [
                "Caller John Doe requested callback at 212-555-0149 regarding severe leak.",
                "Complainant email is sarah.connor92@gmail.com; please send case updates there.",
                "Property owner Robert Smith (SSN: 042-99-1234) refused inspector entry."
            ]
            for idx in corrupted_indices:
                rec = data[idx]
                rec["descriptor"] = (rec.get("descriptor") or "") + " - " + random.choice(pii_templates)
                ground_truth.append({
                    "row_index": idx,
                    "unique_key": rec.get("unique_key"),
                    "problem_type": "personal_data_in_free_text",
                    "details": "Injected phone number, email address, or citizen name into descriptor"
                })

        else:
            raise ValueError(f"Unknown corruption type: {problem_type}")

        return data, ground_truth
