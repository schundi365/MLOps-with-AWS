# Architecture Documentation

## System Architecture Overview

The AWS MovieLens Recommendation System is a production-ready machine learning pipeline that implements collaborative filtering for personalized movie recommendations. The architecture follows AWS best practices for scalability, reliability, and security.

## High-Level Architecture Diagram

```mermaid
graph TB
    subgraph "External"
        User[User/Application]
        MovieLens[MovieLens Dataset]
    end
    
    subgraph "Data Storage Layer"
        S3[(S3 Bucket)]
        RawData[raw-data/]
        ProcessedData[processed-data/]
        Models[models/]
        Monitoring[monitoring/]
        Metrics[metrics/]
    end
    
    subgraph "ML Pipeline Layer"
        Preprocessing[SageMaker Processing Job]
        Training[SageMaker Training Job]
        Tuning[Hyperparameter Tuning]
        Evaluation[Evaluation Lambda]
    end
    
    subgraph "Inference Layer"
        Endpoint[SageMaker Endpoint]
        AutoScale[Auto Scaling Policy]
        Cache[LRU Cache]
    end
    
    subgraph "Orchestration Layer"
        StepFunctions[Step Functions State Machine]
        EventBridge[EventBridge Rule]
    end
    
    subgraph "Monitoring Layer"
        CloudWatch[CloudWatch Metrics]
        Dashboard[CloudWatch Dashboard]
        Alarms[CloudWatch Alarms]
        ModelMonitor[SageMaker Model Monitor]
        SNS[SNS Topic]
    end
    
    subgraph "Security Layer"
        IAM[IAM Roles & Policies]
        KMS[KMS Encryption]
        VPC[VPC Configuration]
    end
    
    %% Data Flow
    MovieLens -->|Download| User
    User -->|Upload| RawData
    RawData --> S3
    S3 --> Preprocessing
    Preprocessing --> ProcessedData
    ProcessedData --> S3
    S3 --> Training
    Training --> Tuning
    Tuning --> Models
    Models --> S3
    S3 --> Evaluation
    Evaluation --> Metrics
    Metrics --> S3
    S3 --> Endpoint
    
    %% Inference Flow
    User -->|Invoke| Endpoint
    Endpoint --> Cache
    Cache --> Endpoint
    Endpoint -->|Response| User
    Endpoint --> AutoScale
    
    %% Orchestration Flow
    EventBridge -->|Weekly Trigger| StepFunctions
    StepFunctions --> Preprocessing
    StepFunctions --> Training
    StepFunctions --> Evaluation
    StepFunctions --> Endpoint
    
    %% Monitoring Flow
    Endpoint --> CloudWatch
    Endpoint --> ModelMonitor
    CloudWatch --> Dashboard
    CloudWatch --> Alarms
    Alarms --> SNS
    SNS -->|Alert| User
    ModelMonitor --> Monitoring
    Monitoring --> S3
    
    %% Security
    IAM -.->|Authorize| Preprocessing
    IAM -.->|Authorize| Training
    IAM -.->|Authorize| Endpoint
    IAM -.->|Authorize| Evaluation
    KMS -.->|Encrypt| S3
    VPC -.->|Network| Endpoint
    
    style S3 fill:#FF9900
    style Endpoint fill:#FF9900
    style StepFunctions fill:#FF9900
    style CloudWatch fill:#FF9900
    style IAM fill:#FF9900
```

## Detailed Component Architecture

### 1. Data Storage Architecture

```mermaid
graph LR
    subgraph "S3 Bucket Structure"
        Root[movielens-recommendation-bucket/]
        Root --> RawData[raw-data/]
        Root --> ProcessedData[processed-data/]
        Root --> Models[models/]
        Root --> Outputs[outputs/]
        Root --> Monitoring[monitoring/]
        Root --> Metrics[metrics/]
        
        RawData --> Movies[movies.csv]
        RawData --> Ratings[ratings.csv]
        RawData --> Tags[tags.csv]
        RawData --> Links[links.csv]
        
        ProcessedData --> Train[train.csv]
        ProcessedData --> Val[validation.csv]
        ProcessedData --> Test[test.csv]
        
        Models --> ModelArtifacts[model.tar.gz]
        Models --> Metadata[metadata.json]
        
        Monitoring --> DataCapture[data-capture/]
        Monitoring --> Baseline[baseline/]
        Monitoring --> Reports[reports/]
        
        Metrics --> EvalResults[evaluation_results.json]
    end
    
    style Root fill:#FF9900
```

