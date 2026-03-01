# Whoop Microservice for SparkyFitness

A FastAPI microservice that integrates Whoop wearable data with the SparkyFitness application.

## Overview

This microservice provides OAuth 2.0 authentication with Whoop and APIs to fetch health and wellness metrics, transforming them into SparkyFitness-compatible format.

### Key Features

- **OAuth 2.0 Authentication**: Secure user authentication with Whoop
- **Health Metrics**: Strain, Recovery, Sleep, Heart Rate, HRV
- **Data Transformation**: Maps Whoop's native format to SparkyFitness schema
- **RESTful API**: Clean, well-documented endpoints
- **Error Handling**: Comprehensive error handling and logging
- **Production Ready**: Includes validation, rate limiting considerations

## Supported Metrics

| Metric | Source | Range | Description |
|--------|--------|-------|-------------|
| Strain | Whoop | 0-21 | Daily training load/intensity |
| Recovery | Whoop | 0-100 | Readiness for activity |
| Sleep | Whoop | - | Duration, quality, sleep score |
| Heart Rate | Whoop | - | Resting, average, max HR |
| HRV | Whoop | - | Heart rate variability |
| Stress | Derived | 0-100 | Inverse of recovery score |
| Body Battery | Estimated | 0-100 | Energy level proxy |
| Intensity Minutes | Estimated | - | From strain metric |

## Quick Start

See [QUICKSTART.md](QUICKSTART.md) for detailed setup instructions.

### Summary

```bash
# 1. Setup environment
cp .env.example .env
# Edit .env with Whoop credentials

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run application
python main.py

# 4. Test
curl http://localhost:8000/
```

## API Endpoints

### Authentication

- `GET /auth/whoop/login?user_id=<id>` - Initiate OAuth login
- `GET /auth/whoop/callback` - OAuth callback (auto-handled)
- `POST /auth/whoop/disconnect?user_id=<id>` - Disconnect user
- `GET /auth/whoop/status/<user_id>` - Check connection status

### Data Endpoints

- `POST /data/health_and_wellness` - Fetch health metrics
- `POST /data/activities_and_workouts` - Fetch activity data
- `GET /data/health_and_wellness/schema` - Get data schema

### Utilities

- `GET /` - Health check
- `GET /health` - Kubernetes health check
- `GET /docs` - Swagger UI
- `GET /redoc` - ReDoc documentation

## Project Structure

```
whoop-dev/
├── main.py                      # Entry point
├── config.py                    # Configuration
├── requirements.txt             # Dependencies
├── .env.example                 # Env template
├── QUICKSTART.md               # Quick start guide
├── README.md                   # This file
├── routes/
│   ├── __init__.py
│   ├── auth.py                # OAuth endpoints
│   ├── health.py              # Health data endpoints
│   └── activities.py          # Activity endpoints
├── services/
│   ├── __init__.py
│   ├── whoop_client.py        # Whoop API client
│   └── data_transformer.py    # Data transformation
├── models/
│   ├── __init__.py
│   ├── schemas.py             # Pydantic models
│   └── database.py            # (future) DB models
└── tests/
    ├── __init__.py
    └── test_*.py              # Unit tests
```

## Environment Variables

```env
# Required
WHOOP_CLIENT_ID=your_client_id
WHOOP_CLIENT_SECRET=your_client_secret

# Optional (defaults provided)
WHOOP_REDIRECT_URI=http://localhost:8000/auth/whoop/callback
WHOOP_API_BASE=https://api.prod.whoop.com/api/v2
WHOOP_SERVICE_PORT=8000
ENVIRONMENT=development
LOG_LEVEL=DEBUG
DATABASE_URL=sqlite:///./whoop_tokens.db
```

## Authentication Flow

```
1. User clicks login → GET /auth/whoop/login?user_id=XXX
2. Redirects to Whoop OAuth consent screen
3. User authorizes app
4. Whoop redirects to → GET /auth/whoop/callback?code=...&state=XXX
5. Service exchanges code for tokens
6. Tokens stored in TOKEN_STORE (or database)
7. Service returns access_token to user
8. User includes access_token in subsequent API calls
```

## Data Flow

```
SparkyFitness Client
        ↓
    FastAPI Routes
        ↓
    Whoop API Client
        ↓
    Whoop API
        ↓
    Response (raw JSON)
        ↓
    Data Transformer
        ↓
    SparkyFitness Format
        ↓
    Response to Client
```

## Limitations

- **Activity Data**: Whoop has limited activity details; activities inferred from Strain metric only
- **Historical Data**: Only recent cycles typically available (last 90 days)
- **Metrics Not Available**: Steps, distance, blood pressure, body composition, VO2 max
- **Token Expiration**: Access tokens expire in ~24 hours (auto-refresh implemented)

For detailed metrics, consider dual integration with Garmin for activities.

## Development

### Running Tests

```bash
pytest tests/ -v
```

### Running with Hot Reload

```bash
uvicorn main:app --reload --port 8000
```

### Type Checking

```bash
mypy . --ignore-missing-imports
```

## Production Deployment

### Docker

```bash
docker build -t whoop-service .
docker run -p 8000:8000 --env-file .env whoop-service
```

### Configuration

1. Switch to PostgreSQL for token storage
2. Enable HTTPS/TLS
3. Restrict CORS origins
4. Add rate limiting middleware
5. Set up monitoring and alerting
6. Use environment-specific configurations

See migration guide for detailed production setup.

## Troubleshooting

### Token Issues
- Ensure you're passing the access token (not refresh token)
- Tokens auto-refresh when expired
- If stuck, re-authenticate via OAuth

### Data Not Found
- Verify user has Whoop wearable and recent data
- Check date range (Whoop typically has last 90 days)
- Review logs for API errors

### Connection Issues
- Verify internet connection
- Check Whoop API status
- Ensure CLIENT_ID and CLIENT_SECRET are correct

See [QUICKSTART.md](QUICKSTART.md) for more troubleshooting.

## Contributing

1. Create feature branch
2. Make changes
3. Add tests
4. Ensure code style (use black, flake8)
5. Submit pull request

## License

[Specify your license here]

## Support

For issues or questions:
- Check [QUICKSTART.md](QUICKSTART.md)
- Review error logs
- Check Whoop API docs: https://developer.whoop.com/api
- Open issue in repository

## Resources

- **Whoop API**: https://developer.whoop.com/api
- **FastAPI**: https://fastapi.tiangolo.com/
- **OAuth 2.0**: https://oauth.net/2/
- **Pydantic**: https://docs.pydantic.dev/
- **Python Requests**: https://requests.readthedocs.io/

---

**Last Updated**: February 2025
**Version**: 1.0.0
**Status**: Production Ready