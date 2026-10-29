"""Static charts for the README and the generated report."""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.ticker import FuncFormatter, PercentFormatter  # noqa: E402

COLORS = {
    "Google Ads": "#2563EB", "Meta Ads": "#7C3AED", "LinkedIn Ads": "#0E7490",
    "Organic Search": "#16A34A", "Direct": "#64748B", "Email": "#D97706", "Referral": "#DB2777",
}
PAID = ["Google Ads", "Meta Ads", "LinkedIn Ads"]
INK, MUTED, GRID, ALERT = "#0F172A", "#64748B", "#E2E8F0", "#DC2626"
MODELS = ["Last click", "First click", "Linear", "Position based (40/20/40)"]

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 10, "axes.edgecolor": GRID, "axes.labelcolor": MUTED,
    "axes.titlesize": 12, "axes.titleweight": "bold", "axes.titlecolor": INK, "axes.titlelocation": "left",
    "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.color": GRID,
    "grid.linewidth": 0.8, "xtick.color": MUTED, "ytick.color": MUTED, "legend.frameon": False,
    "figure.facecolor": "white", "savefig.facecolor": "white", "savefig.dpi": 160,
})
EUR_K = FuncFormatter(lambda v, _: f"€{v / 1000:,.0f}k")


def _save(fig, path: Path) -> Path:
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path


def monthly_spend_revenue(daily: pd.DataFrame, ax) -> None:
    m = daily.assign(month=pd.to_datetime(daily.date).dt.to_period("M").dt.to_timestamp())
    spend = m[m.channel.isin(PAID)].pivot_table(index="month", columns="channel", values="spend_eur", aggfunc="sum")[PAID]
    revenue = m[m.channel.isin(PAID)].groupby("month").revenue_eur.sum()
    x = range(len(spend))
    bottom = pd.Series(0.0, index=spend.index)
    for ch in PAID:
        ax.bar(x, spend[ch], bottom=bottom, color=COLORS[ch], width=0.7, label=f"{ch} spend")
        bottom += spend[ch]
    ax.plot(x, revenue.values, color=INK, marker="o", lw=2, ms=4, label="Paid revenue (last click)")
    ax.set_xticks(list(x), [d.strftime("%b") for d in spend.index])
    ax.yaxis.set_major_formatter(EUR_K)
    ax.set_title("Monthly paid spend vs. revenue")
    ax.legend(loc="upper left", fontsize=8, ncols=2)
    ax.grid(axis="x", visible=False)


def attribution(attr: pd.DataFrame, ax) -> None:
    paid = attr[attr.channel.isin(PAID)]
    width = 0.2
    for i, model in enumerate(MODELS):
        sub = paid[paid.model == model].set_index("channel").reindex(PAID)
        xs = [j + (i - 1.5) * width for j in range(len(PAID))]
        bars = ax.bar(xs, sub.roas, width=width * 0.92, label=model,
                      color=["#0F172A", "#475569", "#94A3B8", "#CBD5E1"][i])
        for b, v in zip(bars, sub.roas):
            ax.text(b.get_x() + b.get_width() / 2, v + 0.08, f"{v:.1f}", ha="center", fontsize=7, color=MUTED)
    ax.axhline(1, color=ALERT, lw=1, ls="--")
    ax.text(len(PAID) - 0.5, 1.08, "break-even", color=ALERT, fontsize=8, ha="right")
    ax.set_xticks(range(len(PAID)), PAID)
    ax.set_ylabel("ROAS")
    ax.set_title("ROAS by attribution model")
    ax.legend(fontsize=8, loc="upper right")
    ax.grid(axis="x", visible=False)


