"""End-to-end run: load raw exports -> build SQL models -> quality checks ->
anomaly detection -> charts -> markdown report.

Run:  python -m marketing_pipeline.run
"""
from __future__ import annotations

import sys
from datetime import date

import pandas as pd

from . import anomaly, charts, quality, warehouse

ROOT = warehouse.ROOT
OUTPUTS = ROOT / "outputs"
IMG = ROOT / "docs" / "img"
ICONS = {"pass": "✅", "warn": "⚠️", "fail": "❌"}


def _md_table(df: pd.DataFrame) -> str:
    cols = list(df.columns)
    lines = ["| " + " | ".join(cols) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    lines += ["| " + " | ".join(str(v) for v in row) + " |" for row in df.itertuples(index=False)]
    return "\n".join(lines)


def write_report(con, checks, incidents, anomalies) -> str:
    s = con.execute("""
        SELECT channel AS "Channel",
               printf('€%,.0f', spend_eur)            AS "Spend",
               printf('%,d', sign_ups::BIGINT)        AS "Sign-ups",
               CASE WHEN spend_eur > 0 THEN printf('€%.0f', cpa_eur) ELSE '–' END AS "CPA",
               printf('%.2f%%', conversion_rate * 100) AS "CVR",
               printf('€%,.0f', revenue_eur)           AS "Revenue (last click)",
               CASE WHEN spend_eur > 0 THEN printf('%.2f×', roas) ELSE '–' END AS "ROAS"
        FROM mart_channel_summary""").df()
    a = con.execute("""
        PIVOT (SELECT model, channel, printf('%.2f×', roas) AS roas FROM mart_attribution
               WHERE channel IN ('Google Ads', 'Meta Ads', 'LinkedIn Ads'))
        ON channel USING first(roas) ORDER BY model""").df()
    p = con.execute("""
        SELECT platform AS "Platform", printf('%,.0f', platform_reported) AS "Platform reported",
               printf('%,d', ga4_measured::BIGINT) AS "GA4 measured",
               printf('+%.0f%%', (over_reporting_ratio - 1) * 100) AS "Over-reporting"
        FROM mart_platform_vs_ga4""").df()

    parts = [
        "# Marketing performance report: Kestrel Cloud 2025",
        f"_Generated {date.today():%Y-%m-%d} by `python -m marketing_pipeline.run` · synthetic data_",
        "## Data-quality checks",
        _md_table(pd.DataFrame([{"": ICONS[c.status], "Check": c.name, "Result": c.detail} for c in checks])),
        "## Tracking incidents",
        _md_table(incidents) if not incidents.empty else "None detected.",
        "## Spend anomalies",
        _md_table(anomalies) if not anomalies.empty else "None detected.",
        "## Channel scorecard",
        _md_table(s),
        "## ROAS under different attribution models",
        _md_table(a),
        "## Platform-reported vs. GA4-measured conversions",
        _md_table(p),
    ]
    text = "\n\n".join(parts) + "\n"
    OUTPUTS.mkdir(exist_ok=True)
    (OUTPUTS / "report.md").write_text(text, encoding="utf-8")
    return text


def main() -> int:
    con = warehouse.build(OUTPUTS / "warehouse.duckdb")
    checks, incidents = quality.run_all(con)
    anomalies = anomaly.detect_spend_anomalies(con)
    n_alerts = len(incidents) + (anomalies.campaign.nunique() if not anomalies.empty else 0)
    charts.render_all(con, incidents, anomalies, n_alerts, IMG)
    con.execute(f"COPY mart_channel_summary TO '{OUTPUTS / 'channel_summary.csv'}' (HEADER)")
    con.execute(f"COPY mart_attribution TO '{OUTPUTS / 'attribution.csv'}' (HEADER)")
    write_report(con, checks, incidents, anomalies)

    for c in checks:
        print(f"{ICONS[c.status]}  {c.name}: {c.detail}")
    print(f"\nReport: {OUTPUTS / 'report.md'}\nCharts: {IMG}")
    # Known, documented incidents are expected in the demo data; only a broken
    # model (grain / reconciliation) should fail the run.
    hard_fail = [c for c in checks if c.status == "fail" and "tracking" not in c.name.lower()]
    return 1 if hard_fail else 0


if __name__ == "__main__":
    sys.exit(main())
