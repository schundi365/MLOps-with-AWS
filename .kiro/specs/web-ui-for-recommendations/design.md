# Design Document: Web UI for MovieLens Recommendations

## Overview

This design document describes two approaches for building user-facing web interfaces that expose the MovieLens recommendation SageMaker endpoints to end users:

1. **AWS-Native Approach**: API Gateway + Lambda + S3 Static Website + Cognito
2. **Modern Stack Approach**: FastAPI + React + Docker + PostgreSQL

Both approaches provide secure, scalable access to the recommendation engine with authentication, rate limiting, and monitoring.

## Architecture Comparison

### AWS-Native Stack
- **Frontend**: Static HTML/CSS/JS on S3 + CloudFront
- **API**: API Gateway REST API
- **Backend**: Lambda functions (Python 3.10+)
- **Auth**: Amazon Cognito
- **Database**: DynamoDB
- **Caching**: API Gateway caching
- **Deployment**: Serverless, pay-per-use

### Modern Stack
- **Frontend**: React 18+ with TypeScript
- **API**: FastAPI (Python 3.10+)
- **Backend**: FastAPI async endpoints
- **Auth**: JWT tokens with python-jose
- **Database**: PostgreSQL with SQLAlchemy
- **Caching**: Redis
- **Deployment**: Docker containers on ECS/EKS/EC2

## High-Level Architecture Diagrams

See architecture diagrams in separate sections below.


## AWS-Native Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         User Browser                             │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             │ HTTPS
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      CloudFront CDN                              │
│                  (Static Assets + HTTPS)                         │
└────────────┬────────────────────────────────────┬────────────────┘
             │                                    │
             │ Static Files                       │ API Calls
             ▼                                    ▼
┌─────────────────────┐              ┌──────────────────────────┐
│   S3 Static Website │              │    API Gateway           │
│   - index.html      │              │    - REST API            │
│   - app.js          │              │    - CORS enabled        │
│   - styles.css      │              │    - Usage plans         │
└─────────────────────┘              └──────────┬───────────────┘
                                                │
                                                │ Invoke
                                                ▼
                                     ┌──────────────────────────┐
                                     │   Cognito Authorizer     │
                                     │   - JWT validation       │
                                     └──────────┬───────────────┘
                                                │
                                                │ Authorized
                                                ▼
┌────────────────────────────────────────────────────────────────┐
│                      Lambda Functions                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│  │ Auth Handler │  │Search Handler│  │ Recommend    │        │
│  │              │  │              │  │ Handler      │        │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘        │
│         │                  │                  │                 │
└─────────┼──────────────────┼──────────────────┼─────────────────┘
          │                  │                  │
          ▼                  ▼                  ▼
┌─────────────────┐  ┌──────────────┐  ┌──────────────────────┐
│   DynamoDB      │  │  DynamoDB    │  │  SageMaker Endpoint  │
│   Users Table   │  │Ratings Table │  │  (Existing ML Model) │
└─────────────────┘  └──────────────┘  └──────────────────────┘
```

### Key Components

**1. CloudFront Distribution**
- CDN for global content delivery
- HTTPS termination with ACM certificate
- Caching for static assets (1 day TTL)
- Origin: S3 bucket for static website

**2. S3 Static Website**
- Bucket configured for static hosting
- Contains: HTML, CSS, JavaScript files
- Versioning enabled for rollback
- Bucket policy allows CloudFront access only

**3. API Gateway**
- REST API with resource-based endpoints
- Cognito authorizer for protected routes
- Request/response validation
- Usage plans: 100 recommendations/day per user
- CloudWatch logging enabled

**4. Lambda Functions**
- Runtime: Python 3.10
- Memory: 512MB - 1024MB
- Timeout: 30 seconds
- VPC: Optional (for DynamoDB VPC endpoints)
- Environment variables for configuration

**5. Amazon Cognito**
- User pool for authentication
- Email verification required
- Password policy: min 8 chars, 1 uppercase, 1 number
- JWT tokens with 1-hour expiration
- Refresh tokens with 30-day expiration

**6. DynamoDB Tables**
- On-demand billing mode
- Point-in-time recovery enabled
- Encryption at rest with AWS managed keys


## Modern Stack Architecture (FastAPI + React)

```
┌─────────────────────────────────────────────────────────────────┐
│                    User Browser (React App)                      │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             │ HTTPS (API Calls)
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│              Application Load Balancer (ALB)                     │
│              - HTTPS termination                                 │
│              - Health checks                                     │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             │ HTTP
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FastAPI Backend (Docker)                      │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  FastAPI Application                                      │  │
│  │  - Async endpoints                                        │  │
│  │  - Pydantic validation                                    │  │
│  │  - JWT middleware                                         │  │
│  │  - CORS middleware                                        │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
│  Routes:                                                         │
│  POST   /api/v1/auth/register                                   │
│  POST   /api/v1/auth/login                                      │
│  GET    /api/v1/movies/search                                   │
│  GET    /api/v1/recommendations                                 │
│  POST   /api/v1/ratings                                         │
│  GET    /api/v1/profile                                         │
└────────┬──────────────────┬──────────────────┬──────────────────┘
         │                  │                  │
         ▼                  ▼                  ▼
┌────────────────┐  ┌──────────────┐  ┌──────────────────────┐
│  PostgreSQL    │  │    Redis     │  │  SageMaker Endpoint  │
│  - Users       │  │  - Cache     │  │  (Existing ML Model) │
│  - Ratings     │  │  - Sessions  │  │                      │
│  - Movies      │  │  - Rate Limit│  │                      │
└────────────────┘  └──────────────┘  └──────────────────────┘
```

### Key Components

**1. React Frontend**
- Built with Vite for fast development
- TypeScript for type safety
- React Router for navigation
- React Query for API state management
- Material-UI for components
- Deployed as static files on S3 + CloudFront

**2. FastAPI Backend**
- Async/await for I/O operations
- Automatic OpenAPI documentation at /docs
- Pydantic models for validation
- SQLAlchemy ORM for database
- python-jose for JWT handling
- Deployed in Docker containers

**3. PostgreSQL Database**
- RDS managed service
- Multi-AZ for high availability
- Automated backups
- Connection pooling via SQLAlchemy

**4. Redis Cache**
- ElastiCache managed service
- Cache recommendations (5 min TTL)
- Store rate limit counters
- Session storage

**5. Docker Deployment**
- Multi-stage builds for optimization
- Health check endpoints
- Graceful shutdown handling
- Environment-based configuration


## API Specification

### Authentication Endpoints

#### POST /api/v1/auth/register
Register a new user account.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "SecurePass123",
  "name": "John Doe"
}
```

