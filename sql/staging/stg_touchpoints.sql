SELECT
    conversion_id,
    CAST(touch_ts AS DATE)                           AS touch_date,
    channel,
    CAST(conversion_date AS DATE)                    AS conversion_date,
    CAST(revenue_eur AS DOUBLE)                      AS revenue_eur
FROM raw_ga4_conversion_paths
