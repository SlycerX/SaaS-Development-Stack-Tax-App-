variable "product_name" { type = string }
variable "environment" { type = string }
variable "region" { type = string }
variable "vpc_cidr" { type = string }
variable "az_count" { type = number }
variable "nat_per_az" { type = bool }
variable "db_instance_class" { type = string }
variable "db_multi_az" { type = bool }
variable "api_cpu" { type = number }
variable "api_memory" { type = number }
variable "web_cpu" { type = number }
variable "web_memory" { type = number }
variable "desired_count" { type = number }
variable "scale_to_zero" { type = bool }
variable "log_retention_in_days" { type = number }
variable "github_repository" { type = string }
variable "oidc_provider_arn" { type = string }
variable "image_api" { type = string }
variable "image_web" { type = string }
variable "route53_zone_id" { type = string }
variable "domain_name" { type = string }
variable "certificate_arn" {
  type    = string
  default = null
}
