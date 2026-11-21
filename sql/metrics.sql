-- Source cost rounded per impression to 12 decimal places, stored as integers.
-- Cost has transformed units, NOT dollars. No revenue or fabricated ROAS.
DROP VIEW IF EXISTS campaign_kpis;
CREATE VIEW campaign_kpis AS
SELECT campaign, SUM(impressions) impressions, SUM(clicks) clicks,
 SUM(conversions) conversions, SUM(post_click_conversions) post_click_conversions,
 SUM(cost_scaled)/1000000000000.0 transformed_cost,
 1.0*SUM(clicks)/NULLIF(SUM(impressions),0) ctr,
 1.0*SUM(post_click_conversions)/NULLIF(SUM(clicks),0) post_click_cvr,
 SUM(cost_scaled)/1000000000000.0/NULLIF(SUM(conversions),0) cpa_transformed,
 SUM(cost_scaled)/1000000000000.0/NULLIF(SUM(clicks),0) cpc_transformed
FROM campaign_daily GROUP BY campaign;
DROP VIEW IF EXISTS daily_kpis;
CREATE VIEW daily_kpis AS
SELECT day, SUM(impressions) impressions, SUM(clicks) clicks,
 SUM(conversions) conversions, SUM(post_click_conversions) post_click_conversions,
 SUM(cost_scaled)/1000000000000.0 transformed_cost,
 1.0*SUM(clicks)/NULLIF(SUM(impressions),0) ctr,
 1.0*SUM(post_click_conversions)/NULLIF(SUM(clicks),0) post_click_cvr,
 SUM(cost_scaled)/1000000000000.0/NULLIF(SUM(conversions),0) cpa_transformed
FROM campaign_daily GROUP BY day;
DROP VIEW IF EXISTS overall_kpis;
CREATE VIEW overall_kpis AS
SELECT SUM(impressions) impressions, SUM(clicks) clicks,
 SUM(conversions) conversions, SUM(post_click_conversions) post_click_conversions,
 SUM(cost_scaled)/1000000000000.0 transformed_cost,
 1.0*SUM(clicks)/NULLIF(SUM(impressions),0) ctr,
 1.0*SUM(post_click_conversions)/NULLIF(SUM(clicks),0) post_click_cvr,
 SUM(cost_scaled)/1000000000000.0/NULLIF(SUM(conversions),0) cpa_transformed
FROM campaign_daily;
