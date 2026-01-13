/**
 * VPC Module - Foundational Network Infrastructure
 * 
 * Creates a production-ready VPC with:
 * - Public and private subnets across 3 availability zones
 * - Internet Gateway for public subnet internet access
 * - NAT Gateways for private subnet egress (one per AZ for HA)
 * - Route tables with appropriate routing rules
 * - Security groups for application, database, and cache tiers
 * - VPC Flow Logs for network traffic analysis
 * 
 * Dependencies: None (foundational module)
 * Consumed By: rds, elasticache, eks modules
 */

# ============================================================================
# DATA SOURCES
# ============================================================================

data "aws_availability_zones" "available" {
  state = "available"

  # Exclude local zones (use only standard AZs)
  filter {
    name   = "opt-in-status"
    values = ["opt-in-not-required"]
  }
}

# ============================================================================
# VPC
# ============================================================================

resource "aws_vpc" "main" {
  cidr_block = var.vpc_cidr

  # Enable DNS support for RDS and other AWS services
  enable_dns_hostnames = true
  enable_dns_support   = true

  # Enable VPC flow logs to CloudWatch
  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-vpc-${var.environment}"
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  )
}

# ============================================================================
# INTERNET GATEWAY (for public subnets)
# ============================================================================

resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-igw-${var.environment}"
      Environment = var.environment
    }
  )
}

# ============================================================================
# ELASTIC IPS (for NAT Gateways)
# ============================================================================

resource "aws_eip" "nat" {
  count  = var.enable_nat_gateway ? length(var.availability_zones) : 0
  domain = "vpc"

  # Ensure IGW exists before creating EIP
  depends_on = [aws_internet_gateway.main]

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-eip-nat-${var.availability_zones[count.index]}-${var.environment}"
      Environment = var.environment
    }
  )
}

# ============================================================================
# PUBLIC SUBNETS (one per AZ)
# ============================================================================

resource "aws_subnet" "public" {
  count = length(var.availability_zones)

  vpc_id            = aws_vpc.main.id
  cidr_block        = cidrsubnet(var.vpc_cidr, 4, count.index)
  availability_zone = data.aws_availability_zones.available.names[count.index]

  # Auto-assign public IPs to instances in public subnets
  map_public_ip_on_launch = true

  tags = merge(
    var.tags,
    {
      Name                                           = "${var.project_name}-public-${var.availability_zones[count.index]}-${var.environment}"
      Environment                                    = var.environment
      Tier                                           = "Public"
      "kubernetes.io/role/elb"                       = "1"
      "kubernetes.io/cluster/${var.project_name}-${var.environment}" = "shared"
    }
  )
}

# ============================================================================
# PRIVATE SUBNETS (one per AZ)
# ============================================================================

resource "aws_subnet" "private" {
  count = length(var.availability_zones)

  vpc_id            = aws_vpc.main.id
  cidr_block        = cidrsubnet(var.vpc_cidr, 4, count.index + length(var.availability_zones))
  availability_zone = data.aws_availability_zones.available.names[count.index]

  # Private subnets should not auto-assign public IPs
  map_public_ip_on_launch = false

  tags = merge(
    var.tags,
    {
      Name                                           = "${var.project_name}-private-${var.availability_zones[count.index]}-${var.environment}"
      Environment                                    = var.environment
      Tier                                           = "Private"
      "kubernetes.io/role/internal-elb"              = "1"
      "kubernetes.io/cluster/${var.project_name}-${var.environment}" = "shared"
    }
  )
}

# ============================================================================
# NAT GATEWAYS (one per AZ for high availability)
# ============================================================================

resource "aws_nat_gateway" "main" {
  count = var.enable_nat_gateway ? length(var.availability_zones) : 0

  allocation_id = aws_eip.nat[count.index].id
  subnet_id     = aws_subnet.public[count.index].id

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-nat-${var.availability_zones[count.index]}-${var.environment}"
      Environment = var.environment
    }
  )

  # Ensure IGW exists before creating NAT Gateway
  depends_on = [aws_internet_gateway.main]
}

# ============================================================================
# ROUTE TABLES - Public
# ============================================================================

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-rt-public-${var.environment}"
      Environment = var.environment
      Tier        = "Public"
    }
  )
}

# Public route to Internet Gateway
resource "aws_route" "public_internet_gateway" {
  route_table_id         = aws_route_table.public.id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id             = aws_internet_gateway.main.id
}

# Associate public subnets with public route table
resource "aws_route_table_association" "public" {
  count = length(var.availability_zones)

  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

# ============================================================================
# ROUTE TABLES - Private (one per AZ for NAT Gateway routing)
# ============================================================================

resource "aws_route_table" "private" {
  count = length(var.availability_zones)

  vpc_id = aws_vpc.main.id

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-rt-private-${var.availability_zones[count.index]}-${var.environment}"
      Environment = var.environment
      Tier        = "Private"
    }
  )
}

