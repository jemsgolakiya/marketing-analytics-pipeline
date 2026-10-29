-- Yearly KPI scorecard per channel (last-click revenue, GA4 sign-ups as the conversion)
SELECT
    channel,
    SUM(spend_eur)                                         AS spend_eur,
    SUM(impressions)                                       AS impressions,
    SUM(clicks)                                            AS clicks,
    SUM(sessions)                                          AS sessions,
    SUM(ga4_sign_ups)                                      AS sign_ups,
    SUM(purchases)                                         AS purchases,
    SUM(revenue_eur)                                       AS revenue_eur,
    SUM(clicks) / NULLIF(SUM(impressions), 0)              AS ctr,
    SUM(spend_eur) / NULLIF(SUM(clicks), 0)                AS cpc_eur,
    SUM(ga4_sign_ups) / NULLIF(SUM(sessions), 0)           AS conversion_rate,
    SUM(spend_eur) / NULLIF(SUM(ga4_sign_ups), 0)          AS cpa_eur,
    SUM(revenue_eur) / NULLIF(SUM(spend_eur), 0)           AS roas
FROM mart_channel_daily
GROUP BY channel
ORDER BY spend_eur DESC, revenue_eur DESC
