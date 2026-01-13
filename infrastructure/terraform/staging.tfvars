/**
 * STAGING ENVIRONMENT CONFIGURATION
 * Staging infrastructure with moderate redundancy for testing
 */

aws_region = "us-east-1"
environment = "staging"
project_name = "tastefully-stained"
team_name = "platform-engineering"

# VPC Configuration
vpc_cidr           = "10.1.0.0/16"
availability_zones = ["us-east-1a", "us-east-1b", "us-east-1c"]

# Full Feature Set for Staging
enable_nat_gateway        = true
enable_flow_logs          = true
flow_logs_retention_days  = 30  # Standard 30-day retention for staging

# EKS Configuration - Standard for staging
kubernetes_version = "1.27"
node_desired_size  = 2
node_min_size      = 2
node_max_size      = 5
node_instance_types = ["t3.large"]
node_disk_size     = 75

# RDS Configuration - Production-like for staging
db_engine_version      = "15.3"
db_instance_class      = "db.t3.small"
db_allocated_storage   = 50
db_multi_az            = false
db_backup_retention_days = 7

# ElastiCache Configuration - Replicated for staging
redis_engine_version = "7.0"
redis_node_type      = "cache.t3.small"
redis_num_nodes      = 1
redis_multi_az       = false

# Logging
log_retention_days = 14