**Response (201):**
```json
{
  "user_id": "uuid-here",
  "email": "user@example.com",
  "message": "Verification email sent"
}
```

#### POST /api/v1/auth/login
Authenticate and receive JWT tokens.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "SecurePass123"
}
```

**Response (200):**
```json
{
  "access_token": "eyJhbGc...",
  "refresh_token": "eyJhbGc...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

#### POST /api/v1/auth/refresh
Refresh access token using refresh token.

**Request:**
```json
{
  "refresh_token": "eyJhbGc..."
}
```

**Response (200):**
```json
{
  "access_token": "eyJhbGc...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

### Movie Endpoints

#### GET /api/v1/movies/search
Search for movies by title or genre.

**Query Parameters:**
- `q`: Search query (optional)
- `genre`: Filter by genre (optional)
- `year_min`: Minimum release year (optional)
- `year_max`: Maximum release year (optional)
- `page`: Page number (default: 1)
- `limit`: Results per page (default: 20, max: 100)

**Response (200):**
```json
{
  "movies": [
    {
      "movie_id": 1,
      "title": "Toy Story (1995)",
      "genres": ["Animation", "Children", "Comedy"],
      "year": 1995,
      "poster_url": "https://..."
    }
  ],
  "total": 150,
  "page": 1,
  "pages": 8
}
```

### Recommendation Endpoints

#### GET /api/v1/recommendations
Get personalized movie recommendations for the authenticated user.

**Headers:**
- `Authorization: Bearer <access_token>`

**Query Parameters:**
- `limit`: Number of recommendations (default: 10, max: 50)

**Response (200):**
```json
{
  "recommendations": [
    {
      "movie_id": 50,
      "title": "The Usual Suspects (1995)",
      "genres": ["Crime", "Mystery", "Thriller"],
      "predicted_rating": 4.5,
      "confidence": 0.85
    }
  ],
  "user_id": "uuid-here",
  "generated_at": "2026-01-23T10:30:00Z"
}
```

### Rating Endpoints

#### POST /api/v1/ratings
Submit or update a movie rating.

**Headers:**
- `Authorization: Bearer <access_token>`

**Request:**
```json
{
  "movie_id": 1,
  "rating": 4.5
}
```

**Response (201):**
```json
{
  "rating_id": "uuid-here",
  "movie_id": 1,
  "rating": 4.5,
  "created_at": "2026-01-23T10:30:00Z"
}
```

#### GET /api/v1/ratings
Get user's rating history.

**Headers:**
- `Authorization: Bearer <access_token>`

**Query Parameters:**
- `page`: Page number (default: 1)
- `limit`: Results per page (default: 20)
- `sort`: Sort by 'date' or 'rating' (default: 'date')

**Response (200):**
```json
{
  "ratings": [
    {
      "rating_id": "uuid-here",
      "movie_id": 1,
      "title": "Toy Story (1995)",
      "rating": 4.5,
      "created_at": "2026-01-23T10:30:00Z"
    }
  ],
  "total": 45,
  "page": 1
}
```

### Profile Endpoints

#### GET /api/v1/profile
Get user profile and statistics.

**Headers:**
- `Authorization: Bearer <access_token>`

**Response (200):**
```json
{
  "user_id": "uuid-here",
  "email": "user@example.com",
  "name": "John Doe",
  "created_at": "2026-01-01T00:00:00Z",
  "statistics": {
    "total_ratings": 45,
    "average_rating": 3.8,
    "favorite_genres": ["Action", "Sci-Fi", "Thriller"]
  }
}
```


## Database Schema

### AWS-Native (DynamoDB)

#### Users Table
```
Partition Key: user_id (String, UUID)
Attributes:
  - email (String, unique)
  - password_hash (String)
  - name (String)
  - created_at (String, ISO 8601)
  - last_login (String, ISO 8601)
  - is_verified (Boolean)

GSI: email-index
  - Partition Key: email
```

#### Ratings Table
```
Partition Key: user_id (String, UUID)
Sort Key: movie_id (Number)
Attributes:
  - rating_id (String, UUID)
  - rating (Number, 0.5-5.0)
  - created_at (String, ISO 8601)
  - updated_at (String, ISO 8601)

GSI: movie-ratings-index
  - Partition Key: movie_id
  - Sort Key: created_at
```

#### RecommendationCache Table
```
Partition Key: user_id (String, UUID)
Attributes:
  - recommendations (List of Maps)
  - created_at (String, ISO 8601)
  - expires_at (Number, Unix timestamp)
TTL: expires_at
```

### Modern Stack (PostgreSQL)

```sql
-- Users table
CREATE TABLE users (
    user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    name VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP,
    is_verified BOOLEAN DEFAULT FALSE
);

CREATE INDEX idx_users_email ON users(email);

-- Ratings table
CREATE TABLE ratings (
    rating_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    movie_id INTEGER NOT NULL,
    rating DECIMAL(2,1) CHECK (rating >= 0.5 AND rating <= 5.0),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, movie_id)
);

CREATE INDEX idx_ratings_user ON ratings(user_id);
CREATE INDEX idx_ratings_movie ON ratings(movie_id);
CREATE INDEX idx_ratings_created ON ratings(created_at DESC);

