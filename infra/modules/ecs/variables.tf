variable "project_name" {
  type = string
}

variable "environment" {
  type = string
}

variable "vpc_id" {
  type = string
}

variable "public_subnet_ids" {
  type = list(string)
}

variable "alb_security_group_id" {
  type = string
}

variable "target_group_arn" {
  type = string
}

variable "container_image" {
  type = string
}

variable "database_url" {
  type      = string
  sensitive = true
}

variable "api_access_key" {
  type      = string
  sensitive = true
}

variable "crawler_contact_url" {
  type = string
}

variable "openai_api_key" {
  type      = string
  sensitive = true
  default   = ""
}

variable "desired_count" {
  type    = number
  default = 0
}

variable "ecr_repository_name" {
  type    = string
  default = "financial-watch-backend"
}

variable "create_ecr_repository" {
  type    = bool
  default = false
}