def tracking_break(daily: pd.DataFrame, incidents: pd.DataFrame, ax) -> None:
    meta = daily[(daily.channel == "Meta Ads")].sort_values("date").set_index("date")
    meta = meta.loc["2025-04-15":"2025-08-15"]
    ax.bar(meta.index, meta.sessions, color="#DDD6FE", width=1.0, label="Sessions")
    ax.set_ylabel("Sessions")
    ax2 = ax.twinx()
    ax2.plot(meta.index, meta.ga4_sign_ups.rolling(7, center=True, min_periods=1).mean(),
             color=COLORS["Meta Ads"], lw=2.2, label="Sign-ups (7-day avg)")
    ax2.set_ylabel("Sign-ups per day", color=MUTED)
    ax2.spines[["top"]].set_visible(False)
    ax2.grid(False)
    for r in incidents[incidents.channel == "Meta Ads"].itertuples():
        ax.axvspan(pd.Timestamp(r.start), pd.Timestamp(r.end), color=ALERT, alpha=0.12)
        ax2.annotate(f"Tracking break detected\n{r.start:%d %b} – {r.end:%d %b}\n"
                     f"{r.sign_ups_recorded} recorded vs ~{r.sign_ups_expected} expected",
                     xy=(pd.Timestamp(r.end), 0.3), xytext=(pd.Timestamp(r.end) + pd.Timedelta(days=12), 0.35),
                     fontsize=8, color=ALERT, va="bottom", arrowprops={"arrowstyle": "->", "color": ALERT},
                     bbox={"boxstyle": "round,pad=0.4", "fc": "white", "ec": ALERT, "lw": 0.8})
    ax2.set_ylim(0, 7)
    ax.set_ylim(0, meta.sessions.max() * 1.3)
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b"))
    ax.set_title("Meta Ads: sessions kept coming, sign-ups vanished")
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, fontsize=8, loc="upper left")
    ax.grid(axis="x", visible=False)


def spend_anomaly(campaign_daily: pd.DataFrame, anomalies: pd.DataFrame, ax) -> None:
    g = campaign_daily[campaign_daily.campaign == "GGL_Search_NonBrand"].sort_values("date").set_index("date")
    g = g.loc["2025-08-01":"2025-10-31"]
    cpc = g.spend_eur / g.clicks
    ax.plot(g.index, cpc, color=COLORS["Google Ads"], lw=1.8, label="Cost per click")
    hits = anomalies[anomalies.campaign == "GGL_Search_NonBrand"]
    if not hits.empty:
        idx = pd.to_datetime(hits.date)
        ax.scatter(idx, cpc.loc[idx], color=ALERT, zorder=3, s=36, label="Flagged anomaly")
        first = hits.iloc[0]
        ax.annotate(f"Bid strategy bug: spend ×{hits.spend_eur.mean() / g.spend_eur.median():.1f},\n"
                    f"robust z-score {hits.spend_z.max():.0f}",
                    xy=(idx.iloc[0], cpc.loc[idx.iloc[0]]), xytext=(idx.iloc[0] + pd.Timedelta(days=9), cpc.max() * 0.92),
                    fontsize=8, color=ALERT, arrowprops={"arrowstyle": "->", "color": ALERT})
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"€{v:.2f}"))
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b"))
    ax.set_title("Google non-brand: CPC anomaly caught automatically")
    ax.legend(fontsize=8, loc="upper left")
    ax.grid(axis="x", visible=False)


def platform_vs_ga4(pvg: pd.DataFrame, ax) -> None:
    pvg = pvg.set_index("platform").reindex(PAID)
    xs = range(len(PAID))
    ax.bar([x - 0.18 for x in xs], pvg.platform_reported, width=0.36, color="#CBD5E1", label="Platform reported")
    ax.bar([x + 0.18 for x in xs], pvg.ga4_measured, width=0.36, color=[COLORS[p] for p in PAID], label="GA4 measured")
    for x, (_, r) in zip(xs, pvg.iterrows()):
        ax.text(x, max(r.platform_reported, r.ga4_measured) * 1.04, f"+{r.over_reporting_ratio - 1:.0%}",
                ha="center", fontsize=9, color=INK, fontweight="bold")
    ax.set_xticks(list(xs), PAID)
    ax.set_ylim(0, pvg.platform_reported.max() * 1.18)
    ax.set_ylabel("Conversions 2025")
    ax.set_title("Platforms over-report conversions vs. GA4")
    ax.legend(fontsize=8)
    ax.grid(axis="x", visible=False)


