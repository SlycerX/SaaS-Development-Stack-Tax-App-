# ADR 0003: Investment ledger

## Status

Accepted.

## Decision

Property, share, and bitcoin records live in Postgres on the signed-in account. Each save writes a history line. The estimate for the account's Australian income year nets capital losses against gains that do not get the discount first, then halves the remaining discountable gain for a resident individual who held the asset for 12 months. A property marked as the main residence is treated as a zero gain. The screen states that this is an estimate from the recorded figures.

## Consequences

The load balancer forwards `/ledger` and `/ledger/*` to the API. The records screen stays on `/records` so that path still reaches the web app. No tax file number is stored.