**Features**:
- **Versioning**: Enabled for data lineage tracking
- **Encryption**: SSE-S3 or SSE-KMS at rest
- **Lifecycle Policies**: Archive to Glacier after 90 days
- **Access Control**: Bucket policies with least-privilege access

### 2. ML Pipeline Architecture

```mermaid
sequenceDiagram
    participant EB as EventBridge
    participant SF as Step Functions
    participant PP as Preprocessing Job
    participant TR as Training Job
    participant EV as Evaluation Lambda
    participant EP as Endpoint
    participant MM as Model Monitor
    participant S3 as S3 Storage
    
    EB->>SF: Trigger (Weekly/Manual)
    SF->>PP: Start Processing Job
    PP->>S3: Read raw data
    PP->>S3: Write processed data
    PP-->>SF: Success
    
    SF->>TR: Start Training Job
    TR->>S3: Read processed data
    TR->>TR: Train model
    TR->>S3: Save model artifacts
    TR-->>SF: Success
    
    SF->>EV: Invoke Evaluation
    EV->>S3: Read test data
    EV->>EP: Create temp endpoint
    EV->>EP: Get predictions
    EV->>EV: Calculate RMSE/MAE
    EV->>S3: Save metrics
    EV-->>SF: Return metrics
    
    alt RMSE < 0.9
        SF->>EP: Deploy/Update Endpoint
        EP->>S3: Load model
        EP-->>SF: Success
        SF->>MM: Enable Monitoring
        MM-->>SF: Success
    else RMSE >= 0.9
        SF->>SF: Fail Pipeline
    end
```

**Pipeline Steps**:
1. **Data Preprocessing**: Transform raw CSV to train/val/test splits
2. **Model Training**: Train collaborative filtering model with PyTorch
3. **Model Evaluation**: Calculate RMSE and MAE on test set
4. **Deployment Decision**: Deploy if RMSE < 0.9 threshold
5. **Monitoring Setup**: Enable data capture and quality monitoring

### 3. Inference Architecture

```mermaid
graph TB
    subgraph "Client Layer"
        App[Application]
        CLI[AWS CLI]
        SDK[Boto3 SDK]
    end
    
    subgraph "API Gateway Layer"
        ALB[Application Load Balancer]
    end
    
    subgraph "Endpoint Layer"
        EP1[Endpoint Instance 1]
        EP2[Endpoint Instance 2]
        EP3[Endpoint Instance 3]
        EP4[Endpoint Instance 4]
        EP5[Endpoint Instance 5]
    end
    
    subgraph "Auto Scaling"
        ASG[Auto Scaling Group]
        Policy[Target Tracking Policy]
    end
    
    subgraph "Model Layer"
        Model[Collaborative Filtering Model]
        Cache[LRU Cache]
    end
    
    subgraph "Monitoring"
        CW[CloudWatch Metrics]
        MM[Model Monitor]
    end
    
    App --> ALB
    CLI --> ALB
    SDK --> ALB
    
    ALB --> EP1
    ALB --> EP2
    ALB --> EP3
    ALB --> EP4
    ALB --> EP5
    
    EP1 --> Model
    EP2 --> Model
    EP3 --> Model
    EP4 --> Model
    EP5 --> Model
    
    Model --> Cache
    
    ASG -.->|Manage| EP1
    ASG -.->|Manage| EP2
    ASG -.->|Manage| EP3
    ASG -.->|Manage| EP4
    ASG -.->|Manage| EP5
    
    Policy -.->|Control| ASG
    
    EP1 --> CW
    EP2 --> CW
    EP3 --> CW
    EP4 --> CW
    EP5 --> CW
    
    EP1 --> MM
    EP2 --> MM
    EP3 --> MM
    EP4 --> MM
    EP5 --> MM
    
    style ALB fill:#FF9900
    style ASG fill:#FF9900
    style CW fill:#FF9900
```

