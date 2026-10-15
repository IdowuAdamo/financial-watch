#!/usr/bin/env bash
# cleanup_orphans.sh
# Safely purges unmanaged/dangling AWS resources from previous failed Terraform applies.
# ONLY runs during initial bootstrap when no S3 remote state exists.

set -e

STATE_BUCKET="$1"

if [ -z "$STATE_BUCKET" ]; then
  echo "Usage: cleanup_orphans.sh <STATE_BUCKET>"
  exit 1
fi

echo "Checking if Terraform remote state exists in s3://${STATE_BUCKET}/financial-watch/prod/terraform.tfstate..."
if aws s3 ls "s3://${STATE_BUCKET}/financial-watch/prod/terraform.tfstate" > /dev/null 2>&1; then
  echo "Terraform state already exists in S3; skipping orphan cleanup."
  exit 0
fi

echo "=========================================================="
echo "NO REMOTE STATE FOUND: Cleaning orphaned resources from prior aborted run..."
echo "=========================================================="

# 1. ECS Service and Cluster
echo "1/12 Cleaning ECS Service & Cluster..."
aws ecs update-service --cluster financial-watch-prod-cluster --service financial-watch-prod-service --desired-count 0 2>/dev/null || true
aws ecs delete-service --cluster financial-watch-prod-cluster --service financial-watch-prod-service --force 2>/dev/null || true
aws ecs delete-cluster --cluster financial-watch-prod-cluster 2>/dev/null || true

# 2. EventBridge Rules
echo "2/12 Cleaning EventBridge rules..."
for RULE in financial-watch-prod-daily-crawl; do
  TARGET_IDS=$(aws events list-targets-by-rule --rule "$RULE" --query "Targets[].Id" --output text 2>/dev/null || true)
  if [ -n "$TARGET_IDS" ] && [ "$TARGET_IDS" != "None" ]; then
    aws events remove-targets --rule "$RULE" --ids $TARGET_IDS 2>/dev/null || true
  fi
  aws events delete-rule --name "$RULE" 2>/dev/null || true
done

# 3. ALB, Listeners, and Target Groups
echo "3/12 Cleaning Application Load Balancer..."
ALB_ARN=$(aws elbv2 describe-load-balancers --names financial-watch-prod-alb --query "LoadBalancers[0].LoadBalancerArn" --output text 2>/dev/null || true)
if [ -n "$ALB_ARN" ] && [ "$ALB_ARN" != "None" ]; then
  for L_ARN in $(aws elbv2 describe-listeners --load-balancer-arn "$ALB_ARN" --query "Listeners[].ListenerArn" --output text 2>/dev/null || true); do
    aws elbv2 delete-listener --listener-arn "$L_ARN" 2>/dev/null || true
  done
  aws elbv2 delete-load-balancer --load-balancer-arn "$ALB_ARN" 2>/dev/null || true
  echo "Waiting for ALB deletion to release network interfaces..."
  aws elbv2 wait load-balancers-deleted --load-balancer-arns "$ALB_ARN" 2>/dev/null || sleep 20
fi

TG_ARN=$(aws elbv2 describe-target-groups --names financial-watch-prod-tg --query "TargetGroups[0].TargetGroupArn" --output text 2>/dev/null || true)
if [ -n "$TG_ARN" ] && [ "$TG_ARN" != "None" ]; then
  aws elbv2 delete-target-group --target-group-arn "$TG_ARN" 2>/dev/null || true
fi

# 4. CloudFront Origin Access Control
echo "4/12 Cleaning CloudFront OAC..."
for OAC_ID in $(aws cloudfront list-origin-access-controls --query "OriginAccessControlList.Items[?Name=='financial-watch-prod-oac'].Id" --output text 2>/dev/null || true); do
  if [ -n "$OAC_ID" ] && [ "$OAC_ID" != "None" ]; then
    ETAG=$(aws cloudfront get-origin-access-control --id "$OAC_ID" --query "ETag" --output text 2>/dev/null || true)
    aws cloudfront delete-origin-access-control --id "$OAC_ID" --if-match "$ETAG" 2>/dev/null || true
  fi
