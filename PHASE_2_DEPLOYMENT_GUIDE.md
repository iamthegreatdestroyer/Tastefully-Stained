# Phase 2: Infrastructure Deployment - Execution Guide

## 📋 Phase 2 Overview

Phase 2 implements Infrastructure as Code (IaC) using Terraform for AWS deployment and Kubernetes manifests for container orchestration.

**Scope:**

- ✅ VPC and networking infrastructure
- ✅ EKS cluster with auto-scaling
- ✅ RDS PostgreSQL database
- ✅ ElastiCache Redis cluster
- ✅ Kubernetes namespaces and RBAC
- ✅ Application deployments
- ✅ Ingress with TLS certificates
- ✅ Monitoring infrastructure

**Timeline:** 2-3 weeks

---

## 🏗️ Infrastructure Components

### AWS Infrastructure (Terraform)

- **VPC**: 10.x.x.x/16 CIDR with public/private subnets
- **EKS**: Managed Kubernetes with auto-scaling nodes
- **RDS**: PostgreSQL 15+ with automated backups
- **ElastiCache**: Redis 7+ for caching
- **S3**: Bucket for assets with versioning
- **CloudFront**: CDN distribution
- **IAM**: Roles for applications and deployments
- **CloudWatch**: Centralized logging and monitoring

### Kubernetes Infrastructure

- **Namespaces**: tastefully-stained, monitoring, ingress-nginx
- **Deployments**: API with 3+ replicas
- **Services**: LoadBalancer for external access
- **Ingress**: Nginx with Let's Encrypt TLS
- **HPA**: Auto-scaling based on CPU/Memory
- **NetworkPolicies**: Egress/ingress controls
- **ResourceQuotas**: Namespace resource limits
- **StorageClasses**: EBS-backed persistent volumes

---

## 🚀 Deployment Steps

### Step 1: Prepare AWS Account

```bash
# Create S3 backend for Terraform state
aws s3api create-bucket \
  --bucket tastefully-stained-tfstate \
  --region us-east-1

# Enable versioning
aws s3api put-bucket-versioning \
  --bucket tastefully-stained-tfstate \
  --versioning-configuration Status=Enabled

# Create DynamoDB lock table
aws dynamodb create-table \
  --table-name terraform-locks \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5
```

### Step 2: Deploy Infrastructure via GitHub Actions

```bash
# Trigger Phase 2 workflow
# Go to: https://github.com/iamthegreatdestroyer/Tastefully-Stained/actions

# Select workflow: "Phase 2 Infrastructure Deployment"
# Choose environment: staging (recommended for testing)
# Click "Run workflow"

# Monitor deployment in GitHub Actions logs
```

### Step 3: Verify EKS Cluster

```bash
# Update kubeconfig
aws eks update-kubeconfig \
  --region us-east-1 \
  --name tastefully-stained-staging

# Verify cluster access
kubectl cluster-info
kubectl get nodes
kubectl get pods -A
```

### Step 4: Deploy Applications

```bash
# Apply Kubernetes manifests (automated via workflow)
kubectl apply -f infrastructure/kubernetes/namespace-setup.yaml
kubectl apply -f infrastructure/kubernetes/api-deployment.yaml
kubectl apply -f infrastructure/kubernetes/configmaps-secrets.yaml
kubectl apply -f infrastructure/kubernetes/ingress-tls.yaml

# Verify deployments
kubectl rollout status deployment/tastefully-stained-api -n tastefully-stained
```

---

## ✅ Success Criteria

Phase 2 is complete when:

- [ ] Terraform deployment completes without errors
- [ ] EKS cluster is accessible via kubectl
- [ ] All pods are in Running state
- [ ] Application is accessible via ingress URL
- [ ] RDS database is online and accessible
- [ ] Redis cache is online and accessible
- [ ] CloudFront distribution is active
- [ ] TLS certificate is valid (Let's Encrypt)
- [ ] Health checks pass (liveness + readiness)
- [ ] Auto-scaling is operational (HPA active)
- [ ] All monitoring metrics are being collected
- [ ] No errors in pod logs

---

## 🔍 Verification Commands

```bash
# Check infrastructure status
terraform output -json > /tmp/infra.json
cat /tmp/infra.json | jq .

# Check EKS cluster
aws eks describe-cluster --name tastefully-stained-staging

# Check RDS
aws rds describe-db-instances \
  --db-instance-identifier tastefully-stained-staging-db

# Check ElastiCache
aws elasticache describe-cache-clusters \
  --cache-cluster-id tastefully-stained-staging-redis

# Check Kubernetes
kubectl get all -n tastefully-stained
kubectl get ingress -n tastefully-stained
kubectl get hpa -n tastefully-stained

# Test application
curl -k https://$(kubectl get ingress -n tastefully-stained -o jsonpath='{.items[0].status.loadBalancer.ingress[0].hostname}')/health
```

---

## 📊 Infrastructure Costs

### Development Environment (Monthly Estimate)

- EKS: $73 + $60/month (compute)
- RDS: $30-50/month
- ElastiCache: $15-20/month
- Data transfer: $5-10/month
- **Total: ~$180-200/month**

### Production Environment (Monthly Estimate)

- EKS: $73 + $300/month (compute, multi-AZ)
- RDS Multi-AZ: $100-150/month
- ElastiCache Multi-AZ: $60-80/month
- Data transfer: $20-50/month
- CloudFront: $10-50/month
- **Total: ~$650-900/month**

---

## 🔐 Security Best Practices

- ✅ All resources in private subnets by default
- ✅ Network policies restrict traffic
- ✅ RBAC controls pod permissions
- ✅ Secrets stored in AWS Secrets Manager
- ✅ TLS termination at ingress
- ✅ Pod security context enforces non-root
- ✅ Images scanned for vulnerabilities
- ✅ Audit logging enabled
- ✅ Encryption at rest (RDS, S3, EBS)
- ✅ Encryption in transit (TLS 1.2+)

---

## 🚨 Troubleshooting

### Pod fails to start

```bash
kubectl describe pod <pod-name> -n tastefully-stained
kubectl logs <pod-name> -n tastefully-stained
```

### Database connection fails

```bash
# Test connectivity
psql -h <RDS_ENDPOINT> -U postgres -d tastefully_stained

# Check security groups
aws ec2 describe-security-groups --group-ids <sg-id>
```

### Ingress not accessible

```bash
kubectl describe ingress -n tastefully-stained
kubectl get events -n ingress-nginx
```

### Out of cluster resources

```bash
kubectl top nodes
kubectl describe nodes
kubectl autoscale deployment <name> --min=1 --max=10
```

---

## 📞 Next Steps

1. **Proceed to Phase 3**: Monitoring & Observability

   - Deploy Prometheus and Grafana
   - Configure alerting rules
   - Set up log aggregation

2. **Production Rollout**

   - Deploy to production environment
   - Run load testing
   - Validate all systems

3. **Documentation**
   - Create runbooks for common operations
   - Document disaster recovery procedures
   - Update team documentation

---

**Phase 2 Status**: 🚀 **READY FOR DEPLOYMENT**

Execute via GitHub Actions: Phase 2 Infrastructure Deployment workflow
