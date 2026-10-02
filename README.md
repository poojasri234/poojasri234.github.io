# Poojasri Medikonda | Data Analyst Portfolio

Live site: [poojasri234.github.io](https://poojasri234.github.io/)

This is a fast, one-page portfolio presenting Poojasri Medikonda’s entry-level data-analytics work in SQL, Python, Power BI, Tableau, and Excel. It focuses on data validation, KPI analysis, dashboard-ready reporting, and clearly communicated business insights.

## Featured case studies

- **E-Commerce Sales & Customer Analysis** — Transaction cleaning, monthly sales trends, customer concentration, and repeat-purchase analysis using the [UCI Online Retail dataset](https://doi.org/10.24432/C5BW33).
- **Customer Churn Analysis** — Contract and tenure cohort analysis using IBM’s fictional telco customer sample. Results are described as observed patterns, not causal business outcomes.
- **Customer Segmentation & Business Insights** — Recency and purchase-frequency segmentation using the UCI Online Retail data.
- **Credit Default Risk Analysis** — Descriptive repayment-status and credit-limit cohort analysis using the UCI Default of Credit Card Clients dataset. It reports observed patterns only and does not make a lending decision or prediction claim.

Each project summary shows the business question, a key calculated metric, and the data source. Public-dataset values are labelled as analysis outputs and are not presented as employer results. The reproducible credit-risk script exports aggregate data only.

## Tools

- SQL and SQLite
- Python and pandas
- Power BI and Tableau
- Excel and data validation
- Lightweight HTML and CSS

## Reproduce the credit-risk study

Use a Python environment with `pandas` and `openpyxl`, and save the official UCI workbook as an `.xlsx` file after conversion:

```bash
python analysis/credit_risk_analysis.py --input /path/to/default_of_credit_card_clients.xlsx --output data/credit-risk-project.json
```

## Run locally

```bash
git clone https://github.com/poojasri234/poojasri234.github.io.git
cd poojasri234.github.io
python3 -m http.server 8000
```

Then open `http://localhost:8000` in a browser.