-- Movies table (cached from MovieLens data)
CREATE TABLE movies (
    movie_id INTEGER PRIMARY KEY,
    title VARCHAR(500) NOT NULL,
    genres TEXT[],
    year INTEGER,
    poster_url VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_movies_title ON movies USING gin(to_tsvector('english', title));
CREATE INDEX idx_movies_genres ON movies USING gin(genres);
CREATE INDEX idx_movies_year ON movies(year);

-- Recommendation cache table
CREATE TABLE recommendation_cache (
    cache_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    recommendations JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL
);

CREATE INDEX idx_cache_user ON recommendation_cache(user_id);
CREATE INDEX idx_cache_expires ON recommendation_cache(expires_at);
```


## Implementation Details

### AWS-Native Lambda Functions

#### Auth Lambda (auth_handler.py)
```python
import json
import boto3
import hashlib
from datetime import datetime

cognito = boto3.client('cognito-idp')
dynamodb = boto3.resource('dynamodb')
users_table = dynamodb.Table('movielens-users')

def lambda_handler(event, context):
    """Handle authentication requests"""
    path = event['path']
    method = event['httpMethod']
    
    if path == '/auth/register' and method == 'POST':
        return register_user(event)
    elif path == '/auth/login' and method == 'POST':
        return login_user(event)
    
    return {
        'statusCode': 404,
        'body': json.dumps({'error': 'Not found'})
    }

def register_user(event):
    """Register new user"""
    body = json.loads(event['body'])
    email = body['email']
    password = body['password']
    
    # Create user in Cognito
    response = cognito.sign_up(
        ClientId=os.environ['COGNITO_CLIENT_ID'],
        Username=email,
        Password=password,
        UserAttributes=[
            {'Name': 'email', 'Value': email}
        ]
    )
    
    # Store user in DynamoDB
    users_table.put_item(
        Item={
            'user_id': response['UserSub'],
            'email': email,
            'created_at': datetime.utcnow().isoformat(),
            'is_verified': False
        }
    )
    
    return {
        'statusCode': 201,
        'body': json.dumps({
            'user_id': response['UserSub'],
            'message': 'Verification email sent'
        })
    }
```

#### Recommendations Lambda (recommendations_handler.py)
```python
import json
import boto3
from datetime import datetime, timedelta

sagemaker_runtime = boto3.client('sagemaker-runtime')
dynamodb = boto3.resource('dynamodb')
cache_table = dynamodb.Table('movielens-recommendation-cache')

ENDPOINT_NAME = os.environ['SAGEMAKER_ENDPOINT_NAME']
CACHE_TTL_MINUTES = 5

def lambda_handler(event, context):
    """Get personalized recommendations"""
    user_id = event['requestContext']['authorizer']['claims']['sub']
    limit = int(event.get('queryStringParameters', {}).get('limit', 10))
    
    # Check cache first
    cached = get_cached_recommendations(user_id)
    if cached:
        return {
            'statusCode': 200,
            'body': json.dumps(cached)
        }
    
    # Get recommendations from SageMaker
    recommendations = get_recommendations_from_sagemaker(user_id, limit)
    
    # Cache results
    cache_recommendations(user_id, recommendations)
    
    return {
        'statusCode': 200,
        'body': json.dumps(recommendations)
    }

def get_recommendations_from_sagemaker(user_id, limit):
    """Invoke SageMaker endpoint"""
    # Get top movies for this user
    payload = {
        'user_id': user_id,
        'top_k': limit
    }
    
    response = sagemaker_runtime.invoke_endpoint(
        EndpointName=ENDPOINT_NAME,
        ContentType='application/json',
        Body=json.dumps(payload)
    )
    
    result = json.loads(response['Body'].read())
    return result
```


### FastAPI Backend Implementation

#### Main Application (main.py)
```python
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
import uvicorn

from .database import get_db
from .auth import verify_token
from .models import User, Rating, Movie
from .schemas import (
    UserRegister, UserLogin, TokenResponse,
    MovieSearch, RecommendationResponse, RatingCreate
)
from .sagemaker import get_recommendations

app = FastAPI(
    title="MovieLens Recommendation API",
    version="1.0.0",
    docs_url="/api/docs"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()

# Auth endpoints
@app.post("/api/v1/auth/register", response_model=TokenResponse)
async def register(user: UserRegister, db: Session = Depends(get_db)):
    """Register new user"""
    # Check if user exists
    existing = db.query(User).filter(User.email == user.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create user
    new_user = User(
        email=user.email,
        password_hash=hash_password(user.password),
        name=user.name
    )
    db.add(new_user)
    db.commit()
    
    # Generate tokens
    access_token = create_access_token(new_user.user_id)
    refresh_token = create_refresh_token(new_user.user_id)
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer"
    )

@app.post("/api/v1/auth/login", response_model=TokenResponse)
async def login(credentials: UserLogin, db: Session = Depends(get_db)):
    """Login user"""
    user = db.query(User).filter(User.email == credentials.email).first()
    if not user or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    access_token = create_access_token(user.user_id)
    refresh_token = create_refresh_token(user.user_id)
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer"
    )

# Movie endpoints
@app.get("/api/v1/movies/search")
async def search_movies(
    q: str = None,
    genre: str = None,
    page: int = 1,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """Search for movies"""
    query = db.query(Movie)
    
    if q:
        query = query.filter(Movie.title.ilike(f"%{q}%"))
    if genre:
        query = query.filter(Movie.genres.contains([genre]))
    
    total = query.count()
    movies = query.offset((page - 1) * limit).limit(limit).all()
    
    return {
        "movies": movies,
        "total": total,
        "page": page,
        "pages": (total + limit - 1) // limit
    }

# Recommendation endpoints
@app.get("/api/v1/recommendations", response_model=RecommendationResponse)
async def get_user_recommendations(
    limit: int = 10,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Get personalized recommendations"""
    user_id = verify_token(credentials.credentials)
    
    # Check cache
    cached = get_cached_recommendations(user_id)
    if cached:
        return cached
    
    # Get from SageMaker
    recommendations = await get_recommendations(user_id, limit)
    
    # Cache results
    cache_recommendations(user_id, recommendations)
    
    return recommendations

# Rating endpoints
@app.post("/api/v1/ratings")
async def submit_rating(
    rating: RatingCreate,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Submit or update movie rating"""
    user_id = verify_token(credentials.credentials)
    
    # Check if rating exists
    existing = db.query(Rating).filter(
        Rating.user_id == user_id,
        Rating.movie_id == rating.movie_id
    ).first()
    
    if existing:
        existing.rating = rating.rating
        existing.updated_at = datetime.utcnow()
    else:
        new_rating = Rating(
            user_id=user_id,
            movie_id=rating.movie_id,
            rating=rating.rating
        )
        db.add(new_rating)
    
    db.commit()
    
    return {"message": "Rating submitted successfully"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
```


### React Frontend Implementation

#### App Structure
```
webapp/frontend/
├── src/
│   ├── components/
│   │   ├── Auth/
│   │   │   ├── LoginForm.tsx
│   │   │   └── RegisterForm.tsx
│   │   ├── Movies/
│   │   │   ├── MovieCard.tsx
│   │   │   ├── MovieList.tsx
│   │   │   └── SearchBar.tsx
│   │   ├── Recommendations/
│   │   │   ├── RecommendationList.tsx
│   │   │   └── RecommendationCard.tsx
│   │   └── Profile/
│   │       ├── ProfileStats.tsx
│   │       └── RatingHistory.tsx
│   ├── pages/
│   │   ├── HomePage.tsx
│   │   ├── LoginPage.tsx
│   │   ├── RecommendationsPage.tsx
│   │   └── ProfilePage.tsx
│   ├── services/
│   │   ├── api.ts
│   │   ├── auth.ts
│   │   └── recommendations.ts
│   ├── hooks/
│   │   ├── useAuth.ts
│   │   └── useRecommendations.ts
│   ├── context/
│   │   └── AuthContext.tsx
│   ├── App.tsx
│   └── main.tsx
├── package.json
└── vite.config.ts
```

#### Key Components

**API Service (services/api.ts)**
```typescript
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add auth token to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle token refresh on 401
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      const refreshToken = localStorage.getItem('refresh_token');
      if (refreshToken) {
        try {
          const response = await axios.post(`${API_BASE_URL}/api/v1/auth/refresh`, {
            refresh_token: refreshToken,
          });
          localStorage.setItem('access_token', response.data.access_token);
          error.config.headers.Authorization = `Bearer ${response.data.access_token}`;
          return axios(error.config);
        } catch {
          localStorage.clear();
          window.location.href = '/login';
        }
      }
    }
    return Promise.reject(error);
  }
);

export default api;
```

**Auth Hook (hooks/useAuth.ts)**
```typescript
import { useState, useEffect } from 'react';
import api from '../services/api';

interface User {
  user_id: string;
  email: string;
  name: string;
}

export const useAuth = () => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (token) {
      fetchUser();
    } else {
      setLoading(false);
    }
  }, []);

  const fetchUser = async () => {
    try {
      const response = await api.get('/api/v1/profile');
      setUser(response.data);
    } catch (error) {
      localStorage.clear();
    } finally {
      setLoading(false);
    }
  };

  const login = async (email: string, password: string) => {
    const response = await api.post('/api/v1/auth/login', { email, password });
    localStorage.setItem('access_token', response.data.access_token);
    localStorage.setItem('refresh_token', response.data.refresh_token);
    await fetchUser();
  };

  const logout = () => {
    localStorage.clear();
    setUser(null);
  };

  return { user, loading, login, logout };
};
```

**Recommendations Component (components/Recommendations/RecommendationList.tsx)**
```typescript
import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { Grid, Card, CardContent, Typography, Rating, CircularProgress } from '@mui/material';
import api from '../../services/api';

