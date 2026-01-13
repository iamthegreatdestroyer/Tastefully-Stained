/**
 * PRODUCTION ENVIRONMENT CONFIGURATION
 * Production infrastructure with full redundancy and high availability
 */

aws_region = "us-east-1"
environment = "prod"
project_name = "tastefully-stained"
team_name = "platform-engineering"
cost_center = "production"

# VPC Configuration
vpc_cidr           = "10.2.0.0/16"
availability_zones = ["us-east-1a", "us-east-1b", "us-east-1c"]

# Production-Grade Features
enable_nat_gateway        = true
enable_flow_logs          = true
flow_logs_retention_days  = 90  # Extended 90-day retention for compliance and auditing

# EKS Configuration - High availability for production
kubernetes_version = "1.27"
node_desired_size  = 3
node_min_size      = 3
node_max_size      = 10
node_instance_types = ["t3.xlarge"]
node_disk_size     = 100

# RDS Configuration - High availability for production
db_engine_version      = "15.3"
db_instance_class      = "db.t3.medium"
db_allocated_storage   = 100
db_multi_az            = true
db_backup_retention_days = 30

# ElastiCache Configuration - Multi-AZ for production
redis_engine_version = "7.0"
redis_node_type      = "cache.t3.large"
redis_num_nodes      = 3
redis_multi_az       = true

# Logging
log_retention_days = 90
