# ADR 0001: Delivery stack

## Status

Accepted for the skeleton.

## Decision

FastAPI and Next.js run on ECS Fargate behind one load balancer. PostgreSQL on RDS is the system of record. Cognito authenticates protected routes. Terraform describes six isolated stacks in one account. GitHub Actions promotes one image digest through every environment. Playwright, Snyk, Grafana k6, OWASP ZAP, and Prowler are the gates named in `docs/guardrails.md`.

## Consequences

A new AWS service, datastore, or test product is a deviation and needs an answer before anyone edits it. Redis and SQS stay out until a change pack records that need.

The first apply is manual for the state bucket and the shared ECR stack. Promotion after that is `promote.yml`.
