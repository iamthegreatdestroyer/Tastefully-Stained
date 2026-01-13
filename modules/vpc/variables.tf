/**
 * VPC Module - Input Variables
 * 
 * Defines all configurable parameters for VPC module.
 * These variables are passed from the root module.
 */

# ============================================================================
# REQUIRED VARIABLES
# ============================================================================

variable "project_name" {
  description = "Name of the project (used for resource naming)"
  type        = string

  validation {
    condition     = can(regex("^[a-z0-9-]+$", var.project_name))
    error_message = "Project name must contain only lowercase letters, numbers, and hyphens."
  }
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be one of: dev, staging, prod."
  }
}

variable "vpc_cidr" {
  description = "CIDR block for VPC (e.g., 10.0.0.0/16)"
  type        = string

  validation {
    condition     = can(cidrhost(var.vpc_cidr, 0))
    error_message = "VPC CIDR must be a valid IPv4 CIDR block."
  }
}

variable "availability_zones" {
  description = "List of availability zones to use (e.g., ['us-east-1a', 'us-east-1b', 'us-east-1c'])"
  type        = list(string)

  validation {
    condition     = length(var.availability_zones) >= 2
    error_message = "At least 2 availability zones are required for high availability."
  }
}

# ============================================================================
# OPTIONAL VARIABLES
# ============================================================================

variable "enable_nat_gateway" {
  description = "Enable NAT Gateway for private subnet internet access (disable for cost savings in dev)"
  type        = bool
  default     = true
}

variable "enable_flow_logs" {
  description = "Enable VPC Flow Logs for network traffic analysis"
  type        = bool
  default     = true
}

variable "flow_logs_retention_days" {
  description = "Number of days to retain VPC Flow Logs in CloudWatch"
  type        = number
  default     = 30

  validation {
    condition     = contains([1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365, 400, 545, 731, 1827, 3653], var.flow_logs_retention_days)
    error_message = "Flow logs retention must be a valid CloudWatch Logs retention period."
  }
}

variable "tags" {
  description = "Additional tags to apply to all resources"
  type        = map(string)
  default     = {}
}
