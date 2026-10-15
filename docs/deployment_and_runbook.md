# FinancialWatch: Deployment Runbook & Operational Cost Optimization

## 1. Local Development Setup

### 1.1 Prerequisites
- Python 3.12+ (managed with `uv`)
- Node.js 20+ (with npm)
- Docker Desktop (for PostgreSQL 16 + pgvector)
- Terraform v1.16+ (installed locally)

### 1.2 Step-by-Step Local Deployment

1. **Clone and Configure Environment:**
   ```bash
   cp .env.example .env
   ```
   Ensure `.env` contains:
   ```env
   DATABASE_URL=postgresql://postgres:postgres@localhost:5433/financial_watch
   API_ACCESS_KEY=fw-test-access-key-2026
   CRAWLER_CONTACT_URL=https://github.com/client/financial-watch
   OPENAI_API_KEY=mock-api-key # Or real sk-proj key for live external API
   ```

2. **Launch Docker pgvector:**
   *(Note: Explicitly mapped to port 5433 to prevent port conflict with native Windows PostgreSQL installations)*
   ```bash
   docker run -d \
     --name financial-watch-pgvector \
     -p 5433:5432 \
     -e POSTGRES_PASSWORD=postgres \
     -e POSTGRES_DB=financial_watch \
     pgvector/pgvector:pg16
   ```

3. **Install Python Dependencies and Load Knowledge Base Snapshot:**
   ```bash
   uv sync
   uv run python -m memory.cli load-snapshot
   ```

4. **Build Frontend Static Export:**
   ```bash
   cd frontend
   npm install
   npm run build
   cd ..
   ```

5. **Start Unified FastAPI Server (Single-Origin Fallback):**
   ```bash
   uv run uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
   ```
   Open `http://localhost:8000/` in your browser. The single-origin server automatically serves the static frontend SPA with the embedded API endpoints.

---

## 2. AWS Production Deployment Guide (Terraform)

### 2.1 Regional Architecture & S3 Native State Locking
The infrastructure is deployed into **`us-east-1`** (US East, N. Virginia). 

**Regional Selection Rationale (`us-east-1`):**
1. **Amazon Bedrock Availability:** Full foundation model access (Anthropic Claude 3.5 Sonnet, Amazon Titan Embeddings) is available natively without requiring cross-region API hops.
2. **Global CloudFront SSL Requirements:** CloudFront distributions require ACM SSL certificates to be provisioned in `us-east-1`.
3. **Lowest Pricing Tiers:** Compute (Fargate $0.04048/vCPU-hr, $0.004445/GB-hr) and RDS pricing in `us-east-1` minimize baseline expenditure to strictly observe the $20 ceiling.

The state configuration utilizes Terraform 1.10+ native S3 state locking (`use_lockfile = true`), eliminating DynamoDB lock table provisioning costs:

```hcl
backend "s3" {
  bucket       = "financial-watch-terraform-state"
  key          = "financial-watch/prod/terraform.tfstate"
  region       = "us-east-1"
  use_lockfile = true
}
```

### 2.2 Managing the ECR Repository Conflict
In continuous deployment pipelines, the ECR repository `financial-watch-backend` is often created via AWS CLI prior to image build. To prevent resource collision (`RepositoryAlreadyExistsException`), `create_ecr_repository` in `variables.tf` defaults to `false`. 

To manage an existing ECR repository under Terraform:
```bash
terraform import module.ecs.aws_ecr_repository.backend[0] financial-watch-backend
```

### 2.3 Staged Provisioning Sequence

To prevent ECS tasks from crashing due to unpopulated secrets or uninitialized database schemas, deployment proceeds in four strict sequential stages:

1. **Initialize Terraform:**
   ```bash
   cd infra
   terraform init -backend=false  # Or configure remote backend
   terraform validate
   ```

2. **Step 1: Apply Infrastructure at `desired_count = 0`:**
   ```bash
   terraform apply -var="desired_count=0"
   ```
   *Result:* VPC, RDS PostgreSQL, ALB, CloudFront, IAM roles, and empty Secrets Manager containers are provisioned safely without running active container tasks.

3. **Step 2: Populate External Secrets via AWS CLI:**
   ```bash
   aws secretsmanager put-secret-value \
     --secret-id $(terraform output -raw ecs_cluster_name)-openai-key \
     --secret-string "sk-proj-YOUR_ACTUAL_KEY"
   ```

