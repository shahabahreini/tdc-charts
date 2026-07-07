# Accuracy and Confidence

## Table of Contents

1. [Purpose](#purpose)
2. [Source Levels](#source-levels)
3. [Ambiguity Handling](#ambiguity-handling)
4. [Indecision Logic](#indecision-logic)
5. [Gap Handling](#gap-handling)
6. [Modeling Guidance](#modeling-guidance)

## Purpose

TDC separates calculated values from confidence in those values. A density
profile built from real intrabar data has a different evidentiary value than a
profile estimated from OHLC alone.

## Source Levels

`profile_source` identifies whether a row came from `real` intrabar data or a
`synthetic` OHLC bridge. `volume_mode` identifies whether volume weighting was
real, synthetic-even, or unavailable.

Synthetic-even volume does not add intrabar volume information. It is exported
only so downstream users can identify that the total bar volume was spread
evenly over synthetic ticks.

## Ambiguity Handling

POC ties are exported through `poc_tie_count`, `poc_is_ambiguous`, and
`poc_confidence`. Value Area ties are exported through
`value_area_is_ambiguous` and `value_area_confidence`.

Flat bars are valid but degenerate. Their POC and Value Area remain at the flat
price, and `profile_degenerate` is set.

## Indecision Logic

Indecision is based on a combined score:

- High normalized entropy.
- Low concentration ratio.
- Neutral or small candle body.
- Centered close location.
- Wide Value Area.

The renderer uses exported `indecision_flag` values when present. Automatic
flags require at least `features.indecision_min_samples` rows and are suppressed
for all-equal score windows.

## Gap Handling

`session_gap` is detected from timestamp spacing. Rendering can show those gaps
and break POC drift across them. This avoids implying continuous POC movement
over weekends, holidays, overnight closures, or missing bars.

## Modeling Guidance

Use `profile_confidence`, `confidence_level`, `profile_warning`, POC ambiguity,
Value Area ambiguity, and `profile_source` as model inputs or filters. Do not
train on synthetic profiles as if they were observed market microstructure.
