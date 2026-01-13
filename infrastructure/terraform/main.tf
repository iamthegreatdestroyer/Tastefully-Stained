/**
 * TASTEFULLY STAINED - MAIN TERRAFORM CONFIGURATION
 * Production-Ready Infrastructure as Code
 * Phase 2: Infrastructure Deployment
 */

terraform {
  required_version = ">= 1.5.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.23"
    }
  }

  backend "s3" {
    bucket         = "tastefully-stained-tfstate"
    key            = "prod/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "terraform-locks"
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project             = "tastefully-stained"
      Environment         = var.environment
      ManagedBy           = "terraform"
      CreatedAt           = timestamp()
      CostCenter          = var.cost_center
    }
  }
}

provider "kubernetes" {
  host                   = module.eks.cluster_endpoint
  cluster_ca_certificate = base64decode(module.eks.cluster_certificate_authority_data)
  
  exec {
    api_version = "client.authentication.k8s.io/v1beta1"
    command     = "aws"
    args        = ["eks", "get-token", "--cluster-name", module.eks.cluster_id]
  }
}

# VPC and Networking
module "vpc" {
  source = "./modules/vpc"
  
  project_name           = var.project_name
  environment            = var.environment
  cidr_block            = var.vpc_cidr
  availability_zones    = data.aws_availability_zones.available.names
  
  tags = local.common_tags
}

# EKS Cluster
module "eks" {
  source = "./modules/eks"
  
  cluster_name           = "${var.project_name}-${var.environment}"
  kubernetes_version     = var.kubernetes_version
  subnet_ids             = module.vpc.private_subnet_ids
  vpc_security_group_ids = [module.vpc.cluster_security_group_id]
  
  node_groups = {
    general = {
      desired_size       = var.node_desired_size
      min_size          = var.node_min_size
      max_size          = var.node_max_size
      instance_types    = var.node_instance_types
      disk_size         = var.node_disk_size
    }
  }
  
  enable_cluster_autoscaling = true
  enable_metrics_server      = true
  enable_ebs_csi_driver      = true
  
  tags = local.common_tags
}

# Database (RDS PostgreSQL)
module "rds" {
  source = "./modules/rds"
  
  identifier           = "${var.project_name}-${var.environment}-db"
  engine              = "postgres"
  engine_version      = var.db_engine_version
  instance_class      = var.db_instance_class
  allocated_storage   = var.db_allocated_storage
  
  db_name             = var.db_name
  username            = var.db_master_username
  password            = random_password.db_password.result
  
  subnet_ids          = module.vpc.database_subnet_ids
  security_groups     = [module.vpc.database_security_group_id]
  
  backup_retention_period = var.db_backup_retention_days
  multi_az            = var.db_multi_az
  
  skip_final_snapshot = var.environment != "prod"
  
  tags = local.common_tags
}

# ElastiCache for Redis
module "redis" {
  source = "./modules/elasticache"
  
  cluster_id           = "${var.project_name}-${var.environment}-redis"
  engine              = "redis"
  engine_version      = var.redis_engine_version
  node_type          = var.redis_node_type
  num_cache_nodes     = var.redis_num_nodes
  
  subnet_ids          = module.vpc.cache_subnet_ids
  security_groups     = [module.vpc.cache_security_group_id]
  
  automatic_failover_enabled = var.redis_multi_az
  
  tags = local.common_tags
}

# S3 Bucket for Assets
module "s3" {
  source = "./modules/s3"
  
  bucket_name         = "${var.project_name}-${var.environment}-assets-${data.aws_caller_identity.current.account_id}"
  versioning_enabled  = true
  
  encryption = {
    enabled = true
    type    = "AES256"
  }
  
  public_access_block = {
    block_public_acls       = true
    block_public_policy     = true
    ignore_public_acls      = true
    restrict_public_buckets = true
  }
  
  lifecycle_rules = [
    {
      id     = "delete-old-versions"
      prefix = ""
      days   = 30
    }
  ]
  
  tags = local.common_tags
}

# CloudFront Distribution
module "cloudfront" {
  source = "./modules/cloudfront"
  
  bucket_id             = module.s3.bucket_id
  bucket_regional_domain_name = module.s3.bucket_regional_domain_name
  
  distribution_enabled  = true
  default_cache_behavior = {
    allowed_methods = ["GET", "HEAD"]
    compress       = true
    ttl           = 3600
  }
  
  tags = local.common_tags
}

# Secrets Manager
module "secrets" {
  source = "./modules/secrets"
  
  db_password = {
    name  = "${var.project_name}/${var.environment}/db/password"
    value = random_password.db_password.result
  }
  
  api_keys = {
    name = "${var.project_name}/${var.environment}/api/keys"
  }
  
  tags = local.common_tags
}

# IAM Roles and Policies
module "iam" {
  source = "./modules/iam"
  
  project_name      = var.project_name
  environment       = var.environment
  eks_cluster_arn   = module.eks.cluster_arn
  
  create_app_role        = true
  create_deployer_role   = true
  
  s3_bucket_arn          = module.s3.arn
  rds_resource_arn       = module.rds.arn
  redis_resource_arn     = module.redis.arn
  
  tags = local.common_tags
}

# Monitoring and Logging
module "monitoring" {
  source = "./modules/monitoring"
  
  project_name      = var.project_name
  environment       = var.environment
  
  enable_cloudwatch = true
  log_retention_days = var.log_retention_days
  
  enable_xray       = true
  
  eks_cluster_name = module.eks.cluster_id
  
  tags = local.common_tags
}

# Random password for DB
resource "random_password" "db_password" {
  length  = 32
  special = true
}

# Data sources
data "aws_caller_identity" "current" {}

data "aws_availability_zones" "available" {
  state = "available"
}

# Local variables
locals {
  common_tags = {
    Project             = var.project_name
    Environment         = var.environment
    ManagedBy           = "terraform"
    Team                = var.team_name
  }
}
