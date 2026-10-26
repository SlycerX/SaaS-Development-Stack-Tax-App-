output "provider_arn" {
  value = local.provider_arn
}

output "role_arn" {
  value = aws_iam_role.deploy.arn
}

output "role_name" {
  value = aws_iam_role.deploy.name
}