**Scaling Behavior**:
- **Min Instances**: 1
- **Max Instances**: 5
- **Scale Out**: When invocations/instance > 70
- **Scale In**: When invocations/instance < 70
- **Cooldown**: 60s scale-out, 300s scale-in

### 4. Monitoring Architecture

```mermaid
graph TB
    subgraph "Data Sources"
        EP[SageMaker Endpoint]
        TR[Training Jobs]
        PP[Processing Jobs]
        LM[Lambda Functions]
    end
    
    subgraph "CloudWatch"
        Metrics[Metrics]
        Logs[Log Groups]
        Dashboard[Dashboard]
        Alarms[Alarms]
    end
    
    subgraph "Model Monitor"
        DataCapture[Data Capture]
        Baseline[Baseline]
        Schedule[Monitoring Schedule]
        Reports[Violation Reports]
    end
    
    subgraph "Alerting"
        SNS[SNS Topic]
        Email[Email Notification]
        SMS[SMS Notification]
    end
    
    EP --> Metrics
    EP --> Logs
    EP --> DataCapture
    TR --> Metrics
    TR --> Logs
    PP --> Logs
    LM --> Logs
    
    Metrics --> Dashboard
    Metrics --> Alarms
    
    DataCapture --> Baseline
    Baseline --> Schedule
    Schedule --> Reports
    
    Alarms --> SNS
    Reports --> SNS
    SNS --> Email
    SNS --> SMS
    
    style Dashboard fill:#FF9900
    style Alarms fill:#FF9900
    style SNS fill:#FF9900
```

**Monitored Metrics**:
- Invocations per minute
- Model latency (P50, P90, P99)
- Error rates (4xx, 5xx)
- Instance CPU/memory utilization
- Model accuracy drift
- Data distribution drift

**Alarms**:
- High error rate (> 5%)
- High latency (> 1000ms P99)

## Data Flow Diagrams

### Training Data Flow

```mermaid
flowchart LR
    A[MovieLens Dataset] -->|Download| B[Local Storage]
    B -->|Upload| C[S3 raw-data/]
    C -->|Read| D[Preprocessing Job]
    D -->|Transform| E[Train/Val/Test Splits]
    E -->|Write| F[S3 processed-data/]
    F -->|Read| G[Training Job]
    G -->|Train| H[Model Artifacts]
    H -->|Save| I[S3 models/]
    
    style C fill:#FF9900
    style F fill:#FF9900
    style I fill:#FF9900
```

### Inference Data Flow

```mermaid
flowchart LR
    A[Client Request] -->|JSON| B[SageMaker Endpoint]
    B -->|Check| C{Cache Hit?}
    C -->|Yes| D[Return Cached]
    C -->|No| E[Load Model]
    E -->|Predict| F[Generate Predictions]
    F -->|Store| G[Update Cache]
    F -->|Return| H[JSON Response]
    G -->|Return| H
    D -->|Return| H
    H -->|Response| A
    
    B -->|Capture| I[Data Capture]
    I -->|Store| J[S3 monitoring/]
    
    style B fill:#FF9900
    style J fill:#FF9900
```

### Monitoring Data Flow

```mermaid
flowchart TB
    A[Endpoint Invocations] -->|Emit| B[CloudWatch Metrics]
    A -->|Capture| C[Request/Response Data]
    
    B -->|Aggregate| D[Dashboard]
    B -->|Evaluate| E{Threshold Exceeded?}
    
    C -->|Store| F[S3 data-capture/]
    F -->|Analyze| G[Model Monitor]
    G -->|Compare| H[Baseline]
    H -->|Detect| I{Drift Found?}
    
    E -->|Yes| J[Trigger Alarm]
    I -->|Yes| K[Generate Report]
    
    J -->|Notify| L[SNS Topic]
    K -->|Notify| L
    L -->|Send| M[Operations Team]
    
    style B fill:#FF9900
    style F fill:#FF9900
    style L fill:#FF9900
```

