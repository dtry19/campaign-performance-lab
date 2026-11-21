# Synthetic client business review

All results below come from a seeded simulation, not a T-Mobile campaign or client.

## Decision brief
- Highest observed channel ROAS: Mobile Web (7.38x); lowest: Online Video (1.65x).
- Investigate Online Video by campaign, region, creative and attribution lag before changing investment. The simulator deliberately introduces an Online Video conversion-rate decline after day 30; this is a test of detection, not a discovered real-world effect.
- Consider a capped experiment reallocating 10% of Online Video spend ($32,728.61) toward Mobile Web, subject to inventory, marginal costs and measurement checks.
- Holding observed average returns constant would imply $187,722.24 additional attributed revenue. This is scenario arithmetic, **not measured lift, incremental revenue, a forecast, or a causal estimate**.

## Reporting integrity
3,240 accepted records; 9 quarantined out of 3,249 input records. See quality.json and quarantine.json for auditable reasons. Monetary values use integer cents. All rates are ratios of summed components, never averages of row rates.

## Client discussion
1. Confirm the business objective and target CPA/ROAS with Customer Success; no client targets are assumed here.
2. Ask Ad Operations to review tracking, creative rotation, frequency and landing-page changes in the weaker segment.
3. Review the first/last 30-day comparison in period_kpis.csv and the dashboard; evaluate attribution lag before calling a decline.
4. Validate results with a controlled test and agreed success criteria before discussing expansion with Sales. Renewal or upsell is conditional on evidence and client goals.

## Measurement boundary
CVR is conversions/clicks; ROAS is attributed revenue/spend, not profit. Click-attributed conversions cannot exceed clicks in this fixture. No user-level data, attribution engine, actual DSP integration, CTV, DOOH, reach/frequency measurement or causal lift measurement is included. Cross-channel attribution comparability is an assumption of this simulation.
