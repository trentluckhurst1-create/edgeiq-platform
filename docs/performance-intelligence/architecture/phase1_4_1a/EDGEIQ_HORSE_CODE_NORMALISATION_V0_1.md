# EDGEiQ Horse-Code Normalisation V0.1

## Problem corrected

CSV numeric parsing may represent an integer horse code as:

`577170.0`

while another source stores:

`577170`

These are formatting variants of the same integer-like value.

## Canonical normalisation

Integer-like horse codes are represented without a decimal suffix.

Examples:

- `577170.0` becomes `577170`
- `00577170` remains provider-specific text unless parsed numerically
- non-numeric codes remain normalised text

## Governance boundary

Code normalisation proves linkage compatibility.

It does not by itself prove that the code is an official globally durable horse-registration identity.

Canonical horse promotion still requires corroborating durability evidence.
