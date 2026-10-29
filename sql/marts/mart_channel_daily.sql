-- Daily KPIs per channel. Sessions and sign-ups include untagged ("(not set)") traffic.
WITH spend AS (
    SELECT date, platform AS channel, SUM(spend_eur) AS spend_eur, SUM(impressions) AS impressions,
           SUM(clicks) AS clicks, SUM(platform_conversions) AS platform_conversions
    FROM int_ad_spend GROUP BY ALL
), ga4 AS (
    SELECT date, channel, SUM(sessions) AS sessions, SUM(sign_ups) AS ga4_sign_ups
    FROM stg_ga4_sessions GROUP BY ALL
), revenue AS (
    SELECT conversion_date AS date, channel, COUNT(*) AS purchases, SUM(revenue_eur) AS revenue_eur
    FROM int_attribution_weights WHERE w_last_click = 1 GROUP BY ALL
)
SELECT
    date, channel,
    COALESCE(spend_eur, 0)            AS spend_eur,
    COALESCE(impressions, 0)          AS impressions,
    COALESCE(clicks, 0)               AS clicks,
    COALESCE(platform_conversions, 0) AS platform_conversions,
    COALESCE(sessions, 0)             AS sessions,
    COALESCE(ga4_sign_ups, 0)         AS ga4_sign_ups,
    COALESCE(purchases, 0)            AS purchases,
    COALESCE(revenue_eur, 0)          AS revenue_eur
FROM ga4
FULL OUTER JOIN spend   USING (date, channel)
FULL OUTER JOIN revenue USING (date, channel)
