"""
Impact Allocation Engine (GiveWell-style) — Streamlit entrypoint.

Evidence-leaning cost-effectiveness with explicit uncertainty and scenario controls.
"""

from __future__ import annotations

import os

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from data_loader import DEFAULT_REMOTE_CSV, load_interventions_csv
from modeling import allocate_budget, calculate_scores, compare_budget_scale, scenario_effect_multiplier
from policy import allocation_insights, funding_brief_markdown

st.set_page_config(
    page_title="Impact Allocation Engine",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
    .block-container { padding-top: 1rem !important; }
    div[data-testid="stMetricValue"] { font-weight: 700 !important; }
</style>
""",
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner=False)
def cached_interventions(remote_url: str) -> tuple:
    """Cache CSV load so reruns do not refetch constantly."""
    df, src = load_interventions_csv(remote_url=remote_url or None)
    return df, src


st.title("Impact Allocation Engine (GiveWell-style)")
st.markdown(
    """
### Methodology

This tool applies **cost-effectiveness logic**, **explicit uncertainty discounts**, and **scenario analysis**
to approximate how a funder might allocate a fixed budget across interventions.

It is **inspired by** evidence-first approaches in global health and development (for example, the transparency
goals behind organizations like [GiveWell](https://www.givewell.org/)), but it is **not** an official GiveWell model
and should not be treated as their published cost-effectiveness estimates.

**Repository:** [IMPACT-ALLOCATION-ENGINE](https://github.com/S-ABDUL-AI/IMPACT-ALLOCATION-ENGINE)
"""
)

# ---------------------------------------------------------------------------
# Sidebar inputs
# ---------------------------------------------------------------------------
st.sidebar.header("Inputs")
remote = st.sidebar.text_input(
    "Raw CSV URL (optional)",
    value=os.environ.get("IMPACT_CSV_URL", DEFAULT_REMOTE_CSV),
    help="Defaults to GitHub raw `interventions.csv` once pushed to the repo root.",
)

_effective_url = remote.strip() or DEFAULT_REMOTE_CSV
df0, data_src = cached_interventions(_effective_url)

regions = sorted(df0["region"].unique().tolist())
region_pick = st.sidebar.selectbox("Region", ["All regions"] + regions)

ids_default = df0["intervention_id"].tolist()
_name_by_id = df0.set_index("intervention_id")["intervention_name"].to_dict()
id_pick = st.sidebar.multiselect(
    "Interventions",
    options=ids_default,
    default=ids_default,
    format_func=lambda i: f"{i} — {_name_by_id.get(i, '')}",
)

total_budget = st.sidebar.slider("Total budget (USD)", 10_000, 2_000_000, 200_000, step=5_000)

scenario = st.sidebar.selectbox("Scenario", ["Base", "Optimistic", "Pessimistic"], index=0)

st.sidebar.subheader("Sensitivity")
cost_adj = st.sidebar.slider("Cost multiplier (all rows)", 0.5, 2.0, 1.0, 0.05)
effect_adj = st.sidebar.slider("Effectiveness multiplier (effect_size)", 0.5, 1.5, 1.0, 0.05)

with st.sidebar.expander("Moral weights (optional)", expanded=False):
    life_weight = st.slider("Weight: lives / life-saving programs", 0.5, 2.0, 1.0, 0.05)
    income_weight = st.slider("Weight: income gains", 0.0, 1.0, 0.10, 0.02)

st.sidebar.divider()
st.sidebar.caption("**Developed by:** Sherriff Abdul-Hamid")

# ---------------------------------------------------------------------------
# Filter + score
# ---------------------------------------------------------------------------
df = df0[df0["intervention_id"].isin(id_pick)].copy()
if region_pick != "All regions":
    df = df[df["region"] == region_pick].copy()

if df.empty:
    st.warning("No rows after filters — broaden region or select interventions.")
    st.stop()

st.success(f"Data source: **{data_src}**")

per_row_cost = pd.Series(1.0, index=df.index)
if st.sidebar.button("What if malaria cost doubles?", help="Doubles cost for Malaria Bed Nets (id=1) only."):
    mask = df["intervention_id"] == 1
    per_row_cost.loc[mask] = 2.0

scored = calculate_scores(
    df,
    cost_adj=cost_adj,
    effect_adj=effect_adj,
    scenario=scenario,  # type: ignore[arg-type]
    life_weight=life_weight,
    income_weight=income_weight,
    per_row_cost_mult=per_row_cost,
)
alloc = allocate_budget(scored, total_budget)

# ---------------------------------------------------------------------------
# Executive metrics
# ---------------------------------------------------------------------------
m1, m2, m3, m4 = st.columns(4)
with m1:
    st.metric("Interventions in scope", len(alloc))
with m2:
    st.metric("Scenario effect multiplier", f"{scenario_effect_multiplier(scenario):.2f}×")
with m3:
    st.metric("Total allocation", f"${alloc['allocation'].sum():,.0f}")
with m4:
    top_name = alloc.sort_values("final_score", ascending=False).iloc[0]["intervention_name"]
    st.metric("Top ranked", top_name[:28] + ("…" if len(top_name) > 28 else ""))

# ---------------------------------------------------------------------------
# What-if strips
# ---------------------------------------------------------------------------
st.subheader("What-if analyses")
w1, w2 = st.columns(2)
with w1:
    st.markdown("**What happens if budget increases by 50%?**")
    cmp_budget = compare_budget_scale(scored, float(total_budget), 1.5)
    st.dataframe(cmp_budget, use_container_width=True, height=220)
with w2:
    st.markdown("**Sensitivity snapshot (current sliders)**")
    st.dataframe(
        alloc[
            [
                "intervention_name",
                "adjusted_effect_size",
                "adjusted_cost",
                "expected_impact",
                "cost_effectiveness",
                "uncertainty_adjusted",
                "final_score",
                "allocation",
            ]
        ].round(6),
        use_container_width=True,
        height=260,
    )

# ---------------------------------------------------------------------------
# Charts
# ---------------------------------------------------------------------------
c1, c2 = st.columns(2)
with c1:
    st.subheader("Allocation (USD)")
    plot_df = alloc.sort_values("allocation", ascending=True)
    fig, ax = plt.subplots(figsize=(6.5, 3.8))
    ax.barh(plot_df["intervention_name"], plot_df["allocation"], color="#0B5D53")
    ax.set_xlabel("Allocated USD")
    fig.tight_layout()
    st.pyplot(fig, use_container_width=True)
    plt.close(fig)

with c2:
    st.subheader("Final score ranking")
    rnk = alloc.sort_values("final_score", ascending=False)
    fig2, ax2 = plt.subplots(figsize=(6.5, 3.8))
    ax2.barh(rnk["intervention_name"], rnk["final_score"], color="#1D4ED8")
    ax2.set_xlabel("Final score")
    fig2.tight_layout()
    st.pyplot(fig2, use_container_width=True)
    plt.close(fig2)

# ---------------------------------------------------------------------------
# Tables + policy
# ---------------------------------------------------------------------------
st.subheader("Allocation table")
show_cols = [
    "intervention_name",
    "region",
    "final_score",
    "allocation",
    "funding_gap",
    "scalability",
    "evidence_strength",
    "uncertainty_level",
]
st.dataframe(alloc[show_cols].sort_values("final_score", ascending=False), use_container_width=True, height=280)

st.subheader("Policy insights (why these allocations)")
for b in allocation_insights(alloc):
    st.markdown(f"- {b}")

st.markdown("## Funding recommendation report")
st.markdown(funding_brief_markdown(alloc, total_budget, scenario))

st.download_button(
    "Download scored table (CSV)",
    data=alloc.to_csv(index=False).encode("utf-8"),
    file_name="impact_allocation_scored.csv",
    mime="text/csv",
    use_container_width=True,
)
