# ADR 0002: Accounts

## Status

Accepted.

## Decision

People sign in with an email and a password stored as a PBKDF2 hash in Postgres. The session cookie holds a random token. Only the token hash is stored. Cognito still protects `POST /items`. Account screens do not collect a tax file number.

Property, share, and crypto records are not in this change. The dashboard names those areas so the next change has a place to put them.

## Consequences

The load balancer forwards `/auth` and `/auth/*` to the API. Locally, the Next.js server proxies those paths and keeps the cookie on the web origin.
