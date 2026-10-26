variable "product_name" {
  type    = string
  default = "example"
}

variable "region" {
  type    = string
  default = "ap-southeast-2"
}

variable "github_repository" {
  type    = string
  default = "CHANGE_ME/saas"
}

variable "oidc_provider_arn" {
  type    = string
  default = "arn:aws:iam::123456789012:oidc-provider/token.actions.githubusercontent.com"
}

variable "route53_zone_id" {
  type    = string
  default = "Z00000000000000000000"
}

variable "domain_name" {
  type    = string
  default = "staging.example.test"
}

variable "certificate_arn" {
  type    = string
  default = null
}

variable "image_api" {
  type    = string
  default = "public.ecr.aws/docker/library/python:3.12-slim"
}

variable "image_web" {
  type    = string
  default = "public.ecr.aws/docker/library/node:22-alpine"
}
