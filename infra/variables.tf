variable "aws_region" {
  description = "Primary AWS region for deployment (us-east-1 N. Virginia)"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Deployment environment name (prod, staging, dev)"
  type        = string
  default     = "prod"
}

variable "project_name" {
  description = "Project identifier used in naming resources"
  type        = string
  default     = "financial-watch"
}

variable "vpc_cidr" {
  description = "CIDR block for the dedicated VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "db_name" {
  description = "PostgreSQL database name"
  type        = string
  default     = "financial_watch"
}

variable "db_username" {
  description = "Master database username"
  type        = string
  default     = "fw_admin"
}

variable "db_password" {
  description = "Master database password. If not provided, a secure random password will be generated."
  type        = string
  sensitive   = true
  default     = null
}

variable "container_image" {
  description = "Docker image URI for the FastAPI backend container in ECR"
  type        = string
  default     = "123456789012.dkr.ecr.us-east-1.amazonaws.com/financial-watch-backend:latest"
}

variable "openai_api_key" {
  description = "OpenAI API Key for live embeddings and agent LLM calls (optional if using mock or Bedrock)"
  type        = string
  sensitive   = true
  default     = ""
}

variable "api_access_key" {
  description = "Shared secret API key required for client authentication via X-API-Key. If null, a secure random key will be generated."
  type        = string
  sensitive   = true
  default     = null
}

variable "crawler_contact_url" {
  description = "Public repository or contact URL identified in the crawler User-Agent header"
  type        = string
  default     = "https://github.com/IdowuAdamo/financial-watch"
}

variable "origin_verify_secret" {
  description = "Shared secret header value (X-Origin-Verify) between CloudFront and ALB to prevent direct public access to ALB"
  type        = string
  sensitive   = true
  default     = null
}

variable "budget_alert_email" {
  description = "Email address for AWS Budget alerts ($20 threshold)"
  type        = string
  default     = "alerts@financialwatch.ng"
}

variable "monthly_budget_amount" {
  description = "Monthly budget ceiling in USD"
  type        = number
  default     = 20.0
}

variable "desired_count" {
  description = "Desired number of running ECS tasks. Defaults to 0 to permit safe initial setup, secrets population, and database migration before scaling to 1."
  type        = number
  default     = 0
}

variable "ecr_repository_name" {
  description = "Name of the ECR repository for the backend image"
  type        = string
  default     = "financial-watch-backend"
}

variable "create_ecr_repository" {
  description = "Set to true if Terraform should create the ECR repository, or false if created via AWS CLI prior to image build"
  type        = bool
  default     = false
}

