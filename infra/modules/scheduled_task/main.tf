# IAM Role for EventBridge to trigger ECS tasks
resource "aws_iam_role" "eventbridge_ecs" {
  name = "${var.project_name}-${var.environment}-eventbridge-ecs-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "events.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_policy" "eventbridge_run_task" {
  name = "${var.project_name}-${var.environment}-eb-run-task-policy"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = "ecs:RunTask"
        Resource = "*"
      },
      {
        Effect   = "Allow"
        Action   = "iam:PassRole"
        Resource = [var.task_execution_role_arn, var.task_role_arn]
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "eb_attach" {
  role       = aws_iam_role.eventbridge_ecs.name
  policy_arn = aws_iam_policy.eventbridge_run_task.arn
}

# Task Definition for One-off Migration & Snapshot Loading
resource "aws_ecs_task_definition" "db_migrate" {
  family                   = "${var.project_name}-${var.environment}-migration"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "512"
  memory                   = "1024"
  execution_role_arn       = var.task_execution_role_arn
  task_role_arn            = var.task_role_arn

  container_definitions = jsonencode([
    {
      name      = "migrator"
      image     = var.container_image
      essential = true
      command   = ["python", "-m", "memory.cli", "load-snapshot"]

      environment = var.database_url_secret_arn != null ? [
        { name = "CRAWLER_CONTACT_URL", value = var.crawler_contact_url }
        ] : [
        { name = "DATABASE_URL", value = var.database_url },
        { name = "CRAWLER_CONTACT_URL", value = var.crawler_contact_url }
      ]

      secrets = var.database_url_secret_arn != null ? [
        {
          name      = "DATABASE_URL"
          valueFrom = var.database_url_secret_arn
        }
      ] : []

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = "/ecs/${var.project_name}-${var.environment}"
          "awslogs-region"        = "us-east-1"
          "awslogs-stream-prefix" = "migration"
        }
      }
    }
  ])

  tags = {
    Name = "${var.project_name}-${var.environment}-migration-task"
  }
}

# Task Definition for Scheduled Compliance Crawling / Ingestion
resource "aws_ecs_task_definition" "ingestion_task" {
  family                   = "${var.project_name}-${var.environment}-ingest"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "512"
  memory                   = "1024"
  execution_role_arn       = var.task_execution_role_arn
  task_role_arn            = var.task_role_arn

  container_definitions = jsonencode([
    {
      name      = "ingestor"
      image     = var.container_image
      essential = true
      command   = ["python", "-m", "memory.cli", "status"]

      environment = var.database_url_secret_arn != null ? [
        { name = "CRAWLER_CONTACT_URL", value = var.crawler_contact_url }
        ] : [
        { name = "DATABASE_URL", value = var.database_url },
        { name = "CRAWLER_CONTACT_URL", value = var.crawler_contact_url }
      ]

      secrets = var.database_url_secret_arn != null ? [
        {
          name      = "DATABASE_URL"
          valueFrom = var.database_url_secret_arn
        }
      ] : []

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = "/ecs/${var.project_name}-${var.environment}"
          "awslogs-region"        = "us-east-1"
          "awslogs-stream-prefix" = "scheduled-ingest"
        }
      }
    }
  ])

  tags = {
    Name = "${var.project_name}-${var.environment}-ingest-task"
  }
}

# EventBridge Rule (Daily 02:00 UTC)
resource "aws_cloudwatch_event_rule" "daily_ingest" {
  name                = "${var.project_name}-${var.environment}-daily-crawl"
  description         = "Triggers scheduled authoritative regulatory check and compliance sweep"
  schedule_expression = "cron(0 2 * * ? *)"

  tags = {
    Name = "${var.project_name}-${var.environment}-daily-crawl"
  }
}

resource "aws_cloudwatch_event_target" "ecs_target" {
  rule      = aws_cloudwatch_event_rule.daily_ingest.name
  target_id = "IngestTaskTarget"
  arn       = var.cluster_arn
  role_arn  = aws_iam_role.eventbridge_ecs.arn

  ecs_target {
    task_count          = 1
    task_definition_arn = aws_ecs_task_definition.ingestion_task.arn
    launch_type         = "FARGATE"

    network_configuration {
      subnets          = var.public_subnet_ids
      security_groups  = [var.ecs_security_group_id]
      assign_public_ip = true
    }
  }
}
