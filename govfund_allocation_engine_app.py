"""
GovFund Allocation Engine
Cost Effectiveness Decision Tool for Public Health Funders
"""

from __future__ import annotations

from datetime import date
import os

import pandas as pd
import plotly.express as px
import streamlit as st

from data_loader import DEFAULT_REMOTE_CSV, load_interventions_csv
from modeling import allocate_budget, calculate_scores, compare_budget_scale
from policy import allocation_insights

try:
    from report_generator import build_report_bytes

    REPORT_AVAILABLE = True
except ImportError:
    REPORT_AVAILABLE = False


# ---------------------------------------------------------------------------
# Design tokens
# ---------------------------------------------------------------------------
NAVY = "#0A1F44"
NAVY_MID = "#152B5C"
GOLD = "#C9A84C"
GOLD_LT = "#E8C97A"
INK = "#1A1A1A"
BODY = "#2C3E50"
MUTED = "#6B7280"
RED = "#C8382A"
AMBER = "#B8560A"
GREEN = "#1A7A2E"
RULE = "#E2E6EC"
OFF_WHITE = "#F8F6F1"


st.set_page_config(
    page_title="GovFund Allocation Engine",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    f"""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');
  html, body, [class*="css"] {{ font-family: 'Inter', sans-serif; background:{OFF_WHITE}; }}
  .hero-wrap {{
    background: linear-gradient(135deg, {NAVY} 0%, {NAVY_MID} 65%, #1E3A6E 100%);
    border-left: 6px solid {GOLD};
    border-radius: 8px;
    padding: 30px 34px 26px;
    margin-bottom: 20px;
  }}
  .hero-eye {{
    font-size: 11px; font-weight: 700; letter-spacing: 2px; color: {GOLD};
    text-transform: uppercase; margin-bottom: 8px;
  }}
  .hero-title {{
    color: #FFFFFF; font-size: 30px; line-height: 1.25; font-weight: 800; margin-bottom: 10px;
  }}
  .hero-sub {{
    color: #CBD5E1; font-size: 14px; line-height: 1.6; max-width: 860px;
  }}
  .scope-box {{
    background: #FFFBF0; border: 1px solid {AMBER}; border-left: 4px solid {AMBER};
    border-radius: 5px; padding: 11px 14px; font-size: 12px; color: {AMBER}; margin-bottom: 16px;
  }}
  .sec-lbl {{
    font-size: 10px; font-weight: 700; letter-spacing: 2px; color: {GOLD};
    text-transform: uppercase; margin-bottom: 4px;
  }}
  .sec-ttl {{
    font-size: 20px; font-weight: 700; color: {NAVY}; margin-bottom: 4px;
  }}
  .sec-sub {{
    font-size: 13px; color: {MUTED}; margin-bottom: 14px;
  }}
  .kpi-card {{
    background: #FFFFFF; border: 1px solid {RULE}; border-top: 3px solid {NAVY};
    border-radius: 5px; padding: 14px 16px; min-height: 112px;
  }}
  .kpi-label {{
    font-size: 11px; font-weight: 700; letter-spacing: 1px; color: {MUTED};
    text-transform: uppercase; margin-bottom: 6px;
  }}
  .kpi-val {{
    font-size: 28px; font-weight: 800; color: {NAVY}; line-height: 1.1;
  }}
  .kpi-delta {{ font-size: 11px; color: {MUTED}; margin-top: 4px; }}
  .brief-risk {{
    background:#FFF5F5; border:1px solid #FFC9C9; border-left:4px solid {RED};
    border-radius:4px; padding:14px 16px;
  }}
  .brief-imp {{
    background:#F0F4FF; border:1px solid #C4D0F5; border-left:4px solid {NAVY};
    border-radius:4px; padding:14px 16px;
  }}
  .brief-act {{
    background:#F0FFF4; border:1px solid #A8D5B5; border-left:4px solid {GREEN};
    border-radius:4px; padding:14px 16px;
  }}
  .brief-head {{
    font-size:10px; font-weight:700; letter-spacing:2px; text-transform:uppercase; margin-bottom:6px;
  }}
  .brief-body {{ font-size:13px; color:{BODY}; line-height:1.6; }}
  .byline {{
    background:{NAVY}; border-radius:4px; padding:18px 24px;
    font-size:12px; color:#B0BFD8; line-height:1.8; margin-top:22px;
  }}
  .byline a {{ color:{GOLD}; text-decoration:none; }}
  .stDownloadButton > button {{
    background:{GOLD} !important; color:{INK} !important; font-weight:700 !important;
  }}
</style>
""",
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner=False)
def cached_interventions(remote_url: str) -> tuple[pd.DataFrame, str]:
    return load_interventions_csv(remote_url=remote_url or None)


