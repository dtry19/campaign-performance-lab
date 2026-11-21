# Third-party data and derived materials

The **Criteo Attribution Modeling for Bidding Dataset** is provided by Criteo under Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International (CC BY-NC-SA 4.0).

- Source and terms: https://ailab.criteo.com/criteo-attribution-modeling-bidding-dataset/
- Publisher mirror: https://huggingface.co/datasets/criteo/criteo-attribution-dataset
- License: https://creativecommons.org/licenses/by-nc-sa/4.0/
- License legal code: https://creativecommons.org/licenses/by-nc-sa/4.0/legalcode

Attribution: Eustache Diemert, Julien Meynet, Damien Lefortier and Pierre Galland (2017), *Attribution Modeling Increases Efficiency of Bidding in Display Advertising*, AdKDD & TargetAd Workshop. https://arxiv.org/abs/1707.06409

Changes made by this project: validation; rounding transformed costs to 12 decimal places for exact integer accumulation; deduplication of Criteo-credited conversion ID/timestamp keys with a documented project allocation rule; aggregation to relative day and campaign; removal of user/conversion identifiers from published artifacts; weighted KPI calculation; charts, reports and explanatory materials.

The data-derived materials in `data/derived/` and `docs/` are shared under CC BY-NC-SA 4.0. Preserve attribution, identify modifications and retain that license when sharing adaptations. Original code in `src/`, `sql/`, `tests/` and workflow configuration is MIT licensed. The MIT code license does not apply to or override the dataset license.

No endorsement by Criteo, the paper's authors or T-Mobile is implied. The public source is already anonymized and subsampled; no actual currency or undisclosed financial value is inferred.
