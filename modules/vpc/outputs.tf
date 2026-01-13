/**
 * VPC Module - Outputs
 * 
 * Exports VPC resources for consumption by other modules.
 * These outputs are critical dependencies for rds, elasticache, and eks modules.
 */

# ============================================================================
# VPC OUTPUTS
# ============================================================================

output "vpc_id" {
  description = "ID of the VPC"
  value       = aws_vpc.main.id
}

output "vpc_cidr_block" {
  description = "CIDR block of the VPC"
  value       = aws_vpc.main.cidr_block
}

output "vpc_arn" {
  description = "ARN of the VPC"
  value       = aws_vpc.main.arn
}

# ============================================================================
# SUBNET OUTPUTS
# ============================================================================

output "public_subnet_ids" {
  description = "IDs of public subnets (for ALB, NAT Gateway)"
  value       = aws_subnet.public[*].id
}

output "private_subnet_ids" {
  description = "IDs of private subnets (for EKS nodes, RDS, ElastiCache)"
  value       = aws_subnet.private[*].id
}

output "public_subnet_cidrs" {
  description = "CIDR blocks of public subnets"
  value       = aws_subnet.public[*].cidr_block
}

output "private_subnet_cidrs" {
  description = "CIDR blocks of private subnets"
  value       = aws_subnet.private[*].cidr_block
}

output "availability_zones" {
  description = "Availability zones used for subnets"
  value       = aws_subnet.private[*].availability_zone
}

# ============================================================================
# GATEWAY OUTPUTS
# ============================================================================

output "internet_gateway_id" {
  description = "ID of the Internet Gateway"
  value       = aws_internet_gateway.main.id
}

output "nat_gateway_ids" {
  description = "IDs of NAT Gateways (one per AZ)"
  value       = aws_nat_gateway.main[*].id
}

output "nat_gateway_public_ips" {
  description = "Public IPs of NAT Gateways"
  value       = aws_eip.nat[*].public_ip
}

# ============================================================================
# ROUTE TABLE OUTPUTS
# ============================================================================

output "public_route_table_id" {
  description = "ID of the public route table"
  value       = aws_route_table.public.id
}

output "private_route_table_ids" {
  description = "IDs of private route tables (one per AZ)"
  value       = aws_route_table.private[*].id
}

# ============================================================================
# SECURITY GROUP OUTPUTS (Critical for other modules)
# ============================================================================

output "application_security_group_id" {
  description = "ID of application tier security group (for EKS nodes)"
  value       = aws_security_group.application.id
}

output "database_security_group_id" {
  description = "ID of database tier security group (for RDS)"
  value       = aws_security_group.database.id
}

output "cache_security_group_id" {
  description = "ID of cache tier security group (for ElastiCache)"
  value       = aws_security_group.cache.id
}

# ============================================================================
# VPC FLOW LOGS OUTPUTS
# ============================================================================

output "flow_logs_log_group_name" {
  description = "Name of CloudWatch Log Group for VPC Flow Logs"
  value       = var.enable_flow_logs ? aws_cloudwatch_log_group.flow_logs[0].name : null
}

output "flow_logs_iam_role_arn" {
  description = "ARN of IAM role used by VPC Flow Logs"
  value       = var.enable_flow_logs ? aws_iam_role.flow_logs[0].arn : null
}

# ============================================================================
# SUMMARY OUTPUTS (for debugging and documentation)
# ============================================================================

output "vpc_summary" {
  description = "Summary of VPC configuration"
  value = {
    vpc_id             = aws_vpc.main.id
    vpc_cidr           = aws_vpc.main.cidr_block
    availability_zones = aws_subnet.private[*].availability_zone
    public_subnets     = length(aws_subnet.public)
    private_subnets    = length(aws_subnet.private)
    nat_gateways       = var.enable_nat_gateway ? length(aws_nat_gateway.main) : 0
    flow_logs_enabled  = var.enable_flow_logs
  }
}
