output "service_url" { value = module.ecs.service_url }
output "deploy_role_arn" { value = module.deploy_role.role_arn }
output "cluster_name" { value = module.ecs.cluster_name }
output "api_service_name" { value = module.ecs.api_service_name }
output "web_service_name" { value = module.ecs.web_service_name }
output "cognito_user_pool_id" { value = module.cognito.user_pool_id }
output "cognito_client_id" { value = module.cognito.client_id }
