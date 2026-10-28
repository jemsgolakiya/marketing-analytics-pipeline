-- One spend model for all ad platforms with shared definitions
SELECT * FROM stg_google_ads
UNION ALL BY NAME
SELECT * FROM stg_meta_ads
UNION ALL BY NAME
SELECT * FROM stg_linkedin_ads
