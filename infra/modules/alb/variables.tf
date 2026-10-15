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

variable "origin_verify_secret" {
  description = "Secret token header required from CloudFront to prevent direct ALB bypass"
  type        = string
  sensitive   = true
}
