"""
Cost-effectiveness scoring, moral-weight adjustments, and budget allocation.

Core pipeline (GiveWell-inspired structure, simplified for transparency):
  expected_impact = adjusted_effect * population * baseline_risk
  adjusted_impact = expected_impact * (evidence_strength / 5)
  cost_effectiveness = adjusted_impact / (adjusted_cost * population)
  uncertainty_adjusted = cost_effectiveness * (1 - uncertainty_level)
  final_score = uncertainty_adjusted * funding_gap * scalability
  (+ optional moral weights on adjusted_impact)
"""

from __future__ import annotations

from typing import Literal, Optional

import numpy as np
import pandas as pd

Scenario = Literal["Base", "Optimistic", "Pessimistic"]

SCENARIO_EFFECT_MULT = {"Base": 1.0, "Optimistic": 1.5, "Pessimistic": 0.6}


def scenario_effect_multiplier(scenario: Scenario) -> float:
    return float(SCENARIO_EFFECT_MULT[scenario])


def calculate_scores(
    df: pd.DataFrame,
    cost_adj: float = 1.0,
    effect_adj: float = 1.0,
    scenario: Scenario = "Base",
    life_weight: float = 1.0,
    income_weight: float = 0.1,
    per_row_cost_mult: Optional[pd.Series] = None,
) -> pd.DataFrame:
    """
    Compute intermediate columns and final_score on a **copy** of df.

    per_row_cost_mult: optional Series aligned to df.index (e.g. 2.0 for malaria only).
    """
    out = df.copy()
    scen = scenario_effect_multiplier(scenario)

    out["adjusted_effect_size"] = out["effect_size"] * float(effect_adj) * scen
    out["adjusted_cost"] = out["cost_per_beneficiary"].astype(float) * float(cost_adj)
    if per_row_cost_mult is not None:
        out["adjusted_cost"] = out["adjusted_cost"] * per_row_cost_mult.reindex(out.index).fillna(1.0)

    out["expected_impact"] = (
        out["adjusted_effect_size"] * out["population_affected"].astype(float) * out["baseline_risk"].astype(float)
    )

    out["adjusted_impact"] = out["expected_impact"] * (out["evidence_strength"].astype(float) / 5.0)

    # Moral weights (simple, transparent): emphasize life-saving rows and income gains.
    lives_mask = out["expected_lives_saved"].astype(float) > 0
    income_norm = (out["income_increase_per_person"].astype(float) / 1000.0).clip(lower=0.0)
    moral_mult = np.where(
        lives_mask,
        float(life_weight) * (1.0 + float(income_weight) * income_norm * 0.25),
        1.0 + float(income_weight) * income_norm,
    )
    out["adjusted_impact"] = out["adjusted_impact"] * moral_mult

    denom = out["adjusted_cost"] * out["population_affected"].astype(float)
    out["cost_effectiveness"] = np.where(denom > 0, out["adjusted_impact"] / denom, 0.0)

    u = out["uncertainty_level"].astype(float).clip(0.0, 0.95)
    out["uncertainty_adjusted"] = out["cost_effectiveness"] * (1.0 - u)

    out["final_score"] = (
        out["uncertainty_adjusted"] * out["funding_gap"].astype(float) * out["scalability"].astype(float)
    )
    out["final_score"] = out["final_score"].clip(lower=0.0)

    return out


def allocate_budget(df: pd.DataFrame, total_budget: float) -> pd.DataFrame:
    """Proportional allocation by final_score; equal split if scores sum to zero."""
    out = df.copy()
    s = float(out["final_score"].sum())
    if s <= 0 or total_budget <= 0:
        n = max(len(out), 1)
        out["allocation"] = float(total_budget) / n
        return out
    out["allocation"] = (out["final_score"] / s) * float(total_budget)
    return out


def compare_budget_scale(df_scored: pd.DataFrame, base_budget: float, scale: float) -> pd.DataFrame:
    """Return side-by-side allocation for base vs scaled budget (same scores)."""
    a1 = allocate_budget(df_scored, base_budget)
    a2 = allocate_budget(df_scored, base_budget * scale)
    cmp = a1[["intervention_name", "final_score"]].copy()
    cmp["allocation_base"] = a1["allocation"].values
    cmp["allocation_scaled"] = a2["allocation"].values
    cmp["delta_usd"] = cmp["allocation_scaled"] - cmp["allocation_base"]
    return cmp
