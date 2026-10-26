data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

locals {
  adot_image   = "public.ecr.aws/aws-observability/aws-otel-collector:v0.43.3"
  listener_arn = one(concat(aws_lb_listener.http[*].arn, aws_lb_listener.https[*].arn))
  service_url  = var.certificate_arn == null ? "http://${var.domain_name}" : "https://${var.domain_name}"
  log_arn      = "arn:aws:logs:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:log-group"
}

resource "aws_iam_role" "execution" {
  name = "${var.name}-execution"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "execution" {
  role       = aws_iam_role.execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role_policy" "execution_secrets" {
  name = "${var.name}-secrets"
  role = aws_iam_role.execution.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["secretsmanager:GetSecretValue"]
      Resource = [var.db_secret_arn]
    }]
  })
}

resource "aws_iam_role" "task" {
  name               = "${var.name}-task"
  assume_role_policy = aws_iam_role.execution.assume_role_policy
}

resource "aws_iam_role_policy" "task_telemetry" {
  name = "${var.name}-telemetry"
  role = aws_iam_role.task.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["xray:PutTraceSegments", "xray:PutTelemetryRecords"]
        Resource = ["*"]
      },
      {
        Effect = "Allow"
        Action = ["logs:PutLogEvents", "logs:CreateLogStream"]
        Resource = [
          "${local.log_arn}:${var.api_log_group}:*",
          "${local.log_arn}:${var.web_log_group}:*",
        ]
      }
    ]
  })
}

resource "aws_lb" "main" {
  name               = substr(var.name, 0, 32)
  load_balancer_type = "application"
  subnets            = var.public_subnet_ids
  security_groups    = [var.alb_security_group_id]
}

resource "aws_lb_target_group" "api" {
  name        = substr("${var.name}-api", 0, 32)
  port        = 8000
  protocol    = "HTTP"
  target_type = "ip"
  vpc_id      = var.vpc_id

  health_check {
    path = "/health"
  }
}

resource "aws_lb_target_group" "web" {
  name        = substr("${var.name}-web", 0, 32)
  port        = 3000
  protocol    = "HTTP"
  target_type = "ip"
  vpc_id      = var.vpc_id

  health_check {
    path = "/"
  }
}

resource "aws_lb_listener" "http" {
  count             = var.certificate_arn == null ? 1 : 0
  load_balancer_arn = aws_lb.main.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.web.arn
  }
}

resource "aws_lb_listener" "http_redirect" {
  count             = var.certificate_arn == null ? 0 : 1
  load_balancer_arn = aws_lb.main.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type = "redirect"
    redirect {
      port        = "443"
      protocol    = "HTTPS"
      status_code = "HTTP_301"
    }
  }
}

resource "aws_lb_listener" "https" {
  count             = var.certificate_arn == null ? 0 : 1
  load_balancer_arn = aws_lb.main.arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = var.certificate_arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.web.arn
  }
}

resource "aws_lb_listener_rule" "api" {
  listener_arn = local.listener_arn
  priority     = 10

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.api.arn
  }

  condition {
    path_pattern {
      values = ["/health", "/items", "/docs", "/openapi.json", "/redoc"]
    }
  }
}

resource "aws_lb_listener_rule" "ledger" {
  listener_arn = local.listener_arn
  priority     = 12

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.api.arn
  }

  condition {
    path_pattern {
      values = ["/ledger", "/ledger/*"]
    }
  }
}

resource "aws_lb_listener_rule" "auth" {
  listener_arn = local.listener_arn
  priority     = 11

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.api.arn
  }

  condition {
    path_pattern {
      values = ["/auth", "/auth/*"]
    }
  }
}

resource "aws_route53_record" "app" {
  zone_id = var.route53_zone_id
  name    = var.domain_name
  type    = "A"

  alias {
    name                   = aws_lb.main.dns_name
    zone_id                = aws_lb.main.zone_id
    evaluate_target_health = true
  }
}

resource "aws_ecs_cluster" "main" {
  name = var.name
}

resource "aws_ecs_task_definition" "api" {
  family                   = "${var.name}-api"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.api_cpu
  memory                   = var.api_memory
  execution_role_arn       = aws_iam_role.execution.arn
  task_role_arn            = aws_iam_role.task.arn

  container_definitions = jsonencode([
    {
      name      = "aws-otel-collector"
      image     = local.adot_image
      essential = true
      command   = ["--config=/etc/ecs/ecs-default-config.yaml"]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = var.api_log_group
          awslogs-region        = var.region
          awslogs-stream-prefix = "otel"
        }
      }
    },
    {
      name         = "api"
      image        = var.image_api
      essential    = true
      portMappings = [{ containerPort = 8000, protocol = "tcp" }]
      environment = [
        { name = "DB_HOST", value = var.db_host },
        { name = "DB_PORT", value = tostring(var.db_port) },
        { name = "DB_NAME", value = var.db_name },
        { name = "PRODUCT_NAME", value = var.product_name },
        { name = "COGNITO_REGION", value = var.region },
        { name = "COGNITO_USER_POOL_ID", value = var.cognito_pool_id },
        { name = "COGNITO_APP_CLIENT_ID", value = var.cognito_client_id },
        { name = "OTEL_EXPORTER_OTLP_ENDPOINT", value = "http://127.0.0.1:4318" },
        { name = "OTEL_SERVICE_NAME", value = "api" },
      ]
      secrets = [
        { name = "DB_USER", valueFrom = "${var.db_secret_arn}:username::" },
        { name = "DB_PASSWORD", valueFrom = "${var.db_secret_arn}:password::" },
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = var.api_log_group
          awslogs-region        = var.region
          awslogs-stream-prefix = "api"
        }
      }
    }
  ])
}

