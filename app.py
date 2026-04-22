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
from report_html import build_mckinsey_style_report_html

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
    /* Keep the control panel readable on wide layouts (does not block Streamlit’s collapse control) */
    section[data-testid="stSidebar"] {
        min-width: 18rem !important;
    }
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
"""
)

# ---------------------------------------------------------------------------
# Sidebar inputs (keep this block contiguous so the sidebar paints reliably)
# ---------------------------------------------------------------------------
st.sidebar.markdown("##### Controls")
with st.sidebar.expander("How to use", expanded=False):
    st.markdown(
        """
1. **Data** — Keep the default CSV URL or paste a raw link to your own `interventions`-style file.
2. **Scope** — Choose **Select Region**, then open **Select Interventions** to add or remove programs.
3. **Budget & scenario** — Set **Total budget** and **Scenario** (Base / Optimistic / Pessimistic).
4. **Stress-test** — Move **Sensitivity** sliders (and optional **Moral weights**) to see how scores and allocations shift.
5. **Decide** — Read the main dashboard (metrics, charts, allocation table, policy notes). Use **Download Report** for an HTML brief (includes an appendix table you can copy into a spreadsheet).
"""
    )
st.sidebar.divider()
st.sidebar.header("Inputs")
remote = st.sidebar.text_input(
    "Raw CSV URL (optional)",
    value=os.environ.get("IMPACT_CSV_URL", DEFAULT_REMOTE_CSV),
    help="Defaults to GitHub raw `interventions.csv` once pushed to the repo root.",
)

_effective_url = remote.strip() or DEFAULT_REMOTE_CSV
df0, _ = cached_interventions(_effective_url)

regions = sorted(df0["region"].unique().tolist())
region_pick = st.sidebar.selectbox("Select Region", ["All regions"] + regions)

ids_default = df0["intervention_id"].tolist()
_name_by_id = df0.set_index("intervention_id")["intervention_name"].to_dict()
with st.sidebar.expander("Select Interventions", expanded=False):
    id_pick = st.multiselect(
        "Select Interventions",
        options=ids_default,
        default=ids_default,
        format_func=lambda i: f"{i} — {_name_by_id.get(i, '')}",
        label_visibility="collapsed",
    )

total_budget = st.sidebar.slider("Total budget (USD)", 10_000, 2_000_000, 200_000, step=5_000)

scenario = st.sidebar.selectbox("Scenario", ["Base", "Optimistic", "Pessimistic"], index=0)

st.sidebar.subheader("Sensitivity")
cost_adj = st.sidebar.slider("Cost multiplier (all rows)", 0.5, 2.0, 1.0, 0.05)
effect_adj = st.sidebar.slider("Effectiveness multiplier (effect_size)", 0.5, 1.5, 1.0, 0.05)

with st.sidebar.expander("Moral weights (optional)", expanded=False):
    life_weight = st.slider("Weight: lives / life-saving programs", 0.5, 2.0, 1.0, 0.05)
    income_weight = st.slider("Weight: income gains", 0.0, 1.0, 0.10, 0.02)

malaria_double = st.sidebar.checkbox(
    "Double cost for Malaria Bed Nets (id=1)",
    value=False,
    help="Applies a 2× multiplier to cost only for Malaria Bed Nets when that intervention is in scope.",
)

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

per_row_cost = pd.Series(1.0, index=df.index)
if malaria_double:
    per_row_cost.loc[df["intervention_id"] == 1] = 2.0

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

st.markdown("**Note**")
st.caption(
    "Figures are illustrative; they should be interpreted alongside qualitative judgment, "
    "implementation risk, and partner capacity."
)

report_html = build_mckinsey_style_report_html(
    alloc,
    float(total_budget),
    scenario,
    region_pick,
    cost_adj,
    effect_adj,
)
st.download_button(
    "Download Report",
    data=report_html.encode("utf-8"),
    file_name="impact_allocation_funding_report.html",
    mime="text/html",
    use_container_width=True,
    help="McKinsey-style HTML brief: headline insight, executive summary, findings, and appendix table. Open in a browser or import into Word.",
)
