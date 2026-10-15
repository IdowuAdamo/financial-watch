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
  # When deploying, uncomment the backend block or initialize with:
  # terraform init -backend-config="bucket=YOUR_TF_STATE_BUCKET" -backend-config="region=YOUR_AWS_REGION"
  #
  # backend "s3" {
  #   bucket       = "financial-watch-terraform-state"
  #   key          = "financial-watch/prod/terraform.tfstate"
  #   region       = "af-south-1"
  #   use_lockfile = true
  # }
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