interface Recommendation {
  movie_id: number;
  title: string;
  genres: string[];
  predicted_rating: number;
  confidence: number;
}

export const RecommendationList: React.FC = () => {
  const { data, isLoading, error } = useQuery({
    queryKey: ['recommendations'],
    queryFn: async () => {
      const response = await api.get('/api/v1/recommendations');
      return response.data;
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  if (isLoading) {
    return <CircularProgress />;
  }

  if (error) {
    return <Typography color="error">Failed to load recommendations</Typography>;
  }

  return (
    <Grid container spacing={3}>
      {data.recommendations.map((rec: Recommendation) => (
        <Grid item xs={12} sm={6} md={4} key={rec.movie_id}>
          <Card>
            <CardContent>
              <Typography variant="h6">{rec.title}</Typography>
              <Typography variant="body2" color="text.secondary">
                {rec.genres.join(', ')}
              </Typography>
              <Rating value={rec.predicted_rating} readOnly precision={0.5} />
              <Typography variant="caption">
                Confidence: {(rec.confidence * 100).toFixed(0)}%
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      ))}
    </Grid>
  );
};
```


## Security Implementation

### JWT Token Structure
```json
{
  "header": {
    "alg": "HS256",
    "typ": "JWT"
  },
  "payload": {
    "sub": "user-uuid",
    "email": "user@example.com",
    "exp": 1706011200,
    "iat": 1706007600
  }
}
```

### Rate Limiting

**AWS-Native (API Gateway Usage Plans)**
```python
# Create usage plan
usage_plan = apigateway.create_usage_plan(
    name='MovieLensBasicPlan',
    throttle={
        'rateLimit': 10,  # requests per second
        'burstLimit': 20
    },
    quota={
        'limit': 1000,  # requests per day
        'period': 'DAY'
    }
)
```

**FastAPI (Redis-based)**
```python
from fastapi import Request, HTTPException
from redis import Redis
import time

redis_client = Redis(host='localhost', port=6379)

async def rate_limit_middleware(request: Request, call_next):
    """Rate limiting middleware"""
    user_id = request.state.user_id
    key = f"rate_limit:{user_id}:{time.strftime('%Y%m%d')}"
    
    current = redis_client.get(key)
    if current and int(current) >= 1000:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    redis_client.incr(key)
    redis_client.expire(key, 86400)  # 24 hours
    
    response = await call_next(request)
    response.headers['X-RateLimit-Limit'] = '1000'
    response.headers['X-RateLimit-Remaining'] = str(1000 - int(current or 0))
    
    return response
```

### Input Validation

**Pydantic Models (FastAPI)**
```python
from pydantic import BaseModel, EmailStr, Field, validator

class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    name: str = Field(..., min_length=1, max_length=255)
    
    @validator('password')
    def validate_password(cls, v):
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain uppercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain digit')
        return v

class RatingCreate(BaseModel):
    movie_id: int = Field(..., gt=0)
    rating: float = Field(..., ge=0.5, le=5.0)
    
    @validator('rating')
    def validate_rating(cls, v):
        if v % 0.5 != 0:
            raise ValueError('Rating must be in 0.5 increments')
        return v
```

### CORS Configuration

**FastAPI**
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://movielens.example.com",
        "http://localhost:3000"  # Development only
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
    max_age=3600
)
```

**API Gateway**
```python
# Enable CORS on API Gateway
apigateway.put_method_response(
    restApiId=api_id,
    resourceId=resource_id,
    httpMethod='OPTIONS',
    statusCode='200',
    responseParameters={
        'method.response.header.Access-Control-Allow-Origin': True,
        'method.response.header.Access-Control-Allow-Methods': True,
        'method.response.header.Access-Control-Allow-Headers': True
    }
)
```


## Deployment Strategies

### AWS-Native Deployment

**Infrastructure as Code (CloudFormation/Terraform)**
```yaml
# CloudFormation template snippet
Resources:
  # S3 bucket for static website
  WebsiteBucket:
    Type: AWS::S3::Bucket
    Properties:
      BucketName: movielens-webapp
      WebsiteConfiguration:
        IndexDocument: index.html
        ErrorDocument: error.html
  
  # CloudFront distribution
  CloudFrontDistribution:
    Type: AWS::CloudFront::Distribution
    Properties:
      DistributionConfig:
        Origins:
          - DomainName: !GetAtt WebsiteBucket.DomainName
            Id: S3Origin
            S3OriginConfig:
              OriginAccessIdentity: !Sub 'origin-access-identity/cloudfront/${CloudFrontOAI}'
        DefaultCacheBehavior:
          TargetOriginId: S3Origin
          ViewerProtocolPolicy: redirect-to-https
          CachePolicyId: 658327ea-f89d-4fab-a63d-7e88639e58f6  # CachingOptimized
        Enabled: true
        HttpVersion: http2
        ViewerCertificate:
          AcmCertificateArn: !Ref SSLCertificate
          SslSupportMethod: sni-only
  
  # API Gateway
  RestApi:
    Type: AWS::ApiGateway::RestApi
    Properties:
      Name: MovieLensAPI
      EndpointConfiguration:
        Types:
          - REGIONAL
  
  # Lambda functions
  AuthFunction:
    Type: AWS::Lambda::Function
    Properties:
      FunctionName: movielens-auth
      Runtime: python3.10
      Handler: auth_handler.lambda_handler
      Code:
        S3Bucket: !Ref LambdaCodeBucket
        S3Key: auth_handler.zip
      Environment:
        Variables:
          COGNITO_CLIENT_ID: !Ref CognitoUserPoolClient
          USERS_TABLE: !Ref UsersTable
```

**Deployment Script**
```bash
#!/bin/bash
# deploy_aws_native.sh

set -e

BUCKET_NAME="movielens-webapp"
STACK_NAME="movielens-web-ui"

echo "Building frontend..."
cd webapp/frontend
npm run build
cd ../..

echo "Uploading to S3..."
aws s3 sync webapp/frontend/dist s3://${BUCKET_NAME}/ --delete

echo "Packaging Lambda functions..."
cd webapp/backend/lambda
zip -r auth_handler.zip auth_handler.py
zip -r recommendations_handler.zip recommendations_handler.py
cd ../../..

echo "Uploading Lambda code..."
aws s3 cp webapp/backend/lambda/auth_handler.zip s3://${BUCKET_NAME}/lambda/
aws s3 cp webapp/backend/lambda/recommendations_handler.zip s3://${BUCKET_NAME}/lambda/

echo "Deploying CloudFormation stack..."
aws cloudformation deploy \
  --template-file infrastructure/cloudformation.yaml \
  --stack-name ${STACK_NAME} \
  --capabilities CAPABILITY_IAM \
  --parameter-overrides \
    BucketName=${BUCKET_NAME}

echo "Invalidating CloudFront cache..."
DISTRIBUTION_ID=$(aws cloudformation describe-stacks \
  --stack-name ${STACK_NAME} \
  --query 'Stacks[0].Outputs[?OutputKey==`DistributionId`].OutputValue' \
  --output text)

aws cloudfront create-invalidation \
  --distribution-id ${DISTRIBUTION_ID} \
  --paths "/*"

echo "Deployment complete!"
```

### FastAPI + Docker Deployment

**Dockerfile**
```dockerfile
# Multi-stage build
FROM python:3.10-slim as builder

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Final stage
FROM python:3.10-slim

WORKDIR /app

# Copy dependencies from builder
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Copy application code
COPY . .

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8000/health')"

# Run application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**docker-compose.yml (Development)**
```yaml
version: '3.8'

services:
  backend:
    build: ./webapp/backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/movielens
      - REDIS_URL=redis://redis:6379
      - SAGEMAKER_ENDPOINT_NAME=movielens-endpoint
    depends_on:
      - db
      - redis
    volumes:
      - ./webapp/backend:/app
    command: uvicorn main:app --reload --host 0.0.0.0 --port 8000
  
  frontend:
    build: ./webapp/frontend
    ports:
      - "3000:3000"
    environment:
      - VITE_API_URL=http://localhost:8000
    volumes:
      - ./webapp/frontend:/app
      - /app/node_modules
    command: npm run dev
  
  db:
    image: postgres:15
    environment:
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
      - POSTGRES_DB=movielens
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
  
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

volumes:
  postgres_data:
```

**ECS Deployment (Production)**
```bash
#!/bin/bash
# deploy_ecs.sh

set -e

AWS_REGION="us-east-1"
ECR_REPO="movielens-backend"
CLUSTER_NAME="movielens-cluster"
SERVICE_NAME="movielens-service"

echo "Building Docker image..."
docker build -t ${ECR_REPO}:latest webapp/backend/

echo "Logging into ECR..."
aws ecr get-login-password --region ${AWS_REGION} | \
  docker login --username AWS --password-stdin \
  $(aws sts get-caller-identity --query Account --output text).dkr.ecr.${AWS_REGION}.amazonaws.com

echo "Tagging and pushing image..."
docker tag ${ECR_REPO}:latest \
  $(aws sts get-caller-identity --query Account --output text).dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO}:latest

docker push \
  $(aws sts get-caller-identity --query Account --output text).dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO}:latest

echo "Updating ECS service..."
aws ecs update-service \
  --cluster ${CLUSTER_NAME} \
  --service ${SERVICE_NAME} \
  --force-new-deployment

echo "Deployment initiated!"
```


## Monitoring and Observability

### CloudWatch Metrics

**Custom Metrics to Track**
```python
import boto3
from datetime import datetime

cloudwatch = boto3.client('cloudwatch')

def publish_api_metrics(endpoint: str, status_code: int, latency_ms: float):
    """Publish API metrics to CloudWatch"""
    cloudwatch.put_metric_data(
        Namespace='MovieLens/WebUI',
        MetricData=[
            {
                'MetricName': 'APIRequests',
                'Dimensions': [
                    {'Name': 'Endpoint', 'Value': endpoint},
                    {'Name': 'StatusCode', 'Value': str(status_code)}
                ],
                'Value': 1,
                'Unit': 'Count',
                'Timestamp': datetime.utcnow()
            },
            {
                'MetricName': 'APILatency',
                'Dimensions': [
                    {'Name': 'Endpoint', 'Value': endpoint}
                ],
                'Value': latency_ms,
                'Unit': 'Milliseconds',
                'Timestamp': datetime.utcnow()
            }
        ]
    )
```

**Key Metrics**
- API request count by endpoint
- API latency (P50, P90, P99)
- Error rate by status code (4xx, 5xx)
- SageMaker endpoint invocations
- Cache hit/miss ratio
- User registration/login events
- Daily active users (DAU)
- Recommendation request patterns

### CloudWatch Dashboard

```python
def create_dashboard():
    """Create CloudWatch dashboard for web UI"""
    dashboard_body = {
        "widgets": [
            {
                "type": "metric",
                "properties": {
                    "metrics": [
                        ["MovieLens/WebUI", "APIRequests", {"stat": "Sum"}]
                    ],
                    "period": 300,
                    "stat": "Sum",
                    "region": "us-east-1",
                    "title": "API Requests"
                }
            },
            {
                "type": "metric",
                "properties": {
                    "metrics": [
                        ["MovieLens/WebUI", "APILatency", {"stat": "Average"}],
                        ["...", {"stat": "p99"}]
                    ],
                    "period": 300,
                    "region": "us-east-1",
                    "title": "API Latency"
                }
            },
            {
                "type": "metric",
                "properties": {
                    "metrics": [
                        ["MovieLens/WebUI", "APIRequests", 
                         {"stat": "Sum", "dimensions": {"StatusCode": "500"}}]
                    ],
                    "period": 300,
                    "stat": "Sum",
                    "region": "us-east-1",
                    "title": "Error Rate"
                }
            }
        ]
    }
    
    cloudwatch.put_dashboard(
        DashboardName='MovieLens-WebUI',
        DashboardBody=json.dumps(dashboard_body)
    )
```

### CloudWatch Alarms

```python
def create_alarms():
    """Create CloudWatch alarms for critical metrics"""
    
    # High error rate alarm
    cloudwatch.put_metric_alarm(
        AlarmName='MovieLens-HighErrorRate',
        ComparisonOperator='GreaterThanThreshold',
        EvaluationPeriods=2,
        MetricName='APIRequests',
        Namespace='MovieLens/WebUI',
        Period=300,
        Statistic='Sum',
        Threshold=50,
        ActionsEnabled=True,
        AlarmActions=['arn:aws:sns:us-east-1:ACCOUNT_ID:alerts'],
        AlarmDescription='Alert when error rate exceeds 5%',
        Dimensions=[
            {'Name': 'StatusCode', 'Value': '500'}
        ]
    )
    
    # High latency alarm
    cloudwatch.put_metric_alarm(
        AlarmName='MovieLens-HighLatency',
        ComparisonOperator='GreaterThanThreshold',
        EvaluationPeriods=2,
        MetricName='APILatency',
        Namespace='MovieLens/WebUI',
        Period=300,
        Statistic='Average',
        Threshold=2000,  # 2 seconds
        ActionsEnabled=True,
        AlarmActions=['arn:aws:sns:us-east-1:ACCOUNT_ID:alerts'],
        AlarmDescription='Alert when P99 latency exceeds 2s'
    )
```

### Application Logging

**Structured Logging (FastAPI)**
```python
import logging
import json
from datetime import datetime

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'
)

