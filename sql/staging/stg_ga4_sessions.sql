-- GA4: harmonise inconsistent UTM tagging into one channel grouping
SELECT
    CAST(STRPTIME(event_date, '%Y%m%d') AS DATE)     AS date,
    session_source,
    session_medium,
    CASE
        WHEN LOWER(session_source) = 'google' AND session_medium = 'cpc'                 THEN 'Google Ads'
        WHEN LOWER(session_source) IN ('facebook', 'fb', 'meta', 'instagram')            THEN 'Meta Ads'
        WHEN LOWER(session_source) IN ('linkedin', 'lnkd')                               THEN 'LinkedIn Ads'
        WHEN session_medium = 'organic'                                                  THEN 'Organic Search'
        WHEN session_medium = 'email'                                                    THEN 'Email'
        WHEN session_medium = 'referral'                                                 THEN 'Referral'
        WHEN session_source = '(direct)'                                                 THEN 'Direct'
        ELSE 'Unmapped'
    END                                              AS channel,
    CASE WHEN session_campaign IN ('(not set)', '(organic)') THEN NULL
         ELSE UPPER(TRIM(session_campaign)) END      AS campaign_key,
    CAST(sessions AS BIGINT)                         AS sessions,
    CAST(sign_ups AS BIGINT)                         AS sign_ups
FROM raw_ga4_sessions_export
