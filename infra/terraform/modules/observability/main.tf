resource "aws_cloudwatch_log_group" "api" {
  name              = "/${var.product_name}/${var.environment}/api"
  retention_in_days = var.retention_in_days
}

resource "aws_cloudwatch_log_group" "web" {
  name              = "/${var.product_name}/${var.environment}/web"
  retention_in_days = var.retention_in_days
}

resource "aws_xray_group" "main" {
  group_name        = "${var.product_name}-${var.environment}"
  filter_expression = "*"
}
