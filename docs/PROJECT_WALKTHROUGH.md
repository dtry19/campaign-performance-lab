# What this project does, in simple terms

Imagine an advertising team has a large spreadsheet of ad activity and needs a clear update for a client.

**The question:** Which campaigns attract clicks, which are linked to credited sales, and which need investigation?

## 1. Start with real records

We use Criteo's public research dataset. Each record represents an ad display. It tells us the anonymous campaign, relative time, click status, conversion information and a disguised cost. This is historical real activity; it is not a new campaign we ran.

## 2. Check the inputs

The code checks for things such as missing fields, impossible flag values and negative costs. It writes a quality report. It does not invent bad records just to show that cleaning happened.

## 3. Count sales correctly

Several ads can be linked to the same sale. Counting every link would exaggerate sales. Some sale IDs recur at different timestamps. The code combines the sale ID and timestamp into an event key to avoid merging those entries, counts each key once and publishes only campaign/day totals. It uses a documented reporting rule to choose the associated impression and does not publish user or sale identifiers.

## 4. Calculate useful metrics

- **CTR:** If an ad was shown 1,000 times and clicked 10 times, CTR is 1%.
- **Post-click credited conversion rate:** Of the observed clicks, how many are represented by unique credited sales with an observed clicked impression?
- **CPA:** How much transformed cost is associated with each unique credited sale? The dataset's disguised costs are not dollars.
- **ROAS:** Normally sales revenue divided by ad spend. We cannot calculate it here because revenue is missing.

## 5. Make the results easy to explore

The dashboard lets someone pick a campaign and day range, compare campaign metrics, inspect daily results and export a CSV for Excel. A minimum-sales filter helps avoid being distracted by tiny samples, but it does not prove that a difference is statistically reliable.

## 6. Turn numbers into a business conversation

The review explains the observed results and what to check next. A low CPA might be worth investigating, but campaigns can sell different things or serve different objectives. We would ask for business targets, actual costs/revenue and a controlled test before recommending budget changes.

## What you built for the resume

A Python and SQL analytics workflow that transforms a large real advertising log into validated campaign reporting, an interactive dashboard and a business review. It demonstrates data quality, advertising KPI definitions and communication of measurement limits. It does not establish that you ran advertising campaigns or improved a real client's sales.

Source: https://ailab.criteo.com/criteo-attribution-modeling-bidding-dataset/
Data-derived materials: CC BY-NC-SA 4.0. Attribution: Diemert, Meynet, Lefortier and Galland (2017), *Attribution Modeling Increases Efficiency of Bidding in Display Advertising*.