4. **Step 3: Execute Database Snapshot Load / Migration Task:**
   Execute the ready-to-run migration command directly from Terraform outputs:
   ```bash
   eval $(terraform output -raw migration_command)
   ```
   *Alternative manual command:*
   ```bash
   aws ecs run-task \
     --cluster $(terraform output -raw ecs_cluster_name) \
     --task-definition $(terraform output -raw migration_task_arn) \
     --launch-type FARGATE \
     --network-configuration "awsvpcConfiguration={subnets=[$(terraform output -json public_subnet_ids | jq -r 'join(",")')],securityGroups=[$(terraform output -raw ecs_security_group_id)],assignPublicIp=ENABLED}"
   ```

5. **Step 4: Scale ECS Service to 1 Task:**
   Once migrations succeed and secrets are present, scale the service:
   ```bash
   aws ecs update-service \
     --cluster $(terraform output -raw ecs_cluster_name) \
     --service $(terraform output -raw ecs_service_name) \
     --desired-count 1
   ```
   *(Or re-run `terraform apply -var="desired_count=1"`).*

---

## 3. Cost Architecture & The $20 Monthly Ceiling

### 3.1 Task Sizing & Monthly Cost Breakdown
The backend container is sized at **0.5 vCPU and 1024 MB (1 GB) RAM** to comfortably run FastAPI, psycopg pgvector operations, and pydantic schema parsing.

```
┌────────────────────────────────────────────────────────────────────────┐
│                        AWS COST BREAKDOWN TABLE                        │
├───────────────────────────────┬────────────────────────┬───────────────┤
│ Resource                      │ Configuration          │ Monthly Est.  │
├───────────────────────────────┼────────────────────────┼───────────────┤
│ ECS Fargate Backend           │ 0.5 vCPU / 1.0 GB RAM  │ ~$18.25/month │
│ RDS PostgreSQL 16             │ db.t4g.micro (20GB)    │ ~$12.40/month │
│                               │ (Eligible for 750 hrs  │               │
│                               │ AWS Free Tier: $0.00)  │               │
│ CloudFront CDN + S3 Static    │ 5 GB Transfer Out      │ ~$0.50/month  │
│ CloudWatch Logs               │ 14-day retention       │ ~$0.40/month  │
│ Architecture Cost Savings:    │                        │               │
│ • Public Subnets (No NAT GW)  │ Direct IGW egress      │ -$35.00/month │
│ • S3 Native State Lock        │ No DynamoDB table      │ -$2.00/month  │
├───────────────────────────────┼────────────────────────┼───────────────┤
│ TOTAL ESTIMATED SPEND (Full)  │ Continuous 24/7 run    │ ~$31.55/month │
│ TOTAL WITH AWS RDS FREE TIER  │ 12-month free tier     │ ~$19.15/month │
└───────────────────────────────┴────────────────────────┴───────────────┘
```

### 3.2 Job-Assessment Demo Estimate (3-Day Evaluation Period)
For evaluation review, the entire stack can be launched, demonstrated for 3 days (72 hours), and torn down:

| Demo Component (72 Hours) | Calculation Basis | Estimated 3-Day Cost |
|---|---|---|
| **ECS Fargate (0.5 vCPU / 1 GB)** | 72 hrs × ($0.02024 vCPU + $0.004445 RAM) | **$1.78 USD** |
| **RDS PostgreSQL (db.t4g.micro)** | 72 hrs × $0.016/hr (if non-free tier) | **$1.15 USD** |
| **Application Load Balancer** | 72 hrs × $0.0225/hr + 0.1 LCU | **$1.68 USD** |
| **CloudFront, S3 & CloudWatch** | Demo assets and request logs | **$0.15 USD** |
| **Total 3-Day Job Review Spend** | Complete live environment | **~$4.76 USD** |

*(If tasks are set to `desired_count = 0` between evaluation tests, the 3-day demo cost drops to under **$2.50 USD**).*

### 3.3 AWS Budget Alert Enforcement
Terraform provisions an automated `aws_budgets_budget` with an absolute **$20.00 USD monthly limit**:
- **80% Forecasted Threshold ($16.00):** Sends early warning alert email to operations.
- **100% Actual Threshold ($20.00):** Immediate critical escalation.

---

## 4. Teardown Runbook (`terraform destroy`)

To clean up all cloud resources after evaluation and prevent ongoing charges:

1. **Empty Frontend S3 Bucket:**
   ```bash
   BUCKET_NAME=$(terraform output -raw frontend_s3_bucket)
   aws s3 rm "s3://$BUCKET_NAME" --recursive
   ```

2. **Execute Full Infrastructure Teardown:**
   ```bash
   cd infra
   terraform destroy -auto-approve
   ```

3. **Verify Resource Release:**
   - Confirm ECS tasks and services have terminated.
   - Confirm RDS instance is deleted (skip final snapshot configured for PoC).
   - Confirm CloudFront distribution is disabled/deleted.
