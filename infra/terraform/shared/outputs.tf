output "api_repository_url" { value = module.ecr.api_repository_url }
output "web_repository_url" { value = module.ecr.web_repository_url }
output "oidc_provider_arn" { value = module.build_role.provider_arn }
output "build_role_arn" { value = module.build_role.role_arn }
output "audit_role_arn" { value = module.audit_role.role_arn }
