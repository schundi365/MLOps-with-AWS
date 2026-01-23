# Design Document: Web UI for Movie Recommendations

## Overview

This design document describes two architectural approaches for building user-facing web interfaces that expose the MovieLens recommendation SageMaker endpoints to end users. Both approaches provide secure, scalable access to the ML recommendation engine with authentication, rate limiting, and monitoring.

### Approach 1: AWS-Native Stack
- **Frontend**: Static website (HTML/CSS/JavaScript) hosted on S3 + CloudFront
- **API Layer**: Amazon API Gateway with REST endpoints
- **Backend**: AWS Lambda functions (Python)
- **Authentication**: Amazon Cognito
- **Database**: Amazon DynamoDB
- **Benefits**: Fully serverless, auto-scaling, pay-per-use pricing, minimal operational overhead

### Approach 2: Modern Stack
- **Frontend**: React + TypeScript SPA
- **API Layer**: FastAPI (Python) with async support
- **Backend**: FastAPI application
- **Authentication**: JWT tokens with python-jose
- **Database**: PostgreSQL or MySQL
- **Deployment**: Docker containers on ECS/EKS/EC2
- **Benefits**: Modern development experience, better local development, more control, familiar stack

Both approaches integrate with the existing SageMaker endpoint for movie recommendations.

## Architecture Diagrams

### Approach 1: AWS-Native Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         User's Browser                          │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTPS
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    CloudFront (CDN)                             │
│                  SSL/TLS Termination                            │
└────────────┬────────────────────────────────────┬───────────────┘
             │                                    │
             │ Static Assets                      │ API Requests
             ▼                                    ▼
