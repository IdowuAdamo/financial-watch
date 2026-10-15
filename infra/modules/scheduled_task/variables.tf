variable "project_name" {
  type = string
}

variable "environment" {
  type = string
}

variable "cluster_arn" {
  type = string
}

variable "public_subnet_ids" {
  type = list(string)
}

variable "ecs_security_group_id" {
  type = string
}

variable "task_execution_role_arn" {
  type = string
}

variable "task_role_arn" {
  type = string
}

variable "container_image" {
  type = string
}

variable "database_url" {
  type      = string
  sensitive = true
}

variable "crawler_contact_url" {
  type = string
}

variable "database_url_secret_arn" {
  type    = string
  default = null
}

