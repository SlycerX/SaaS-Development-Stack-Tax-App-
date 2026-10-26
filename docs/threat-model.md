# Threat model

## Trust boundaries

- The browser talks to the load balancer. The web service and the API are the only targets.
- The API talks to RDS inside the private subnets. The database is not public.
- GitHub Actions assumes an IAM role with OIDC. There are no long-lived AWS keys in the repository.
- The production role can be assumed only from the production GitHub Environment. The same pattern holds for the other environments.
- Cognito issues tokens. The API verifies them against the user pool. A missing pool configuration returns 503. It does not accept an unsigned token.
- `GET /health` and `GET /items` are public on the skeleton so the delivery path can be proven. `POST /items` requires a bearer token.

## What the pipeline blocks

- A critical or high Snyk finding blocks the pull request and promotion.
- An open GitHub secret-scanning alert blocks the pull request and promotion.
- Playwright must pass on test before UAT.
- Grafana k6 thresholds in the change pack block pre-prod promotion when they miss.
- OWASP ZAP high and critical alerts block the baseline and the authenticated scan.
- An expired waiver fails CI.
- Prowler opens a GitHub issue and fails the weekly job when critical or high AWS findings exist.

## What stays outside the pipeline

A certified external penetration test is still a yearly engagement. Import its findings and block release while critical or high issues are open. The ZAP jobs are the continuous attack scan, not a substitute for that engagement.

## Waivers

Waivers live in `docs/security/waivers` and expire on a date. An agent does not edit them. A person approves a waiver as a deviation, and CI rejects it after `expires_on`.
