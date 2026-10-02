#!/usr/bin/env python3
"""Create a descriptive credit-default risk case study from UCI public data.

Usage:
  python credit_risk_analysis.py \
    --input /path/to/default_of_credit_card_clients.xlsx \
    --output /path/to/credit-risk-project.json

The input is the UCI "Default of Credit Card Clients" workbook after conversion
from the official XLS file. This is an exploratory public-dataset study, not a
production credit model or a lending decision system.
"""

from __future__ import annotations

import argparse
import json
import math
import sqlite3
from pathlib import Path

import pandas as pd

TARGET = "default payment next month"
REQUIRED_COLUMNS = {
    "ID", "LIMIT_BAL", "SEX", "EDUCATION", "MARRIAGE", "AGE",
    "PAY_0", "PAY_2", "PAY_3", "PAY_4", "PAY_5", "PAY_6",
    "BILL_AMT1", "BILL_AMT2", "BILL_AMT3", "BILL_AMT4", "BILL_AMT5", "BILL_AMT6",
    "PAY_AMT1", "PAY_AMT2", "PAY_AMT3", "PAY_AMT4", "PAY_AMT5", "PAY_AMT6", TARGET,
}
SOURCE_URL = "https://doi.org/10.24432/C55S3H"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def percentage(numerator: int, denominator: int) -> float:
    return 100 * numerator / denominator


def group_metrics(data: pd.DataFrame, group_column: str, order: list[str]) -> pd.DataFrame:
    grouped = data.groupby(group_column, observed=True)["default_flag"].agg(customers="size", defaults="sum")
    grouped = grouped.reindex(order)
    grouped["default_rate_percent"] = 100 * grouped["defaults"] / grouped["customers"]
    return grouped


def load_data(path: Path) -> tuple[pd.DataFrame, dict]:
    require(path.exists(), f"Input workbook not found: {path}")
    raw = pd.read_excel(path, header=1)
    require(set(raw.columns) == REQUIRED_COLUMNS, "Unexpected input schema; review source workbook before using it.")
    require(len(raw) == 30_000, "Unexpected row count; expected the UCI 30,000-client dataset.")
    require(raw["ID"].nunique() == len(raw), "Customer IDs are not unique.")
    require(int(raw.duplicated().sum()) == 0, "Exact duplicate records found; investigate before analysis.")
    require(int(raw.isna().sum().sum()) == 0, "Missing values found; investigate before analysis.")
    require(set(raw[TARGET].unique()) == {0, 1}, "Unexpected target values.")
    require(raw["PAY_0"].between(-2, 8).all(), "Unexpected recent repayment-status value.")

    data = raw.copy()
    data["default_flag"] = data[TARGET].astype(int)
    data["recent_payment_status"] = pd.Series("No reported delay", index=data.index)
    data.loc[data["PAY_0"].eq(1), "recent_payment_status"] = "1 month delay"
    data.loc[data["PAY_0"].ge(2), "recent_payment_status"] = "2+ months delay"
    # These are data-driven quartiles, used only for descriptive comparisons.
    data["limit_quartile"] = pd.qcut(
        data["LIMIT_BAL"], q=4,
        labels=["Lowest limit quartile", "Lower-middle limit quartile", "Upper-middle limit quartile", "Highest limit quartile"],
    )
    audit = {
        "rows": int(len(data)),
        "input_columns": int(len(raw.columns)),
        "unique_customer_ids": int(raw["ID"].nunique()),
        "duplicate_rows": int(raw.duplicated().sum()),
        "missing_values": int(raw.isna().sum().sum()),
    }
    return data, audit


