-- How much each ad platform over-reports conversions compared with GA4
SELECT
    platform,
    SUM(platform_conversions)                              AS platform_reported,
    SUM(ga4_sign_ups)                                      AS ga4_measured,
    SUM(platform_conversions) / NULLIF(SUM(ga4_sign_ups), 0) AS over_reporting_ratio
FROM mart_daily_campaign
GROUP BY platform
ORDER BY over_reporting_ratio DESC
