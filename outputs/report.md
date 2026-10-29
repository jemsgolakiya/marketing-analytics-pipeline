# Marketing performance report: Kestrel Cloud 2025

_Generated 2026-10-29 by `python -m marketing_pipeline.run` · synthetic data_

## Data-quality checks

|  | Check | Result |
|---|---|---|
| ✅ | Raw exports are not empty | All raw exports contain rows |
| ⚠️ | Duplicate rows in LinkedIn export | 28 duplicated rows found in the raw export and removed in staging |
| ✅ | One row per day and campaign in the spend model | 0 duplicated day/campaign keys |
| ✅ | Spend reconciles from raw export to model | Google Ads: raw EUR 121,983.69 vs model EUR 121,983.69 |
| ✅ | Paid traffic carries a campaign UTM | 3.0% of paid sessions have campaign '(not set)'; 0 rows with an unmapped source/medium |
| ❌ | No conversion tracking breaks | Meta Ads 2025-06-10 to 2025-06-24 (4 recorded vs ~50 expected) |

## Tracking incidents

| channel | start | end | days | sessions | sign_ups_recorded | sign_ups_expected |
|---|---|---|---|---|---|---|
| Meta Ads | 2025-06-10 | 2025-06-24 | 15 | 2752 | 4 | 50 |

## Spend anomalies

| date | platform | campaign | spend_eur | cpc_eur | sign_ups | spend_z | cpc_z |
|---|---|---|---|---|---|---|---|
| 2025-09-15 | Google Ads | GGL_Search_NonBrand | 717.81 | 6.71 | 4 | 8.3 | 8.6 |
| 2025-09-16 | Google Ads | GGL_Search_NonBrand | 762.38 | 8.66 | 2 | 8.3 | 13.5 |
| 2025-09-17 | Google Ads | GGL_Search_NonBrand | 873.43 | 10.16 | 2 | 9.5 | 17.2 |

## Channel scorecard

| Channel | Spend | Sign-ups | CPA | CVR | Revenue (last click) | ROAS |
|---|---|---|---|---|---|---|
| Google Ads | €121,984 | 2,397 | €51 | 5.33% | €754,482 | 6.19× |
| LinkedIn Ads | €94,498 | 371 | €255 | 2.88% | €64,603 | 0.68× |
| Meta Ads | €68,284 | 1,323 | €52 | 2.06% | €273,107 | 4.00× |
| Organic Search | €0 | 3,014 | – | 2.23% | €630,481 | – |
| Direct | €0 | 1,522 | – | 1.83% | €434,476 | – |
| Email | €0 | 659 | – | 2.91% | €165,470 | – |
| Referral | €0 | 543 | – | 4.88% | €154,199 | – |

## ROAS under different attribution models

| model | Google Ads | LinkedIn Ads | Meta Ads |
|---|---|---|---|
| First click | 4.20× | 4.55× | 5.99× |
| Last click | 6.19× | 0.68× | 4.00× |
| Linear | 4.92× | 2.98× | 5.28× |
| Position based (40/20/40) | 5.07× | 2.77× | 5.10× |

## Platform-reported vs. GA4-measured conversions

| Platform | Platform reported | GA4 measured | Over-reporting |
|---|---|---|---|
| Meta Ads | 2,186 | 1,284 | +70% |
| LinkedIn Ads | 521 | 358 | +46% |
| Google Ads | 2,545 | 2,336 | +9% |
