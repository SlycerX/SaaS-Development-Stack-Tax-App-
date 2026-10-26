module "ecr" {
  source       = "../modules/ecr"
  product_name = var.product_name
}

module "build_role" {
  source             = "../modules/github_oidc"
  create_provider    = true
  role_name          = "${var.product_name}-gha-build"
  github_repository  = var.github_repository
  github_environment = "build"
  policy_json = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["ecr:GetAuthorizationToken"]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "ecr:BatchCheckLayerAvailability",
          "ecr:BatchGetImage",
          "ecr:CompleteLayerUpload",
          "ecr:GetDownloadUrlForLayer",
          "ecr:InitiateLayerUpload",
          "ecr:PutImage",
          "ecr:UploadLayerPart",
        ]
        Resource = [module.ecr.api_repository_arn, module.ecr.web_repository_arn]
      }
    ]
  })
}

module "audit_role" {
  source                = "../modules/github_oidc"
  create_provider       = false
  existing_provider_arn = module.build_role.provider_arn
  role_name             = "${var.product_name}-gha-audit"
  github_repository     = var.github_repository
  github_environment    = "security"
  policy_json = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["sts:GetCallerIdentity"]
      Resource = "*"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "audit" {
  role       = module.audit_role.role_name
  policy_arn = "arn:aws:iam::aws:policy/SecurityAudit"
}
