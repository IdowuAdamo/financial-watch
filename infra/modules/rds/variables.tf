variable "project_name" {
  type = string
}

variable "environment" {
  type = string
}

variable "vpc_id" {
  type = string
}

variable "private_subnet_ids" {
  type = list(string)
}

variable "ecs_security_group_id" {
  description = "Security group of ECS tasks allowed to connect to PostgreSQL"
  type        = string
}

variable "db_name" {
  type    = string
  default = "financial_watch"
}

variable "db_username" {
  type    = string
  default = "fw_admin"
}

variable "db_password" {
  type      = string
  sensitive = true
}
