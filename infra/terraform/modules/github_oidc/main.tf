resource "aws_iam_openid_connect_provider" "github" {
  count = var.create_provider ? 1 : 0
  url   = "https://token.actions.githubusercontent.com"
  client_id_list = [
    "sts.amazonaws.com",
  ]
  thumbprint_list = [
    "6938fd4d98bab03faadb97b34396831e3780aea1",
  ]
}

locals {
  provider_arn = var.create_provider ? aws_iam_openid_connect_provider.github[0].arn : var.existing_provider_arn
}

resource "aws_iam_role" "deploy" {
  name = var.role_name

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = "sts:AssumeRoleWithWebIdentity"
        Principal = {
          Federated = local.provider_arn
        }
        Condition = {
          StringEquals = {
            "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
          }
          StringLike = {
            "token.actions.githubusercontent.com:sub" = "repo:${var.github_repository}:environment:${var.github_environment}"
          }
        }
      }
    ]
  })
}

resource "aws_iam_role_policy" "deploy" {
  name   = "${var.role_name}-deploy"
  role   = aws_iam_role.deploy.id
  policy = var.policy_json
}
