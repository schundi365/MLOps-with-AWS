"""
FastAPI Backend for MovieLens Recommendation System

This API provides endpoints to interact with the SageMaker model endpoint
for movie rating predictions.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator
from typing import List, Optional
import boto3
import json
import os
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="MovieLens Recommendation API",
    description="API for movie rating predictions using collaborative filtering",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
ENDPOINT_NAME = os.getenv("SAGEMAKER_ENDPOINT_NAME", "movielens-endpoint-20260123-122948")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

# Initialize SageMaker runtime client
try:
    sagemaker_runtime = boto3.client('sagemaker-runtime', region_name=AWS_REGION)
    logger.info(f"Initialized SageMaker runtime client for region {AWS_REGION}")
except Exception as e:
    logger.error(f"Failed to initialize SageMaker client: {e}")
    sagemaker_runtime = None


# Pydantic models for request/response validation
class PredictionRequest(BaseModel):
    """Request model for single prediction"""
    user_id: int = Field(..., ge=1, description="User ID (must be positive)")
    movie_id: int = Field(..., ge=1, description="Movie ID (must be positive)")
    
    class Config:
        schema_extra = {
            "example": {
                "user_id": 1,
                "movie_id": 50
            }
        }


class BatchPredictionRequest(BaseModel):
    """Request model for batch predictions"""
    user_ids: List[int] = Field(..., min_items=1, max_items=100, description="List of user IDs")
    movie_ids: List[int] = Field(..., min_items=1, max_items=100, description="List of movie IDs")
    
    @validator('user_ids', 'movie_ids')
    def validate_positive(cls, v):
        if any(x < 1 for x in v):
            raise ValueError('All IDs must be positive integers')
        return v
    
    @validator('movie_ids')
    def validate_same_length(cls, v, values):
        if 'user_ids' in values and len(v) != len(values['user_ids']):
            raise ValueError('user_ids and movie_ids must have the same length')
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "user_ids": [1, 1, 10],
                "movie_ids": [1, 50, 100]
            }
        }


class PredictionResponse(BaseModel):
    """Response model for single prediction"""
    user_id: int
    movie_id: int
    predicted_rating: float
    timestamp: str


class BatchPredictionResponse(BaseModel):
    """Response model for batch predictions"""
    predictions: List[dict]
    count: int
    timestamp: str


class HealthResponse(BaseModel):
    """Response model for health check"""
    status: str
    endpoint_name: str
    region: str
    timestamp: str


class ErrorResponse(BaseModel):
    """Response model for errors"""
    error: str
    detail: Optional[str] = None
    timestamp: str


# API Endpoints

@app.get("/", response_model=dict)
async def root():
    """Root endpoint with API information"""
    return {
        "name": "MovieLens Recommendation API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "predict": "/predict",
            "batch_predict": "/batch-predict",
            "docs": "/docs"
        }
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint
    
    Returns the status of the API and SageMaker endpoint connection.
    """
    try:
        # Check if SageMaker client is initialized
        if sagemaker_runtime is None:
            raise HTTPException(
                status_code=503,
                detail="SageMaker client not initialized"
            )
        
        # Try to describe the endpoint
        sagemaker = boto3.client('sagemaker', region_name=AWS_REGION)
        endpoint_info = sagemaker.describe_endpoint(EndpointName=ENDPOINT_NAME)
        endpoint_status = endpoint_info['EndpointStatus']
        
        if endpoint_status != 'InService':
            logger.warning(f"Endpoint status: {endpoint_status}")
        
        return HealthResponse(
            status="healthy" if endpoint_status == "InService" else "degraded",
            endpoint_name=ENDPOINT_NAME,
            region=AWS_REGION,
            timestamp=datetime.utcnow().isoformat()
        )
    
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"Service unavailable: {str(e)}"
        )


