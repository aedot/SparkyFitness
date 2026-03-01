# Whoop Microservice - Quick Start Guide

## Prerequisites

- Python 3.9+
- pip or poetry
- Whoop API credentials (see below)
- Git (optional)

## Step 1: Get Whoop API Credentials

1. Go to https://developer.whoop.com/
2. Create a developer account
3. Create a new application
4. You'll receive:
   - **Client ID**: Store this
   - **Client Secret**: Store this (keep private!)
   - **Redirect URI**: Set to `http://localhost:8000/auth/whoop/callback` for local development

## Step 2: Clone/Create Project Structure

```bash
# The project structure is already created with the following:
whoop-dev/
├── main.py                 # Entry point
├── config.py              # Configuration management
├── requirements.txt       # Python dependencies
├── .env.example          # Environment variables template
├── routes/               # API route handlers
│   ├── auth.py          # OAuth authentication
│   ├── health.py        # Health & wellness endpoints
│   └── activities.py     # Activities endpoints
├── services/             # Business logic
│   ├── whoop_client.py  # Whoop API client
│   └── data_transformer.py  # Data transformation logic
├── models/              # Pydantic models
│   └── schemas.py       # Request/response schemas
└── tests/               # Unit tests (to be created)
```

## Step 3: Setup Environment

### 3a. Create .env file

```bash
cd whoop-dev
cp .env.example .env
```

### 3b. Edit .env with your credentials

```env
WHOOP_CLIENT_ID=your_client_id_here
WHOOP_CLIENT_SECRET=your_client_secret_here
WHOOP_REDIRECT_URI=http://localhost:8000/auth/whoop/callback
WHOOP_SERVICE_PORT=8000
ENVIRONMENT=development
LOG_LEVEL=DEBUG
```

## Step 4: Install Dependencies

```bash
# Using pip
pip install -r requirements.txt

# OR using poetry
poetry install
```

## Step 5: Run the Application

```bash
python main.py
```

You should see:
```
Starting Whoop microservice on port 8000
INFO:     Uvicorn running on http://0.0.0.0:8000
```

## Step 6: Test the Service

### 6a. Health Check

```bash
curl http://localhost:8000/
```

Response:
```json
{
  "message": "Whoop Microservice is running!",
  "status": "healthy",
  "version": "1.0.0"
}
```

### 6b. Initiate OAuth Login

Open in browser:
```
http://localhost:8000/auth/whoop/login?user_id=test_user_123
```

This redirects to Whoop's login page. Sign in and authorize the app.

After authorization, you'll be redirected to:
```
http://localhost:8000/auth/whoop/callback?code=...&state=test_user_123
```

The response will show your access token:
```json
{
  "status": "success",
  "user_id": "test_user_123",
  "access_token": "whoop_access_token_...",
  "message": "Successfully connected to Whoop!"
}
```

### 6c. Fetch Health Data

```bash
curl -X POST http://localhost:8000/data/health_and_wellness \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_user_123",
    "tokens": "YOUR_ACCESS_TOKEN_HERE",
    "start_date": "2024-01-01",
    "end_date": "2024-01-07"
  }'
```

### 6d. Fetch Activities

```bash
curl -X POST http://localhost:8000/data/activities_and_workouts \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_user_123",
    "tokens": "YOUR_ACCESS_TOKEN_HERE",
    "start_date": "2024-01-01",
    "end_date": "2024-01-07"
  }'
```

### 6e. Check Connection Status

```bash
curl http://localhost:8000/auth/whoop/status/test_user_123
```

## Step 7: Common Development Tasks

### Run with Debug Mode

```bash
# In main.py, uvicorn is already configured for debug with live reload
python main.py
# or
uvicorn main:app --reload --port 8000
```

### View API Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### View Logs

The application outputs comprehensive logs. Check for:
- `[WHOOP_SYNC]` - Data sync operations
- `[ERROR]` - Error conditions
- `[WARNING]` - Warnings (e.g., missing data)

