# Downstream Compatibility Review V1

Is the candidate a drop-in replacement? `NO`.

The production warehouse is runner-grain. The candidate is mixed runner-aggregate plus GraphQL segment-grain. Production consumers should not receive the candidate without a canonical adapter or explicit contract migration.

Compatibility status: `REQUIRES_ADAPTER`.