## Security Architecture

### IAM Roles and Policies

```mermaid
graph TB
    subgraph "IAM Roles"
        SM[SageMaker Execution Role]
        LM[Lambda Execution Role]
        SF[Step Functions Role]
        EB[EventBridge Role]
    end
    
    subgraph "AWS Services"
        S3[S3 Bucket]
        SMP[SageMaker Processing]
        SMT[SageMaker Training]
        SME[SageMaker Endpoint]
        LF[Lambda Functions]
        SFM[Step Functions]
        EBR[EventBridge Rule]
        CW[CloudWatch]
    end
    
    SM -->|Read/Write| S3
    SM -->|Logs| CW
    LM -->|Read/Write| S3
    LM -->|Invoke| SME
    LM -->|Logs| CW
    SF -->|Start| SMP
    SF -->|Start| SMT
    SF -->|Invoke| LF
    SF -->|Update| SME
    EB -->|Start| SFM
    
    SMP -.->|Assume| SM
    SMT -.->|Assume| SM
    SME -.->|Assume| SM
    LF -.->|Assume| LM
    SFM -.->|Assume| SF
    EBR -.->|Assume| EB
    
    style SM fill:#DD344C
    style LM fill:#DD344C
    style SF fill:#DD344C
    style EB fill:#DD344C
```

**Security Features**:
- **Least Privilege**: Each role has minimal required permissions
- **Encryption at Rest**: S3 (SSE-S3/KMS), SageMaker volumes (KMS)
- **Encryption in Transit**: TLS 1.2+ for all data transfers
- **VPC Deployment**: Endpoints deployed in private subnets
- **Audit Logging**: CloudTrail enabled for all API calls
- **Bucket Policies**: Restrict S3 access to authorized services only

### Network Architecture

```mermaid
graph TB
    subgraph "Public Subnet"
        NAT[NAT Gateway]
        ALB[Application Load Balancer]
    end
    
    subgraph "Private Subnet A"
        EP1[Endpoint Instance 1]
        EP2[Endpoint Instance 2]
    end
    
    subgraph "Private Subnet B"
        EP3[Endpoint Instance 3]
        EP4[Endpoint Instance 4]
    end
    
    subgraph "VPC Endpoints"
        S3E[S3 VPC Endpoint]
        CWE[CloudWatch VPC Endpoint]
    end
    
    Internet[Internet] --> ALB
    ALB --> EP1
    ALB --> EP2
    ALB --> EP3
    ALB --> EP4
    
    EP1 --> S3E
    EP2 --> S3E
    EP3 --> S3E
    EP4 --> S3E
    
    EP1 --> CWE
    EP2 --> CWE
    EP3 --> CWE
    EP4 --> CWE
    
    EP1 --> NAT
    EP2 --> NAT
    EP3 --> NAT
    EP4 --> NAT
    
    NAT --> Internet
    
    style ALB fill:#FF9900
    style S3E fill:#FF9900
    style CWE fill:#FF9900
```

## Deployment Architecture

### Infrastructure as Code

```mermaid
graph TB
    subgraph "Deployment Scripts"
        Deploy[deploy_all.py]
        S3Setup[s3_setup.py]
        IAMSetup[iam_setup.py]
        SMDeploy[sagemaker_deployment.py]
        LMDeploy[lambda_deployment.py]
        SFDeploy[stepfunctions_deployment.py]
        EBDeploy[eventbridge_deployment.py]
    end
    
    subgraph "AWS Resources"
        S3Bucket[S3 Bucket]
        IAMRoles[IAM Roles]
        Lambda[Lambda Functions]
        StepFunc[Step Functions]
        EventB[EventBridge]
        Endpoint[SageMaker Endpoint]
    end
    
    Deploy --> S3Setup
    Deploy --> IAMSetup
    Deploy --> SMDeploy
    Deploy --> LMDeploy
    Deploy --> SFDeploy
    Deploy --> EBDeploy
    
    S3Setup --> S3Bucket
    IAMSetup --> IAMRoles
    SMDeploy --> Endpoint
    LMDeploy --> Lambda
    SFDeploy --> StepFunc
    EBDeploy --> EventB
    
    style Deploy fill:#232F3E
```

