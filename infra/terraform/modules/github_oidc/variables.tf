variable "create_provider" { type = bool }
variable "existing_provider_arn" {
  type    = string
  default = null
}
variable "role_name" { type = string }
variable "github_repository" { type = string }
variable "github_environment" { type = string }
variable "policy_json" { type = string }
