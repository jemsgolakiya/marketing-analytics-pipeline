"""Robust anomaly detection on daily campaign metrics.

Uses a rolling median and the median absolute deviation (MAD) instead of
mean and standard deviation, so a single bad day does not hide the next one.
"""
from __future__ import annotations

import duckdb
import numpy as np
import pandas as pd

MAD_TO_SIGMA = 1.4826


def robust_zscores(series: pd.Series, window: int = 28) -> pd.Series:
    baseline = series.rolling(window, min_periods=14).median().shift(1)
    mad = (series - baseline).abs().rolling(window, min_periods=14).median().shift(1)
    return (series - baseline) / (MAD_TO_SIGMA * mad.replace(0, np.nan))


def detect_spend_anomalies(con: duckdb.DuckDBPyConnection, threshold: float = 4.0) -> pd.DataFrame:
    """Flag days where a campaign's spend AND cost per click jump far above normal."""
    df = con.execute("""
        SELECT date, platform, campaign, spend_eur, clicks, ga4_sign_ups,
               spend_eur / NULLIF(clicks, 0) AS cpc_eur
        FROM mart_daily_campaign
        ORDER BY campaign, date""").df()
    flagged = []
    for campaign, g in df.groupby("campaign"):
        g = g.set_index("date").sort_index().copy()
        g["spend_z"] = robust_zscores(g.spend_eur)
        g["cpc_z"] = robust_zscores(g.cpc_eur)
        hits = g[(g.spend_z > threshold) & (g.cpc_z > threshold)]
        for date, row in hits.iterrows():
            flagged.append({
                "date": date.date(), "platform": row.platform, "campaign": campaign,
                "spend_eur": round(row.spend_eur, 2), "cpc_eur": round(row.cpc_eur, 2),
                "sign_ups": int(row.ga4_sign_ups),
                "spend_z": round(row.spend_z, 1), "cpc_z": round(row.cpc_z, 1),
            })
    return pd.DataFrame(flagged)
