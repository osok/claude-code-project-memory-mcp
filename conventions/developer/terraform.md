# Terraform Conventions

## Project Structure

```
infrastructure/
├── environments/
│   ├── dev/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   ├── outputs.tf
│   │   └── terraform.tfvars
│   ├── staging/
│   └── prod/
├── modules/
│   ├── vpc/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── outputs.tf
│   ├── ecs/
│   ├── rds/
│   └── s3/
├── shared/
│   └── backend.tf
└── README.md
```

## Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| File | lowercase | `main.tf`, `variables.tf` |
| Resource | snake_case | `aws_instance.web_server` |
| Variable | snake_case | `instance_type` |
| Output | snake_case | `vpc_id` |
| Module | kebab-case | `modules/vpc-network` |
| Local | snake_case | `common_tags` |

## Resource Naming Pattern

```hcl
# Format: {project}-{environment}-{resource_type}-{name}
resource "aws_s3_bucket" "app_assets" {
  bucket = "${var.project}-${var.environment}-assets"

  tags = merge(local.common_tags, {
    Name = "${var.project}-${var.environment}-assets"
  })
}
```

## Standard Variables

```hcl
# variables.tf
variable "project" {
  description = "Project name"
  type        = string
}

variable "environment" {
  description = "Environment (dev, staging, prod)"
  type        = string

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be dev, staging, or prod."
  }
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "tags" {
  description = "Additional tags"
  type        = map(string)
  default     = {}
}
```

## Commands

| Action | Command |
|--------|---------|
| Initialize | `terraform init` |
| Plan | `terraform plan` |
| Apply | `terraform apply` |
| Destroy | `terraform destroy` |
| Format | `terraform fmt -recursive` |
| Validate | `terraform validate` |
| Import | `terraform import {resource} {id}` |
| State list | `terraform state list` |

## Module Structure

```hcl
# modules/vpc/main.tf
resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = merge(var.tags, {
    Name = "${var.name}-vpc"
  })
}

resource "aws_subnet" "public" {
  count             = length(var.public_subnets)
  vpc_id            = aws_vpc.main.id
  cidr_block        = var.public_subnets[count.index]
  availability_zone = var.availability_zones[count.index]

  map_public_ip_on_launch = true

  tags = merge(var.tags, {
    Name = "${var.name}-public-${count.index + 1}"
    Type = "public"
  })
}

# modules/vpc/variables.tf
variable "name" {
  description = "Name prefix for resources"
  type        = string
}

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
}

variable "public_subnets" {
  description = "List of public subnet CIDRs"
  type        = list(string)
}

variable "availability_zones" {
  description = "List of availability zones"
  type        = list(string)
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}

# modules/vpc/outputs.tf
output "vpc_id" {
  description = "ID of the VPC"
  value       = aws_vpc.main.id
}

output "public_subnet_ids" {
  description = "IDs of public subnets"
  value       = aws_subnet.public[*].id
}
```

## Module Usage

```hcl
# environments/dev/main.tf
terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket = "myproject-terraform-state"
    key    = "dev/terraform.tfstate"
    region = "us-east-1"
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = local.common_tags
  }
}

locals {
  common_tags = {
    Project     = var.project
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

module "vpc" {
  source = "../../modules/vpc"

  name               = "${var.project}-${var.environment}"
  vpc_cidr           = "10.0.0.0/16"
  public_subnets     = ["10.0.1.0/24", "10.0.2.0/24"]
  availability_zones = ["us-east-1a", "us-east-1b"]
  tags               = local.common_tags
}
```

## Code Style

- Use `terraform fmt` for formatting
- Pin provider versions
- Use remote state with locking
- Keep modules small and focused
- Document all variables
- Use locals for repeated values
- Add validation to variables
- Always tag resources
- Use data sources over hardcoded values