done

# 5. CloudWatch Log Group
echo "5/12 Cleaning CloudWatch Log Groups..."
aws logs delete-log-group --log-group-name /ecs/financial-watch-prod 2>/dev/null || true

# 6. Secrets Manager
echo "6/12 Cleaning Secrets Manager secrets..."
aws secretsmanager delete-secret --secret-id financial-watch-prod-openai-key --force-delete-without-recovery 2>/dev/null || true
aws secretsmanager delete-secret --secret-id financial-watch-prod-database-url --force-delete-without-recovery 2>/dev/null || true
aws secretsmanager delete-secret --secret-id financial-watch-prod-api-access-key --force-delete-without-recovery 2>/dev/null || true

# 7. RDS DB Subnet Group and Parameter Group
echo "7/12 Cleaning RDS Parameter & Subnet Groups..."
aws rds delete-db-subnet-group --db-subnet-group-name financial-watch-prod-db-subnets 2>/dev/null || true
aws rds delete-db-parameter-group --db-parameter-group-name financial-watch-prod-pg16-vector 2>/dev/null || true

# 8. AWS Budget
echo "8/12 Cleaning AWS Budget..."
ACCOUNT_ID=$(aws sts get-caller-identity --query "Account" --output text 2>/dev/null || true)
if [ -n "$ACCOUNT_ID" ] && [ "$ACCOUNT_ID" != "None" ]; then
  aws budgets delete-budget --account-id "$ACCOUNT_ID" --budget-name financial-watch-prod-monthly-budget 2>/dev/null || true
fi

# 9. SNS Topic
echo "9/12 Cleaning SNS Topic..."
SNS_ARN=$(aws sns list-topics --query "Topics[?contains(TopicArn, 'financial-watch-prod-alerts')].TopicArn" --output text 2>/dev/null || true)
if [ -n "$SNS_ARN" ] && [ "$SNS_ARN" != "None" ]; then
  aws sns delete-topic --topic-arn "$SNS_ARN" 2>/dev/null || true
fi

# 10. Frontend S3 Buckets
echo "10/12 Cleaning Frontend S3 Buckets..."
for BUCKET in $(aws s3api list-buckets --query "Buckets[?starts_with(Name, 'financial-watch-prod-frontend')].Name" --output text 2>/dev/null || true); do
  if [ -n "$BUCKET" ] && [ "$BUCKET" != "None" ]; then
    echo "Deleting S3 bucket: $BUCKET"
    aws s3 rm "s3://$BUCKET" --recursive 2>/dev/null || true
    aws s3 rb "s3://$BUCKET" --force 2>/dev/null || true
  fi
done

# 11. IAM Roles & Policies
echo "11/12 Cleaning IAM Roles & Policies..."
for ROLE in financial-watch-prod-ecs-execution-role financial-watch-prod-ecs-task-role financial-watch-prod-eventbridge-ecs-role; do
  for P_ARN in $(aws iam list-attached-role-policies --role-name "$ROLE" --query "AttachedPolicies[].PolicyArn" --output text 2>/dev/null || true); do
    aws iam detach-role-policy --role-name "$ROLE" --policy-arn "$P_ARN" 2>/dev/null || true
  done
  for POL_NAME in $(aws iam list-role-policies --role-name "$ROLE" --query "PolicyNames[]" --output text 2>/dev/null || true); do
    aws iam delete-role-policy --role-name "$ROLE" --policy-name "$POL_NAME" 2>/dev/null || true
  done
  aws iam delete-role --role-name "$ROLE" 2>/dev/null || true
done

for POL_NAME in financial-watch-prod-bedrock-policy financial-watch-prod-secrets-policy financial-watch-prod-eb-run-task-policy; do
  POL_ARN=$(aws iam list-policies --scope Local --query "Policies[?PolicyName=='$POL_NAME'].Arn" --output text 2>/dev/null || true)
  if [ -n "$POL_ARN" ] && [ "$POL_ARN" != "None" ]; then
    aws iam delete-policy --policy-arn "$POL_ARN" 2>/dev/null || true
  fi
