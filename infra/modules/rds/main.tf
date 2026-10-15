resource "aws_db_subnet_group" "main" {
  name       = "${var.project_name}-${var.environment}-db-subnets"
  subnet_ids = var.private_subnet_ids

  tags = {
    Name = "${var.project_name}-${var.environment}-db-subnet-group"
  }
}

resource "aws_db_parameter_group" "pg16_vector" {
  name   = "${var.project_name}-${var.environment}-pg16-vector"
  family = "postgres16"

  tags = {
    Name = "${var.project_name}-${var.environment}-pg16-vector-params"
  }
}

resource "aws_security_group" "db" {
  name        = "${var.project_name}-${var.environment}-db-sg"
  description = "Controls inbound traffic to RDS PostgreSQL exclusively from ECS Fargate tasks"
  vpc_id      = var.vpc_id

  ingress {
    description     = "PostgreSQL from ECS tasks only"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [var.ecs_security_group_id]
  }

  egress {
    from_port        = 0
    to_port          = 0
    protocol         = "-1"
    cidr_blocks      = ["0.0.0.0/0"]
    ipv6_cidr_blocks = ["::/0"]
  }

  tags = {
    Name = "${var.project_name}-${var.environment}-db-sg"
  }
}

resource "aws_db_instance" "postgres" {
  identifier        = "${var.project_name}-${var.environment}-db"
  allocated_storage = 20
  storage_type      = "gp3"
  engine            = "postgres"
  engine_version    = "16.3"
  instance_class    = "db.t4g.micro" # Graviton2 - high efficiency, low cost for PoC

  db_name  = var.db_name
  username = var.db_username
  password = var.db_password

  db_subnet_group_name   = aws_db_subnet_group.main.name
  parameter_group_name   = aws_db_parameter_group.pg16_vector.name
  vpc_security_group_ids = [aws_security_group.db.id]

  publicly_accessible = false
  skip_final_snapshot = true
  deletion_protection = false

  backup_retention_period    = 1
  auto_minor_version_upgrade = true

  tags = {
    Name = "${var.project_name}-${var.environment}-rds"
  }
}
