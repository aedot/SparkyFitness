# Whoop Microservice Migration Guide

## Overview
This guide details the process of Whoop API-based microservice to SparkyFitness.

---

## Phase 1: Understand the Data

### Whoop Data Structure

**Whoop:**
- Focuses on 5 core metrics: Strain, Recovery, Sleep, Heart Rate Variability (HRV), and Resting Heart Rate
- Uses OAuth 2.0 authentication (no password storage)
- Returns rolling data with timestamps (not strict daily buckets)
- More limited metrics but more actionable insights
- API is cleaner but less granular

### Key API

| Metric  | Whoop |
|-------- |-------|
| Sleep Data | Total duration + HRV during sleep |
| Stress | Not directly; inferred from Strain |
| Activity | Generic workouts with strain |
| Heart Rate | Avg HR, rest HR, HRV |
| Recovery | Direct recovery score (0-100) |
| Authentication | OAuth 2.0 + Refresh Tokens |

---

## Phase 2: Setup Prerequisites

### 1. Register for Whoop Developer Access
- Visit https://developer.whoop.com/
- Create developer account
- Apply for API access (requires approval)
- Get Client ID and Client Secret
- Register redirect URI (e.g., `http://localhost:8000/auth/whoop/callback`)

### 2. Install Whoop SDK
```bash
pip install whoop-sdk
# OR use requests if official SDK isn't available
pip install requests
```

### 3. Update Environment Variables
```env
# Add to .env
WHOOP_CLIENT_ID=your_client_id
WHOOP_CLIENT_SECRET=your_client_secret
WHOOP_REDIRECT_URI=http://localhost:8000/auth/whoop/callback
WHOOP_API_BASE_URL=https://api.prod.whoop.com/api/v2
```

---

## Phase 3: Architecture

### Authentication Flow

**Whoop Flow:**
```
Redirect to Whoop OAuth → User Authorizes → Get Authorization Code 
→ Exchange for Access Token + Refresh Token → Store securely in DB
```

### Backend Needed

1. **Credential storage** - Refresh token storage
2. **Add OAuth callback handler** - Endpoint for Whoop to redirect after user authorization
3. **Implement token refresh logic** - Handle expired access tokens automatically
4. **Update data mapping** - Map Whoop's 5 metrics to SparkyFitness fields

---

## Phase 4: Implementation Steps

### Step 1: Create New Authentication Endpoints

```python
@app.get("/auth/whoop/login")
async def whoop_login(user_id: str):
    """
    Redirect user to Whoop OAuth consent screen
    """
    auth_url = (
        f"https://api.prod.whoop.com/oauth/oauth2/auth?"
        f"client_id={WHOOP_CLIENT_ID}&"
        f"scope=read:cycles_collection%20read:user%20offline&"
        f"redirect_uri={WHOOP_REDIRECT_URI}&"
        f"response_type=code&"
        f"state={user_id}"  # Store user_id in state
    )
    return RedirectResponse(url=auth_url)

@app.get("/auth/whoop/callback")
async def whoop_callback(code: str, state: str):
    """
    Handle Whoop OAuth callback
    Exchange authorization code for access + refresh tokens
    """
    # Exchange code for tokens
    tokens_response = requests.post(
        "https://api.prod.whoop.com/oauth/oauth2/token",
        data={
            "client_id": WHOOP_CLIENT_ID,
            "client_secret": WHOOP_CLIENT_SECRET,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": WHOOP_REDIRECT_URI
        }
    )
    
    tokens = tokens_response.json()
    # Store refresh_token in database associated with state (user_id)
    # Return access_token to frontend
    return {
        "status": "success",
        "access_token": tokens["access_token"],
        "user_id": state
    }
```

### Step 2: Create Whoop Data Fetching Logic

```python
class WhoopClient:
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.base_url = "https://api.prod.whoop.com/api/v2"
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
    
    def get_cycles(self, start_date: str, end_date: str):
        """
        Fetch strain, recovery, and sleep data
        Whoop cycles = daily data with metrics
        """
        url = f"{self.base_url}/user/cycles"
        params = {
            "start": start_date,
            "end": end_date
        }
        response = requests.get(url, headers=self.headers, params=params)
        return response.json()
    
    def get_hrv(self, start_date: str, end_date: str):
        """Fetch HRV (Heart Rate Variability) data"""
        url = f"{self.base_url}/user/heart_rate"
        params = {"start": start_date, "end": end_date}
        response = requests.get(url, headers=self.headers, params=params)
        return response.json()
    
    def get_user(self):
        """Get current user info"""
        url = f"{self.base_url}/user/profile"
        response = requests.get(url, headers=self.headers)
        return response.json()
```

