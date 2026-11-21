# Campaign Performance Lab

**Real advertising data → checked campaign metrics → a clear client conversation.**

This independent portfolio project analyzes Criteo's real, anonymized display-ad research release using Python and SQL. It produces an interactive offline dashboard, Excel-compatible CSVs, an auditable quality report, and a client-style business review.

![Real-data campaign dashboard](docs/dashboard-preview.png)

## In plain English

Think of a campaign manager asking, “Are people clicking our ads, are those interactions linked to sales, and where should we investigate performance?” This project:

1. Reads the real advertising records released by Criteo.
2. Checks the fields and totals so broken records do not silently distort the report.
3. Counts ad displays, clicks and distinct credited conversion events for each campaign and relative day. A conversion key linked to several ads is counted once.
4. Calculates campaign metrics and presents them in a dashboard with filters, ranking and CSV downloads.
5. Writes a short business review explaining the findings, next questions and limits.

This is a reporting and analysis project, not an ad-buying system or a claim of client impact. See [the walkthrough](docs/PROJECT_WALKTHROUGH.md).

## Open the project

Requires Python 3.10+; no third-party Python packages, keys or paid account.

```bash
python3 src/pipeline.py
python3 -m unittest discover -s tests -v
```

Open `docs/index.html` in a browser. The dashboard embeds only campaign/day aggregates and works offline. Or serve it locally:

```bash
python3 -m http.server 8000 --directory docs
```

Then visit http://localhost:8000. Choose a campaign and relative day range, sort the campaign table, apply a minimum-conversions threshold, and download the table as CSV. The minimum-conversions threshold affects the campaign table/chart/export; cards and daily totals continue to represent all selected campaigns.

The default rebuild uses the committed real-data aggregates, so it is fast and reproducible without downloading the large source file. It does **not** generate simulated observations.

## Reproduce from the original records

The full original file is approximately 653 MB compressed and is excluded from Git. To independently reproduce the aggregate import:

```bash
python3 src/fetch_data.py
python3 src/pipeline.py --from-source data/source/criteo_attribution_dataset.tsv.gz
```

The downloader pins the publisher revision and checks the SHA-256. The importer refuses a source file with a different hash, reads the full file, validates each record, and writes aggregate CSVs plus an import audit into `data/derived/`. This can take several minutes. The importer retains no user ID, conversion ID, or contextual fingerprint in published outputs.

