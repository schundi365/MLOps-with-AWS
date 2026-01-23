# Web UI Quick Start Guide

## 📋 What You've Got

You now have complete specifications for building web UIs to expose your SageMaker recommendation endpoint:

1. **Requirements Document** (`.kiro/specs/web-ui-for-recommendations/requirements.md`)
   - 20 detailed requirements covering all aspects
   - User stories and acceptance criteria
   - Two implementation approaches

2. **Design Document** (`.kiro/specs/web-ui-for-recommendations/design.md`)
   - Complete architecture diagrams
   - API specifications
   - Database schemas
   - Implementation code examples
   - Testing strategies
   - Cost analysis
   - Deployment guides

3. **Cost Analysis** (`AWS_COST_ANALYSIS.md`)
   - Detailed breakdown of AWS costs
   - Resources that cost money
   - Cleanup scripts
   - Cost protection strategies

## 🚀 Quick Start: Choose Your Path

### Path 1: AWS-Native (Serverless)
**Best for:** Learning, low traffic, minimal ops

```bash
# 1. Set up frontend
cd webapp/frontend
npm create vite@latest . -- --template react-ts
npm install

# 2. Create Lambda functions
mkdir -p webapp/backend/lambda
# Copy Lambda code from design doc

# 3. Deploy infrastructure
python src/infrastructure/deploy_web_ui_aws_native.py

# 4. Deploy frontend
npm run build
aws s3 sync dist/ s3://your-bucket/
```

**Estimated Cost:** $5-15/month for low traffic

### Path 2: FastAPI + React (Modern Stack)
**Best for:** Production, high traffic, flexibility

```bash
# 1. Set up backend
cd webapp/backend
pip install fastapi uvicorn sqlalchemy psycopg2-binary python-jose

# 2. Set up frontend
cd ../frontend
npm create vite@latest . -- --template react-ts
npm install @tanstack/react-query @mui/material

# 3. Run locally with Docker
docker-compose up

# 4. Deploy to AWS ECS
./deploy_ecs.sh
```

**Estimated Cost:** $57/month for development, $161/month for production

## ⚠️ IMPORTANT: Cost Management

### Before You Start

1. **Check current costs:**
```bash
python check_current_costs.py
```

2. **Set up billing alerts:**
```bash
# Go to AWS Console > Billing > Budgets
# Create a budget for $50-100/month with alerts
```

3. **Understand what costs money:**
   - **SageMaker Endpoint:** $387/month (2 instances, 24/7) - HIGHEST COST
   - **EC2/ECS:** $15-120/month depending on size
   - **RDS Database:** $12-100/month depending on size
   - **Lambda + API Gateway:** $1-20/month for low-medium traffic

### Cost-Saving Tips

1. **Delete SageMaker endpoint when not in use:**
```bash
aws sagemaker delete-endpoint --endpoint-name your-endpoint-name
```

2. **Use development environment for learning:**
   - Single t3.small EC2 instance: $15/month
   - db.t3.micro RDS: $12/month
   - Total: ~$30/month

3. **Stop resources overnight:**
```bash
# Stop EC2 instances
aws ec2 stop-instances --instance-ids i-xxxxx

# Stop RDS database
aws rds stop-db-instance --db-instance-identifier your-db
```

## 📚 Learning Path

### Week 1: AWS-Native Basics
- [ ] Set up Cognito user pool
- [ ] Create simple Lambda function
- [ ] Deploy static website to S3
- [ ] Connect API Gateway to Lambda
- [ ] Test authentication flow

### Week 2: Frontend Development
- [ ] Build React app with Vite
- [ ] Implement login/register forms
- [ ] Create movie search interface
- [ ] Add recommendation display
- [ ] Style with Material-UI

### Week 3: Backend Development
- [ ] Set up FastAPI project
- [ ] Implement JWT authentication
- [ ] Create database models
- [ ] Build API endpoints
- [ ] Add caching with Redis

### Week 4: Deployment & Testing
- [ ] Containerize with Docker
- [ ] Deploy to AWS ECS
- [ ] Set up monitoring
- [ ] Load testing
- [ ] Security hardening

## 🛠️ Essential Commands

### Check AWS Resources
```bash
# List SageMaker endpoints
aws sagemaker list-endpoints

# List EC2 instances
aws ec2 describe-instances --filters "Name=instance-state-name,Values=running"

# List RDS databases
aws rds describe-db-instances

# Check current month costs
python check_current_costs.py
```

### Development
```bash
# Run FastAPI backend locally
cd webapp/backend
uvicorn main:app --reload

# Run React frontend locally
cd webapp/frontend
npm run dev

# Run with Docker Compose
docker-compose up
```

### Testing
```bash
# Backend tests
pytest tests/

# Frontend tests
npm test

# E2E tests
npx playwright test

# Load testing
locust -f tests/performance/locustfile.py
```

## 📖 Documentation Structure

```
.kiro/specs/web-ui-for-recommendations/
├── requirements.md          # What to build
├── design.md               # How to build it
└── tasks.md               # Step-by-step plan (create next)

AWS_COST_ANALYSIS.md        # Cost breakdown & cleanup
WEB_UI_QUICK_START.md       # This file
check_current_costs.py      # Cost checking script
```

## 🎯 Recommended Approach

**For Learning Both Stacks:**
1. Start with AWS-Native to learn serverless (1-2 weeks)
2. Build Modern Stack to learn containers (2-3 weeks)
3. Compare and understand trade-offs
4. Choose based on your needs

**For Production:**
1. Use Hybrid approach:
   - React frontend on S3 + CloudFront
   - FastAPI backend on ECS Fargate
   - Cognito for auth
   - RDS PostgreSQL for database
   - ElastiCache Redis for caching

## 🔗 Next Steps

1. **Review the design document** to understand the architecture
2. **Choose your approach** (AWS-Native or Modern Stack)
3. **Set up billing alerts** to avoid surprise costs
4. **Start with MVP** - authentication and basic recommendations
5. **Iterate and improve** based on usage

## 💡 Pro Tips

1. **Always check costs before deploying:** Run `python check_current_costs.py`
2. **Use development environment first:** Test everything locally with Docker
3. **Start small:** MVP with basic features, then add more
4. **Monitor from day one:** Set up CloudWatch dashboards early
5. **Cache aggressively:** Reduce SageMaker endpoint calls to save money
6. **Delete when not using:** Stop/delete resources when not actively developing

## 🆘 Need Help?

- **Design questions:** Review `.kiro/specs/web-ui-for-recommendations/design.md`
- **Cost concerns:** Check `AWS_COST_ANALYSIS.md`
- **Current costs:** Run `python check_current_costs.py`
- **Requirements:** See `.kiro/specs/web-ui-for-recommendations/requirements.md`

---

**Remember:** The SageMaker endpoint is your biggest cost (~$387/month for 2 instances). Delete it when not in use!

Good luck building your web UI! 🚀