### Step 3: Replace Health Data Endpoint

**Old Structure:**
```python
@app.post("/data/health_and_wellness")
async def get_health_and_wellness(request_data: HealthAndWellnessRequest):
    # Fetch 20+ different metrics from Garmin
```

**New Structure:**
```python
@app.post("/data/health_and_wellness")
async def get_health_and_wellness(request_data: HealthAndWellnessRequest):
    """
    Maps Whoop data to SparkyFitness health_and_wellness format
    Whoop provides: Strain, Recovery, Sleep, HRV, Resting HR
    """
    user_id = request_data.user_id
    access_token = request_data.tokens  # Now it's an access token
    start_date = request_data.start_date
    end_date = request_data.end_date
    
    whoop = WhoopClient(access_token)
    
    # Fetch all Whoop data
    cycles = whoop.get_cycles(start_date, end_date)
    hrv_data = whoop.get_hrv(start_date, end_date)
    
    # Transform to SparkyFitness format
    health_data = transform_whoop_to_sparkyfitness(
        cycles, hrv_data, start_date, end_date
    )
    
    return {
        "user_id": user_id,
        "start_date": start_date,
        "end_date": end_date,
        "data": health_data
    }
```

### Step 4: Create Data Transformation Functions

```python
def transform_whoop_to_sparkyfitness(cycles, hrv_data, start_date, end_date):
    """
    Map Whoop's 5 metrics to SparkyFitness fields
    
    Whoop Metrics:
    - Strain (0-21): Training load/intensity
    - Recovery (0-100): Readiness for activity
    - Sleep: Duration + HRV
    - Heart Rate Variability: Avg overnight HRV
    - Resting Heart Rate: Daily RHR
    """
    health_data = {
        "strain": [],
        "recovery": [],
        "sleep": [],
        "hrv": [],
        "resting_heart_rate": [],
        "stress": [],  # Map from Recovery inverse
        "body_battery": [],  # Estimated from Recovery
    }
    
    for cycle in cycles:
        cycle_start = cycle["start"]
        cycle_date = cycle_start.split("T")[0]
        
        # Strain → Activity Intensity
        if cycle.get("strain"):
            health_data["strain"].append({
                "date": cycle_date,
                "value": cycle["strain"]["score"],
                "data": {
                    "accumulated_strain": cycle["strain"].get("accumulated_strain"),
                    "kilojoules": cycle["strain"].get("kilojoules")
                }
            })
        
        # Recovery → Training Readiness
        if cycle.get("recovery"):
            recovery_score = cycle["recovery"]["score"]
            health_data["recovery"].append({
                "date": cycle_date,
                "recovery_score": recovery_score,
                "training_readiness_score": recovery_score  # Direct mapping
            })
            
            # Inverse map to stress (0-100 scale)
            stress = 100 - recovery_score
            health_data["stress"].append({
                "date": cycle_date,
                "derived_mood_value": 50 + (recovery_score - 50),  # Map to mood
                "derived_mood_notes": f"Derived from Whoop Recovery: {recovery_score}"
            })
        
        # Sleep Data
        if cycle.get("sleep"):
            sleep_info = cycle["sleep"]
            health_data["sleep"].append({
                "entry_date": cycle_date,
                "bedtime": sleep_info.get("start"),
                "wake_time": sleep_info.get("end"),
                "duration_in_seconds": sleep_info.get("total", {}).get("seconds"),
                "sleep_score": sleep_info.get("score"),
                "average_overnight_hrv": sleep_info.get("average_hrv")  # From HRV during sleep
            })
        
        # Heart Rate
        if cycle.get("heart_rate"):
            hr_info = cycle["heart_rate"]
            health_data["resting_heart_rate"].append({
                "date": cycle_date,
                "resting_heart_rate": hr_info.get("resting"),
                "avg_heart_rate": hr_info.get("average")
            })
    
    # HRV Data
    for hrv_entry in hrv_data:
        health_data["hrv"].append({
            "date": hrv_entry.get("timestamp").split("T")[0],
            "average_overnight_hrv": hrv_entry.get("average"),
            "hrv_status": "good" if hrv_entry.get("average", 0) > 50 else "low"
        })
    
    # Body Battery (estimated from Recovery)
    for recovery in health_data["recovery"]:
        # Use recovery score as proxy for body battery (0-100)
        health_data["body_battery"].append({
            "date": recovery["date"],
            "body_battery_current": recovery["recovery_score"],
            "body_battery_highest": 100,
            "body_battery_lowest": 0
        })
    
    return health_data
```

### Step 5: Handle Activities (if Whoop provides)