@app.post("/predict", response_model=PredictionResponse)
async def predict(request: PredictionRequest):
    """
    Get movie rating prediction for a single user-movie pair
    
    - **user_id**: ID of the user (positive integer)
    - **movie_id**: ID of the movie (positive integer)
    
    Returns predicted rating on a scale of 0-5.
    """
    try:
        # Prepare input for SageMaker (expects lists)
        input_data = {
            "user_ids": [request.user_id],
            "movie_ids": [request.movie_id]
        }
        
        logger.info(f"Predicting for user {request.user_id}, movie {request.movie_id}")
        
        # Invoke SageMaker endpoint
        response = sagemaker_runtime.invoke_endpoint(
            EndpointName=ENDPOINT_NAME,
            ContentType='application/json',
            Body=json.dumps(input_data)
        )
        
        # Parse response
        result = json.loads(response['Body'].read().decode())
        predicted_rating = result['predictions'][0]
        
        logger.info(f"Prediction: {predicted_rating:.3f}")
        
        return PredictionResponse(
            user_id=request.user_id,
            movie_id=request.movie_id,
            predicted_rating=round(predicted_rating, 3),
            timestamp=datetime.utcnow().isoformat()
        )
    
    except Exception as e:
        logger.error(f"Prediction failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Prediction failed: {str(e)}"
        )


@app.post("/batch-predict", response_model=BatchPredictionResponse)
async def batch_predict(request: BatchPredictionRequest):
    """
    Get movie rating predictions for multiple user-movie pairs
    
    - **user_ids**: List of user IDs (1-100 items)
    - **movie_ids**: List of movie IDs (1-100 items, same length as user_ids)
    
    Returns predicted ratings for all pairs.
    """
    try:
        # Prepare input for SageMaker
        input_data = {
            "user_ids": request.user_ids,
            "movie_ids": request.movie_ids
        }
        
        logger.info(f"Batch predicting for {len(request.user_ids)} pairs")
        
        # Invoke SageMaker endpoint
        response = sagemaker_runtime.invoke_endpoint(
            EndpointName=ENDPOINT_NAME,
            ContentType='application/json',
            Body=json.dumps(input_data)
        )
        
        # Parse response
        result = json.loads(response['Body'].read().decode())
        predictions = result['predictions']
        
        # Format predictions
        formatted_predictions = [
            {
                "user_id": request.user_ids[i],
                "movie_id": request.movie_ids[i],
                "predicted_rating": round(predictions[i], 3)
            }
            for i in range(len(predictions))
        ]
        
        logger.info(f"Batch prediction completed: {len(predictions)} results")
        
        return BatchPredictionResponse(
            predictions=formatted_predictions,
            count=len(predictions),
            timestamp=datetime.utcnow().isoformat()
        )
    
    except Exception as e:
        logger.error(f"Batch prediction failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Batch prediction failed: {str(e)}"
        )


@app.get("/endpoint-info")
async def endpoint_info():
    """
    Get information about the SageMaker endpoint
    
    Returns endpoint configuration and status.
    """
    try:
        sagemaker = boto3.client('sagemaker', region_name=AWS_REGION)
        endpoint_info = sagemaker.describe_endpoint(EndpointName=ENDPOINT_NAME)
        
        return {
            "endpoint_name": endpoint_info['EndpointName'],
            "endpoint_arn": endpoint_info['EndpointArn'],
            "status": endpoint_info['EndpointStatus'],
            "creation_time": endpoint_info['CreationTime'].isoformat(),
            "last_modified_time": endpoint_info['LastModifiedTime'].isoformat(),
            "instance_type": endpoint_info['ProductionVariants'][0]['InstanceType'],
            "current_instance_count": endpoint_info['ProductionVariants'][0]['CurrentInstanceCount'],
            "desired_instance_count": endpoint_info['ProductionVariants'][0]['DesiredInstanceCount']
        }
    
    except Exception as e:
        logger.error(f"Failed to get endpoint info: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get endpoint info: {str(e)}"
        )


# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Custom HTTP exception handler"""
    return {
        "error": exc.detail,
        "status_code": exc.status_code,
        "timestamp": datetime.utcnow().isoformat()
    }


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """General exception handler"""
    logger.error(f"Unhandled exception: {exc}")
    return {
        "error": "Internal server error",
        "detail": str(exc),
        "timestamp": datetime.utcnow().isoformat()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