def calculate(data: pd.DataFrame, audit: dict) -> tuple[dict, dict]:
    total = len(data)
    defaults = int(data["default_flag"].sum())
    overall_rate = percentage(defaults, total)

    status_order = ["No reported delay", "1 month delay", "2+ months delay"]
    status = group_metrics(data, "recent_payment_status", status_order)
    quartile_order = ["Lowest limit quartile", "Lower-middle limit quartile", "Upper-middle limit quartile", "Highest limit quartile"]
    limits = group_metrics(data, "limit_quartile", quartile_order)

    # Recompute the core status statistics independently in SQLite.
    with sqlite3.connect(":memory:") as connection:
        data[["recent_payment_status", "default_flag"]].to_sql("credit_clients", connection, index=False)
        sql_status = pd.read_sql_query(
            """
            SELECT recent_payment_status AS cohort,
                   COUNT(*) AS customers,
                   SUM(default_flag) AS defaults,
                   100.0 * SUM(default_flag) / COUNT(*) AS default_rate_percent
            FROM credit_clients
            GROUP BY recent_payment_status
            """,
            connection,
        ).set_index("cohort")
    for cohort in status_order:
        require(int(sql_status.loc[cohort, "customers"]) == int(status.loc[cohort, "customers"]),
                f"SQLite and pandas customer counts disagree for {cohort}.")
        require(int(sql_status.loc[cohort, "defaults"]) == int(status.loc[cohort, "defaults"]),
                f"SQLite and pandas default counts disagree for {cohort}.")
        require(math.isclose(float(sql_status.loc[cohort, "default_rate_percent"]),
                             float(status.loc[cohort, "default_rate_percent"]), abs_tol=1e-10),
                f"SQLite and pandas default rates disagree for {cohort}.")

    no_delay = status.loc["No reported delay"]
    two_plus = status.loc["2+ months delay"]
    low_limit = limits.loc["Lowest limit quartile"]
    high_limit = limits.loc["Highest limit quartile"]

    project = {
        "id": "credit-default-risk",
        "title": "Credit default risk profile",
        "category": "Risk",
        "kicker": "Risk analytics / UCI public dataset",
        "description": "A descriptive analysis of public credit-card client data, showing how observed next-month default varies across repayment-status and credit-limit cohorts.",
        "tools": ["Python", "pandas", "SQL", "SQLite"],
        "metrics": [
            {"label": "Clients profiled", "value": f"{total:,}", "detail": "Unique credit-card client records across 24 input attributes"},
            {"label": "Observed default rate", "value": f"{overall_rate:.1f}%", "detail": f"{defaults:,} records labeled as next-month default"},
            {"label": "2+ month delay cohort", "value": f"{two_plus['default_rate_percent']:.1f}%", "detail": f"{int(two_plus['defaults']):,} of {int(two_plus['customers']):,} clients"},
            {"label": "No-reported-delay cohort", "value": f"{no_delay['default_rate_percent']:.1f}%", "detail": f"{int(no_delay['defaults']):,} of {int(no_delay['customers']):,} clients"},
        ],
        "chart": {
            "type": "bar",
            "labels": status_order,
            "values": [round(float(status.loc[c, "default_rate_percent"]), 2) for c in status_order],
            "unit": "percent",
            "title": "Observed next-month default rate by recent repayment status",
        },
        "question": "Which client cohorts show higher observed next-month default rates, and which signals warrant further risk review?",
        "method": [
            "Loaded the UCI workbook and validated 30,000 unique client IDs, 25 source fields, no exact duplicate rows, and no missing values.",
            "Calculated observed next-month default as records labeled 1 divided by all clients in each cohort; this is a descriptive rate, not a prediction score.",
            "Grouped clients by their most recent recorded repayment-status field and data-driven credit-limit quartiles using pandas.",
            "Reconciled repayment-status cohort counts and default rates with independent SQLite GROUP BY queries before exporting aggregate results.",
        ],
        "findings": [
            f"{defaults:,} of {total:,} clients were labeled as defaulting next month, an observed rate of {overall_rate:.2f}%.",
            f"Clients with 2+ months of reported recent payment delay had a {two_plus['default_rate_percent']:.2f}% observed default rate ({int(two_plus['defaults']):,}/{int(two_plus['customers']):,}), compared with {no_delay['default_rate_percent']:.2f}% ({int(no_delay['defaults']):,}/{int(no_delay['customers']):,}) for the no-reported-delay cohort.",
            f"The lowest credit-limit quartile had a {low_limit['default_rate_percent']:.2f}% observed default rate, versus {high_limit['default_rate_percent']:.2f}% for the highest quartile.",
        ],
        "recommendations": [
            "Use repayment-status cohorts as a descriptive monitoring view and investigate whether differences persist after controlling for other documented attributes.",
            "Validate feature definitions, timing, fairness, and performance on current business data before using any model or cohort for a credit decision.",
            "Track data completeness and cohort mix alongside default rates so changes in composition are not mistaken for changing risk.",
        ],
        "limitations": [
            "This is a historical public dataset of Taiwan credit-card clients; results are portfolio findings, not employer outcomes.",
            "The analysis describes associations in a labeled dataset. It does not demonstrate causality, predict future default, or recommend an automated lending decision.",
            "No model was trained, validated, deployed, or used for a real credit decision. Fairness, regulatory, and business-policy review would be required before any practical use.",
        ],
        "source": {
            "name": "UCI Default of Credit Card Clients — Yeh (2009)",
            "url": SOURCE_URL,
            "license": "CC BY 4.0. Aggregate portfolio findings only; raw customer-level data is not redistributed.",
        },
        "analysisPath": "analysis/credit_risk_analysis.py",
    }
    audit.update({
        "defaults": defaults,
        "overall_default_rate_percent": overall_rate,
        "recent_payment_status": [
            {"cohort": c, "customers": int(status.loc[c, "customers"]), "defaults": int(status.loc[c, "defaults"]),
             "default_rate_percent": float(status.loc[c, "default_rate_percent"])}
            for c in status_order
        ],
        "limit_quartiles": [
            {"cohort": c, "customers": int(limits.loc[c, "customers"]), "defaults": int(limits.loc[c, "defaults"]),
             "default_rate_percent": float(limits.loc[c, "default_rate_percent"])}
            for c in quartile_order
        ],
        "validation": "Pandas and SQLite repayment-status cohort counts and rates reconcile.",
    })
    return project, audit


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", type=Path, required=True, help="Converted UCI .xlsx workbook")
    parser.add_argument("--output", type=Path, required=True, help="Aggregate project JSON output")
    parser.add_argument("--audit-output", type=Path, help="Optional detailed audit JSON output")
    args = parser.parse_args()

    data, audit = load_data(args.input)
    project, audit = calculate(data, audit)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(project, indent=2) + "\n", encoding="utf-8")
    if args.audit_output:
        args.audit_output.parent.mkdir(parents=True, exist_ok=True)
        args.audit_output.write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"project": str(args.output), "audit": str(args.audit_output) if args.audit_output else None, **audit}, indent=2))


if __name__ == "__main__":
    main()
