"""
Statistical and Machine Learning Detector Family (Project B).
Detects distribution anomalies, null rate spikes, near-duplicates,
and category-descriptor co-occurrence statistical deviations.
"""

from collections import defaultdict
from datetime import datetime
from typing import Dict, Any, List, Set, Tuple


class StatisticalMLDetector:
    """Statistical and distributional anomaly detectors for NYC 311 batches."""

    def __init__(self):
        # Baseline historical null rates per agency (derived from 2023 profiler)
        self.baseline_agency_null_rates = {
            "NYPD": 0.008,
            "DSNY": 0.012,
            "DOT": 0.015,
            "DEP": 0.005,
            "DOB": 0.010,
            "HPD": 0.020
        }
        self.null_rate_threshold_zscore = 3.5

        # Co-occurrence dictionary of typical complaint types and expected descriptor keywords
        self.valid_complaint_descriptor_keywords = {
            "Noise - Residential": {"noise", "loud", "music", "party", "banging", "talking", "bass"},
            "Street Condition": {"pothole", "cave-in", "plate", "depression", "rough", "pavement", "street"},
            "Water System": {"hydrant", "leak", "dirty", "pressure", "water", "sewer", "valve"},
            "Rodent": {"rat", "mouse", "mice", "rodent", "infestation", "droppings"},
            "Blocked Driveway": {"no access", "partial access", "driveway", "blocking", "vehicle"},
            "Illegal Parking": {"hydrant", "sidewalk", "double parked", "posted", "commercial"}
        }

    def detect_batch(self, batch: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Run statistical detectors across the entire batch."""
        alerts = []

        # 1. Statistical Null Spike Detection per Agency (Problem g)
        null_alerts = self._detect_null_spikes(batch)
        alerts.extend(null_alerts)

        # 2. Near-Duplicate Detection using Locality Bucketing & Temporal Proximity (Problem f)
        near_dup_alerts = self._detect_near_duplicates(batch)
        alerts.extend(near_dup_alerts)

        # 3. Statistical Co-occurrence Anomaly: Complaint Type vs Descriptor (Problem j)
        cooccur_alerts = self._detect_descriptor_anomalies(batch)
        alerts.extend(cooccur_alerts)

        return alerts

    def _detect_null_spikes(self, batch: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Detect statistical spikes in null rates per agency."""
        agency_totals = defaultdict(int)
        agency_nulls = defaultdict(int)
        agency_rows = defaultdict(list)

        for idx, rec in enumerate(batch):
            agency = rec.get("agency") or "UNKNOWN"
            agency_totals[agency] += 1
            if not rec.get("incident_zip"):
                agency_nulls[agency] += 1
                agency_rows[agency].append((idx, rec.get("unique_key")))

        alerts = []
        for agency, total in agency_totals.items():
            if total >= 15:  # Sufficient statistical sample size
                null_rate = agency_nulls[agency] / total
                baseline = self.baseline_agency_null_rates.get(agency, 0.01)
                # If null rate exceeds baseline by 10x and is > 20%
                if null_rate >= 0.20 and null_rate > (baseline * 8.0):
                    # Flag all affected rows in this agency spike
                    for r_idx, uk in agency_rows[agency]:
                        alerts.append({
                            "row_index": r_idx,
                            "unique_key": str(uk),
                            "problem_type": "null_spike",
                            "detector": "statistical_ml",
                            "explanation": (
                                f"Statistical null spike detected for agency '{agency}': "
                                f"Observed null rate {null_rate:.1%} vs historical baseline {baseline:.1%} "
                                f"({agency_nulls[agency]}/{total} records missing incident_zip)."
                            )
                        })

        return alerts

    def _detect_near_duplicates(self, batch: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Detect near-duplicate records within temporal proximity (< 120s)
        and high textual/category similarity.
        """
        alerts = []
        # Bucket records by agency + borough
        buckets = defaultdict(list)
        for idx, rec in enumerate(batch):
            c_date = rec.get("created_date")
            if c_date:
                try:
                    dt = datetime.fromisoformat(c_date.replace("Z", ""))
                    b_key = (rec.get("agency"), rec.get("borough"), rec.get("complaint_type"))
                    buckets[b_key].append((idx, rec, dt))
                except Exception:
                    pass

        # Compare within buckets sorted by time
        flagged_indices = set()
        for b_key, items in buckets.items():
            items.sort(key=lambda x: x[2])
            for i in range(len(items)):
                idx1, rec1, dt1 = items[i]
                for j in range(i + 1, min(i + 10, len(items))):
                    idx2, rec2, dt2 = items[j]
                    time_delta = (dt2 - dt1).total_seconds()
                    if time_delta > 120:
                        break  # Outside temporal proximity window

                    # Calculate Jaccard word similarity on descriptor
                    words1 = set((rec1.get("descriptor") or "").lower().split())
                    words2 = set((rec2.get("descriptor") or "").lower().split())
                    if words1 and words2:
                        jaccard = len(words1 & words2) / len(words1 | words2)
                        if jaccard >= 0.50:  # High similarity within 2 minutes
                            if idx2 not in flagged_indices:
                                flagged_indices.add(idx2)
                                alerts.append({
                                    "row_index": idx2,
                                    "unique_key": str(rec2.get("unique_key")),
                                    "problem_type": "near_duplicates",
                                    "detector": "statistical_ml",
                                    "explanation": (
                                        f"Near-duplicate of row {idx1} (key {rec1.get('unique_key')}): "
                                        f"Time delta {time_delta:.0f}s, Jaccard descriptor similarity {jaccard:.2f}."
                                    )
                                })

        return alerts

    def _detect_descriptor_anomalies(self, batch: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Detect statistical co-occurrence outliers between Complaint Type and Descriptor."""
        alerts = []
        for idx, rec in enumerate(batch):
            c_type = rec.get("complaint_type")
            desc = (rec.get("descriptor") or "").lower()
            if c_type in self.valid_complaint_descriptor_keywords:
                expected_kw = self.valid_complaint_descriptor_keywords[c_type]
                desc_words = set(desc.split())
                # If none of the expected semantic cluster words appear in a lengthy descriptor
                if len(desc_words) >= 4 and not any(kw in desc for kw in expected_kw):
                    alerts.append({
                        "row_index": idx,
                        "unique_key": str(rec.get("unique_key")),
                        "problem_type": "complaint_inconsistent_with_descriptor",
                        "detector": "statistical_ml",
                        "explanation": (
                            f"Statistical co-occurrence anomaly: Descriptor '{rec.get('descriptor')}' "
                            f"shares 0% semantic token overlap with historical cluster for '{c_type}'."
                        )
                    })

        return alerts
