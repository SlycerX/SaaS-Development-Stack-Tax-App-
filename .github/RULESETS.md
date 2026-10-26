# GitHub rules

Configure these in the repository before the first promotion. The workflows fail closed when a secret or variable is missing. They cannot create these settings for you.

## Ruleset on `main`

- Pull request required before merge.
- Required status checks from `ci.yml`: `change-pack`, `requirements`, `waivers`, `protected-paths`, `workflows`, `release-class`, `secret-scanning`, `snyk-code`, `snyk-open-source`, `snyk-iac`, `snyk-container`, `playwright`.
- Block force pushes.
- Secret scanning and push protection enabled.

## Environments

Create `build`, `security`, `dev`, `test`, `uat`, `staging`, `preprod`, and `prod`.

- `uat` and `prod` have required reviewers. The reviewer is a person. An agent cannot approve its own production release.
- Each environment has a secret `AWS_ROLE_ARN`.
- `build` uses the shared stack output `build_role_arn`.
- `security` uses `audit_role_arn`.
- `dev`, `test`, `uat`, `staging`, `preprod`, and `prod` use that environment's `deploy_role_arn`.
- Each application environment has variables `DOMAIN_NAME` and `ROUTE53_ZONE_ID`.
- `prod` also has `CERTIFICATE_ARN`.

## Repository variables

- `AWS_REGION` is `ap-southeast-2` unless the product file says otherwise.
- `TF_STATE_BUCKET` and `TF_LOCK_TABLE` come from the bootstrap stack.
- `ECR_API_URL` and `ECR_WEB_URL` come from the shared stack.
- `OIDC_PROVIDER_ARN` comes from the shared stack.

## Repository secrets

- `SNYK_TOKEN`
- `SECRET_SCANNING_PAT` — fine-grained PAT on this repository with **Secret scanning alerts** read access. The built-in `GITHUB_TOKEN` cannot call that API.
- `CURSOR_API_KEY` for the remediation workflow
- `ZAP_AUTH_TOKEN` on the pre-prod authenticated scan

## What promotion does

`promote.yml` is the only workflow that deploys. It builds one image, pushes it by commit SHA, and walks dev, test, Playwright, the ZAP baseline, UAT, staging, pre-prod, Grafana k6, the authenticated ZAP scan, and production. A major release then tags `vX.0.0`. An experiment does not.