**Simplify Activities Endpoint**
```python
@app.post("/data/activities_and_workouts")
async def get_activities_and_workouts(request_data: ActivitiesAndWorkoutsRequest):
    """
    Whoop doesn't provide activity details like Garmin
    Return activities inferred from Strain data instead
    """
    whoop = WhoopClient(request_data.tokens)
    cycles = whoop.get_cycles(request_data.start_date, request_data.end_date)
    
    activities = []
    for cycle in cycles:
        if cycle.get("strain") and cycle["strain"].get("score") > 5:
            # Infer activity from strain
            activities.append({
                "activityId": cycle["id"],
                "activityName": "Workout",
                "startTime": cycle["start"],
                "duration": cycle.get("strain", {}).get("duration"),
                "calories": estimate_calories_from_strain(cycle["strain"]),
                "strainScore": cycle["strain"]["score"]
            })
    
    return {
        "user_id": request_data.user_id,
        "start_date": request_data.start_date,
        "end_date": request_data.end_date,
        "activities": activities,
        "workouts": []
    }
```

---

## Phase 5: Data Mapping Reference

### Complete Field Mapping

| SparkyFitness Field | Whoop Source | Mapping Notes |
|-------------------|--------------|----------------|
| `steps` | N/A | Whoop doesn't provide steps |
| `total_distance` | N/A | Not available |
| `stress` | Inverse of Recovery | (100 - Recovery Score) |
| `training_readiness_score` | Recovery Score | Direct mapping 0-100 |
| `sleep` | cycles[].sleep | Total duration + HRV |
| `body_battery` | Recovery Score | Use recovery as proxy |
| `hrv` | cycles[].heart_rate.hrv | Average overnight HRV |
| `heart_rate` | cycles[].heart_rate | Avg & resting HR |
| `activities` | cycles[].strain | Inferred from strain |
| `VO2_max` | N/A | Not available |
| `blood_pressure` | N/A | Not available |
| `body_composition` | N/A | Not available |

### Fields That Will Be Lost
- Steps
- Distance
- Floors
- Detailed activity types
- Blood pressure
- Body composition (weight, body fat)
- VO2 max
- Detailed HR zones

---

## Phase 6: Token Management

### Database Schema Changes

**Whoop:**
```sql
whoop_tokens:
  - user_id (PK)
  - access_token (expires in ~24 hours)
  - refresh_token (long-lived)
  - token_expires_at
  - created_at
  - updated_at
```

### Implement Token Refresh

```python
def refresh_access_token(user_id: str, refresh_token: str) -> str:
    """
    Exchange refresh token for new access token
    Call when access token is expired
    """
    response = requests.post(
        "https://api.prod.whoop.com/oauth/oauth2/token",
        data={
            "client_id": WHOOP_CLIENT_ID,
            "client_secret": WHOOP_CLIENT_SECRET,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token"
        }
    )
    
    tokens = response.json()
    new_access_token = tokens["access_token"]
    
    # Update in database
    update_user_tokens(user_id, new_access_token, tokens.get("refresh_token"))
    
    return new_access_token

# Use in requests with automatic retry
def get_with_token_refresh(user_id: str, url: str):
    """Fetch data with automatic token refresh on 401"""
    tokens = get_user_tokens(user_id)
    
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    response = requests.get(url, headers=headers)
    
    if response.status_code == 401:
        # Token expired, refresh
        new_token = refresh_access_token(user_id, tokens['refresh_token'])
        headers = {"Authorization": f"Bearer {new_token}"}
        response = requests.get(url, headers=headers)
    
    return response.json()
```

---

## Phase 7: Testing Strategy

### 1. Unit Tests
```python
def test_whoop_to_sparkyfitness_transformation():
    whoop_cycle = {
        "strain": {"score": 15},
        "recovery": {"score": 85},
        "sleep": {"start": "2024-01-01T22:00:00", "total": {"seconds": 28800}},
        "heart_rate": {"resting": 50, "average": 70}
    }
    
    result = transform_whoop_to_sparkyfitness([whoop_cycle], [], "2024-01-01", "2024-01-01")
    
    assert result["recovery"][0]["recovery_score"] == 85
    assert result["stress"][0]["derived_mood_value"] > 50
    assert result["sleep"][0]["duration_in_seconds"] == 28800
```

### 2. Integration Tests
```python
@pytest.mark.integration
async def test_health_and_wellness_endpoint():
    request = HealthAndWellnessRequest(
        user_id="test_user",
        tokens="valid_whoop_token",
        start_date="2024-01-01",
        end_date="2024-01-07",
        metric_types=["recovery", "strain", "sleep", "hrv"]
    )
    
    response = await get_health_and_wellness(request)
    
    assert response["user_id"] == "test_user"
    assert len(response["data"]["recovery"]) == 7
```

