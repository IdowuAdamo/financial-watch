variable "project_name" {
  type = string
}

variable "environment" {
  type = string
}

variable "alb_dns_name" {
  type = string
}

variable "origin_verify_secret" {
  type      = string
  sensitive = true
}

variable "api_access_key" {
  type        = string
  sensitive   = true
  description = "Backend API access key injected into ALB origin requests"
}