logger = logging.getLogger(__name__)

def log_api_request(request, response, duration_ms):
    """Log API request in structured format"""
    log_entry = {
        'timestamp': datetime.utcnow().isoformat(),
        'level': 'INFO',
        'method': request.method,
        'path': request.url.path,
        'status_code': response.status_code,
        'duration_ms': duration_ms,
        'user_id': getattr(request.state, 'user_id', None),
        'ip_address': request.client.host
    }
    logger.info(json.dumps(log_entry))
```


## Testing Strategy

### Unit Tests

**Backend Tests (pytest)**
```python
# tests/test_auth.py
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_register_user():
    """Test user registration"""
    response = client.post("/api/v1/auth/register", json={
        "email": "test@example.com",
        "password": "SecurePass123",
        "name": "Test User"
    })
    assert response.status_code == 201
    assert "access_token" in response.json()

def test_register_duplicate_email():
    """Test duplicate email registration fails"""
    # Register first user
    client.post("/api/v1/auth/register", json={
        "email": "test@example.com",
        "password": "SecurePass123",
        "name": "Test User"
    })
    
    # Try to register again
    response = client.post("/api/v1/auth/register", json={
        "email": "test@example.com",
        "password": "SecurePass123",
        "name": "Test User 2"
    })
    assert response.status_code == 400

