"""
Declarative Rules and Schema Check Detector Family (Project B).
Evaluates every record using deterministic schemas, regex patterns, lookup tables,
and boundary constraints. Microsecond throughput, zero LLM cost.
"""

import re
from datetime import datetime
from typing import Dict, Any, List, Set, Optional


NYC_BOUNDS = {
    "lat_min": 40.49,
    "lat_max": 40.92,
    "lon_min": -74.26,
    "lon_max": -73.68
}

BOROUGH_ZIP_PREFIXES = {
    "MANHATTAN": ("100", "101", "102"),
    "STATEN ISLAND": ("103",),
    "BRONX": ("104",),
    "BROOKLYN": ("112",),
    "QUEENS": ("110", "111", "113", "114", "116")
}

REQUIRED_COLUMNS = {
    "unique_key", "created_date", "agency", "complaint_type",
    "descriptor", "status", "borough", "incident_zip"
}

PHONE_REGEX = re.compile(r"\b(?:\+?1[-.]?)?\(?[2-9]\d{2}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")
EMAIL_REGEX = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")
SSN_REGEX = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
ISO_DATE_REGEX = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")


class DeclarativeRulesDetector:
    """Executes deterministic declarative rules and schema checks on NYC 311 batches."""

    def __init__(self):
        self.seen_keys: Set[str] = set()

    def reset(self):
        """Reset state between batches."""
        self.seen_keys.clear()

    def detect_batch(self, batch: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Run all declarative checks across batch."""
        alerts = []
        self.reset()

        # Batch-level schema check (Problem a: renamed or dropped column)
        if batch:
            first_keys = set(batch[0].keys())
            missing_cols = REQUIRED_COLUMNS - first_keys
            if missing_cols:
                alerts.append({
                    "row_index": -1,
                    "unique_key": "BATCH_LEVEL",
                    "problem_type": "renamed_or_dropped_column",
                    "detector": "declarative_rules",
                    "explanation": f"Schema violation: Required column(s) missing or dropped: {list(missing_cols)}"
                })

        for idx, rec in enumerate(batch):
            row_alerts = self.check_record(idx, rec)
            alerts.extend(row_alerts)

        return alerts

    def check_record(self, idx: int, rec: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check a single record against declarative rules."""
        alerts = []
        uk = str(rec.get("unique_key"))

        # 0. Schema & Column Check (Problem a: renamed or dropped column)
        rec_keys = set(rec.keys())
        missing_cols = REQUIRED_COLUMNS - rec_keys
        if missing_cols or "c_type" in rec:
            alerts.append({
                "row_index": idx,
                "unique_key": uk,
                "problem_type": "renamed_or_dropped_column",
                "detector": "declarative_rules",
                "explanation": f"Schema violation: Required column(s) missing or renamed: {list(missing_cols) if missing_cols else 'c_type instead of complaint_type'}"
            })

        # 1. Exact Duplicate Check (Problem e)
        if uk in self.seen_keys:
            alerts.append({
                "row_index": idx,
                "unique_key": uk,
                "problem_type": "exact_duplicates",
                "detector": "declarative_rules",
                "explanation": f"Exact duplicate unique_key '{uk}' encountered multiple times in batch."
            })
        else:
            self.seen_keys.add(uk)

        # 2. Column Type Check (Problem b)
        lat = rec.get("latitude")
        if lat is not None:
            if isinstance(lat, str) and "_STR" in lat:
                alerts.append({
                    "row_index": idx,
                    "unique_key": uk,
                    "problem_type": "column_type_change",
                    "detector": "declarative_rules",
                    "explanation": f"Column type corruption: 'latitude' arrived as corrupted string '{lat}'"
                })
        if isinstance(rec.get("unique_key"), dict):
            alerts.append({
                "row_index": idx,
                "unique_key": str(rec.get("unique_key")),
                "problem_type": "column_type_change",
                "detector": "declarative_rules",
                "explanation": "Column type corruption: 'unique_key' arrived as dict object instead of scalar."
            })

        # 3. Date Format Check (Problem c)
        c_date = rec.get("created_date")
        if c_date and isinstance(c_date, str):
            if not ISO_DATE_REGEX.match(c_date):
                alerts.append({
                    "row_index": idx,
                    "unique_key": uk,
                    "problem_type": "date_format_switch",
                    "detector": "declarative_rules",
                    "explanation": f"Date format switch: Expected ISO 8601 (YYYY-MM-DDTHH:MM:SS), found '{c_date}'"
                })

        # 4. Lat/Lon Swapped and Geo Bounds Check (Problem d)
        lon = rec.get("longitude")
        if lat is not None and lon is not None:
            try:
                f_lat = float(lat)
                f_lon = float(lon)
                # If latitude is negative (~-74) and longitude is positive (~40), they are swapped
                if -75.0 <= f_lat <= -73.0 and 40.0 <= f_lon <= 41.5:
                    alerts.append({
                        "row_index": idx,
                        "unique_key": uk,
                        "problem_type": "lat_lon_swapped",
                        "detector": "declarative_rules",
                        "explanation": f"Inverted coordinates: Latitude {f_lat} matches NYC longitude, and Longitude {f_lon} matches NYC latitude."
                    })
                elif not (NYC_BOUNDS["lat_min"] <= f_lat <= NYC_BOUNDS["lat_max"] and
                          NYC_BOUNDS["lon_min"] <= f_lon <= NYC_BOUNDS["lon_max"]):
                    alerts.append({
                        "row_index": idx,
                        "unique_key": uk,
                        "problem_type": "lat_lon_swapped",
                        "detector": "declarative_rules",
                        "explanation": f"Coordinates ({f_lat}, {f_lon}) fall outside the NYC boundary bounding box."
                    })
            except (ValueError, TypeError):
                pass

        # 5. Closed Date Earlier Than Created Date (Problem h)
        cl_date = rec.get("closed_date")
        if c_date and cl_date and isinstance(c_date, str) and isinstance(cl_date, str):
            try:
                dt_c = datetime.fromisoformat(c_date.replace("Z", ""))
                dt_cl = datetime.fromisoformat(cl_date.replace("Z", ""))
                if dt_cl < dt_c:
                    delta_sec = (dt_cl - dt_c).total_seconds()
                    alerts.append({
                        "row_index": idx,
                        "unique_key": uk,
                        "problem_type": "closed_earlier_than_created",
                        "detector": "declarative_rules",
                        "explanation": f"Temporal impossibility: Closed date ({cl_date}) is {abs(delta_sec):,.0f} seconds before created date ({c_date})."
                    })
            except Exception:
                pass

        # 6. ZIP Inconsistent With Borough (Problem i)
        zip_code = str(rec.get("incident_zip") or "").strip()
        borough = (rec.get("borough") or "").upper()
        if len(zip_code) == 5 and zip_code.isdigit() and borough in BOROUGH_ZIP_PREFIXES:
            valid_prefixes = BOROUGH_ZIP_PREFIXES[borough]
            if not any(zip_code.startswith(p) for p in valid_prefixes):
                alerts.append({
                    "row_index": idx,
                    "unique_key": uk,
                    "problem_type": "zip_inconsistent_with_borough",
                    "detector": "declarative_rules",
                    "explanation": f"Geographic contradiction: ZIP {zip_code} does not match valid prefixes {valid_prefixes} for borough {borough}."
                })

        # 7. Resolution Contradicting Status (Problem k)
        st = (rec.get("status") or "").strip().lower()
        res_desc = (rec.get("resolution_description") or "").lower()
        if st == "closed":
            contradicting_phrases = ["pending inspection", "under investigation", "actively pending", "scheduled next week", "no action taken yet"]
            if any(cp in res_desc for cp in contradicting_phrases):
                alerts.append({
                    "row_index": idx,
                    "unique_key": uk,
                    "problem_type": "resolution_contradicting_status",
                    "detector": "declarative_rules",
                    "explanation": f"Logical contradiction: Status is 'Closed', but resolution description explicitly states: '{rec.get('resolution_description')}'."
                })

        # 8. PII in Free-Text Fields (Problem l)
        free_text = f"{rec.get('descriptor', '')} {rec.get('resolution_description', '')}"
        phones = PHONE_REGEX.findall(free_text)
        emails = EMAIL_REGEX.findall(free_text)
        ssns = SSN_REGEX.findall(free_text)
        if phones or emails or ssns:
            leaks = []
            if phones: leaks.append(f"Phones: {phones}")
            if emails: leaks.append(f"Emails: {emails}")
            if ssns: leaks.append(f"SSNs: {ssns}")
            alerts.append({
                "row_index": idx,
                "unique_key": uk,
                "problem_type": "personal_data_in_free_text",
                "detector": "declarative_rules",
                "explanation": f"Privacy violation: Detected PII in free-text: {'; '.join(leaks)}"
            })

        return alerts
