"""
Load intervention panel from GitHub raw CSV, local bundled CSV, or synthetic fallback.
"""

from __future__ import annotations

import io
import os
from typing import Tuple

import pandas as pd
import requests

# After you push `interventions.csv` to the repo root, this URL resolves.
DEFAULT_REMOTE_CSV = (
    "https://raw.githubusercontent.com/S-ABDUL-AI/IMPACT-ALLOCATION-ENGINE/main/interventions.csv"
)

REQUIRED_COLS = [
    "intervention_id",
    "intervention_name",
    "sector",
    "region",
    "cost_per_beneficiary",
    "cost_per_life_saved",
    "effect_size",
    "evidence_strength",
    "population_affected",
    "baseline_risk",
    "expected_lives_saved",
    "income_increase_per_person",
    "funding_gap",
    "scalability",
    "time_to_impact",
    "uncertainty_level",
]


def _validate(df: pd.DataFrame) -> pd.DataFrame:
    missing = [c for c in REQUIRED_COLS if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns: {missing}")
    out = df[REQUIRED_COLS].copy()
    for c in REQUIRED_COLS:
        if c not in ("intervention_name", "sector", "region"):
            out[c] = pd.to_numeric(out[c], errors="coerce")
    if out[REQUIRED_COLS[4:]].isna().any().any():
        raise ValueError("Non-numeric or null values in numeric columns.")
    return out


def generate_synthetic_data() -> pd.DataFrame:
    """Bundled copy of the sample panel (same rows as interventions.csv)."""
    here = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(here, "interventions.csv")
    return _validate(pd.read_csv(path))


def load_interventions_csv(
    remote_url: str | None = None,
    timeout: int = 25,
) -> Tuple[pd.DataFrame, str]:
    """
    Try remote raw GitHub CSV, then local `interventions.csv`, then identical synthetic.

    Returns (dataframe, provenance_label).
    """
    url = (remote_url or DEFAULT_REMOTE_CSV).strip()
    headers = {
        "User-Agent": "ImpactAllocationEngine/1.0 (+https://github.com/S-ABDUL-AI/IMPACT-ALLOCATION-ENGINE)"
    }

    try:
        r = requests.get(url, headers=headers, timeout=timeout)
        r.raise_for_status()
        df = _validate(pd.read_csv(io.StringIO(r.text)))
        return df, f"Remote CSV ({url})"
    except Exception:
        pass

    here = os.path.dirname(os.path.abspath(__file__))
    local_path = os.path.join(here, "interventions.csv")
    if os.path.exists(local_path):
        df = _validate(pd.read_csv(local_path))
        return df, f"Local bundled CSV ({local_path})"

    return generate_synthetic_data(), "Synthetic fallback (remote and local file unavailable)"