**Deployment Order**:
1. S3 bucket creation
2. IAM roles and policies
3. Lambda functions
4. Step Functions state machine
5. EventBridge scheduled rule
6. SageMaker endpoint (after training)

## Performance Characteristics

### Latency Targets

| Component | Target | Typical |
|-----------|--------|---------|
| Endpoint P50 | < 200ms | 150ms |
| Endpoint P90 | < 400ms | 300ms |
| Endpoint P99 | < 500ms | 450ms |
| Preprocessing | < 30 min | 15 min |
| Training (100K) | < 30 min | 20 min |
| Training (25M) | < 2 hours | 90 min |

### Throughput Targets

| Metric | Target | Notes |
|--------|--------|-------|
| Requests/second | 100+ | With 5 instances |
| Concurrent requests | 500+ | With auto-scaling |
| Training throughput | 10K samples/sec | With GPU |

### Scalability

- **Horizontal Scaling**: 1-5 endpoint instances
- **Vertical Scaling**: Instance type upgrades (m5.xlarge → m5.2xlarge)
- **Data Scaling**: Supports datasets up to 100M ratings
- **User Scaling**: Supports millions of users and movies

## Cost Architecture

### Cost Breakdown (Monthly Estimates)

| Component | Development | Production |
|-----------|-------------|------------|
| S3 Storage | $5 | $20 |
| SageMaker Training | $10 | $50 |
| SageMaker Endpoint | $30 | $200 |
| Lambda | $1 | $5 |
| CloudWatch | $5 | $20 |
| Data Transfer | $5 | $30 |
| **Total** | **$56** | **$325** |

### Cost Optimization Strategies

1. **Use Spot Instances**: 70% savings on training
2. **Reserved Instances**: 40% savings on endpoints
3. **S3 Intelligent Tiering**: Automatic cost optimization
4. **Auto-scaling**: Scale to zero during low traffic
5. **Lifecycle Policies**: Archive old data to Glacier

## Disaster Recovery

### Backup Strategy

- **S3 Versioning**: Enabled for all buckets
- **Cross-Region Replication**: Optional for critical data
- **Model Artifacts**: Versioned and retained for 90 days
- **CloudWatch Logs**: Retained for 30 days

### Recovery Procedures

1. **Endpoint Failure**: Auto-scaling launches new instances
2. **Training Failure**: Retry with exponential backoff
3. **Data Corruption**: Restore from S3 versions
4. **Region Failure**: Failover to secondary region (if configured)

### RTO/RPO Targets

- **Recovery Time Objective (RTO)**: < 1 hour
- **Recovery Point Objective (RPO)**: < 24 hours

## Future Enhancements

### Planned Improvements

1. **Multi-Region Deployment**: Active-active across regions
2. **A/B Testing**: Compare model versions in production
3. **Real-Time Features**: Incorporate real-time user behavior
4. **Advanced Models**: Deep learning architectures (NCF, AutoRec)
5. **Explainability**: Add model interpretation features
6. **API Gateway**: Add REST API layer for easier integration

### Scalability Roadmap

- **Phase 1**: Support 1M users, 100K movies (current)
- **Phase 2**: Support 10M users, 1M movies
- **Phase 3**: Support 100M users, 10M movies
- **Phase 4**: Real-time streaming recommendations

## References

- [AWS SageMaker Best Practices](https://docs.aws.amazon.com/sagemaker/latest/dg/best-practices.html)
- [AWS Well-Architected Framework](https://aws.amazon.com/architecture/well-architected/)
- [MovieLens Dataset Documentation](https://grouplens.org/datasets/movielens/)
- [Collaborative Filtering Research](https://dl.acm.org/doi/10.1145/371920.372071)