def _build_scope_note(data_src: str, region: str, n_rows: int) -> str:
    region_text = region if region != "All regions" else "All regions"
    return (
        f"<strong>Scope note:</strong> Data source is {data_src}. "
        "This malaria CEA engine supports funding decisions but does not replace program diligence, local implementation "
        f"constraints, or governance review. <strong>{n_rows}</strong> interventions in scope · <strong>{region_text}</strong>."
    )


def _policy_brief_cards(alloc: pd.DataFrame, total_budget: float) -> tuple[str, str, str]:
    ranked = alloc.sort_values("final_score", ascending=False)
    top = ranked.iloc[0]
    high_uncert = int((alloc["uncertainty_level"] > 0.25).sum())
    second_name = ranked.iloc[1]["intervention_name"] if len(ranked) > 1 else "None"
    top_share = (
        100.0 * float(top["allocation"]) / float(total_budget) if float(total_budget) > 0 else 0.0
    )
    risk = (
        f"<strong>{high_uncert}</strong> intervention(s) carry elevated uncertainty and can shift ranking under new evidence. "
        f"Current top allocation concentration is <strong>{top_share:.0f}%</strong>."
    )
    implication = (
        f"At <strong>${float(total_budget):,.0f}</strong>, the model channels the largest tranche to "
        f"<strong>{top['intervention_name']}</strong> based on composite score. "
        f"<strong>{second_name}</strong> is the next leverage option for diversification."
    )
    action = (
        "Prioritize the top ranked intervention for immediate funding. Run scenario and sensitivity checks before "
        "final approval and maintain a reserve allocation for second tier interventions when implementation risk rises."
    )
    return risk, implication, action


