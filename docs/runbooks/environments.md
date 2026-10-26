# Environments

Region default is `ap-southeast-2`. Quote `D:\SaaS Development` in scripts because of the space.

Do not apply Terraform until the AWS account, the Route 53 zone, and the GitHub Environments in `.github/RULESETS.md` are ready. This repository does not create cloud resources by itself.

## Sizing

| Environment | Tasks | Database | Availability | Notes |
| --- | --- | --- | --- | --- |
| dev | 0.25 vCPU, 512 MB | db.t4g.micro, one AZ | one NAT | Scales to 0 at 13:00 UTC and back at 21:00 UTC |
| test | same as dev | same as dev | one NAT | Playwright and the ZAP baseline run here |
| uat | 0.5 vCPU, 1 GB | db.t4g.micro | one NAT | A person accepts the change pack |
| staging | same as uat | same as uat | one NAT | Release candidate |
| preprod | 0.5 vCPU, 1 GB | db.t4g.small, multi-AZ | NAT per AZ | Grafana k6 and authenticated ZAP |
| prod | 1 vCPU, 2 GB, two tasks | db.t4g.medium, multi-AZ | NAT per AZ | Requires a certificate ARN |

Dev and test use EventBridge scheduled scaling. Production does not scale to zero.

## First apply, by hand

1. `terraform init` and `terraform apply` in `infra/terraform/bootstrap`. This creates the state bucket and the lock table. It uses a local backend.
2. Copy `infra/terraform/backend.hcl.example` and fill the bucket and table names.
3. Init `infra/terraform/shared` with that backend and apply it. Record `build_role_arn`, `audit_role_arn`, `oidc_provider_arn`, and the two ECR URLs.
4. Put those values in the GitHub variables and environment secrets named in `.github/RULESETS.md`.
5. Run `promote.yml`. It applies each environment with the image built in that run.

`terraform validate` is the local check. `terraform plan` needs AWS credentials and the real zone id, so it is not part of the scaffold.

## Rollback

The deploy job writes the previous API task definition into the GitHub job summary. To roll back, update the ECS service to that task definition and wait until the service is stable. The circuit breaker also rolls back a task set that fails its health check.

## When to split accounts

Keep one account while the six stacks are small. Move ECR, the state bucket, and the OIDC provider to a shared-services account first. Then give staging, pre-prod, and production their own accounts. The environment folders stay the same. The backend configuration and the role ARNs change.

## Local run

```powershell
Copy-Item -LiteralPath "D:\SaaS Development\.env.example" -Destination "D:\SaaS Development\.env"
docker compose -f "D:\SaaS Development\compose.yaml" up --build
```

The API is on port 8000 and the web app is on port 3000.

To rename the product:

```powershell
& "D:\SaaS Development\scripts\new-product.ps1" -Name "acme" -Domain "acme.example"
```