┌────────────────────────┐         ┌─────────────────────────────┐
│   S3 Static Website    │         │    API Gateway (REST)       │
│  - HTML/CSS/JS         │         │  - /auth/*                  │
│  - Images/Fonts        │         │  - /movies/*                │
└────────────────────────┘         │  - /recommendations         │
                                   │  - /ratings                 │
                                   │  - /profile                 │
                                   └──────────┬──────────────────┘
                                              │
                                              ▼
                                   ┌──────────────────────────────┐
                                   │   Cognito Authorizer         │
                                   │  (JWT Validation)            │
                                   └──────────┬───────────────────┘
                                              │
                                              ▼
┌──────────────────────────────────────────────────────────────────┐
│                      Lambda Functions                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ Auth Handler │  │Movie Search  │  │Recommendations│          │
│  │              │  │   Handler    │  │   Handler     │          │
│  └──────────────┘  └──────────────┘  └──────┬───────┘          │
│  ┌──────────────┐  ┌──────────────┐         │                  │
│  │Rating Handler│  │Profile Handler│         │                  │
│  └──────────────┘  └──────────────┘         │                  │
└────────┬─────────────────────┬───────────────┼──────────────────┘
         │                     │               │
         ▼                     ▼               ▼
┌─────────────────┐   ┌──────────────┐  ┌────────────────────┐
│  DynamoDB       │   │  ElastiCache │  │ SageMaker Endpoint │
│  - users        │   │  (Redis)     │  │  (ML Model)        │
│  - ratings      │   │  - Cache     │  └────────────────────┘
│  - cache        │   │  - Sessions  │
└─────────────────┘   └──────────────┘
         │
         ▼
┌─────────────────┐
│  CloudWatch     │
│  - Logs         │
│  - Metrics      │
│  - Alarms       │
└─────────────────┘
```


### Approach 2: Modern Stack Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         User's Browser                          │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTPS
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│              Application Load Balancer (ALB)                    │
│                    SSL/TLS Termination                          │
└────────────┬────────────────────────────────────┬───────────────┘
             │                                    │
             │ Static Assets (/)                  │ API Requests (/api/*)
             ▼                                    ▼
┌────────────────────────┐         ┌─────────────────────────────┐
│   React Frontend       │         │    FastAPI Backend          │
│   (Nginx Container)    │         │    (Uvicorn Container)      │
│  - React 18 + TS       │         │  - POST /api/v1/auth/*      │
│  - React Router        │         │  - GET /api/v1/movies/*     │
│  - React Query         │         │  - GET /api/v1/recommendations│
│  - Material-UI         │         │  - POST /api/v1/ratings     │
└────────────────────────┘         │  - GET /api/v1/profile      │
                                   └──────────┬──────────────────┘
                                              │
                                              ▼
                                   ┌──────────────────────────────┐
                                   │   JWT Middleware             │
                                   │  (Token Validation)          │
                                   └──────────┬───────────────────┘
                                              │
                                              ▼
┌──────────────────────────────────────────────────────────────────┐
│                    FastAPI Route Handlers                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ Auth Routes  │  │Movie Routes  │  │Recommendation│          │
│  │              │  │              │  │   Routes     │          │
│  └──────────────┘  └──────────────┘  └──────┬───────┘          │
│  ┌──────────────┐  ┌──────────────┐         │                  │
│  │Rating Routes │  │Profile Routes│         │                  │
│  └──────────────┘  └──────────────┘         │                  │
└────────┬─────────────────────┬───────────────┼──────────────────┘
         │                     │               │
         ▼                     ▼               ▼
┌─────────────────┐   ┌──────────────┐  ┌────────────────────┐
│  PostgreSQL     │   │  Redis       │  │ SageMaker Endpoint │
│  - users        │   │  - Cache     │  │  (ML Model)        │
│  - ratings      │   │  - Sessions  │  └────────────────────┘
│  - metadata     │   │  - Rate Limit│
└─────────────────┘   └──────────────┘
         │
         ▼
┌─────────────────┐
│  CloudWatch     │
│  - Logs         │
│  - Metrics      │
│  - Alarms       │
└─────────────────┘
```

## Data Flow

### User Registration Flow
1. User submits registration form (email, password)
2. Frontend validates input and sends POST to `/auth/register`
3. Backend validates email format and password strength
4. Backend hashes password (bcrypt/Argon2)
5. Backend creates user record in database
6. Backend sends verification email
7. User clicks verification link
8. Backend marks account as verified
9. User can now log in

### Authentication Flow
1. User submits login form (email, password)
2. Frontend sends POST to `/auth/login`
3. Backend validates credentials against database
4. Backend generates JWT token with user claims
5. Backend returns access token and refresh token
6. Frontend stores tokens (localStorage or httpOnly cookie)
7. Frontend includes token in Authorization header for subsequent requests
8. Backend validates token on each protected endpoint

### Recommendation Request Flow
1. User clicks "Get Recommendations" button
2. Frontend checks cache for recent recommendations
3. If cache miss, frontend sends GET to `/recommendations`
4. Backend validates JWT token
5. Backend checks rate limit for user
6. Backend invokes SageMaker endpoint with user_id
7. SageMaker returns predicted ratings for top movies
8. Backend formats response and caches for 5 minutes
9. Frontend displays recommendations with ratings
10. User can click movies for more details


## Component Designs

### 1. API Gateway Component (AWS-Native)

**Purpose**: Manage REST API endpoints and route requests to Lambda functions

**Configuration**:
```yaml
API Name: MovieLensRecommendationAPI
Protocol: REST
Stage: prod
Endpoint Type: Regional
```

**Endpoints**:
```
POST   /auth/register          - User registration
POST   /auth/login             - User login
POST   /auth/refresh           - Token refresh
POST   /auth/logout            - User logout
GET    /movies/search          - Search movies
GET    /movies/{id}            - Get movie details
GET    /recommendations        - Get personalized recommendations
POST   /ratings                - Submit movie rating
PUT    /ratings/{id}           - Update rating
GET    /profile                - Get user profile
GET    /profile/ratings        - Get user's rating history
DELETE /profile                - Delete user account
```

**CORS Configuration**:
```json
{
  "allowOrigins": ["https://yourdomain.com"],
  "allowMethods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
  "allowHeaders": ["Content-Type", "Authorization", "X-Api-Key"],
  "exposeHeaders": ["X-RateLimit-Limit", "X-RateLimit-Remaining"],
  "maxAge": 3600
}
```

**Request Validation**:
```json
{
  "POST /auth/register": {
    "body": {
      "type": "object",
      "required": ["email", "password"],
      "properties": {
        "email": {"type": "string", "format": "email"},
        "password": {"type": "string", "minLength": 8}
      }
    }
  }
}
```

**Usage Plan**:
```yaml
Name: StandardUserPlan
Throttle:
  rateLimit: 100    # requests per second
  burstLimit: 200   # burst capacity
Quota:
  limit: 10000      # requests per day
  period: DAY
```

**Integration**:
- Lambda Proxy Integration for all endpoints
- Cognito Authorizer for protected endpoints
- CloudWatch logging enabled
- X-Ray tracing enabled

### 2. Lambda Functions (AWS-Native)

**Function 1: Auth Handler**

**Purpose**: Handle user authentication operations

**Runtime**: Python 3.10
**Memory**: 512 MB
**Timeout**: 30 seconds

**Environment Variables**:
```python
COGNITO_USER_POOL_ID = "us-east-1_xxxxx"
COGNITO_CLIENT_ID = "xxxxxxxxxxxxx"
JWT_SECRET = "stored-in-secrets-manager"
DYNAMODB_TABLE = "movielens-users"
```

**Handler Code Structure**:
```python
import json
import boto3
from typing import Dict, Any

cognito = boto3.client('cognito-idp')
dynamodb = boto3.resource('dynamodb')

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Handle authentication requests
    
    Routes:
    - POST /auth/register
    - POST /auth/login
    - POST /auth/refresh
    """
    http_method = event['httpMethod']
    path = event['path']
    
    if path == '/auth/register' and http_method == 'POST':
        return handle_register(event)
    elif path == '/auth/login' and http_method == 'POST':
        return handle_login(event)
    elif path == '/auth/refresh' and http_method == 'POST':
        return handle_refresh(event)
    
    return {
        'statusCode': 404,
        'body': json.dumps({'error': 'Not found'})
    }

def handle_register(event: Dict[str, Any]) -> Dict[str, Any]:
    """Register new user"""
    body = json.loads(event['body'])
    email = body['email']
    password = body['password']
    
    # Validate input
    if not validate_email(email):
        return error_response(400, 'Invalid email format')
    
    if not validate_password(password):
        return error_response(400, 'Password must be at least 8 characters')
    
    try:
        # Create user in Cognito
        response = cognito.sign_up(
            ClientId=COGNITO_CLIENT_ID,
            Username=email,
            Password=password,
            UserAttributes=[
                {'Name': 'email', 'Value': email}
            ]
        )
        
        # Create user record in DynamoDB
        table = dynamodb.Table(DYNAMODB_TABLE)
        table.put_item(
            Item={
                'user_id': response['UserSub'],
                'email': email,
                'created_at': datetime.now().isoformat(),
                'is_verified': False
            }
        )
        
        return success_response({
            'message': 'User registered successfully',
            'user_id': response['UserSub']
        })
        
    except cognito.exceptions.UsernameExistsException:
        return error_response(409, 'User already exists')
    except Exception as e:
        return error_response(500, str(e))
```

**Function 2: Recommendations Handler**

**Purpose**: Get personalized movie recommendations from SageMaker

**Runtime**: Python 3.10
**Memory**: 1024 MB
**Timeout**: 60 seconds

**Environment Variables**:
```python
SAGEMAKER_ENDPOINT = "movielens-recommendation-endpoint"
DYNAMODB_CACHE_TABLE = "movielens-cache"
CACHE_TTL_SECONDS = 300  # 5 minutes
```

**Handler Code Structure**:
```python
import json
import boto3
from datetime import datetime, timedelta
from typing import Dict, Any, List

sagemaker_runtime = boto3.client('sagemaker-runtime')
dynamodb = boto3.resource('dynamodb')

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Get personalized recommendations for user
    """
    # Extract user_id from JWT claims
    user_id = event['requestContext']['authorizer']['claims']['sub']
    
    # Check cache first
    cached = get_cached_recommendations(user_id)
    if cached:
        return success_response(cached)
    
    # Get recommendations from SageMaker
    try:
        recommendations = get_recommendations_from_sagemaker(user_id)
        
        # Cache results
        cache_recommendations(user_id, recommendations)
        
        return success_response(recommendations)
        
    except Exception as e:
        return error_response(500, f'Failed to get recommendations: {str(e)}')

def get_recommendations_from_sagemaker(user_id: str) -> List[Dict]:
    """
    Invoke SageMaker endpoint for recommendations
    """
    # Get top 100 movies to score
    movie_ids = get_popular_movies(limit=100)
    
    # Prepare payload
    payload = {
        'user_ids': [int(user_id)] * len(movie_ids),
        'movie_ids': movie_ids
    }
    
    # Invoke endpoint
    response = sagemaker_runtime.invoke_endpoint(
        EndpointName=SAGEMAKER_ENDPOINT,
        ContentType='application/json',
        Body=json.dumps(payload)
    )
    
    # Parse response
    result = json.loads(response['Body'].read())
    predictions = result['predictions']
    
    # Combine with movie metadata
    recommendations = []
    for movie_id, rating in zip(movie_ids, predictions):
        movie = get_movie_metadata(movie_id)
        recommendations.append({
            'movie_id': movie_id,
            'title': movie['title'],
            'genres': movie['genres'],
            'predicted_rating': round(rating, 2),
            'year': movie.get('year')
        })
    
    # Sort by predicted rating and return top 10
    recommendations.sort(key=lambda x: x['predicted_rating'], reverse=True)
    return recommendations[:10]
```


**Function 3: Movie Search Handler**

**Purpose**: Search movies by title and filter by genre

**Runtime**: Python 3.10
**Memory**: 512 MB
**Timeout**: 30 seconds

**Handler Code Structure**:
```python
def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Search movies with filters
    
    Query Parameters:
    - q: search query (title)
    - genre: filter by genre
    - year_min: minimum year
    - year_max: maximum year
    - page: page number (default 1)
    - limit: results per page (default 20)
    """
    params = event.get('queryStringParameters', {})
    query = params.get('q', '')
    genre = params.get('genre')
    year_min = params.get('year_min')
    year_max = params.get('year_max')
    page = int(params.get('page', 1))
    limit = int(params.get('limit', 20))
    
    # Search in DynamoDB or ElasticSearch
    results = search_movies(
        query=query,
        genre=genre,
        year_min=year_min,
        year_max=year_max,
        page=page,
        limit=limit
    )
    
    return success_response({
        'movies': results['items'],
        'total': results['total'],
        'page': page,
        'pages': (results['total'] + limit - 1) // limit
    })
```

**Function 4: Ratings Handler**

**Purpose**: Handle movie rating submissions and updates

**Runtime**: Python 3.10
**Memory**: 256 MB
**Timeout**: 15 seconds

**Handler Code Structure**:
```python
def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Handle rating operations
    
    POST /ratings - Submit new rating
    PUT /ratings/{id} - Update existing rating
    """
    http_method = event['httpMethod']
    user_id = event['requestContext']['authorizer']['claims']['sub']
    
    if http_method == 'POST':
        return handle_submit_rating(event, user_id)
    elif http_method == 'PUT':
        return handle_update_rating(event, user_id)
    
    return error_response(405, 'Method not allowed')

def handle_submit_rating(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """Submit new movie rating"""
    body = json.loads(event['body'])
    movie_id = body['movie_id']
    rating = body['rating']
    
    # Validate rating
    if not (0.5 <= rating <= 5.0):
        return error_response(400, 'Rating must be between 0.5 and 5.0')
    
    # Check if user already rated this movie
    existing = get_user_rating(user_id, movie_id)
    if existing:
        return error_response(409, 'Rating already exists. Use PUT to update.')
    
    # Store rating
    table = dynamodb.Table('movielens-ratings')
    rating_id = str(uuid.uuid4())
    
    table.put_item(
        Item={
            'rating_id': rating_id,
            'user_id': user_id,
            'movie_id': movie_id,
            'rating': rating,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
    )
    
    # Invalidate recommendation cache
    invalidate_cache(user_id)
    
    return success_response({
        'rating_id': rating_id,
        'message': 'Rating submitted successfully'
    })
```

### 3. DynamoDB Tables (AWS-Native)

**Table 1: Users Table**

**Purpose**: Store user account information

**Schema**:
```yaml
TableName: movielens-users
PartitionKey: user_id (String)
Attributes:
  - user_id: String (UUID)
  - email: String
  - created_at: String (ISO timestamp)
  - last_login: String (ISO timestamp)
  - is_verified: Boolean
  - rating_count: Number
  - favorite_genres: List

GlobalSecondaryIndexes:
  - IndexName: email-index
    PartitionKey: email
    ProjectionType: ALL
```

**Table 2: Ratings Table**

**Purpose**: Store user movie ratings

**Schema**:
```yaml
TableName: movielens-ratings
PartitionKey: user_id (String)
SortKey: movie_id (Number)
Attributes:
  - rating_id: String (UUID)
  - user_id: String
  - movie_id: Number
  - rating: Number (0.5-5.0)
  - created_at: String
  - updated_at: String

GlobalSecondaryIndexes:
  - IndexName: movie-ratings-index
    PartitionKey: movie_id
    SortKey: rating
    ProjectionType: ALL
```

**Table 3: Recommendation Cache Table**

**Purpose**: Cache recommendation results

**Schema**:
```yaml
TableName: movielens-cache
PartitionKey: user_id (String)
Attributes:
  - user_id: String
  - recommendations: Map (JSON)
  - created_at: String
  - expires_at: Number (TTL)

TimeToLive:
  Enabled: true
  AttributeName: expires_at
```

### 4. Cognito User Pool (AWS-Native)

**Purpose**: Manage user authentication and authorization

**Configuration**:
```yaml
UserPoolName: MovieLensUserPool
MfaConfiguration: OPTIONAL
PasswordPolicy:
  MinimumLength: 8
  RequireUppercase: true
  RequireLowercase: true
  RequireNumbers: true
  RequireSymbols: false

EmailConfiguration:
  EmailSendingAccount: COGNITO_DEFAULT
  
AutoVerifiedAttributes:
  - email

Schema:
  - Name: email
    AttributeDataType: String
    Required: true
    Mutable: false
```

**App Client**:
```yaml
ClientName: MovieLensWebApp
GenerateSecret: false
RefreshTokenValidity: 30 days
AccessTokenValidity: 1 hour
IdTokenValidity: 1 hour
AuthFlows:
  - ALLOW_USER_PASSWORD_AUTH
  - ALLOW_REFRESH_TOKEN_AUTH
```


### 5. FastAPI Backend (Modern Stack)

**Purpose**: Provide REST API with modern Python framework

**Project Structure**:
```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── config.py            # Configuration
│   ├── database.py          # Database connection
│   ├── models/              # SQLAlchemy models
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── rating.py
│   │   └── cache.py
│   ├── schemas/             # Pydantic schemas
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── auth.py
│   │   ├── movie.py
│   │   └── rating.py
│   ├── routers/             # API routes
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── movies.py
│   │   ├── recommendations.py
│   │   ├── ratings.py
│   │   └── profile.py
│   ├── services/            # Business logic
│   │   ├── __init__.py
│   │   ├── auth_service.py
│   │   ├── movie_service.py
│   │   ├── recommendation_service.py
│   │   └── rating_service.py
│   ├── middleware/          # Custom middleware
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── rate_limit.py
│   │   └── logging.py
│   └── utils/               # Utilities
│       ├── __init__.py
│       ├── security.py
│       ├── cache.py
│       └── sagemaker.py
├── tests/
├── requirements.txt
├── Dockerfile
└── docker-compose.yml
```

**Main Application (main.py)**:
```python
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
import time

from app.routers import auth, movies, recommendations, ratings, profile
from app.middleware.logging import LoggingMiddleware
from app.middleware.rate_limit import RateLimitMiddleware
from app.database import engine, Base

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="MovieLens Recommendation API",
    description="API for movie recommendations using ML",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://yourdomain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-RateLimit-Limit", "X-RateLimit-Remaining"]
)

# Compression middleware
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Custom middleware
app.add_middleware(LoggingMiddleware)
app.add_middleware(RateLimitMiddleware)

# Include routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(movies.router, prefix="/api/v1/movies", tags=["Movies"])
app.include_router(recommendations.router, prefix="/api/v1/recommendations", tags=["Recommendations"])
app.include_router(ratings.router, prefix="/api/v1/ratings", tags=["Ratings"])
app.include_router(profile.router, prefix="/api/v1/profile", tags=["Profile"])

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": time.time()}

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc)}
    )
```

**Authentication Router (routers/auth.py)**:
```python
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta

from app.database import get_db
from app.schemas.auth import UserRegister, UserLogin, Token
from app.services.auth_service import AuthService
from app.utils.security import create_access_token, verify_password

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserRegister,
    db: Session = Depends(get_db)
):
    """
    Register new user
    
    - **email**: Valid email address
    - **password**: Minimum 8 characters, 1 uppercase, 1 number
    """
    auth_service = AuthService(db)
    
    # Check if user exists
    if auth_service.get_user_by_email(user_data.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User already exists"
        )
    
    # Create user
    user = auth_service.create_user(
        email=user_data.email,
        password=user_data.password
    )
    
    return {
        "message": "User registered successfully",
        "user_id": user.user_id,
        "email": user.email
    }

@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    Login and get access token
    
    Returns JWT access token and refresh token
    """
    auth_service = AuthService(db)
    
    # Authenticate user
    user = auth_service.authenticate_user(
        email=form_data.username,
        password=form_data.password
    )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Create tokens
    access_token = create_access_token(
        data={"sub": user.user_id, "email": user.email},
        expires_delta=timedelta(hours=1)
    )
    
    refresh_token = create_access_token(
        data={"sub": user.user_id, "type": "refresh"},
        expires_delta=timedelta(days=30)
    )
    
    # Update last login
    auth_service.update_last_login(user.user_id)
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

@router.post("/refresh", response_model=Token)
async def refresh_token(
    refresh_token: str,
    db: Session = Depends(get_db)
):
    """
    Refresh access token using refresh token
    """
    # Verify and decode refresh token
    payload = verify_token(refresh_token)
    
    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    user_id = payload.get("sub")
    
    # Create new access token
    access_token = create_access_token(
        data={"sub": user_id},
        expires_delta=timedelta(hours=1)
    )
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }
```

**Recommendations Router (routers/recommendations.py)**:
```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.schemas.movie import MovieRecommendation
from app.services.recommendation_service import RecommendationService
from app.middleware.auth import get_current_user
from app.models.user import User

router = APIRouter()

@router.get("/", response_model=List[MovieRecommendation])
async def get_recommendations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get personalized movie recommendations
    
    Returns top 10 recommended movies with predicted ratings
    """
    rec_service = RecommendationService(db)
    
    try:
        recommendations = await rec_service.get_recommendations(
            user_id=current_user.user_id
        )
        return recommendations
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get recommendations: {str(e)}"
        )
```
