# EDGEiQ Non-Blank Race-Time Consistency V0.1

## Core rule

Blank winning-time values are missing evidence.

They are not timing values and cannot create a race-time conflict.

## Race classifications

### CONSISTENT_COMPLETE

One unique numeric winning-time value and no blank or invalid rows.

### CONSISTENT_WITH_MISSING

One unique numeric winning-time value and one or more blank rows.

### NO_TIME_AVAILABLE

No numeric winning-time evidence exists.

### MULTIPLE_NON_BLANK_VALUES

Two or more distinct numeric winning-time values exist within one governed race context.

This is a genuine source conflict.

### INVALID_TIME_VALUE

At least one populated winning-time value cannot be parsed as a positive numeric value.

## Unit rule

A consistent numeric race time may be converted from centiseconds to seconds only when the resulting race speed is plausible and competing units are implausible.

## Benchmark eligibility

A race is eligible only when:

- its consistency state is CONSISTENT_COMPLETE or CONSISTENT_WITH_MISSING
- its time unit is CENTISECONDS_CONFIRMED
- distance evidence is singular and available
- no invalid or conflicting time evidence exists

## Preservation

Raw time values, blanks, invalid values and quality states remain separately auditable.

No source value is overwritten.