def test_login_success():
    """Test successful login"""
    # Register user
    client.post("/api/v1/auth/register", json={
        "email": "test@example.com",
        "password": "SecurePass123",
        "name": "Test User"
    })
    
    # Login
    response = client.post("/api/v1/auth/login", json={
        "email": "test@example.com",
        "password": "SecurePass123"
    })
    assert response.status_code == 200
    assert "access_token" in response.json()

def test_login_invalid_credentials():
    """Test login with invalid credentials"""
    response = client.post("/api/v1/auth/login", json={
        "email": "test@example.com",
        "password": "WrongPassword"
    })
    assert response.status_code == 401
```

**Frontend Tests (Jest + React Testing Library)**
```typescript
// tests/LoginForm.test.tsx
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { LoginForm } from '../components/Auth/LoginForm';
import { AuthProvider } from '../context/AuthContext';

describe('LoginForm', () => {
  it('renders login form', () => {
    render(
      <AuthProvider>
        <LoginForm />
      </AuthProvider>
    );
    
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /login/i })).toBeInTheDocument();
  });
  
  it('shows validation errors for invalid input', async () => {
    render(
      <AuthProvider>
        <LoginForm />
      </AuthProvider>
    );
    
    const submitButton = screen.getByRole('button', { name: /login/i });
    fireEvent.click(submitButton);
    
    await waitFor(() => {
      expect(screen.getByText(/email is required/i)).toBeInTheDocument();
      expect(screen.getByText(/password is required/i)).toBeInTheDocument();
    });
  });
  
  it('submits form with valid credentials', async () => {
    const mockLogin = jest.fn();
    
    render(
      <AuthProvider value={{ login: mockLogin }}>
        <LoginForm />
      </AuthProvider>
    );
    
    fireEvent.change(screen.getByLabelText(/email/i), {
      target: { value: 'test@example.com' }
    });
    fireEvent.change(screen.getByLabelText(/password/i), {
      target: { value: 'SecurePass123' }
    });
    
    fireEvent.click(screen.getByRole('button', { name: /login/i }));
    
    await waitFor(() => {
      expect(mockLogin).toHaveBeenCalledWith('test@example.com', 'SecurePass123');
    });
  });
});
```

### Integration Tests

**API Integration Tests**
```python
# tests/integration/test_recommendations_flow.py
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

@pytest.fixture
def authenticated_user():
    """Create and authenticate a test user"""
    # Register
    response = client.post("/api/v1/auth/register", json={
        "email": "test@example.com",
        "password": "SecurePass123",
        "name": "Test User"
    })
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

