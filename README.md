# Impact Allocation Engine

A production style Streamlit app that helps NGOs and funders allocate a fixed budget across interventions using cost effectiveness, uncertainty adjustment, and scenario testing.

## Quickstart in 1 minute

```bash
pip install -r requirements.txt
streamlit run app.py
```

Then:

1. Set budget, region, and interventions in the sidebar
2. Review the Executive summary at the top of the page
3. Click `Download Report` for the decision memo

## Screenshots

Add your screenshots in a folder such as `docs/screenshots/`, then update the paths below.

### Executive summary view

![Executive summary](docs/screenshots/executive-summary.png)

### Sidebar controls

![Sidebar controls](docs/screenshots/sidebar-controls.png)

### Allocation and ranking

![Allocation and ranking](docs/screenshots/allocation-ranking.png)

## What this app does

- Converts intervention data into a comparable score per program
- Allocates a total budget in proportion to those scores
- Supports sensitivity analysis for cost and effectiveness assumptions
- Supports scenario analysis (Base, Optimistic, Pessimistic)
- Provides an executive summary for quick decision making
- Exports a downloadable HTML funding report

## Problem this solves

Funding teams often need to decide where marginal dollars should go, while balancing evidence quality, uncertainty, scalability, and available funding headroom.  
This tool provides a transparent decision support workflow that makes trade offs visible.

## Core model

The scoring stack follows this sequence:

1. `expected_impact = adjusted_effect_size * population_affected * baseline_risk`
2. `adjusted_impact = expected_impact * (evidence_strength / 5)`
3. `cost_effectiveness = adjusted_impact / (adjusted_cost * population_affected)`
4. `uncertainty_adjusted = cost_effectiveness * (1 - uncertainty_level)`
5. `final_score = uncertainty_adjusted * funding_gap * scalability`

Budget allocation is then:

- `allocation = (final_score / sum(final_score)) * total_budget`

If all scores are zero, the app falls back to an equal split.

## Features

### Inputs

- Total budget
- Region filter
- Intervention selector
- Scenario selector
- Sensitivity sliders
- Optional moral weights
- Optional malaria cost stress test

### Outputs

- Executive summary strip with recommendation and risk notes
- Key metrics and ranking
- Budget what if table (plus 50 percent)
- Sensitivity snapshot table
- Allocation and score charts
- Allocation table and policy insights
- Downloadable report button in the executive summary

## Data schema

Expected columns in `interventions.csv`:

- `intervention_id`
- `intervention_name`
- `sector`
- `region`
- `cost_per_beneficiary`
- `cost_per_life_saved`
- `effect_size`
- `evidence_strength`
- `population_affected`
- `baseline_risk`
- `expected_lives_saved`
- `income_increase_per_person`
- `funding_gap`
- `scalability`
- `time_to_impact`
- `uncertainty_level`

## Project structure

```text
IMPACT_ALLOCATION_ENGINE/
  app.py              # Streamlit UI
  data_loader.py      # Remote/local/fallback data loading + validation
  modeling.py         # Scoring and budget allocation logic
  policy.py           # Executive summary and policy insights copy
  report_html.py      # Downloadable HTML report builder
  interventions.csv   # Sample intervention dataset
  requirements.txt
```

## Run locally

### 1) Install dependencies

```bash
pip install -r requirements.txt
```

### 2) Start Streamlit

```bash
streamlit run app.py
```

## How to use

1. Keep the default CSV URL, or paste your own raw CSV URL
2. Select region and interventions
3. Set budget and scenario
4. Adjust sensitivity controls
5. Review executive summary, tables, and charts
6. Click `Download Report` for the HTML memo

## Data loading behavior

The app tries data sources in this order:

1. Remote CSV URL (if available)
2. Local bundled `interventions.csv`
3. Synthetic fallback with matching schema

This keeps the app resilient in cloud and local environments.

## Deployment notes

- Built for Streamlit Cloud or any environment that supports Streamlit
- `requirements.txt` pins compatible major versions
- If remote data is not accessible, the app still runs using local or fallback data

## Disclaimer

This is a transparent modeling aid, not a substitute for grant diligence, partner assessment, governance review, or board approval.  
Use this tool alongside qualitative judgment and implementation context.
