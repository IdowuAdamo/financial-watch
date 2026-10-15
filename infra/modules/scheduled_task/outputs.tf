output "migration_task_definition_arn" {
  value = aws_ecs_task_definition.db_migrate.arn
}

output "scheduled_task_definition_arn" {
  value = aws_ecs_task_definition.ingestion_task.arn
}

output "eventbridge_rule_arn" {
  value = aws_cloudwatch_event_rule.daily_ingest.arn
}
