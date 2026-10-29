-- Blended daily view: platform spend joined to GA4 outcomes on a shared campaign key
WITH ga4 AS (
    SELECT date, campaign_key, channel AS platform,
           SUM(sessions) AS sessions, SUM(sign_ups) AS ga4_sign_ups
    FROM stg_ga4_sessions
    WHERE channel IN ('Google Ads', 'Meta Ads', 'LinkedIn Ads') AND campaign_key IS NOT NULL
    GROUP BY ALL
)
SELECT
    s.date, s.platform, s.campaign, s.campaign_key,
    s.spend_eur, s.impressions, s.clicks, s.platform_conversions,
    COALESCE(g.sessions, 0)       AS sessions,
    COALESCE(g.ga4_sign_ups, 0)   AS ga4_sign_ups
FROM int_ad_spend AS s
LEFT JOIN ga4 AS g USING (date, campaign_key, platform)
