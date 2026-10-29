"""Data-quality checks that run before anything reaches a report.

Each check returns a CheckResult. "fail" stops trust in the numbers,
"warn" means the numbers are usable but someone should look.
"""
from __future__ import annotations

from dataclasses import dataclass

import duckdb
import pandas as pd


@dataclass
class CheckResult:
    name: str
    status: str          # "pass" | "warn" | "fail"
    detail: str


def _scalar(con: duckdb.DuckDBPyConnection, sql: str) -> float:
    return con.execute(sql).fetchone()[0]


def check_row_counts(con) -> CheckResult:
    empty = [t for (t,) in con.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_name LIKE 'raw_%'").fetchall()
        if _scalar(con, f"SELECT COUNT(*) FROM {t}") == 0]
    if empty:
        return CheckResult("Raw exports are not empty", "fail", f"Empty: {', '.join(empty)}")
    return CheckResult("Raw exports are not empty", "pass", "All raw exports contain rows")


def check_duplicates(con) -> CheckResult:
    raw = _scalar(con, "SELECT COUNT(*) FROM raw_linkedin_ads_export")
    clean = _scalar(con, "SELECT COUNT(*) FROM stg_linkedin_ads")
    dups = raw - clean
    status = "warn" if dups else "pass"
    return CheckResult("Duplicate rows in LinkedIn export", status,
                       f"{dups} duplicated rows found in the raw export and removed in staging")


def check_grain(con) -> CheckResult:
    bad = _scalar(con, """
        SELECT COUNT(*) FROM (
            SELECT date, campaign_key FROM int_ad_spend GROUP BY ALL HAVING COUNT(*) > 1)""")
    status = "fail" if bad else "pass"
    return CheckResult("One row per day and campaign in the spend model", status,
                       f"{bad} duplicated day/campaign keys")


def check_spend_reconciliation(con) -> CheckResult:
    google_raw = _scalar(con, 'SELECT SUM(CAST("Cost (micros)" AS BIGINT)) / 1e6 FROM raw_google_ads_export')
    google_model = _scalar(con, "SELECT SUM(spend_eur) FROM int_ad_spend WHERE platform = 'Google Ads'")
    diff = abs(google_raw - google_model)
    status = "pass" if diff < 0.01 else "fail"
    return CheckResult("Spend reconciles from raw export to model", status,
                       f"Google Ads: raw EUR {google_raw:,.2f} vs model EUR {google_model:,.2f}")


def check_utm_coverage(con, threshold: float = 0.05) -> CheckResult:
    share = _scalar(con, """
        SELECT SUM(sessions) FILTER (WHERE channel IN ('Google Ads','Meta Ads','LinkedIn Ads')
                                           AND campaign_key IS NULL)
               / SUM(sessions) FILTER (WHERE channel IN ('Google Ads','Meta Ads','LinkedIn Ads'))
        FROM stg_ga4_sessions""")
    unmapped = _scalar(con, "SELECT COUNT(*) FROM stg_ga4_sessions WHERE channel = 'Unmapped'")
    status = "warn" if share > threshold or unmapped else "pass"
    return CheckResult("Paid traffic carries a campaign UTM", status,
                       f"{share:.1%} of paid sessions have campaign '(not set)'; "
                       f"{unmapped} rows with an unmapped source/medium")


def detect_tracking_breaks(con, baseline_days: int = 56, smooth_days: int = 7, drop: float = 0.3,
                           min_expected: float = 10, min_days: int = 3) -> pd.DataFrame:
    """Flag periods where conversions collapse while traffic keeps coming in.

    A real performance drop moves sessions and conversions together. When
    sessions hold steady but sign-ups fall below `drop` x what the normal
    conversion rate predicts, the most likely cause is a broken tracking event.

    Daily sign-up counts are small and noisy, so the test runs on a centred
    7-day window and only when at least `min_expected` sign-ups were expected
    (avoids false alarms on low-volume channels). Incident edges are then
    refined day by day.
    """
    df = con.execute("""
        SELECT date, channel, sessions, ga4_sign_ups
        FROM mart_channel_daily
        WHERE channel IN ('Google Ads', 'Meta Ads', 'LinkedIn Ads')
        ORDER BY channel, date""").df()
    incidents = []
    for channel, g in df.groupby("channel"):
        g = g.set_index("date").sort_index()
        cvr = g.ga4_sign_ups / g.sessions.where(g.sessions > 0)
        base_cvr = cvr.rolling(baseline_days, min_periods=21).median().bfill()
        recorded = g.ga4_sign_ups.rolling(smooth_days, center=True, min_periods=1).sum()
        expected = (base_cvr * g.sessions).rolling(smooth_days, center=True, min_periods=1).sum()
        core = (expected >= min_expected) & (recorded < drop * expected)
        daily_low = cvr < drop * base_cvr
        # grow each core block outwards while the single-day conversion rate is still broken
        flag = core.copy()
        changed = True
        while changed:
            grown = flag | (daily_low & (flag.shift(1, fill_value=False) | flag.shift(-1, fill_value=False)))
            changed = bool((grown != flag).any())
            flag = grown
        run_id = (flag != flag.shift()).cumsum()
        for _, run in g[flag].groupby(run_id[flag]):
            if len(run) >= min_days:
                expected = (base_cvr[run.index] * run.sessions).sum()
                incidents.append({
                    "channel": channel,
                    "start": run.index.min().date(),
                    "end": run.index.max().date(),
                    "days": len(run),
                    "sessions": int(run.sessions.sum()),
                    "sign_ups_recorded": int(run.ga4_sign_ups.sum()),
                    "sign_ups_expected": round(float(expected)),
                })
    return pd.DataFrame(incidents)


def check_tracking(con) -> tuple[CheckResult, pd.DataFrame]:
    incidents = detect_tracking_breaks(con)
    if incidents.empty:
        return CheckResult("No conversion tracking breaks", "pass", "Conversion rates are stable"), incidents
    parts = [f"{r.channel} {r.start} to {r.end} ({r.sign_ups_recorded} recorded vs ~{r.sign_ups_expected} expected)"
             for r in incidents.itertuples()]
    return CheckResult("No conversion tracking breaks", "fail", "; ".join(parts)), incidents


def run_all(con) -> tuple[list[CheckResult], pd.DataFrame]:
    results = [check_row_counts(con), check_duplicates(con), check_grain(con),
               check_spend_reconciliation(con), check_utm_coverage(con)]
    tracking, incidents = check_tracking(con)
    results.append(tracking)
    return results, incidents
