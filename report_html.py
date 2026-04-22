"""McKinsey-style HTML funding brief (kept separate from policy.py for clearer deploy bundles)."""

from __future__ import annotations

import html
from datetime import datetime, timezone

import pandas as pd


def _escape(s: object) -> str:
    return html.escape(str(s), quote=True)


def _report_headline(alloc: pd.DataFrame, total_budget: float, scenario: str) -> str:
    """
    McKinsey-style action title: lead with the answer (who gets funded and why, in one line).
    """
    if alloc.empty or total_budget <= 0:
        return "Insufficient data to form a funding headline; expand filters or raise budget."
    ranked = alloc.sort_values("final_score", ascending=False)
    top = ranked.iloc[0]
    name = _escape(top["intervention_name"])
    pct = 100.0 * float(top["allocation"]) / float(total_budget)
    scen = _escape(scenario)
    tail = ""
    if len(ranked) > 1:
        second = ranked.iloc[1]
        p2 = 100.0 * float(second["allocation"]) / float(total_budget)
        tail = (
            f" <span class=\"muted\">The next tranche goes chiefly to "
            f"<strong>{_escape(second['intervention_name'])}</strong> (~{p2:.0f}% of budget).</span>"
        )
    return (
        f"<strong>{name}</strong> should receive the dominant share of this portfolio—about "
        f"<strong>{pct:.0f}%</strong> of the <strong>${total_budget:,.0f}</strong> envelope under the "
        f"<strong>{scen}</strong> effectiveness case—because it scores highest on evidence-adjusted "
        f"impact per dollar after uncertainty, funding gap, and scalability are applied.{tail}"
    )


