# GovFund Allocation Engine  
Cost Effectiveness Decision Tool for Public Health Funders

GovFund Allocation Engine is a production style Streamlit app for public health funders to prioritize interventions using transparent cost effectiveness logic, uncertainty adjustments, and scenario testing.
The current portfolio view is calibrated for malaria intervention decision support (SMC, ITNs, cash transfers, and related options).

## Why this app exists

Public health funders often face a simple question with high stakes: **Where should this dollar go?**  
This app helps decision makers compare interventions with a structured scoring model and produce a board ready policy memo.

## Primary users

- GiveWell style research teams
- Gates Foundation and other philanthropic funders
- USAID and bilateral program officers
- Global health policy and allocation teams

## Core capabilities

- Navy and gold McKinsey style interface
- Hero section with decision framing
- Scope note with data source and model caveat
- Four KPI cards for executive snapshot
- Policy brief cards in Risk, Implication, Action format
- Scenario and sensitivity analysis
- Malaria focused CEA framing for portfolio decisions
- Allocation and ranking charts (Plotly)
- Allocation table plus CSV export
- McKinsey style PDF report generation and download
- Credentialed byline and cross portfolio links

## Model logic

The model computes:

1. `expected_impact = adjusted_effect_size * population_affected * baseline_risk`
2. `adjusted_impact = expected_impact * (evidence_strength / 5)`
3. `cost_effectiveness = adjusted_impact / (adjusted_cost * population_affected)`
4. `uncertainty_adjusted = cost_effectiveness * (1 - uncertainty_level)`
5. `final_score = uncertainty_adjusted * funding_gap * scalability`

Budget is allocated proportionally to `final_score`.

## Files delivered

- `govfund_allocation_engine_app.py` — complete app file
- `report_generator.py` — PDF report engine (`build_report_bytes`)
- `app.py` — launcher entrypoint that runs GovFund app
- `requirements.txt` — standardized dependency list

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Data

Uses `interventions.csv` by default through `data_loader.py`.  
If a remote URL is supplied and available, the app can load from remote raw CSV.

## PDF report pattern

The app uses:

```python
from report_generator import build_report_bytes
```

and generates report bytes for download in the Export section.

## Notes

- This is a decision support tool, not a replacement for implementation diligence.
- Recommendations should be validated with local context, partner capacity, and governance review.