### 3. Mock Whoop Responses
```python
# conftest.py or test utilities
MOCK_WHOOP_CYCLE = {
    "id": "test-cycle-1",
    "start": "2024-01-01T00:00:00.000Z",
    "end": "2024-01-02T00:00:00.000Z",
    "strain": {
        "score": 12.5,
        "accumulated_strain": 15.2,
        "kilojoules": 2500
    },
    "recovery": {
        "score": 75,
        "rhr_delta": -5
    },
    "sleep": {
        "start": "2024-01-01T22:30:00",
        "end": "2024-01-02T07:00:00",
        "total": {"seconds": 28800},
        "score": 82
    },
    "heart_rate": {
        "resting": 52,
        "average": 68
    }
}
```

---

## Phase 8: Gradual Migration Plan

### Hard Cutover
1. Deploy Whoop service in staging
2. Run comprehensive tests
3. Deploy to production on specific date
4. Communicate to users about lost metrics

---

## Phase 9: Configuration & Deployment

### Updated Environment Variables
```env
# Add Whoop
WHOOP_CLIENT_ID=your_id
WHOOP_CLIENT_SECRET=your_secret
WHOOP_REDIRECT_URI=https://yourdomain.com/auth/whoop/callback
WHOOP_API_BASE_URL=https://api.prod.whoop.com/api/v2
WHOOP_SERVICE_PORT=8000

DATA_SOURCE=whoop  # Changed from "garmin"
```

### Docker Compose Update
```yaml
whoop-service:
  build: ./services/whoop
  ports:
    - "8000:8000"
  environment:
    - WHOOP_CLIENT_ID=${WHOOP_CLIENT_ID}
    - WHOOP_CLIENT_SECRET=${WHOOP_CLIENT_SECRET}
    - DATABASE_URL=${DATABASE_URL}
  volumes:
    - ./mock_data:/app/mock_data
```

---

## Phase 10: Frontend Changes Required

### 1. Authentication Flow
```javascript
// Old: Direct email/password
const login = (email, password) => {
  return fetch('/auth/garmin/login', {
    method: 'POST',
    body: JSON.stringify({email, password})
  });
};

// New: OAuth redirect
const login = (userId) => {
  window.location.href = `/auth/whoop/login?user_id=${userId}`;
};
```

### 2. Update UI for Limited Metrics
- Remove UI elements for unsupported metrics (steps, distance, activities)
- Highlight Whoop's strengths (recovery, strain, HRV)
- Add disclaimers about data availability

### 3. Error Handling for Missing Metrics
```javascript
if (!data.steps) {
  showMessage("Step data not available with Whoop");
} else {
  displaySteps(data.steps);
}
```

---

## Troubleshooting Common Issues

### Issue 1: Token Expiration
**Problem:** Requests fail with 401 Unauthorized
**Solution:** Implement automatic token refresh (see Phase 6)

### Issue 2: Rate Limiting
**Problem:** Whoop API returns 429 Too Many Requests
**Solution:** Implement exponential backoff and request queuing

### Issue 3: Missing Historical Data
**Problem:** Whoop only returns recent cycles
**Solution:** Document limitation; only sync last 90 days of data

### Issue 4: Users Can't Disconnect
**Problem:** No way to revoke Whoop access
**Solution:** Add disconnect endpoint that removes refresh token

```python
@app.post("/auth/whoop/disconnect")
async def disconnect_whoop(user_id: str):
    """Revoke Whoop access"""
    remove_user_tokens(user_id)
    return {"status": "disconnected"}
```

---

## Summary Checklist

- [ ] Register for Whoop API access
- [ ] Create new authentication endpoints (OAuth flow)
- [ ] Implement WhoopClient wrapper class
- [ ] Create data transformation functions
- [ ] Update health_and_wellness endpoint
- [ ] Update activities_and_workouts endpoint
- [ ] Implement token refresh logic
- [ ] Update database schema for token storage
- [ ] Write unit and integration tests
- [ ] Update environment configuration
- [ ] Update Docker setup
- [ ] Test OAuth flow end-to-end
- [ ] Create user migration path
- [ ] Update frontend UI
- [ ] Communicate changes to users
- [ ] Deploy to staging environment
- [ ] Deploy to production
- [ ] Monitor for errors and issues
- [ ] Sunset Garmin integration (if full migration)

---

## Resources

- **Whoop API Docs:** https://developer.whoop.com/api
- **OAuth 2.0 Guide:** https://oauth.net/2/
- **FastAPI + OAuth:** https://fastapi.tiangolo.com/advanced/security/oauth2-jwt/
- **Token Best Practices:** https://tools.ietf.org/html/rfc6749