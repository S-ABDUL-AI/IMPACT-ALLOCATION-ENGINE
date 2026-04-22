"""Narrative policy insights and executive brief text."""

from __future__ import annotations

from typing import TypedDict

import pandas as pd


class ExecutiveSummaryStrip(TypedDict):
    """Payload for the dashboard ‘Executive summary’ strip (portfolio / sponsor readers)."""

    headline: str
    caption: str
    bullets: list[str]
    top_pct: float
    n_programs: int


def executive_summary_strip(
    alloc: pd.DataFrame,
    total_budget: float,
    scenario: str,
    region_scope: str,
) -> ExecutiveSummaryStrip:
    """
    Board level executive readout, clear recommendation first.
    """
    ranked = alloc.sort_values("final_score", ascending=False)
    top = ranked.iloc[0]
    tb = float(total_budget)
    top_pct = 100.0 * float(top["allocation"]) / tb if tb > 0 else 0.0
    scope = region_scope if region_scope else "All regions"
    scen = str(scenario)
    headline = (
        f"**Recommendation:** Under the **{scen}** assumptions, **{top['intervention_name']}** should receive the "
        f"largest share of this budget, about **{top_pct:.0f}%** of **${tb:,.0f}**."
    )
    caption = (
        f"**Scope:** **{len(alloc)}** program(s), **{scope}**. "
        "This is a transparent model for decision support, not a final funding decision. "
        "Use **Download Report** in the top right for the full memo and appendix table."
    )
    bullets: list[str] = [
        "**Why this is first.** This option performs best on the model estimate of impact per dollar, after evidence quality and uncertainty are considered.",
    ]
    if len(ranked) > 1:
        second = ranked.iloc[1]
        p2 = 100.0 * float(second["allocation"]) / tb if tb > 0 else 0.0
        bullets.append(
            f"**Portfolio balance.** **{second['intervention_name']}** is next at about **{p2:.0f}%**, and can be used to reduce concentration risk."
        )
    else:
        bullets.append(
            "**Portfolio breadth.** Add more interventions in **Select Interventions** to compare options across a wider portfolio."
        )
    if float(ranked["uncertainty_level"].max()) > 0.25:
        bullets.append(
            "**Risk note.** At least one program has high uncertainty, so treat this ranking as directional and validate with current field evidence before approval."
        )
    else:
        bullets.append(
            "**What to test next.** Use **Sensitivity** and alternate **Scenario** settings below to confirm whether the ranking remains stable."
        )
    return {
        "headline": headline,
        "caption": caption,
        "bullets": bullets,
        "top_pct": top_pct,
        "n_programs": int(len(alloc)),
    }


def allocation_insights(df: pd.DataFrame) -> list[str]:
    """Short bullet reasons WHY allocations shifted (deterministic from columns)."""
    if df.empty:
        return ["No interventions in scope."]
    top = df.sort_values("final_score", ascending=False).iloc[0]
    bullets: list[str] = []
    bullets.append(
        f"**{top['intervention_name']}** ranks first because its combined score balances "
        f"evidence-adjusted expected impact, cost-effectiveness after uncertainty, and multipliers "
        f"(funding_gap={int(top['funding_gap'])}, scalability={int(top['scalability'])})."
    )
    hi_ev = df[df["evidence_strength"] >= 4]
    if not hi_ev.empty:
        bullets.append(
            f"{len(hi_ev)} intervention(s) carry **strong evidence** (4–5); the model up-weights their expected impact before cost normalization."
        )
    if float(df["uncertainty_level"].max()) > 0.25:
        bullets.append(
            "Higher **uncertainty_level** mechanically reduces cost-effectiveness, reflecting GiveWell-style skepticism toward noisy estimates."
        )
    if (df["funding_gap"] >= 4).any():
        bullets.append(
            "**Funding gap** acts as 'room for more funding'—interventions with more headroom receive a higher final multiplier."
        )
    return bullets


def funding_brief_markdown(df: pd.DataFrame, total_budget: float, scenario: str) -> str:
    """Auto-generated GiveWell-style brief for decision-makers."""
    ranked = df.sort_values("final_score", ascending=False)
    top = ranked.iloc[0]
    second = ranked.iloc[1] if len(ranked) > 1 else None

    lines = [
        "### Summary",
        "",
        f"Under the **{scenario}** effectiveness scenario and the current sensitivity sliders, "
        f"**{top['intervention_name']}** delivers the highest risk-adjusted score per modeling assumptions.",
        "",
        "### Key insights",
        "",
        f"- **Cost-effectiveness path:** expected impact scales with effect size, population, and baseline risk, then discounts for evidence strength and uncertainty.",
        f"- **Top pick drivers:** final_score integrates funding_gap and scalability, pushing resources toward interventions that are both impactful and expandable.",
    ]
    if second is not None:
        lines.append(f"- **Runner-up:** {second['intervention_name']} remains material for diversification if concentration limits are a concern.")
    lines += [
        "",
        "### Recommendation",
        "",
        f"Allocate the largest marginal dollar share to **{top['intervention_name']}** while preserving a tail allocation to runner-ups for robustness.",
        f"Total modeled budget: **${total_budget:,.0f}**.",
    ]
    return "\n".join(lines)


# Re-export so `from policy import build_mckinsey_style_report_html` still works after deploy.
from report_html import build_mckinsey_style_report_html as build_mckinsey_style_report_html
