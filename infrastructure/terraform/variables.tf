/**
 * TERRAFORM VARIABLES
 * Input variables for infrastructure configuration
 */

variable "aws_region" {
  description = "AWS region for resource deployment"
  type        = string
  default     = "us-east-1"
  
  validation {
    condition     = can(regex("^[a-z]{2}-[a-z]+-\\d{1}$", var.aws_region))
    error_message = "AWS region must be valid format (e.g., us-east-1)."
  }
}

variable "project_name" {
  description = "Name of the project"
  type        = string
  default     = "tastefully-stained"
  
  validation {
    condition     = can(regex("^[a-z0-9-]+$", var.project_name))
    error_message = "Project name must contain only lowercase letters, numbers, and hyphens."
  }
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"
  
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be one of: dev, staging, prod."
  }
}

variable "team_name" {
  description = "Team responsible for this infrastructure"
  type        = string
  default     = "platform-engineering"
}

variable "cost_center" {
  description = "Cost center for billing purposes"
  type        = string
  default     = "engineering"
}

# VPC Configuration
variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
  
  validation {
    condition     = can(cidrhost(var.vpc_cidr, 0))
    error_message = "VPC CIDR must be a valid CIDR block."
  }
}

# EKS Configuration
variable "kubernetes_version" {
  description = "Kubernetes version for EKS cluster"
  type        = string
  default     = "1.27"
}

variable "node_desired_size" {
  description = "Desired number of worker nodes"
  type        = number
  default     = 3
  
  validation {
    condition     = var.node_desired_size >= 1 && var.node_desired_size <= 100
    error_message = "Desired node size must be between 1 and 100."
  }
}

variable "node_min_size" {
  description = "Minimum number of worker nodes"
  type        = number
  default     = 1
}

variable "node_max_size" {
  description = "Maximum number of worker nodes"
  type        = number
  default     = 10
}

variable "node_instance_types" {
  description = "EC2 instance types for worker nodes"
  type        = list(string)
  default     = ["t3.large"]
}

variable "node_disk_size" {
  description = "EBS volume size for worker nodes (GB)"
  type        = number
  default     = 100
}

# RDS Configuration
variable "db_engine_version" {
  description = "PostgreSQL engine version"
  type        = string
  default     = "15.3"
}

variable "db_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.small"
}

variable "db_allocated_storage" {
  description = "Allocated storage for RDS (GB)"
  type        = number
  default     = 20
}

variable "db_name" {
  description = "Initial database name"
  type        = string
  default     = "tastefully_stained"
  sensitive   = true
}

variable "db_master_username" {
  description = "Master username for RDS"
  type        = string
  default     = "postgres"
  sensitive   = true
}

variable "db_multi_az" {
  description = "Enable Multi-AZ for RDS"
  type        = bool
  default     = false
}

variable "db_backup_retention_days" {
  description = "RDS backup retention period (days)"
  type        = number
  default     = 7
}

# ElastiCache Configuration
variable "redis_engine_version" {
  description = "Redis engine version"
  type        = string
  default     = "7.0"
}

variable "redis_node_type" {
  description = "ElastiCache node type"
  type        = string
  default     = "cache.t3.micro"
}

variable "redis_num_nodes" {
  description = "Number of Redis nodes"
  type        = number
  default     = 1
}

variable "redis_multi_az" {
  description = "Enable Multi-AZ for Redis"
  type        = bool
  default     = false
}

# Logging
variable "log_retention_days" {
  description = "CloudWatch log retention period (days)"
  type        = number
  default     = 30
  
  validation {
    condition     = contains([1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365, 400, 545, 731, 1827, 3653], var.log_retention_days)
    error_message = "Log retention days must be a valid CloudWatch value."
  }
}

# Environment-specific overrides
variable "environment_config" {
  description = "Environment-specific configuration overrides"
  type        = map(any)
  default     = {}
}