# Private route to NAT Gateway (if enabled)
resource "aws_route" "private_nat_gateway" {
  count = var.enable_nat_gateway ? length(var.availability_zones) : 0

  route_table_id         = aws_route_table.private[count.index].id
  destination_cidr_block = "0.0.0.0/0"
  nat_gateway_id         = aws_nat_gateway.main[count.index].id
}

# Associate private subnets with private route tables
resource "aws_route_table_association" "private" {
  count = length(var.availability_zones)

  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private[count.index].id
}

# ============================================================================
# SECURITY GROUPS
# ============================================================================

# Application Security Group (for EKS nodes and application workloads)
resource "aws_security_group" "application" {
  name_prefix = "${var.project_name}-app-${var.environment}-"
  description = "Security group for application tier (EKS nodes)"
  vpc_id      = aws_vpc.main.id

  # Allow all traffic within the security group (for pod-to-pod communication)
  ingress {
    description = "Allow all traffic from within security group"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    self        = true
  }

  # Allow HTTPS from anywhere (for ALB/NLB health checks and ingress)
  ingress {
    description = "HTTPS from anywhere"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Allow HTTP from anywhere (for ALB/NLB health checks)
  ingress {
    description = "HTTP from anywhere"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Allow all outbound traffic
  egress {
    description = "Allow all outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-sg-app-${var.environment}"
      Environment = var.environment
      Tier        = "Application"
    }
  )

  lifecycle {
    create_before_destroy = true
  }
}

# Database Security Group (for RDS)
resource "aws_security_group" "database" {
  name_prefix = "${var.project_name}-db-${var.environment}-"
  description = "Security group for database tier (RDS)"
  vpc_id      = aws_vpc.main.id

  # Allow PostgreSQL from application security group
  ingress {
    description     = "PostgreSQL from application tier"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.application.id]
  }

  # No outbound rules needed for RDS (managed by AWS)
  egress {
    description = "Allow all outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-sg-db-${var.environment}"
      Environment = var.environment
      Tier        = "Database"
    }
  )

  lifecycle {
    create_before_destroy = true
  }
}

# Cache Security Group (for ElastiCache)
resource "aws_security_group" "cache" {
  name_prefix = "${var.project_name}-cache-${var.environment}-"
  description = "Security group for cache tier (ElastiCache)"
  vpc_id      = aws_vpc.main.id

  # Allow Redis from application security group
  ingress {
    description     = "Redis from application tier"
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [aws_security_group.application.id]
  }

  # No outbound rules needed for ElastiCache (managed by AWS)
  egress {
    description = "Allow all outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-sg-cache-${var.environment}"
      Environment = var.environment
      Tier        = "Cache"
    }
  )

  lifecycle {
    create_before_destroy = true
  }
}

# ============================================================================
# VPC FLOW LOGS (for network traffic analysis)
# ============================================================================

resource "aws_flow_log" "main" {
  count = var.enable_flow_logs ? 1 : 0

  iam_role_arn    = aws_iam_role.flow_logs[0].arn
  log_destination = aws_cloudwatch_log_group.flow_logs[0].arn
  traffic_type    = "ALL"
  vpc_id          = aws_vpc.main.id

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-flow-logs-${var.environment}"
      Environment = var.environment
    }
  )
}

# CloudWatch Log Group for VPC Flow Logs
resource "aws_cloudwatch_log_group" "flow_logs" {
  count = var.enable_flow_logs ? 1 : 0

  name              = "/aws/vpc/${var.project_name}-${var.environment}"
  retention_in_days = var.flow_logs_retention_days

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-flow-logs-${var.environment}"
      Environment = var.environment
    }
  )
}

# IAM Role for VPC Flow Logs
resource "aws_iam_role" "flow_logs" {
  count = var.enable_flow_logs ? 1 : 0

  name_prefix = "${var.project_name}-flow-logs-${var.environment}-"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "vpc-flow-logs.amazonaws.com"
        }
      }
    ]
  })

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-flow-logs-role-${var.environment}"
      Environment = var.environment
    }
  )
}

# IAM Policy for VPC Flow Logs
resource "aws_iam_role_policy" "flow_logs" {
  count = var.enable_flow_logs ? 1 : 0

  name_prefix = "${var.project_name}-flow-logs-policy-${var.environment}-"
  role        = aws_iam_role.flow_logs[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "logs:DescribeLogGroups",
          "logs:DescribeLogStreams"
        ]
        Effect = "Allow"
        Resource = "*"
      }
    ]
  })
}