- Publisher: [Criteo AI Lab](https://ailab.criteo.com/criteo-attribution-modeling-bidding-dataset/)
- Publisher's mirror: [criteo/criteo-attribution-dataset](https://huggingface.co/datasets/criteo/criteo-attribution-dataset)
- Pinned revision: `904188a63cbad78bee43cd26ff5ee4ac77903986`
- Source SHA-256: `94ac7a465564349bc7ba008602211d5990a3c53cc133abc0aadef61ea2391a98`
- Coverage: the entire pinned release, with no additional sampling by this project. Criteo already subsampled and anonymized the underlying live traffic.
- Historical research release associated with the authors' 2017 paper; not current T-Mobile or Criteo campaign reporting.

Exact imported counts are in [summary.json](docs/summary.json), [quality.json](docs/quality.json) and [provenance.json](docs/provenance.json).

## Observed release totals

- 16,468,027 accepted impressions; 5,947,563 clicks; 675 campaigns.
- 20,665 campaign/day aggregates across 31 relative day bins.
- 237,157 distinct Criteo-credited conversion keys after collapsing 205,267 repeated links.
- 2,910 conversion IDs occur at more than one conversion timestamp; ID/time pairs are used to distinguish recorded events.
- Zero rows failed the implemented field checks. This does not establish that every source record is free of measurement issues.

The observed CTR is 36.12% and post-click credited CVR is 3.99% **in this subsampled release**. These are not population or industry benchmarks, and the project claims no performance improvement. An independent pandas pass over the original file confirmed impression/click totals, 438,730 observed conversion keys, 237,157 credited keys and the 2,910 reused IDs.

## What the metrics mean

| Metric | Calculation | Important interpretation |
|---|---|---|
| Impressions | Count of accepted source records | Ad displays observed in the public release |
| CTR | Total clicks / total impressions | Share of displays that were clicked |
| Credited conversions | Distinct (conversion ID, conversion timestamp) pairs with attribution flag 1 | Counted once globally using the allocation rule below |
| Post-click credited CVR | Credited conversions with an observed clicked credited impression / total clicks | Uses the clicked subset, not every credited sale |
| Transformed CPA | Total transformed cost / all credited conversions | Includes credited sales without an observed click; units have no documented currency |
| ROAS | Unavailable | Source does not contain sales revenue |

All rates are ratios of sums, not averages of row rates. Because the publisher subsampled the source traffic and supplies no sampling weights, observed CTR and CVR are sample-specific and must not be treated as population or industry benchmarks. SQL returns NULL and the dashboard shows an em dash when a denominator is zero. The source `cpo` field is transformed cost per order, **not revenue**. No dollar costs, calendar dates, channels, regions or missing financial results are invented.

### Why conversion deduplication matters

One conversion can be linked to multiple impressions. Summing the raw `conversion` flag would overcount sales. The source contains reused conversion IDs at different conversion timestamps. The importer therefore counts each credited `(conversion_id, conversion_timestamp)` key once globally, rather than merging separate timestamped events under one ID. For campaign/day reporting, it selects the latest observed clicked impression linked to that credited conversion; if no clicked one is observed, it selects the latest linked credited impression. Ties resolve by campaign ID, then source row.

This is an explicit project allocation convention over the observed subsample. It does not reconstruct the platform's exact credited touchpoint, prove causality, or identify every click from the original traffic. A day filter selects allocated impression cohorts and their observed follow-up outcomes; it is not a count of sales occurring on that calendar day. The quality report separately audits reused IDs and conversion keys appearing against multiple campaigns. These are recorded data limitations; the composite key is an explicit operational definition, not a verified count of underlying transactions.

There is no impression ID in the release, so identical published attributes are not automatically deleted: separate legitimate impressions can look identical. Deduplication applies to composite conversion keys for conversion accounting, not arbitrary removal of ad events.

### Cost precision

Source cost is transformed by Criteo. Each value is rounded to 12 decimal places and stored as integer scaled units (`cost_scaled`, scale 10^12). This avoids accumulated binary floating-point error during ingestion and SQL aggregation. Final ratios use floating point for display. It does not recover actual currency, actual media spend or real financial returns.

## Reporting integrity

- Validate required fields, numeric format, finite/nonnegative cost, binary flags, relative timestamps, and conversion metadata.
- Preserve rejected source positions and reasons without publishing identifiers.
- Reconcile raw accepted impressions, clicks, credited sales and scaled cost to campaign/day totals and SQL views.
- Test repeated sale links, no-observed-click conversions, non-Criteo conversions, malformed records, precision, zero denominators and weighted rates.
- Rebuild the dashboard and reports from versioned aggregates in GitHub Actions and fail if generated text artifacts differ.

Test fixtures are intentionally artificial and live only in tests. No bad rows are injected into the production data. A zero-row quarantine is a valid audit result, not a reason to manufacture errors.

## From findings to recommendations

The [business review](docs/client_review.md) reports observed totals and identifies a campaign for investigation using a disclosed minimum-volume heuristic. Campaign IDs may represent different advertisers, product mixes and goals, so a low CPA is only a diagnostic shortlist. It is not sufficient evidence to reallocate spend across advertisers.

Customer Success would confirm objectives and attribution settings; Ad Operations would inspect tracking, targeting and delivery; Sales would need actual client economics and validated results before proposing renewal or expansion. This project does not claim actual collaboration with these teams, business lift, client adoption or revenue improvement.

## Files

| Path | Purpose |
|---|---|
| `src/fetch_data.py` | Pinned source download and checksum verification |
| `src/pipeline.py` | Full-source ingestion, validation, sale deduplication and offline reporting |
| `sql/metrics.sql` | Campaign, daily and overall weighted metrics |
| `src/dashboard.html` | Dashboard template |
| `data/derived/` | Real campaign/day aggregates, provenance and import audit |
| `docs/` | Generated dashboard, review, CSVs and walkthrough |
| `tests/test_pipeline.py` | Meaningful accounting and metric edge-case tests |
| `.github/workflows/validate.yml` | Tests and aggregate-to-report reproducibility |

The generated SQLite database is local and ignored. To query it using the optional SQLite CLI:

```bash
sqlite3 -header -csv docs/campaigns.sqlite \
  "SELECT * FROM campaign_kpis WHERE conversions >= 100 ORDER BY cpa_transformed LIMIT 10;"
```

## Attribution and licensing

Dataset: Criteo Attribution Modeling for Bidding Dataset. Cite Eustache Diemert, Julien Meynet, Damien Lefortier and Pierre Galland (2017), *Attribution Modeling Increases Efficiency of Bidding in Display Advertising*, AdKDD & TargetAd Workshop. [Paper](https://arxiv.org/abs/1707.06409).

The Criteo dataset and data-derived materials in `data/derived/` and `docs/` are under **[CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/)**. This project changes the source into validated campaign/day aggregates and reporting artifacts. The code is separately MIT licensed; MIT does not relicense Criteo's data. See [DATA_LICENSE.md](DATA_LICENSE.md).

The earlier Git history contains the initial synthetic prototype. The current default branch and dashboard use real source data exclusively.
