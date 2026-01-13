/**
 * TERRAFORM OUTPUTS
 * Export infrastructure details for consumption by applications
 */

# VPC Outputs
output "vpc_id" {
  description = "VPC ID"
  value       = module.vpc.vpc_id
}

output "private_subnet_ids" {
  description = "Private subnet IDs"
  value       = module.vpc.private_subnet_ids
}

output "public_subnet_ids" {
  description = "Public subnet IDs"
  value       = module.vpc.public_subnet_ids
}

# EKS Outputs
output "eks_cluster_id" {
  description = "EKS cluster ID"
  value       = module.eks.cluster_id
}

output "eks_cluster_endpoint" {
  description = "EKS cluster endpoint"
  value       = module.eks.cluster_endpoint
  sensitive   = true
}

output "eks_cluster_security_group_id" {
  description = "EKS cluster security group ID"
  value       = module.eks.cluster_security_group_id
}

output "eks_cluster_arn" {
  description = "EKS cluster ARN"
  value       = module.eks.cluster_arn
}

output "eks_oidc_provider_arn" {
  description = "EKS OIDC provider ARN for IRSA"
  value       = module.eks.oidc_provider_arn
}

# RDS Outputs
output "rds_endpoint" {
  description = "RDS database endpoint"
  value       = module.rds.endpoint
  sensitive   = true
}

output "rds_database_name" {
  description = "RDS database name"
  value       = module.rds.database_name
}

output "rds_master_username" {
  description = "RDS master username"
  value       = module.rds.master_username
  sensitive   = true
}

output "rds_arn" {
  description = "RDS database ARN"
  value       = module.rds.arn
}

# ElastiCache Outputs
output "redis_endpoint" {
  description = "Redis primary endpoint"
  value       = module.redis.primary_endpoint_address
}

output "redis_port" {
  description = "Redis port"
  value       = module.redis.port
}

output "redis_cluster_id" {
  description = "Redis cluster ID"
  value       = module.redis.cluster_id
}

# S3 Outputs
output "s3_bucket_id" {
  description = "S3 bucket ID"
  value       = module.s3.bucket_id
}

output "s3_bucket_arn" {
  description = "S3 bucket ARN"
  value       = module.s3.arn
}

output "s3_regional_domain_name" {
  description = "S3 regional domain name"
  value       = module.s3.bucket_regional_domain_name
}

# CloudFront Outputs
output "cloudfront_distribution_id" {
  description = "CloudFront distribution ID"
  value       = module.cloudfront.distribution_id
}

output "cloudfront_domain_name" {
  description = "CloudFront domain name"
  value       = module.cloudfront.distribution_domain_name
}

# Secrets Manager Outputs
output "db_password_secret_arn" {
  description = "ARN of DB password secret"
  value       = module.secrets.db_password_secret_arn
}

output "api_keys_secret_arn" {
  description = "ARN of API keys secret"
  value       = module.secrets.api_keys_secret_arn
}

# IAM Outputs
output "app_role_arn" {
  description = "ARN of application IAM role"
  value       = module.iam.app_role_arn
}

output "deployer_role_arn" {
  description = "ARN of deployer IAM role"
  value       = module.iam.deployer_role_arn
}

# Monitoring Outputs
output "cloudwatch_log_group_name" {
  description = "CloudWatch log group name"
  value       = module.monitoring.log_group_name
}

# Export as JSON for easy consumption
output "infrastructure_config" {
  description = "Complete infrastructure configuration"
  value = jsonencode({
    region           = var.aws_region
    environment      = var.environment
    project_name     = var.project_name
    
    eks = {
      cluster_id   = module.eks.cluster_id
      endpoint     = module.eks.cluster_endpoint
      oidc_provider = module.eks.oidc_provider_arn
    }
    
    rds = {
      endpoint = module.rds.endpoint
      port     = module.rds.port
      database = var.db_name
      username = var.db_master_username
    }
    
    redis = {
      endpoint = module.redis.primary_endpoint_address
      port     = module.redis.port
    }
    
    s3 = {
      bucket = module.s3.bucket_id
      region = var.aws_region
    }
    
    cloudfront = {
      domain_name = module.cloudfront.distribution_domain_name
    }
  })
  sensitive = true
}