def build_mckinsey_style_report_html(
    alloc: pd.DataFrame,
    total_budget: float,
    scenario: str,
    region_scope: str,
    cost_adj: float,
    effect_adj: float,
) -> str:
    """
    Single-file HTML report: pyramid structure (headline insight → summary → findings → implications).

    Styled for a crisp consulting read (open in browser; paste into Word if needed).
    """
    ranked = alloc.sort_values("final_score", ascending=False).copy()
    headline_html = _report_headline(alloc, float(total_budget), scenario)
    n = len(ranked)
    scope = _escape(region_scope)

    # Executive bullets (answer-first)
    top = ranked.iloc[0]
    top_pct = 100.0 * float(top["allocation"]) / float(total_budget) if total_budget else 0.0
    ex_bullets = [
        (
            f"<strong>Portfolio tilt.</strong> The model concentrates roughly <strong>{top_pct:.0f}%</strong> of funds in "
            f"<strong>{_escape(top['intervention_name'])}</strong>, consistent with maximizing the composite "
            f"score (cost-effectiveness × funding gap × scalability, after uncertainty)."
        ),
        (
            f"<strong>Scenario stance.</strong> The <strong>{_escape(scenario)}</strong> case scales underlying effectiveness "
            f"before other adjustments; sensitivity sliders apply cost ×{cost_adj:.2f} and effect ×{effect_adj:.2f} "
            f"to stress-test robustness."
        ),
        (
            "<strong>Evidence discipline.</strong> Strong RCT-style inputs (higher evidence strength) increase adjusted impact "
            "before dollars are divided; high uncertainty mechanically trims the score."
        ),
    ]

    # Numbered findings (McKinsey “exhibit-style” narrative without charts)
    findings: list[str] = []
    findings.append(
        f"<strong>Ranking concentration.</strong> With {n} intervention(s) in scope ({scope}), "
        f"the score distribution {'materially separates leaders from the tail' if n > 2 else 'allocates across the set'} "
        f"—see allocation shares in the appendix table."
    )
    ev_hi = int((ranked["evidence_strength"] >= 4).sum())
    findings.append(
        f"<strong>Evidence mix.</strong> {ev_hi} of {n} row(s) carry evidence strength ≥4, "
        f"which lifts adjusted impact prior to cost normalization."
    )
    if float(ranked["uncertainty_level"].max()) > 0.2:
        findings.append(
            "<strong>Uncertainty drag.</strong> At least one program carries elevated model uncertainty, "
            "reducing its cost-effectiveness multiplier—mirroring conservative funder practice."
        )
    else:
        findings.append(
            "<strong>Uncertainty drag.</strong> Uncertainty levels in this slice are moderate; "
            "rankings are driven more by cost-effectiveness and funding headroom than by pessimistic discounts."
        )

    # Implications
    implications = [
        "Prioritize diligence and implementation capacity on the top-ranked program before scaling commitments.",
        "If governance limits concentration, cap the top share and redistribute using the same score weights.",
        "Re-run the model after updated RCT inputs, unit costs, or population estimates—small data moves can reorder the tail.",
    ]

    # Appendix rows
    rows_html: list[str] = []
    for _, r in ranked.iterrows():
        share = 100.0 * float(r["allocation"]) / float(total_budget) if total_budget else 0.0
        rows_html.append(
            "<tr>"
            f"<td>{_escape(r['intervention_name'])}</td>"
            f"<td>{_escape(r.get('region', ''))}</td>"
            f"<td class=\"num\">{float(r['allocation']):,.0f}</td>"
            f"<td class=\"num\">{share:.1f}%</td>"
            f"<td class=\"num\">{float(r['final_score']):.6f}</td>"
            f"<td class=\"num\">{int(r['evidence_strength'])}</td>"
            f"<td class=\"num\">{float(r['uncertainty_level']):.2f}</td>"
            "</tr>"
        )

    ex_html = "".join(f"<li>{b}</li>" for b in ex_bullets)
    find_html = "".join(f"<li><span class=\"num-mark\">{i + 1}.</span> {t}</li>" for i, t in enumerate(findings))
    impl_html = "".join(f"<li>{_escape(t)}</li>" for t in implications)
    table_body = "\n".join(rows_html)
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    # Consulting palette: navy accent, high contrast body, generous whitespace
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>Impact Allocation — Funding Report</title>
  <style>
    :root {{
      --ink: #1a1a1a;
      --muted: #5c5c5c;
      --rule: #d9d9d9;
      --navy: #002855;
      --bg: #fafafa;
    }}
    body {{
      font-family: "Segoe UI", Calibri, "Helvetica Neue", Arial, sans-serif;
      color: var(--ink);
      background: #fff;
      margin: 0;
      padding: 48px 56px 64px;
      line-height: 1.5;
      max-width: 900px;
      margin-left: auto;
      margin-right: auto;
    }}
    .eyebrow {{
      font-size: 11px;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      color: var(--navy);
      font-weight: 600;
      margin-bottom: 10px;
    }}
    h1 {{
      font-size: 26px;
      font-weight: 600;
      color: var(--navy);
      line-height: 1.28;
      margin: 0 0 28px 0;
      border-bottom: 3px solid var(--navy);
      padding-bottom: 16px;
    }}
    h2 {{
      font-size: 13px;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      color: var(--navy);
      margin: 32px 0 12px 0;
      font-weight: 700;
    }}
    p.lead {{
      font-size: 15px;
      color: var(--ink);
      margin: 0 0 20px 0;
    }}
    ul {{
      margin: 0 0 0 1.1em;
      padding: 0;
    }}
    li {{
      margin-bottom: 10px;
    }}
    .muted {{
      color: var(--muted);
      font-weight: 400;
    }}
    .num-mark {{
      font-weight: 700;
      color: var(--navy);
      margin-right: 6px;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 13px;
      margin-top: 12px;
    }}
    th {{
      background: var(--navy);
      color: #fff;
      text-align: left;
      padding: 10px 12px;
      font-weight: 600;
    }}
    td {{
      border-bottom: 1px solid var(--rule);
      padding: 10px 12px;
      vertical-align: top;
    }}
    td.num {{
      text-align: right;
      font-variant-numeric: tabular-nums;
    }}
    .note {{
      font-size: 13px;
      color: var(--muted);
      margin-top: 36px;
      padding-top: 20px;
      border-top: 1px solid var(--rule);
    }}
    footer {{
      font-size: 11px;
      color: var(--muted);
      margin-top: 24px;
    }}
  </style>
</head>
<body>
  <div class="eyebrow">Impact Allocation Engine · Decision briefing</div>
  <h1>{headline_html}</h1>

  <h2>Executive summary</h2>
  <ul class="lead">{ex_html}</ul>

  <h2>Context</h2>
  <p class="lead">
    This briefing synthesizes a transparent cost-effectiveness stack (expected impact adjusted for evidence strength
    and uncertainty, normalized by cost, then multiplied by funding gap and scalability). Region filter:
    <strong>{scope}</strong>. Total budget modeled: <strong>${float(total_budget):,.0f}</strong>.
  </p>

  <h2>Key findings</h2>
  <ol style="list-style: none; margin: 0; padding: 0;">{find_html}</ol>

  <h2>Implications for funders</h2>
  <ul>{impl_html}</ul>

  <h2>Appendix — Allocation table</h2>
  <table>
    <thead>
      <tr>
        <th>Intervention</th>
        <th>Region</th>
        <th style="text-align:right">Allocation (USD)</th>
        <th style="text-align:right">Share</th>
        <th style="text-align:right">Final score</th>
        <th style="text-align:right">Evidence</th>
        <th style="text-align:right">Uncertainty</th>
      </tr>
    </thead>
    <tbody>
      {table_body}
    </tbody>
  </table>

  <p class="note"><strong>Note.</strong>
    Figures are illustrative; they should be interpreted alongside qualitative judgment, implementation risk,
    and partner capacity. This tool is not an official GiveWell or McKinsey product.
  </p>
  <footer>Generated {generated} · Impact Allocation Engine</footer>
</body>
</html>
"""
