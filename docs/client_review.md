# Real-data campaign business review

## What the full release shows
- 16,468,027 observed impressions across 675 campaigns and 31 relative day bins.
- 5,947,563 clicks; weighted CTR: 36.12%.
- 237,157 unique Criteo-credited conversion keys (ID + timestamp) after deduplication; 237,157 have an observed clicked credited impression.
- Post-click credited CVR: 3.99%. CPA: 0.020363 transformed cost units per credited conversion.
- Among campaigns with at least 100 credited conversions and 100 clicks, campaign 2869134 has the lowest observed CPA (0.000402 transformed units). This volume gate is a review heuristic, not a significance test or evidence of incremental effectiveness.

## Recommended conversation
1. Ask Customer Success for the advertiser objective, target efficiency, attribution settings and actual cost/revenue exports before treating these comparisons as actionable client economics.
2. Review the candidate campaign's targeting, bid strategy, product mix and coverage with Ad Operations. Campaign IDs are anonymous; different advertisers and objectives may be mixed, so cross-campaign CPA ranking is only a diagnostic shortlist.
3. Confirm daily coverage and tracking; zero-conversion days produce undefined CPA rather than a misleading zero. Historical subsampled data is not a current performance benchmark.
4. Propose an advertiser-specific, capped experiment only after comparable objectives and measurement are established. No spend shift, dollar return, realized lift, renewal, or upsell result is claimed.

## Conversion accounting
A conversion can be linked to many impressions. Summing the conversion flag would overcount sales. The source reuses 2,910 conversion IDs at different timestamps, so ID alone is not a sufficient event key. This project counts each credited (conversion_id, conversion_timestamp) pair once globally, allocating it to the most recent observed clicked credited impression, or the most recent credited impression if no clicked one is observed. This reporting rule does not recover an unknown platform touchpoint. CVR uses only the clicked subset; CPA uses all unique credited conversions. Filtering by day reports the allocated impression cohort with the source's observed follow-up outcomes, not conversions occurring on that calendar day.

## Integrity
16,468,027 accepted source rows; 0 rejected; 205,267 repeated credited conversion links collapsed. Identical source impressions are not automatically deleted because the source has no impression ID and distinct impressions can share published attributes. 0 credited conversion keys span more than one campaign and are allocated using the same explicit reporting rule. Published data contains campaign/day aggregates, not user IDs or conversion IDs.

## Measurement limits
Source costs are transformed and have no documented currency; revenue is absent. ROAS is unavailable. The cpo field is a transformed cost-per-order field, not revenue. No channel, region, demographic, calendar date or synthetic performance values are invented. Data is historical, anonymized and already subsampled by Criteo; findings describe the release rather than all live traffic. No sampling weights are supplied, so observed CTR/CVR cannot be used as population or industry benchmarks.

Source: https://ailab.criteo.com/criteo-attribution-modeling-bidding-dataset/
Dataset and derived data: CC BY-NC-SA 4.0. Attribution: Diemert, Meynet, Lefortier and Galland (2017), Attribution Modeling Increases Efficiency of Bidding in Display Advertising.
