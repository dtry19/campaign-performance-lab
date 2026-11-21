-- Weighted KPIs: dollars from cents; NULL denotes undefined ratios.
DROP VIEW IF EXISTS campaign_kpis;
CREATE VIEW campaign_kpis AS
SELECT campaign, channel, SUM(impressions) impressions, SUM(clicks) clicks,
 SUM(conversions) conversions, SUM(spend_cents)/100.0 spend,
 SUM(revenue_cents)/100.0 revenue,
 1.0*SUM(clicks)/NULLIF(SUM(impressions),0) ctr,
 1.0*SUM(conversions)/NULLIF(SUM(clicks),0) cvr,
 SUM(spend_cents)/100.0/NULLIF(SUM(conversions),0) cpa,
 1.0*SUM(revenue_cents)/NULLIF(SUM(spend_cents),0) roas
FROM campaign_daily GROUP BY campaign, channel;
DROP VIEW IF EXISTS channel_kpis;
CREATE VIEW channel_kpis AS
SELECT channel, SUM(spend) spend, SUM(revenue) revenue,
 1.0*SUM(clicks)/NULLIF(SUM(impressions),0) ctr,
 1.0*SUM(conversions)/NULLIF(SUM(clicks),0) cvr,
 SUM(spend)/NULLIF(SUM(conversions),0) cpa,
 SUM(revenue)/NULLIF(SUM(spend),0) roas
FROM campaign_kpis GROUP BY channel;
DROP VIEW IF EXISTS period_kpis;
CREATE VIEW period_kpis AS
SELECT channel, CASE WHEN date < '2026-10-01' THEN 'First 30 days' ELSE 'Last 30 days' END period,
 SUM(impressions) impressions, SUM(clicks) clicks, SUM(conversions) conversions,
 SUM(spend_cents)/100.0 spend, SUM(revenue_cents)/100.0 revenue,
 1.0*SUM(conversions)/NULLIF(SUM(clicks),0) cvr,
 1.0*SUM(revenue_cents)/NULLIF(SUM(spend_cents),0) roas
FROM campaign_daily GROUP BY channel, period;