### Test Individual Services

```python
# test_whoop_client.py
from services.whoop_client import WhoopClient

# Test with a real token
client = WhoopClient(access_token="your_token_here")
user = client.get_user()
print(user)
```

## Step 8: Next Steps

1. **Store Tokens Securely**: Replace in-memory `TOKEN_STORE` with database
   - See `routes/auth.py` for where tokens are stored
   - Implement with SQLAlchemy + PostgreSQL or similar

2. **Add Database Models**:
   ```python
   # models/database.py
   from sqlalchemy import Column, String, DateTime
   from sqlalchemy.ext.declarative import declarative_base
   
   Base = declarative_base()
   
   class WhoopToken(Base):
       __tablename__ = "whoop_tokens"
       
       user_id = Column(String, primary_key=True)
       access_token = Column(String, nullable=False)
       refresh_token = Column(String)
       expires_at = Column(DateTime)
       created_at = Column(DateTime)
   ```

3. **Add Unit Tests**:
   ```bash
   # tests/test_auth.py
   from fastapi.testclient import TestClient
   from main import app
   
   client = TestClient(app)
   
   def test_login_redirect():
       response = client.get("/auth/whoop/login?user_id=test")
       assert response.status_code == 307
   ```

4. **Deploy with Docker**:
   ```dockerfile
   FROM python:3.9-slim
   
   WORKDIR /app
   COPY requirements.txt .
   RUN pip install -r requirements.txt
   
   COPY . .
   
   CMD ["python", "main.py"]
   ```

5. **Production Configuration**:
   - Set `ENVIRONMENT=production`
   - Use PostgreSQL instead of SQLite
   - Enable HTTPS/TLS
   - Restrict CORS origins
   - Add rate limiting
   - Set up monitoring/alerting

## Troubleshooting

### Issue: "Missing required settings: WHOOP_CLIENT_ID, WHOOP_CLIENT_SECRET"

**Solution**: Make sure .env file exists and has correct credentials

```bash
cat .env  # Verify credentials are set
```

### Issue: "Connection error to Whoop API"

**Solution**: 
- Check internet connection
- Verify Whoop API is not down: https://status.whoop.com/
- Check if CLIENT_ID and CLIENT_SECRET are correct

### Issue: "Token expired - 401 Unauthorized"

**Solution**: The token refresh logic should handle this automatically, but if not:
- Go through OAuth flow again (`/auth/whoop/login`)
- Or implement explicit token refresh endpoint

### Issue: "No cycles found for date range"

**Solution**:
- Whoop user must have Whoop wearable data for those dates
- Try with recent dates where user has been active
- Check Whoop app to verify user has data

## Architecture Overview

```
User/Client
    ↓
FastAPI Application (main.py)
    ├── Routes (auth, health, activities)
    ├── Services (WhoopClient, DataTransformer)
    ├── Models (Pydantic schemas)
    └── Config (settings management)
    ↓
Whoop API
    ├── OAuth endpoints
    ├── Cycles endpoint (main data source)
    └── User profile
    ↓
SparkyFitness Database
    (stores transformed data)
```

## Key Components

| Component | Purpose |
|-----------|---------|
| `main.py` | FastAPI app initialization, route registration |
| `config.py` | Environment variables and settings |
| `routes/auth.py` | OAuth login/callback, token management |
| `routes/health.py` | Health & wellness data endpoints |
| `routes/activities.py` | Activities and workouts endpoints |
| `services/whoop_client.py` | Whoop API client and OAuth handler |
| `services/data_transformer.py` | Converts Whoop data to SparkyFitness format |
| `models/schemas.py` | Pydantic request/response models |

## Support & Resources

- **Whoop API Docs**: https://developer.whoop.com/api
- **FastAPI Docs**: https://fastapi.tiangolo.com/
- **OAuth 2.0**: https://oauth.net/2/
- **Python Requests**: https://requests.readthedocs.io/

---

**Next Step**: Go to Step 6 and test the API!