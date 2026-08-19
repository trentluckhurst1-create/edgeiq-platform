# EDGEiQ Governed Race-Time Unit Resolution V0.1

## Race identity

Race-time consistency must use:

- race date
- jurisdiction
- track
- race number
- provider race ID

Provider race ID alone is not globally unique.

## Source unit

The historical GraphQL winning-time field is predominantly stored as centiseconds.

The governed conversion is:

seconds = raw centiseconds / 100

## Preservation

A corrected warehouse must retain:

- raw source value
- source unit
- governed seconds
- unit-rule version
- quality state

## Anomalies

Values that plausibly use another unit are quarantined.

They do not redefine the source contract and are not automatically converted.

## Benchmark rule

Only races classified as CENTISECONDS_CONFIRMED are benchmark eligible.
