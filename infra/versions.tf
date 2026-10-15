terraform {
  required_version = ">= 1.10.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.50"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }

  # Remote State Storage with S3 Native State Locking (Terraform >= 1.10)
  backend "s3" {
    use_lockfile = true
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "FinancialWatch"
      Environment = var.environment
      ManagedBy   = "Terraform"
      Repository  = "financial-watch"
    }
  }
}

provider "aws" {
  alias  = "us_east_1"
  region = "us-east-1" # Required for CloudFront ACM TLS Certificates

  default_tags {
    tags = {
      Project     = "FinancialWatch"
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  }
}