def run() -> None:
    st.markdown(
        """
<div class="hero-wrap">
  <div class="hero-eye">GovFund Allocation Engine · Malaria CEA Portfolio</div>
  <div class="hero-title">Where should this dollar go?</div>
  <div class="hero-sub">
    A decision tool for GiveWell style analysts, Gates Foundation portfolios, USAID teams, and global health funders
    to compare SMC, ITNs, cash transfers, and adjacent interventions using transparent cost effectiveness assumptions.
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

    with st.sidebar:
        st.markdown("### Portfolio inputs")
        remote = st.text_input(
            "Raw CSV URL (optional)",
            value=os.environ.get("IMPACT_CSV_URL", DEFAULT_REMOTE_CSV),
            help="If blank, the app uses bundled data.",
        )

    df0, data_src = cached_interventions(remote.strip() or DEFAULT_REMOTE_CSV)

    with st.sidebar:
        regions = sorted(df0["region"].unique().tolist())
        region_pick = st.selectbox("Region", ["All regions"] + regions, index=0)
        ids_default = df0["intervention_id"].tolist()
        id_to_name = df0.set_index("intervention_id")["intervention_name"].to_dict()
        id_pick = st.multiselect(
            "Interventions",
            options=ids_default,
            default=ids_default,
            format_func=lambda i: f"{i} — {id_to_name.get(i, '')}",
        )
        st.markdown("---")
        total_budget = st.slider("Total budget (USD)", 10_000, 2_000_000, 250_000, step=10_000)
        scenario = st.selectbox("Scenario", ["Base", "Optimistic", "Pessimistic"], index=0)
        cost_adj = st.slider("Cost multiplier", 0.5, 2.0, 1.0, 0.05)
        effect_adj = st.slider("Effectiveness multiplier", 0.5, 1.5, 1.0, 0.05)
        with st.expander("Moral weights", expanded=False):
            life_weight = st.slider("Life saved weight", 0.5, 2.0, 1.0, 0.05)
            income_weight = st.slider("Income increase weight", 0.0, 1.0, 0.10, 0.02)
        malaria_double = st.checkbox("What if malaria unit cost doubles?", value=False)

    df = df0[df0["intervention_id"].isin(id_pick)].copy()
    if region_pick != "All regions":
        df = df[df["region"] == region_pick].copy()
    if df.empty:
        st.warning("No data rows match current filters.")
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
    alloc = allocate_budget(scored, float(total_budget))

    st.markdown(f'<div class="scope-box">{_build_scope_note(data_src, region_pick, len(alloc))}</div>', unsafe_allow_html=True)

    top = alloc.sort_values("final_score", ascending=False).iloc[0]
    top_share = 100.0 * float(top["allocation"]) / float(total_budget) if float(total_budget) > 0 else 0.0
    scenario_mult = {"Base": 1.0, "Optimistic": 1.5, "Pessimistic": 0.6}[scenario]

    st.markdown('<div class="sec-lbl">Executive Snapshot</div>', unsafe_allow_html=True)
    k1, k2, k3, k4 = st.columns(4)
    kpis = [
        (k1, "Top recommendation", str(top["intervention_name"]), f"{top_share:.0f}% of modeled envelope"),
        (k2, "Total allocation", f"${alloc['allocation'].sum():,.0f}", f"{len(alloc)} interventions in scope"),
        (k3, "Scenario multiplier", f"{scenario_mult:.2f}x", f"{scenario} scenario"),
        (k4, "Strong evidence (4-5)", str(int((alloc['evidence_strength'] >= 4).sum())), "Count of strong evidence rows"),
    ]
    for col, label, value, delta in kpis:
        with col:
            st.markdown(
                f"""
<div class="kpi-card">
  <div class="kpi-label">{label}</div>
  <div class="kpi-val">{value}</div>
  <div class="kpi-delta">{delta}</div>
</div>
""",
                unsafe_allow_html=True,
            )

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="sec-lbl">Policy Brief</div>', unsafe_allow_html=True)
    st.markdown('<div class="sec-ttl">Risk · Implication · Action</div>', unsafe_allow_html=True)
    risk_text, imp_text, action_text = _policy_brief_cards(alloc, float(total_budget))
    b1, b2, b3 = st.columns(3)
    with b1:
        st.markdown(
            f'<div class="brief-risk"><div class="brief-head" style="color:{RED};">Risk</div><div class="brief-body">{risk_text}</div></div>',
            unsafe_allow_html=True,
        )
    with b2:
        st.markdown(
            f'<div class="brief-imp"><div class="brief-head" style="color:{NAVY};">Implication</div><div class="brief-body">{imp_text}</div></div>',
            unsafe_allow_html=True,
        )
    with b3:
        st.markdown(
            f'<div class="brief-act"><div class="brief-head" style="color:{GREEN};">Action</div><div class="brief-body">{action_text}</div></div>',
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown('<div class="sec-lbl">What If Analysis</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**What happens if budget increases by 50 percent?**")
        cmp_budget = compare_budget_scale(scored, float(total_budget), 1.5)
        st.dataframe(cmp_budget.round(4), use_container_width=True, height=250)
    with c2:
        st.markdown("**Sensitivity snapshot**")
        snap = alloc[
            [
                "intervention_name",
                "adjusted_effect_size",
                "adjusted_cost",
                "uncertainty_adjusted",
                "final_score",
                "allocation",
            ]
        ].copy()
        st.dataframe(snap.round(6), use_container_width=True, height=250)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="sec-lbl">Charts</div>', unsafe_allow_html=True)
    ch1, ch2 = st.columns(2)
    with ch1:
        alloc_plot = alloc.sort_values("allocation", ascending=True)
        fig_alloc = px.bar(
            alloc_plot,
            x="allocation",
            y="intervention_name",
            orientation="h",
            title="Allocation by intervention (USD)",
            color_discrete_sequence=[NAVY],
        )
        fig_alloc.update_layout(
            paper_bgcolor="white",
            plot_bgcolor="white",
            margin=dict(t=45, b=20, l=20, r=10),
            xaxis=dict(showgrid=False, zeroline=False, title="USD"),
            yaxis=dict(showgrid=False, zeroline=False, title=""),
            showlegend=False,
        )
        st.plotly_chart(fig_alloc, use_container_width=True)
    with ch2:
        rank_plot = alloc.sort_values("final_score", ascending=True)
        fig_rank = px.bar(
            rank_plot,
            x="final_score",
            y="intervention_name",
            orientation="h",
            title="Final score ranking",
            color_discrete_sequence=[GOLD],
        )
        fig_rank.update_layout(
            paper_bgcolor="white",
            plot_bgcolor="white",
            margin=dict(t=45, b=20, l=20, r=10),
            xaxis=dict(showgrid=False, zeroline=False, title="Score"),
            yaxis=dict(showgrid=False, zeroline=False, title=""),
            showlegend=False,
        )
        st.plotly_chart(fig_rank, use_container_width=True)

    st.markdown('<div class="sec-lbl">Allocation table</div>', unsafe_allow_html=True)
    table_cols = [
        "intervention_name",
        "sector",
        "region",
        "final_score",
        "allocation",
        "funding_gap",
        "scalability",
        "evidence_strength",
        "uncertainty_level",
    ]
    st.dataframe(
        alloc[table_cols].sort_values("final_score", ascending=False).round(5),
        use_container_width=True,
        height=280,
    )

    csv_bytes = alloc.to_csv(index=False).encode("utf-8")
    st.download_button(
        "📥 Download allocation table CSV",
        data=csv_bytes,
        file_name=f"govfund_allocation_panel_{date.today().isoformat()}.csv",
        mime="text/csv",
        use_container_width=True,
    )

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="sec-lbl">Policy insights</div>', unsafe_allow_html=True)
    for line in allocation_insights(alloc):
        st.markdown(f"- {line}")

    st.markdown("---")
    st.markdown('<div class="sec-lbl">Export</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sec-ttl">Download McKinsey style policy report</div><div class="sec-sub">'
        "Generate a board ready memo with executive summary, malaria CEA allocation logic, "
        "risk implication action framing, and chart exhibits."
        "</div>",
        unsafe_allow_html=True,
    )

    if REPORT_AVAILABLE:
        if st.button("📄 Generate Report PDF", type="primary", use_container_width=True):
            with st.spinner("Building your report…"):
                pdf_bytes = build_report_bytes(
                    alloc=alloc,
                    scored=scored,
                    total_budget=float(total_budget),
                    scenario=scenario,
                    region_scope=region_pick,
                    data_source=data_src,
                )
                st.session_state["govfund_report_bytes"] = pdf_bytes
                st.success("Report ready. Use download below.")
        if "govfund_report_bytes" in st.session_state:
            st.download_button(
                "⬇ Download PDF Report",
                data=st.session_state["govfund_report_bytes"],
                file_name=f"govfund_allocation_report_{date.today().isoformat()}.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
    else:
        st.warning("report_generator.py not found. Add it to enable PDF export.")

    st.markdown(
        f"""
<div class="byline">
  <strong style="color:{GOLD};">Built by Sherriff Abdul-Hamid</strong> — Product leader specializing in government digital services,
  safety net benefits delivery, and decision support tools for underserved communities. Former Founder and CEO, Poverty 360
  (25,000 plus beneficiaries served across West Africa). Partnered with Ghana's National Health Insurance Authority to enroll
  1,250 vulnerable women into national health coverage. Directed 200 million plus dollars in resource allocation for USAID, UNDP,
  and UKAID. Obama Foundation Leaders Award (Top 1.3 percent) · Mandela Washington Fellow (Top 0.3 percent) · Harvard Business School.<br><br>
  <strong style="color:{GOLD};">Related tools:</strong> &nbsp;
  <a href="https://smart-resource-allocation-dashboard-eudzw5r2f9pbu4qyw3psez.streamlit.app">Public Budget Allocation Tool</a> &nbsp;·&nbsp;
  <a href="https://chpghrwawmvddoquvmniwm.streamlit.app">Medicaid Access Risk Monitor</a> &nbsp;·&nbsp;
  <a href="https://povertyearlywarningsystem-7rrmkktbi7bwha2nna8gk7.streamlit.app">Safety Net Risk Monitor</a> &nbsp;·&nbsp;
  <a href="https://impact-allocation-engine-ahxxrbgwmvyapwmifahk2b.streamlit.app">GovFund Allocation Engine</a> &nbsp;·&nbsp;
  <a href="https://worldvaccinationcoverage-etl-ftvwbikifyyx78xyy2j3zv.streamlit.app">Global Vaccination Coverage Explorer</a> &nbsp;·&nbsp;
  <a href="https://www.linkedin.com/in/abdul-hamid-sherriff-08583354">LinkedIn</a>
</div>
""",
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    run()