resource "aws_ecs_task_definition" "web" {
  family                   = "${var.name}-web"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.web_cpu
  memory                   = var.web_memory
  execution_role_arn       = aws_iam_role.execution.arn
  task_role_arn            = aws_iam_role.task.arn

  container_definitions = jsonencode([
    {
      name      = "aws-otel-collector"
      image     = local.adot_image
      essential = true
      command   = ["--config=/etc/ecs/ecs-default-config.yaml"]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = var.web_log_group
          awslogs-region        = var.region
          awslogs-stream-prefix = "otel"
        }
      }
    },
    {
      name         = "web"
      image        = var.image_web
      essential    = true
      portMappings = [{ containerPort = 3000, protocol = "tcp" }]
      environment = [
        { name = "OTEL_SERVICE_NAME", value = "web" },
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = var.web_log_group
          awslogs-region        = var.region
          awslogs-stream-prefix = "web"
        }
      }
    }
  ])
}

resource "aws_ecs_service" "api" {
  name            = "${var.name}-api"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.api.arn
  desired_count   = var.desired_count
  launch_type     = "FARGATE"

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [var.service_security_group_id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.api.arn
    container_name   = "api"
    container_port   = 8000
  }

  lifecycle {
    ignore_changes = [desired_count]
  }
}

resource "aws_ecs_service" "web" {
  name            = "${var.name}-web"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.web.arn
  desired_count   = var.desired_count
  launch_type     = "FARGATE"

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [var.service_security_group_id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.web.arn
    container_name   = "web"
    container_port   = 3000
  }

  lifecycle {
    ignore_changes = [desired_count]
  }
}

resource "aws_appautoscaling_target" "api" {
  count              = var.scale_to_zero ? 1 : 0
  max_capacity       = var.desired_count
  min_capacity       = 0
  resource_id        = "service/${aws_ecs_cluster.main.name}/${aws_ecs_service.api.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

resource "aws_appautoscaling_target" "web" {
  count              = var.scale_to_zero ? 1 : 0
  max_capacity       = var.desired_count
  min_capacity       = 0
  resource_id        = "service/${aws_ecs_cluster.main.name}/${aws_ecs_service.web.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

resource "aws_appautoscaling_scheduled_action" "api_down" {
  count              = var.scale_to_zero ? 1 : 0
  name               = "${var.name}-api-down"
  service_namespace  = "ecs"
  resource_id        = aws_appautoscaling_target.api[0].resource_id
  scalable_dimension = aws_appautoscaling_target.api[0].scalable_dimension
  schedule           = "cron(0 13 * * ? *)"

  scalable_target_action {
    min_capacity = 0
    max_capacity = 0
  }
}

resource "aws_appautoscaling_scheduled_action" "api_up" {
  count              = var.scale_to_zero ? 1 : 0
  name               = "${var.name}-api-up"
  service_namespace  = "ecs"
  resource_id        = aws_appautoscaling_target.api[0].resource_id
  scalable_dimension = aws_appautoscaling_target.api[0].scalable_dimension
  schedule           = "cron(0 21 * * ? *)"

  scalable_target_action {
    min_capacity = var.desired_count
    max_capacity = var.desired_count
  }
}

resource "aws_appautoscaling_scheduled_action" "web_down" {
  count              = var.scale_to_zero ? 1 : 0
  name               = "${var.name}-web-down"
  service_namespace  = "ecs"
  resource_id        = aws_appautoscaling_target.web[0].resource_id
  scalable_dimension = aws_appautoscaling_target.web[0].scalable_dimension
  schedule           = "cron(0 13 * * ? *)"

  scalable_target_action {
    min_capacity = 0
    max_capacity = 0
  }
}

resource "aws_appautoscaling_scheduled_action" "web_up" {
  count              = var.scale_to_zero ? 1 : 0
  name               = "${var.name}-web-up"
  service_namespace  = "ecs"
  resource_id        = aws_appautoscaling_target.web[0].resource_id
  scalable_dimension = aws_appautoscaling_target.web[0].scalable_dimension
  schedule           = "cron(0 21 * * ? *)"

  scalable_target_action {
    min_capacity = var.desired_count
    max_capacity = var.desired_count
  }
}
