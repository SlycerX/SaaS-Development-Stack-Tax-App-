terraform {
  required_version = ">= 1.6.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.70"
    }
  }
  backend "s3" {}
}

provider "aws" {
  region = var.region
  default_tags {
    tags = {
      Product     = var.product_name
      Environment = "prod"
    }
  }
}
