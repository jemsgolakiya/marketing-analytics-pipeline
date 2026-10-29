-- Revenue and conversions credited to each channel under each attribution model
WITH credit AS (
    UNPIVOT int_attribution_weights
    ON w_last_click AS 'Last click', w_first_click AS 'First click',
       w_linear AS 'Linear', w_position_based AS 'Position based (40/20/40)'
    INTO NAME model VALUE weight
), spend AS (
    SELECT platform AS channel, SUM(spend_eur) AS spend_eur FROM int_ad_spend GROUP BY ALL
)
SELECT
    c.model,
    c.channel,
    SUM(c.weight)                                          AS credited_conversions,
    SUM(c.weight * c.revenue_eur)                          AS credited_revenue_eur,
    SUM(c.weight * c.revenue_eur)
        / SUM(SUM(c.weight * c.revenue_eur)) OVER (PARTITION BY c.model) AS revenue_share,
    SUM(c.weight * c.revenue_eur) / NULLIF(ANY_VALUE(s.spend_eur), 0)  AS roas
FROM credit AS c
LEFT JOIN spend AS s USING (channel)
GROUP BY c.model, c.channel
ORDER BY c.model, credited_revenue_eur DESC
