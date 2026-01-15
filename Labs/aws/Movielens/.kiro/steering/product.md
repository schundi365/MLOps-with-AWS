# Product Overview

## MovieLens Recommendation System on AWS

A scalable, production-ready movie recommendation system built on AWS infrastructure using collaborative filtering with the MovieLens dataset.

## Core Functionality

- **Collaborative Filtering**: Matrix factorization-based neural network predicting user ratings for movies
- **End-to-End ML Pipeline**: Automated workflow from data ingestion through model deployment
- **Real-Time Inference**: SageMaker endpoints serving predictions with auto-scaling
- **Continuous Monitoring**: CloudWatch metrics, data drift detection, and alerting
- **Automated Retraining**: Weekly scheduled pipeline execution to keep models current

## Key Components

- **Data Pipeline**: S3-based storage with preprocessing for train/val/test splits
- **Training Service**: SageMaker training jobs with hyperparameter tuning
- **Inference Endpoints**: Auto-scaling SageMaker endpoints with <500ms P99 latency
- **Orchestration**: Step Functions state machine coordinating the ML workflow
- **Monitoring**: CloudWatch dashboards, Model Monitor for drift detection, SNS alerts

## Success Criteria

- Validation RMSE < 0.9
- P99 inference latency < 500ms
- Auto-scaling between 1-5 instances based on traffic
- Automated weekly retraining on Sundays at 2 AM UTC
