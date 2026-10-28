-- Meta Ads: account is billed in USD -> convert to EUR with the daily ECB-style rate
SELECT
    CAST(m.date_start AS DATE)                       AS date,
    'Meta Ads'                                       AS platform,
    m.campaign_name                                  AS campaign,
    UPPER(TRIM(m.campaign_name))                     AS campaign_key,
    CAST(m.spend AS DOUBLE) / CAST(fx.usd_per_eur AS DOUBLE) AS spend_eur,
    CAST(m.impressions AS BIGINT)                    AS impressions,
    CAST(m.inline_link_clicks AS BIGINT)             AS clicks,
    CAST(m.actions_lead AS DOUBLE)                   AS platform_conversions
FROM raw_meta_ads_export AS m
JOIN raw_fx_rates AS fx
  ON CAST(fx.date AS DATE) = CAST(m.date_start AS DATE)