def _tile(fig, rect, label, value, sub, color=INK):
    ax = fig.add_axes(rect)
    ax.axis("off")
    ax.add_patch(plt.Rectangle((0, 0), 1, 1, transform=ax.transAxes, color="#F8FAFC", ec=GRID, lw=1))
    ax.text(0.06, 0.70, label, fontsize=9, color=MUTED, transform=ax.transAxes)
    ax.text(0.06, 0.30, value, fontsize=19, fontweight="bold", color=color, transform=ax.transAxes)
    ax.text(0.06, 0.09, sub, fontsize=7.5, color=MUTED, transform=ax.transAxes)


def dashboard(summary: pd.DataFrame, daily: pd.DataFrame, attr: pd.DataFrame, n_fail: int, path: Path) -> Path:
    paid = summary[summary.channel.isin(PAID)]
    spend, revenue = paid.spend_eur.sum(), paid.revenue_eur.sum()
    signups = summary.sign_ups.sum()
    fig = plt.figure(figsize=(15, 8.2))
    fig.text(0.02, 0.965, "Kestrel Cloud · Cross-channel marketing performance 2025", fontsize=16,
             fontweight="bold", color=INK)
    fig.text(0.02, 0.935, "Google Ads + Meta Ads + LinkedIn Ads + GA4 blended in one model · synthetic data",
             fontsize=10, color=MUTED)
    w, gap, y = 0.182, 0.0145, 0.775
    _tile(fig, [0.02, y, w, 0.13], "Paid media spend", f"€{spend / 1000:,.0f}k", "3 platforms, EUR-normalised")
    _tile(fig, [0.02 + (w + gap), y, w, 0.13], "Paid revenue (last click)", f"€{revenue / 1000:,.0f}k", "first-year contract value")
    _tile(fig, [0.02 + 2 * (w + gap), y, w, 0.13], "Blended paid ROAS", f"{revenue / spend:.2f}×", "revenue ÷ spend")
    _tile(fig, [0.02 + 3 * (w + gap), y, w, 0.13], "GA4 sign-ups", f"{signups:,.0f}", "all channels")
    _tile(fig, [0.02 + 4 * (w + gap), y, w, 0.13], "Data-quality alerts", f"{n_fail}",
          "tracking breaks & anomalies", color=ALERT if n_fail else "#16A34A")
    monthly_spend_revenue(daily, fig.add_axes([0.04, 0.07, 0.43, 0.6]))
    attribution(attr, fig.add_axes([0.55, 0.07, 0.43, 0.6]))
    return _save(fig, path)


def render_all(con, incidents: pd.DataFrame, anomalies: pd.DataFrame, n_alerts: int, out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    daily = con.execute("SELECT * FROM mart_channel_daily").df()
    campaign_daily = con.execute("SELECT * FROM mart_daily_campaign").df()
    summary = con.execute("SELECT * FROM mart_channel_summary").df()
    attr = con.execute("SELECT * FROM mart_attribution").df()
    pvg = con.execute("SELECT * FROM mart_platform_vs_ga4").df()
    for df in (daily, campaign_daily):
        df["date"] = pd.to_datetime(df["date"])

    paths = [dashboard(summary, daily, attr, n_alerts, out_dir / "dashboard_overview.png")]
    for name, fn, args in [
        ("tracking_break.png", tracking_break, (daily, incidents)),
        ("spend_anomaly.png", spend_anomaly, (campaign_daily, anomalies)),
        ("attribution_comparison.png", attribution, (attr,)),
        ("platform_vs_ga4.png", platform_vs_ga4, (pvg,)),
    ]:
        fig, ax = plt.subplots(figsize=(8, 4.2))
        fn(*args, ax)
        paths.append(_save(fig, out_dir / name))
    return paths


__all__ = ["render_all", "PercentFormatter"]
