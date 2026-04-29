# LLM Review Scheduling

## Purpose
Define how external LLM review runs after the runtime is shifted to local-first trading decisions.

## Default
- cadence: `3h`

## Allowed cadence values
- `manual_only`
- `1h`
- `3h`
- `6h`
- `12h`
- `24h`

## Principles
- external LLM is not called per candle
- runtime trading decisions remain local
- periodic review is bounded and non-destructive
- no automatic config/model apply from the review run

## Suggested review artifacts
- recent decision summary
- recent trade outcome summary
- pair/session analysis
- config recommendation update
- approval summary refresh

## UI expectations
Operators should be able to:
- see current cadence
- change cadence manually
- disable review (`manual_only`)
- trigger `run now`
- inspect last run and next run
