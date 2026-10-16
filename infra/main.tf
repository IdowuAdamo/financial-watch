# FinancialWatch Infrastructure Orchestration

resource "random_password" "db_password" {
  count   = var.db_password == null ? 1 : 0
  length  = 24
  special = false
}

resource "random_password" "origin_secret" {
  count   = var.origin_verify_secret == null ? 1 : 0
  length  = 32
  special = false
}

resource "random_password" "api_access_key" {
  count   = var.api_access_key == null ? 1 : 0
  length  = 32
  special = false
}

locals {
  db_password          = var.db_password != null ? var.db_password : random_password.db_password[0].result
  origin_verify_secret = var.origin_verify_secret != null ? var.origin_verify_secret : random_password.origin_secret[0].result
  api_access_key       = var.api_access_key != null ? var.api_access_key : random_password.api_access_key[0].result
  database_url         = "postgresql://${var.db_username}:${local.db_password}@${module.rds.address}:${module.rds.port}/${var.db_name}"
}

# 1. VPC Module
module "vpc" {
  source       = "./modules/vpc"
  project_name = var.project_name
  environment  = var.environment
  vpc_cidr     = var.vpc_cidr
}

# 2. ALB Module
module "alb" {
  source               = "./modules/alb"
  project_name         = var.project_name
  environment          = var.environment
  vpc_id               = module.vpc.vpc_id
  public_subnet_ids    = module.vpc.public_subnet_ids
  origin_verify_secret = local.origin_verify_secret
}

# 3. ECS Fargate Backend Module
module "ecs" {
  source                = "./modules/ecs"
  project_name          = var.project_name
  environment           = var.environment
  vpc_id                = module.vpc.vpc_id
  public_subnet_ids     = module.vpc.public_subnet_ids
  alb_security_group_id = module.alb.alb_security_group_id
  target_group_arn      = module.alb.target_group_arn
  container_image       = var.container_image
  database_url          = local.database_url
  api_access_key        = local.api_access_key
  crawler_contact_url   = var.crawler_contact_url
  openai_api_key        = var.openai_api_key
  desired_count         = var.desired_count
  ecr_repository_name   = var.ecr_repository_name
  create_ecr_repository = var.create_ecr_repository
}

# 4. RDS PostgreSQL 16 + pgvector Module
module "rds" {
  source                = "./modules/rds"
  project_name          = var.project_name
  environment           = var.environment
  vpc_id                = module.vpc.vpc_id
  private_subnet_ids    = module.vpc.private_subnet_ids
  ecs_security_group_id = module.ecs.ecs_security_group_id
  db_name               = var.db_name
  db_username           = var.db_username
  db_password           = local.db_password
}

# 5. CloudFront CDN & S3 Static Frontend Module
module "cloudfront_s3" {
  source               = "./modules/cloudfront_s3"
  project_name         = var.project_name
  environment          = var.environment
  alb_dns_name         = module.alb.dns_name
  origin_verify_secret = local.origin_verify_secret
  api_access_key       = local.api_access_key
}

# 6. EventBridge Scheduled Ingestion & Database Migration Task Module
module "scheduled_task" {
  source                  = "./modules/scheduled_task"
  project_name            = var.project_name
  environment             = var.environment
  cluster_arn             = module.ecs.cluster_id
  public_subnet_ids       = module.vpc.public_subnet_ids
  ecs_security_group_id   = module.ecs.ecs_security_group_id
  task_execution_role_arn = module.ecs.task_execution_role_arn
  task_role_arn           = module.ecs.task_role_arn
  container_image         = var.container_image
  database_url            = local.database_url
  database_url_secret_arn = module.ecs.database_url_secret_arn
  crawler_contact_url     = var.crawler_contact_url
}

# Extract ARN suffixes for CloudWatch metrics
locals {
  alb_arn_suffix          = join("/", slice(split("/", module.alb.alb_arn), 1, length(split("/", module.alb.alb_arn))))
  target_group_arn_suffix = join("/", slice(split("/", module.alb.target_group_arn), 1, length(split("/", module.alb.target_group_arn))))
}

# 7. CloudWatch Alarms & AWS Budget Module ($20 Ceiling)
module "monitoring" {
  source                  = "./modules/monitoring"
  project_name            = var.project_name
  environment             = var.environment
  cluster_name            = module.ecs.cluster_name
  service_name            = module.ecs.service_name
  alb_arn_suffix          = local.alb_arn_suffix
  target_group_arn_suffix = local.target_group_arn_suffix
  budget_alert_email      = var.budget_alert_email
  monthly_budget_amount   = var.monthly_budget_amount
}
