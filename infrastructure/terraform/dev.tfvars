/**
 * DEVELOPMENT ENVIRONMENT CONFIGURATION
 * Development infrastructure with minimal redundancy for cost efficiency
 */

aws_region = "us-east-1"
environment = "dev"
project_name = "tastefully-stained"
team_name = "platform-engineering"

# VPC Configuration
vpc_cidr = "10.0.0.0/16"

# EKS Configuration - Minimal for dev
kubernetes_version = "1.27"
node_desired_size  = 1
node_min_size      = 1
node_max_size      = 3
node_instance_types = ["t3.medium"]
node_disk_size     = 50

# RDS Configuration - Smaller instances for dev
db_engine_version      = "15.3"
db_instance_class      = "db.t3.micro"
db_allocated_storage   = 20
db_multi_az            = false
db_backup_retention_days = 3

# ElastiCache Configuration - Single node for dev
redis_engine_version = "7.0"
redis_node_type      = "cache.t3.micro"
redis_num_nodes      = 1
redis_multi_az       = false

# Logging
log_retention_days = 7
