-- Google Ads: cost is exported in micros, campaign names are the source of truth
SELECT
    CAST("Day" AS DATE)                              AS date,
    'Google Ads'                                     AS platform,
    "Campaign"                                       AS campaign,
    UPPER(TRIM("Campaign"))                          AS campaign_key,
    CAST("Cost (micros)" AS BIGINT) / 1e6            AS spend_eur,
    CAST("Impressions" AS BIGINT)                    AS impressions,
    CAST("Clicks" AS BIGINT)                         AS clicks,
    CAST("Conversions" AS DOUBLE)                    AS platform_conversions
FROM raw_google_ads_export
