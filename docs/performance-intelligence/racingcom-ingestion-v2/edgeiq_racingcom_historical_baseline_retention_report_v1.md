# Historical Baseline Retention V1

The production warehouse is runner-grain with 80 historical CSV runner records across 8 races. Earlier 574-row counts refer to historical normalised sectional records at a different grain, not a contradiction.

- Historical races retained: `8/8`
- Historical runner keys retained: `80/80`
- Historical CSV parser remains the adapter for historical CSV.
- GraphQL parser adds separate segment-grain records and does not overwrite historical CSV records.
