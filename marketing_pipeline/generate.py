"""Generate a realistic, fully synthetic set of raw marketing exports.

The company ("Kestrel Cloud", a fictional B2B SaaS) and every number are
invented. The exports deliberately reproduce problems found in real ad and
analytics data, so the pipeline has something real to solve:

* each platform uses its own column names, date formats and units
  (Google: cost in micros, Meta: spend in USD, LinkedIn: US-style dates)
* UTM tagging is inconsistent (fb / facebook / Meta, mixed casing, "(not set)")
* the LinkedIn export contains overlapping, duplicated rows
* ad platforms over-report conversions compared with GA4 (view-through etc.)
* a GA4 tracking break: the sign-up event stops firing for paid social traffic
  for two weeks in June while sessions keep coming in
* a spend anomaly: a bid-strategy bug triples Google non-brand spend for
  three days in September without extra conversions

Run:  python -m marketing_pipeline.generate
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 42
START, END = "2025-01-01", "2025-12-31"
RAW_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"

TRACKING_BREAK = ("2025-06-10", "2025-06-24")   # GA4 sign_up missing for paid social
SPEND_SPIKE = ("2025-09-15", "2025-09-17")      # Google non-brand bid bug
LINKEDIN_DUPLICATE_WINDOW = ("2025-03-01", "2025-03-14")


@dataclass(frozen=True)
class Campaign:
    platform: str
    name: str
    daily_budget: float     # in platform currency
    cpm: float              # cost per 1,000 impressions
    ctr: float              # clicks / impressions
    cvr: float              # GA4 sign-ups / sessions
    purchase_rate: float    # purchases / sign-ups
    over_report: float      # platform-reported conversions / GA4 conversions


CAMPAIGNS = [
    Campaign("google", "GGL_Search_Brand", 60, 110, 0.120, 0.090, 0.30, 1.05),
    Campaign("google", "GGL_Search_NonBrand", 220, 130, 0.040, 0.030, 0.16, 1.08),
    Campaign("google", "GGL_Search_Competitor", 90, 135, 0.030, 0.020, 0.12, 1.10),
    Campaign("meta", "META_Prospecting_Lookalike", 150, 9, 0.009, 0.012, 0.10, 1.65),
    Campaign("meta", "META_Retargeting_Website", 60, 14, 0.016, 0.040, 0.20, 1.55),
    Campaign("linkedin", "LI_ABM_DecisionMakers", 180, 45, 0.0055, 0.020, 0.28, 1.35),
    Campaign("linkedin", "LI_Content_Whitepaper", 110, 35, 0.0070, 0.035, 0.12, 1.40),
]

UTM_VARIANTS = {
    "google": [("google", "cpc", 1.0)],
    "meta": [("facebook", "paid_social", 0.45), ("fb", "paid_social", 0.25),
             ("Facebook", "paid-social", 0.15), ("meta", "cpc", 0.15)],
    "linkedin": [("linkedin", "paid_social", 0.6), ("LinkedIn", "paid-social", 0.25),
                 ("lnkd", "cpc", 0.15)],
}

NON_PAID = [  # source, medium, daily sessions, cvr, purchase rate, attribution channel
    ("google", "organic", 420, 0.022, 0.14, "Organic Search"),
    ("(direct)", "(none)", 260, 0.018, 0.22, "Direct"),
    ("newsletter", "email", 70, 0.030, 0.20, "Email"),
    ("g2.com", "referral", 35, 0.045, 0.25, "Referral"),
]

PLATFORM_CHANNEL = {"google": "Google Ads", "meta": "Meta Ads", "linkedin": "LinkedIn Ads"}

# Channels that tend to appear early in a B2B journey (used for assist touches)
ASSIST_CHANNELS = {
    "LinkedIn Ads": 0.27, "Meta Ads": 0.22, "Organic Search": 0.20,
    "Google Ads": 0.13, "Email": 0.12, "Referral": 0.06,
}


def _seasonality(dates: pd.DatetimeIndex) -> np.ndarray:
    weekday = np.where(dates.dayofweek >= 5, 0.55, 1.0)
    month = dates.month.to_numpy()
    monthly = np.select([month == 8, month == 12, np.isin(month, [10, 11])], [0.8, 0.75, 1.15], 1.0)
    trend = np.linspace(0.9, 1.15, len(dates))
    return weekday * monthly * trend


def generate(seed: int = SEED, out_dir: Path = RAW_DIR) -> dict[str, pd.DataFrame]:
    rng = np.random.default_rng(seed)
    dates = pd.date_range(START, END, freq="D")
    season = _seasonality(dates)

    fx = pd.DataFrame({
        "date": dates.strftime("%Y-%m-%d"),
        "usd_per_eur": np.round(1.04 + np.cumsum(rng.normal(0, 0.0025, len(dates))) + 0.06 * np.arange(len(dates)) / len(dates), 4),
    })

    ads_rows: list[dict] = []
    ga4_rows: list[dict] = []
    purchases: list[dict] = []
    break_start, break_end = map(pd.Timestamp, TRACKING_BREAK)
    spike_start, spike_end = map(pd.Timestamp, SPEND_SPIKE)

    for c in CAMPAIGNS:
        for i, d in enumerate(dates):
            spend = c.daily_budget * season[i] * rng.lognormal(0, 0.12)
            impressions = spend / c.cpm * 1000 * rng.lognormal(0, 0.05)
            clicks = rng.binomial(int(impressions), c.ctr)
            if c.name == "GGL_Search_NonBrand" and spike_start <= d <= spike_end:
                spend *= 3.2          # broken bid strategy: CPCs explode
                clicks = int(clicks * 1.25)
            sessions = rng.binomial(clicks, 0.9)
            conversions = rng.binomial(sessions, c.cvr)
            ga4_conversions = conversions
            if c.platform == "meta" and break_start <= d <= break_end:
                ga4_conversions = rng.binomial(conversions, 0.04)   # event stops firing
            n_purchases = rng.binomial(conversions, c.purchase_rate)
            platform_conv = round(conversions * c.over_report * rng.lognormal(0, 0.08), 1)

            ads_rows.append({"platform": c.platform, "date": d, "campaign": c.name, "spend": spend,
                             "impressions": int(impressions), "clicks": int(clicks),
                             "platform_conversions": platform_conv})

            variants = UTM_VARIANTS[c.platform]
            weights = np.array([v[2] for v in variants])
            split = rng.multinomial(sessions, weights / weights.sum())
            conv_split = rng.multinomial(ga4_conversions, weights / weights.sum())
            for (src, med, _), s, cv in zip(variants, split, conv_split):
                if s == 0:
                    continue
                campaign_value = c.name if rng.random() > 0.3 else c.name.lower()
                if rng.random() < 0.03:
                    campaign_value = "(not set)"
                ga4_rows.append({"event_date": d.strftime("%Y%m%d"), "session_source": src,
                                 "session_medium": med, "session_campaign": campaign_value,
                                 "sessions": int(s), "sign_ups": int(cv)})
            for _ in range(n_purchases):
                purchases.append({"date": d, "channel": PLATFORM_CHANNEL[c.platform], "campaign": c.name})

    for src, med, base, cvr, prate, channel in NON_PAID:
        for i, d in enumerate(dates):
            sessions = rng.poisson(base * season[i])
            conversions = rng.binomial(sessions, cvr)
            ga4_rows.append({"event_date": d.strftime("%Y%m%d"), "session_source": src,
                             "session_medium": med, "session_campaign": "(organic)" if med != "email" else "monthly_newsletter",
                             "sessions": int(sessions), "sign_ups": int(conversions)})
            for _ in range(rng.binomial(conversions, prate)):
                purchases.append({"date": d, "channel": channel, "campaign": None})

    ads = pd.DataFrame(ads_rows)

    google = ads[ads.platform == "google"]
    google_export = pd.DataFrame({
        "Day": google.date.dt.strftime("%Y-%m-%d"),
        "Campaign": google.campaign,
        "Cost (micros)": (google.spend * 1_000_000).round().astype("int64"),
        "Impressions": google.impressions,
        "Clicks": google.clicks,
        "Conversions": google.platform_conversions,
        "Currency": "EUR",
    })

    meta = ads[ads.platform == "meta"].merge(
        fx.assign(date=pd.to_datetime(fx.date)), on="date")
    meta_export = pd.DataFrame({
        "date_start": meta.date.dt.strftime("%Y-%m-%d"),
        "campaign_name": meta.campaign,
        "spend": (meta.spend * meta.usd_per_eur).round(2),   # account billed in USD
        "account_currency": "USD",
        "impressions": meta.impressions,
        "inline_link_clicks": meta.clicks,
        "actions_lead": meta.platform_conversions,
    })

    li = ads[ads.platform == "linkedin"]
    li_export = pd.DataFrame({
        "Start Date (in UTC)": li.date.dt.strftime("%m/%d/%Y"),
        "Campaign Name": li.campaign,
        "Total Spent": li.spend.round(2),
        "Currency": "EUR",
        "Impressions": li.impressions,
        "Clicks": li.clicks,
        "Conversions": li.platform_conversions,
    })
    dup_mask = li.date.between(*LINKEDIN_DUPLICATE_WINDOW).to_numpy()
    li_export = pd.concat([li_export, li_export[dup_mask]]).sort_values(
        ["Start Date (in UTC)", "Campaign Name"], kind="stable")

    ga4 = pd.DataFrame(ga4_rows)

    # Conversion paths: last touch is the channel that drove the purchase,
    # earlier touches are assists sampled from typical B2B journey patterns.
    touch_rows = []
    assist_names = list(ASSIST_CHANNELS)
    assist_p = np.array(list(ASSIST_CHANNELS.values()))
    assist_p = assist_p / assist_p.sum()
    for n, p in enumerate(purchases, start=1):
        conv_id = f"C{n:05d}"
        revenue = round(float(rng.lognormal(np.log(1100), 0.55)), 2)
        n_assists = min(rng.geometric(0.45) - 1, 5)
        offsets = sorted(rng.integers(1, 30, n_assists), reverse=True)
        for k, off in enumerate(offsets):
            ch = assist_names[rng.choice(len(assist_names), p=assist_p)]
            touch_rows.append({"conversion_id": conv_id, "touch_ts": (p["date"] - pd.Timedelta(days=int(off))).strftime("%Y-%m-%d"),
                               "channel": ch, "conversion_date": p["date"].strftime("%Y-%m-%d"), "revenue_eur": revenue})
        touch_rows.append({"conversion_id": conv_id, "touch_ts": p["date"].strftime("%Y-%m-%d"),
                           "channel": p["channel"], "conversion_date": p["date"].strftime("%Y-%m-%d"), "revenue_eur": revenue})
    touchpoints = pd.DataFrame(touch_rows)

    out = {
        "google_ads_export": google_export,
        "meta_ads_export": meta_export,
        "linkedin_ads_export": li_export,
        "ga4_sessions_export": ga4,
        "ga4_conversion_paths": touchpoints,
        "fx_rates": fx,
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, df in out.items():
        df.to_csv(out_dir / f"{name}.csv", index=False)
    return out


if __name__ == "__main__":
    frames = generate()
    for name, df in frames.items():
        print(f"{name:<24} {len(df):>7,} rows")
