output "api_log_group" {
  value = aws_cloudwatch_log_group.api.name
}

output "web_log_group" {
  value = aws_cloudwatch_log_group.web.name
}