def test_full_recommendation_flow(authenticated_user):
    """Test complete recommendation flow"""
    # Submit ratings
    for movie_id in [1, 2, 3, 4, 5]:
        response = client.post(
            "/api/v1/ratings",
            json={"movie_id": movie_id, "rating": 4.5},
            headers=authenticated_user
        )
        assert response.status_code == 201
    
    # Get recommendations
    response = client.get(
        "/api/v1/recommendations",
        headers=authenticated_user
    )
    assert response.status_code == 200
    data = response.json()
    assert "recommendations" in data
    assert len(data["recommendations"]) > 0
    
    # Verify recommendation structure
    rec = data["recommendations"][0]
    assert "movie_id" in rec
    assert "title" in rec
    assert "predicted_rating" in rec
    assert 0.5 <= rec["predicted_rating"] <= 5.0
```

### End-to-End Tests

**Playwright E2E Tests**
```typescript
// tests/e2e/recommendation-flow.spec.ts
import { test, expect } from '@playwright/test';

test.describe('Recommendation Flow', () => {
  test('user can register, login, and get recommendations', async ({ page }) => {
    // Navigate to app
    await page.goto('http://localhost:3000');
    
    // Register
    await page.click('text=Register');
    await page.fill('input[name="email"]', 'test@example.com');
    await page.fill('input[name="password"]', 'SecurePass123');
    await page.fill('input[name="name"]', 'Test User');
    await page.click('button:has-text("Register")');
    
    // Wait for redirect to home
    await expect(page).toHaveURL('http://localhost:3000/');
    
    // Rate some movies
    await page.click('text=Search Movies');
    await page.fill('input[placeholder="Search..."]', 'Toy Story');
    await page.click('button:has-text("Search")');
    
    // Click on first movie and rate it
    await page.click('.movie-card:first-child');
    await page.click('[aria-label="4 stars"]');
    await page.click('button:has-text("Submit Rating")');
    
    // Get recommendations
    await page.click('text=Recommendations');
    await expect(page).toHaveURL('http://localhost:3000/recommendations');
    
    // Verify recommendations are displayed
    await expect(page.locator('.recommendation-card')).toHaveCount(10);
  });
});
```

### Performance Tests

**Load Testing with Locust**
```python
# tests/performance/locustfile.py
from locust import HttpUser, task, between

class MovieLensUser(HttpUser):
    wait_time = between(1, 3)
    
    def on_start(self):
        """Login before starting tasks"""
        response = self.client.post("/api/v1/auth/login", json={
            "email": "test@example.com",
            "password": "SecurePass123"
        })
        self.token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    @task(3)
    def search_movies(self):
        """Search for movies"""
        self.client.get(
            "/api/v1/movies/search?q=star&limit=20",
            headers=self.headers
        )
    
    @task(2)
    def get_recommendations(self):
        """Get recommendations"""
        self.client.get(
            "/api/v1/recommendations?limit=10",
            headers=self.headers
        )
    
    @task(1)
    def submit_rating(self):
        """Submit a rating"""
        self.client.post(
            "/api/v1/ratings",
            json={"movie_id": 1, "rating": 4.5},
            headers=self.headers
        )
```

**Run Load Test**
```bash
# Test with 100 concurrent users
locust -f tests/performance/locustfile.py \
  --host http://localhost:8000 \
  --users 100 \
  --spawn-rate 10 \
  --run-time 5m
```


## Cost Optimization

### Cost Breakdown by Approach

#### AWS-Native Stack (Estimated Monthly Costs)

**Low Traffic (< 10K requests/day)**
```
CloudFront: $1-5
S3 Storage (10 GB): $0.23
API Gateway (300K requests): $1.05
Lambda (300K invocations): $0.20
DynamoDB (on-demand, light usage): $1-3
Cognito (< 50K MAU): FREE
CloudWatch Logs: $1-2
---
TOTAL: ~$5-15/month
```

**Medium Traffic (100K requests/day)**
```
CloudFront: $10-20
S3 Storage (50 GB): $1.15
API Gateway (3M requests): $10.50
Lambda (3M invocations): $2.00
DynamoDB (on-demand): $10-20
Cognito (< 50K MAU): FREE
CloudWatch Logs: $5-10
---
TOTAL: ~$40-65/month
```

**High Traffic (1M requests/day)**
```
CloudFront: $50-100
S3 Storage (200 GB): $4.60
API Gateway (30M requests): $105
Lambda (30M invocations): $20
DynamoDB (on-demand): $50-100
Cognito (> 50K MAU): $10-50
CloudWatch Logs: $20-30
---
TOTAL: ~$260-405/month
```

#### Modern Stack (Estimated Monthly Costs)

**Low Traffic (Development)**
```
EC2 t3.small (backend): $15
RDS db.t3.micro: $12
ElastiCache cache.t3.micro: $12
S3 + CloudFront (frontend): $2
ALB: $16
---
TOTAL: ~$57/month
```

**Medium Traffic (Production)**
```
EC2 t3.medium x2 (backend): $60
RDS db.t3.small (Multi-AZ): $50
ElastiCache cache.t3.small: $25
S3 + CloudFront: $10
ALB: $16
---
TOTAL: ~$161/month
```

**High Traffic (Scaled Production)**
```
ECS Fargate (4 tasks, 1 vCPU, 2GB): $120
RDS db.t3.medium (Multi-AZ): $100
ElastiCache cache.t3.medium: $50
S3 + CloudFront: $30
ALB: $16
---
TOTAL: ~$316/month
```

### Cost Optimization Strategies

**1. Use Caching Aggressively**
```python
# Cache recommendations for 5 minutes
@cache(ttl=300)
def get_recommendations(user_id: str, limit: int):
    """Get cached recommendations"""
    return fetch_from_sagemaker(user_id, limit)

# Cache movie search results
@cache(ttl=600)
def search_movies(query: str, filters: dict):
    """Get cached search results"""
    return query_database(query, filters)
```

**2. Implement Request Batching**
```python
# Batch SageMaker requests
async def get_batch_recommendations(user_ids: List[str]):
    """Get recommendations for multiple users in one call"""
    payload = {
        'user_ids': user_ids,
        'top_k': 10
    }
    response = await sagemaker_runtime.invoke_endpoint_async(
        EndpointName=ENDPOINT_NAME,
        ContentType='application/json',
        Body=json.dumps(payload)
    )
    return response
```

**3. Use CloudFront Caching**
```python
# Set cache headers for static content
@app.get("/api/v1/movies/{movie_id}")
async def get_movie(movie_id: int):
    """Get movie details with caching"""
    movie = get_movie_from_db(movie_id)
    
    return Response(
        content=json.dumps(movie),
        media_type="application/json",
        headers={
            "Cache-Control": "public, max-age=3600",  # 1 hour
            "ETag": f'"{movie_id}-{movie.updated_at}"'
        }
    )
