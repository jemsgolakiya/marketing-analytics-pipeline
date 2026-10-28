-- LinkedIn Ads: US date format and overlapping exports -> parse and de-duplicate
SELECT DISTINCT
    CAST(STRPTIME("Start Date (in UTC)", '%m/%d/%Y') AS DATE) AS date,
    'LinkedIn Ads'                                   AS platform,
    "Campaign Name"                                  AS campaign,
    UPPER(TRIM("Campaign Name"))                     AS campaign_key,
    CAST("Total Spent" AS DOUBLE)                    AS spend_eur,
    CAST("Impressions" AS BIGINT)                    AS impressions,
    CAST("Clicks" AS BIGINT)                         AS clicks,
    CAST("Conversions" AS DOUBLE)                    AS platform_conversions
FROM raw_linkedin_ads_export
