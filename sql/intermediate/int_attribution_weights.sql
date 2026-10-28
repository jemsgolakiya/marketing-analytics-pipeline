-- Credit per touchpoint under four attribution models.
-- Every conversion's weights sum to exactly 1 for each model.
WITH ordered AS (
    SELECT
        *,
        ROW_NUMBER() OVER (PARTITION BY conversion_id ORDER BY touch_date, channel) AS pos,
        COUNT(*)     OVER (PARTITION BY conversion_id)                              AS n
    FROM stg_touchpoints
)
SELECT
    conversion_id, touch_date, conversion_date, channel, revenue_eur, pos, n,
    CASE WHEN pos = n THEN 1.0 ELSE 0.0 END                                  AS w_last_click,
    CASE WHEN pos = 1 THEN 1.0 ELSE 0.0 END                                  AS w_first_click,
    1.0 / n                                                                  AS w_linear,
    CASE
        WHEN n = 1 THEN 1.0
        WHEN n = 2 THEN 0.5
        WHEN pos = 1 OR pos = n THEN 0.4
        ELSE 0.2 / (n - 2)
    END                                                                      AS w_position_based
FROM ordered
