output "app_url" {
  description = "Primary CloudFront CDN URL for the FinancialWatch application"
  value       = "https://${module.cloudfront_s3.distribution_domain_name}"
}

output "cloudfront_distribution_id" {
  description = "CloudFront distribution ID for deployment invalidations"
  value       = module.cloudfront_s3.distribution_id
}

output "frontend_s3_bucket" {
  description = "S3 bucket name for syncing Next.js static export"
  value       = module.cloudfront_s3.frontend_bucket_name
}

output "alb_dns_name" {
  description = "Application Load Balancer DNS name"
  value       = module.alb.dns_name
}

output "database_endpoint" {
  description = "RDS PostgreSQL database endpoint"
  value       = module.rds.endpoint
  sensitive   = true
}

output "ecs_cluster_name" {
  description = "ECS cluster name"
  value       = module.ecs.cluster_name
}

output "ecs_service_name" {
  description = "ECS Fargate service name"
  value       = module.ecs.service_name
}

output "migration_task_arn" {
  description = "ARN of the one-off migration task definition to run 'load-snapshot'"
  value       = module.scheduled_task.migration_task_definition_arn
}

output "api_access_key" {
  description = "Configured or generated API Access Key for client authentication"
  value       = local.api_access_key
  sensitive   = true
}

output "public_subnet_ids" {
  description = "List of public subnet IDs in the VPC"
  value       = module.vpc.public_subnet_ids
}

output "private_subnet_ids" {
  description = "List of private subnet IDs in the VPC"
  value       = module.vpc.private_subnet_ids
}

output "ecs_security_group_id" {
  description = "Security group ID for ECS Fargate tasks"
  value       = module.ecs.ecs_security_group_id
}

output "migration_command" {
  description = "Ready-to-run AWS CLI command to execute the one-off database migration / snapshot load task"
  value       = "aws ecs run-task --cluster ${module.ecs.cluster_name} --task-definition ${module.scheduled_task.migration_task_definition_arn} --launch-type FARGATE --network-configuration 'awsvpcConfiguration={subnets=[${join(",", module.vpc.public_subnet_ids)}],securityGroups=[${module.ecs.ecs_security_group_id}],assignPublicIp=ENABLED}'"
}

