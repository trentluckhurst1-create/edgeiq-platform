# EDGEiQ Racing Australia Horse Identity Governance V0.1

## Racing Australia identity

The Base64 HorseCode decodes into a numeric Racing Australia horse identifier.

Repeated source rows do not automatically indicate duplicate horses.

They may represent the same horse appearing in multiple current race entries.

## Duplicate-source rule

When one decoded Racing Australia ID has one stable normalised name:

- preserve every source row
- materialise one provider identity candidate
- retain source membership and lineage
- do not treat repeat rows as an identity failure

When one decoded ID has multiple names:

- classify as an identity conflict
- block promotion
- preserve every conflicting row

## Historical crosswalk rule

Exact-name equality creates candidate evidence only.

Temporal separation may identify an older namesake and one currently active horse, but it still does not authorise an automatic cross-provider merge.

## Canonical boundary

No canonical horse ID is created in this phase.