```

**4. Optimize Database Queries**
```python
# Use database connection pooling
from sqlalchemy.pool import QueuePool

engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True
)

# Use query optimization
@app.get("/api/v1/ratings")
async def get_ratings(user_id: str, db: Session = Depends(get_db)):
    """Get ratings with optimized query"""
    # Use select_related to avoid N+1 queries
    ratings = db.query(Rating).options(
        joinedload(Rating.movie)
    ).filter(
        Rating.user_id == user_id
    ).order_by(
        Rating.created_at.desc()
    ).limit(100).all()
    
    return ratings
```

**5. Use Serverless for Low Traffic**
```python
# For low traffic, use Lambda instead of always-on EC2
# AWS-native approach is more cost-effective for < 100K requests/day

# For medium-high traffic, use containers
# Modern stack with ECS/EKS is more cost-effective for > 100K requests/day
```

**6. Set Up Auto-scaling**
```yaml
# ECS auto-scaling configuration
AutoScalingTarget:
  Type: AWS::ApplicationAutoScaling::ScalableTarget
  Properties:
    MaxCapacity: 10
    MinCapacity: 2
    ResourceId: !Sub service/${ClusterName}/${ServiceName}
    ScalableDimension: ecs:service:DesiredCount
    ServiceNamespace: ecs

AutoScalingPolicy:
  Type: AWS::ApplicationAutoScaling::ScalingPolicy
  Properties:
    PolicyName: cpu-scaling
    PolicyType: TargetTrackingScaling
    ScalingTargetId: !Ref AutoScalingTarget
    TargetTrackingScalingPolicyConfiguration:
      TargetValue: 70.0
      PredefinedMetricSpecification:
        PredefinedMetricType: ECSServiceAverageCPUUtilization
```

**7. Monitor and Optimize Costs**
```python
# Script to analyze costs
import boto3
from datetime import datetime, timedelta

ce = boto3.client('ce')

def get_cost_breakdown():
    """Get cost breakdown by service"""
    response = ce.get_cost_and_usage(
        TimePeriod={
            'Start': (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'),
            'End': datetime.now().strftime('%Y-%m-%d')
        },
        Granularity='MONTHLY',
        Metrics=['UnblendedCost'],
        GroupBy=[
            {'Type': 'DIMENSION', 'Key': 'SERVICE'}
        ]
    )
    
    for result in response['ResultsByTime']:
        print(f"\nCosts for {result['TimePeriod']['Start']}:")
        for group in result['Groups']:
            service = group['Keys'][0]
            cost = float(group['Metrics']['UnblendedCost']['Amount'])
            if cost > 0:
                print(f"  {service}: ${cost:.2f}")
```

### Cost Comparison Summary

| Traffic Level | AWS-Native | Modern Stack | Recommendation |
|--------------|------------|--------------|----------------|
| Development | $5-15/mo | $57/mo | AWS-Native |
| Low (< 10K req/day) | $5-15/mo | $57/mo | AWS-Native |
| Medium (100K req/day) | $40-65/mo | $161/mo | AWS-Native |
| High (1M req/day) | $260-405/mo | $316/mo | Modern Stack |
| Very High (> 5M req/day) | $1000+/mo | $500-800/mo | Modern Stack |

**Key Takeaway:** AWS-Native is more cost-effective for low-medium traffic. Modern Stack becomes more cost-effective at high scale due to predictable container costs vs. per-request Lambda/API Gateway pricing.


## Decision Matrix: Which Approach to Choose?

### AWS-Native (API Gateway + Lambda + S3)

**Choose this if:**
- ✅ You want serverless, pay-per-use pricing
- ✅ Traffic is unpredictable or low-medium volume
- ✅ You want minimal operational overhead
- ✅ You prefer AWS-managed services
- ✅ You want automatic scaling without configuration
- ✅ Development/learning project with budget constraints

**Avoid this if:**
- ❌ You need sub-100ms latency (Lambda cold starts)
- ❌ You have very high traffic (> 1M requests/day)
- ✅ You want to avoid vendor lock-in
- ❌ You need complex backend logic (Lambda 15min timeout)

### Modern Stack (FastAPI + React + Docker)

**Choose this if:**
- ✅ You want full control over the stack
- ✅ Traffic is consistent and high volume
- ✅ You need predictable costs
- ✅ You want to avoid vendor lock-in
- ✅ You need complex backend processing
- ✅ You want to deploy anywhere (AWS, GCP, Azure, on-prem)
- ✅ You're building a production SaaS product

**Avoid this if:**
- ❌ You want minimal operational overhead
- ❌ Traffic is very low or unpredictable
- ❌ You don't want to manage containers/databases
- ❌ You're building a quick prototype

### Hybrid Approach (Recommended for Production)

**Best of both worlds:**
- Frontend: React on S3 + CloudFront (static, cheap, fast)
- API: FastAPI on ECS Fargate (flexible, scalable)
- Auth: Cognito (managed, secure)
- Database: RDS PostgreSQL (reliable, managed)
- Cache: ElastiCache Redis (fast, managed)
- ML Inference: Existing SageMaker endpoint

**Benefits:**
- Leverage AWS managed services where it makes sense
- Keep flexibility with containerized backend
- Optimize costs with static frontend hosting
- Easy to migrate backend to other clouds if needed

## Next Steps

### Phase 1: MVP (2-3 weeks)
1. Set up basic authentication (Cognito or JWT)
2. Create simple React frontend with login/search
3. Implement recommendation endpoint
4. Deploy to development environment
5. Basic testing and validation

### Phase 2: Production Ready (2-3 weeks)
1. Add rate limiting and security hardening
2. Implement caching layer
3. Set up monitoring and alerting
4. Add comprehensive error handling
5. Performance testing and optimization
6. Deploy to production

### Phase 3: Enhancements (Ongoing)
1. Add user profile features
2. Implement rating history and analytics
3. Add social features (share recommendations)
4. Mobile app development
5. Advanced recommendation features
6. A/B testing framework

## Conclusion

This design document provides two complete approaches for building a web UI for the MovieLens recommendation system. Both approaches are production-ready and can scale to handle significant traffic.

**For learning and skill development:** Start with the AWS-Native approach to learn serverless architecture, then build the Modern Stack to learn containerization and modern web development.

**For production deployment:** Use the Hybrid approach to get the best of both worlds - managed services where appropriate, with flexibility where needed.

The key is to start simple, validate with users, and iterate based on actual usage patterns and requirements.
