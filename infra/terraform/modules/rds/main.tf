resource "aws_db_subnet_group" "main" {
  name       = var.name
  subnet_ids = var.subnet_ids
}

resource "aws_db_instance" "main" {
  identifier     = var.name
  engine         = "postgres"
  engine_version = "16"
  instance_class = var.instance_class

  allocated_storage = 20
  storage_encrypted = true
  db_name           = "saas"
  username          = "saas"

  manage_master_user_password = true
  multi_az                    = var.multi_az
  publicly_accessible         = false
  db_subnet_group_name        = aws_db_subnet_group.main.name
  vpc_security_group_ids      = [var.security_group_id]

  backup_retention_period = var.environment == "prod" ? 7 : 1
  skip_final_snapshot     = var.environment != "prod"
  deletion_protection     = var.environment == "prod"
}
