import pytest

from marketing_pipeline import anomaly, quality, warehouse


@pytest.fixture(scope="module")
def con():
    return warehouse.build()


def test_attribution_weights_sum_to_one(con):
    bad = con.execute("""
        SELECT COUNT(*) FROM (
            SELECT conversion_id,
                   SUM(w_last_click) a, SUM(w_first_click) b, SUM(w_linear) c, SUM(w_position_based) d
            FROM int_attribution_weights GROUP BY conversion_id)
        WHERE abs(a - 1) > 1e-9 OR abs(b - 1) > 1e-9 OR abs(c - 1) > 1e-9 OR abs(d - 1) > 1e-9
    """).fetchone()[0]
    assert bad == 0


def test_every_model_credits_all_revenue(con):
    totals = con.execute("SELECT model, SUM(credited_revenue_eur) FROM mart_attribution GROUP BY model").fetchall()
    per_conv = con.execute("SELECT SUM(revenue_eur) FROM (SELECT DISTINCT conversion_id, revenue_eur FROM stg_touchpoints)").fetchone()[0]
    assert per_conv > 0
    for _, total in totals:
        assert total == pytest.approx(per_conv)


def test_linkedin_duplicates_removed(con):
    raw = con.execute("SELECT COUNT(*) FROM raw_linkedin_ads_export").fetchone()[0]
    clean = con.execute("SELECT COUNT(*) FROM stg_linkedin_ads").fetchone()[0]
    assert raw - clean == 28


def test_spend_model_grain(con):
    assert quality.check_grain(con).status == "pass"


def test_spend_reconciles(con):
    assert quality.check_spend_reconciliation(con).status == "pass"


def test_meta_spend_converted_to_eur(con):
    raw_usd = con.execute("SELECT SUM(CAST(spend AS DOUBLE)) FROM raw_meta_ads_export").fetchone()[0]
    eur = con.execute("SELECT SUM(spend_eur) FROM stg_meta_ads").fetchone()[0]
    assert eur < raw_usd  # EUR is worth more than USD throughout 2025


def test_no_unmapped_channels(con):
    assert con.execute("SELECT COUNT(*) FROM stg_ga4_sessions WHERE channel = 'Unmapped'").fetchone()[0] == 0


def test_tracking_break_detected_exactly(con):
    incidents = quality.detect_tracking_breaks(con)
    assert len(incidents) == 1
    row = incidents.iloc[0]
    assert row.channel == "Meta Ads"
    assert str(row.start) == "2025-06-10" and str(row.end) == "2025-06-24"


def test_spend_spike_detected(con):
    hits = anomaly.detect_spend_anomalies(con)
    assert set(hits.campaign) == {"GGL_Search_NonBrand"}
    assert {str(d) for d in hits.date} == {"2025-09-15", "2025-09-16", "2025-09-17"}
