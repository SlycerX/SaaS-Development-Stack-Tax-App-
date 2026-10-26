# Frameworks and guardrails

AI implements inside this architecture. GitHub Actions and AWS IAM decide what can ship. An agent cannot approve its own UAT or production release.

Read this file before changing the repository. The Cursor rule in `.cursor/rules/guardrails.mdc` tells the agent to stop and ask. The workflows make a skipped step fail.

## Approved products

GitHub Issues, Figma, OpenAPI in this repo, Cursor, Playwright, Snyk Code, Snyk Open Source, Snyk Container, Snyk IaC, GitHub secret scanning, GitHub Actions, GitHub Environments, GitHub Releases, GitHub OIDC, Terraform, Amazon S3, DynamoDB, ECS Fargate, Route 53, an Application Load Balancer, Amazon Cognito, Amazon RDS for PostgreSQL, AWS Secrets Manager, Amazon ECR, OpenTelemetry, CloudWatch, X-Ray, Sentry, Grafana k6, OWASP ZAP, Prowler, and Docker Compose.

Adding a product, a datastore, a language, or an AWS service is a deviation.

## Steps that always run

Both release classes walk the same path. Playwright is the only step whose breadth changes. No job in `.github/workflows` may set `if`. CI rejects a workflow that does.

1. GitHub Issue
2. Change pack, including `release_class`
3. Design when the UI or the API contract changes
4. Implementation pull request
5. New Playwright tests for the behavior being added
6. Snyk Code, Snyk Open Source, Snyk Container, and Snyk IaC
7. GitHub secret scanning
8. Playwright lane for this release class, on the test environment
9. Deploy dev
10. Deploy test
11. UAT approval in GitHub Environments
12. Deploy staging
13. Deploy pre-prod
14. Grafana k6
15. OWASP ZAP
16. Production approval in GitHub Environments
17. Deploy prod

`promote.yml` is the only deploy path. A pull request runs the checks and the Playwright lane. It does not deploy.

`release_class` is required. CI fails a pack that omits it.

## Playwright lanes

- `experiment` runs tests tagged `@lite` or `@feature`. Lite is the critical journeys and every test that exists because a bug was found or fixed. The new feature still gets its full Playwright case list, tagged `@feature`, and those tests run. An experiment cannot use a version `x.0.0`.
- `major` runs the entire Playwright tree with no grep. The version in the change pack and in `product.yaml` is `x.0.0`. A green production deploy creates the tag `vX.0.0`.

A test is born as `@feature`. It joins `@lite` only when it protects a critical journey or a bug that must not return. After the major release that includes it, remove `@feature` and leave the test in the full suite.

A pull request that changes behavior adds `@feature` tests. A behavior-preserving refactor sets `behavior_change: false` in the change pack. The lite suite still runs.

## Asking before a deviation

Stop and ask in one message. Wait for an answer. Do not implement the deviation in that turn.

- What you are trying to do
- Which rule blocks it
- Why the current architecture cannot do the job
- The smallest change that would break the rule
- Which pipeline steps would still run

Reasons to stop: a new AWS service or datastore, replacing a named product, skipping an environment, skipping Snyk, k6, ZAP, or Playwright, running the lite suite on a major release, marking a required step not applicable, editing a waiver, or changing production IAM or Cognito.

Work inside Next.js, FastAPI, Playwright, and the existing Terraform modules is not a deviation.

Record an approved deviation in the change pack:

```yaml
deviations:
  - id: DEV-002
    what: What would change
    rule: Which guardrail it breaks
    why: Why the current architecture cannot do the job
    pipeline_steps_still_run: Which of the seventeen steps still run
    approved_by: operator
```

CI rejects a change to a protected path that has no deviation. Protected paths are `infra/`, `.github/workflows/`, `apps/api/app/auth.py`, and the dependency manifests.

A step marked `not_applicable` also needs a deviation. Do not use that status to skip a gate.
