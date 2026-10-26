locals {
  name = "${var.product_name}-${var.environment}"
}

module "network" {
  source     = "../network"
  name       = local.name
  vpc_cidr   = var.vpc_cidr
  az_count   = var.az_count
  nat_per_az = var.nat_per_az
}

resource "aws_security_group" "alb" {
  name   = "${local.name}-alb"
  vpc_id = module.network.vpc_id

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_security_group" "service" {
  name   = "${local.name}-service"
  vpc_id = module.network.vpc_id

  ingress {
    from_port       = 8000
    to_port         = 8000
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  ingress {
    from_port       = 3000
    to_port         = 3000
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_security_group" "db" {
  name   = "${local.name}-db"
  vpc_id = module.network.vpc_id

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.service.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

module "observability" {
  source            = "../observability"
  product_name      = var.product_name
  environment       = var.environment
  retention_in_days = var.log_retention_in_days
}

module "cognito" {
  source      = "../cognito"
  name        = local.name
  domain_name = var.domain_name
  region      = var.region
}

module "rds" {
  source            = "../rds"
  name              = local.name
  environment       = var.environment
  subnet_ids        = module.network.private_subnet_ids
  security_group_id = aws_security_group.db.id
  instance_class    = var.db_instance_class
  multi_az          = var.db_multi_az
}

module "ecs" {
  source                    = "../ecs"
  name                      = local.name
  environment               = var.environment
  region                    = var.region
  product_name              = var.product_name
  vpc_id                    = module.network.vpc_id
  public_subnet_ids         = module.network.public_subnet_ids
  private_subnet_ids        = module.network.private_subnet_ids
  alb_security_group_id     = aws_security_group.alb.id
  service_security_group_id = aws_security_group.service.id
  image_api                 = var.image_api
  image_web                 = var.image_web
  api_cpu                   = var.api_cpu
  api_memory                = var.api_memory
  web_cpu                   = var.web_cpu
  web_memory                = var.web_memory
  desired_count             = var.desired_count
  scale_to_zero             = var.scale_to_zero
  certificate_arn           = var.certificate_arn
  domain_name               = var.domain_name
  route53_zone_id           = var.route53_zone_id
  db_host                   = module.rds.address
  db_port                   = module.rds.port
  db_name                   = module.rds.name
  db_secret_arn             = module.rds.master_user_secret_arn
  cognito_pool_id           = module.cognito.user_pool_id
  cognito_client_id         = module.cognito.client_id
  api_log_group             = module.observability.api_log_group
  web_log_group             = module.observability.web_log_group
}

module "deploy_role" {
  source                = "../github_oidc"
  create_provider       = false
  existing_provider_arn = var.oidc_provider_arn
  role_name             = "${local.name}-gha"
  github_repository     = var.github_repository
  github_environment    = var.environment
  policy_json = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ecs:DescribeServices",
          "ecs:DescribeTaskDefinition",
          "ecs:RegisterTaskDefinition",
          "ecs:UpdateService",
          "ecs:DescribeClusters",
        ]
        Resource = "*"
      },
      {
        Effect   = "Allow"
        Action   = ["iam:PassRole"]
        Resource = [module.ecs.execution_role_arn, module.ecs.task_role_arn]
      },
      {
        Effect = "Allow"
        Action = [
          "ecr:BatchGetImage",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchCheckLayerAvailability",
        ]
        Resource = "*"
      },
      {
        Effect   = "Allow"
        Action   = ["ecr:GetAuthorizationToken"]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "logs:DescribeLogGroups",
          "elasticloadbalancing:Describe*",
        ]
        Resource = "*"
      }
    ]
  })
}