done

# 12. Dangling VPCs and Subnets
echo "12/12 Cleaning dangling VPC resources..."
for VPC_ID in $(aws ec2 describe-vpcs --filters "Name=tag:Name,Values=financial-watch-prod-vpc" --query "Vpcs[].VpcId" --output text 2>/dev/null || true); do
  if [ -n "$VPC_ID" ] && [ "$VPC_ID" != "None" ]; then
    echo "Cleaning up VPC: $VPC_ID"

    # Revoke rules from security groups to eliminate circular dependencies
    for SG in $(aws ec2 describe-security-groups --filters "Name=vpc-id,Values=$VPC_ID" --query "SecurityGroups[?GroupName!='default'].GroupId" --output text 2>/dev/null || true); do
      IP_PERMS=$(aws ec2 describe-security-groups --group-ids "$SG" --query "SecurityGroups[0].IpPermissions" --output json 2>/dev/null || true)
      if [ "$IP_PERMS" != "[]" ] && [ -n "$IP_PERMS" ]; then
        aws ec2 revoke-security-group-ingress --group-id "$SG" --ip-permissions "$IP_PERMS" 2>/dev/null || true
      fi
      EG_PERMS=$(aws ec2 describe-security-groups --group-ids "$SG" --query "SecurityGroups[0].IpPermissionsEgress" --output json 2>/dev/null || true)
      if [ "$EG_PERMS" != "[]" ] && [ -n "$EG_PERMS" ]; then
        aws ec2 revoke-security-group-egress --group-id "$SG" --ip-permissions "$EG_PERMS" 2>/dev/null || true
      fi
    done

    # Disassociate and delete non-main route tables
    for RTB in $(aws ec2 describe-route-tables --filters "Name=vpc-id,Values=$VPC_ID" --query "RouteTables[?Associations[0].Main!=true].RouteTableId" --output text 2>/dev/null || true); do
      for ASSOC in $(aws ec2 describe-route-tables --route-table-ids "$RTB" --query "RouteTables[0].Associations[?Main!=true].RouteTableAssociationId" --output text 2>/dev/null || true); do
        aws ec2 disassociate-route-table --association-id "$ASSOC" 2>/dev/null || true
      done
      aws ec2 delete-route-table --route-table-id "$RTB" 2>/dev/null || true
    done

    # Detach and delete internet gateways
    for IGW in $(aws ec2 describe-internet-gateways --filters "Name=attachment.vpc-id,Values=$VPC_ID" --query "InternetGateways[].InternetGatewayId" --output text 2>/dev/null || true); do
      aws ec2 detach-internet-gateway --internet-gateway-id "$IGW" --vpc-id "$VPC_ID" 2>/dev/null || true
      aws ec2 delete-internet-gateway --internet-gateway-id "$IGW" 2>/dev/null || true
    done

    # Delete security groups (retrying to allow network interface teardown)
    for retry in 1 2 3; do
      for SG in $(aws ec2 describe-security-groups --filters "Name=vpc-id,Values=$VPC_ID" --query "SecurityGroups[?GroupName!='default'].GroupId" --output text 2>/dev/null || true); do
        aws ec2 delete-security-group --group-id "$SG" 2>/dev/null || true
      done
      sleep 2
    done

    # Delete subnets
    for SNET in $(aws ec2 describe-subnets --filters "Name=vpc-id,Values=$VPC_ID" --query "Subnets[].SubnetId" --output text 2>/dev/null || true); do
      aws ec2 delete-subnet --subnet-id "$SNET" 2>/dev/null || true
    done

    # Delete VPC
    aws ec2 delete-vpc --vpc-id "$VPC_ID" 2>/dev/null || true
  fi
done

echo "=========================================================="
echo "Orphan cleanup complete. Ready for clean Terraform apply."
echo "=========================================================="
