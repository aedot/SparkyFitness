"""
Pydantic models for request/response validation
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import date


class HealthAndWellnessRequest(BaseModel):
    """Request model for health and wellness data"""
    user_id: str = Field(..., description="SparkyFitness user ID")
    tokens: str = Field(..., description="Whoop access token")
    start_date: str = Field(..., description="Start date (YYYY-MM-DD)")
    end_date: str = Field(..., description="End date (YYYY-MM-DD)")
    metric_types: List[str] = Field(default_factory=list, description="Specific metrics to fetch (empty = all)")
    
    class Config:
        schema_extra = {
            "example": {
                "user_id": "sparky_user_123",
                "tokens": "whoop_access_token_here",
                "start_date": "2024-01-01",
                "end_date": "2024-01-07",
                "metric_types": ["recovery", "sleep", "hrv"]
            }
        }


class ActivitiesRequest(BaseModel):
    """Request model for activities and workouts"""
    user_id: str = Field(..., description="SparkyFitness user ID")
    tokens: str = Field(..., description="Whoop access token")
    start_date: str = Field(..., description="Start date (YYYY-MM-DD)")
    end_date: str = Field(..., description="End date (YYYY-MM-DD)")
    
    class Config:
        schema_extra = {
            "example": {
                "user_id": "sparky_user_123",
                "tokens": "whoop_access_token_here",
                "start_date": "2024-01-01",
                "end_date": "2024-01-07"
            }
        }


class StrainMetric(BaseModel):
    date: str
    value: float
    percent_recorded: Optional[float] = None
    kilojoules: Optional[float] = None
    average_heart_rate: Optional[float] = None
    max_heart_rate: Optional[float] = None


class RecoveryMetric(BaseModel):
    date: str
    recovery_score: float
    training_readiness_score: Optional[float] = None
    rhr_delta: Optional[float] = None
    hrv_delta: Optional[float] = None


class SleepMetric(BaseModel):
    entry_date: str
    bedtime: str
    wake_time: str
    duration_in_seconds: int
    sleep_score: Optional[float] = None
    average_spo2_value: Optional[float] = None


class HRVMetric(BaseModel):
    date: str
    average_overnight_hrv: Optional[float] = None
    lowest_hrv: Optional[float] = None
    highest_hrv: Optional[float] = None
    hrv_status: Optional[str] = None


class HealthAndWellnessResponse(BaseModel):
    """Response model for health and wellness data"""
    user_id: str
    start_date: str
    end_date: str
    source: str = "whoop"
    data: dict
    
    class Config:
        schema_extra = {
            "example": {
                "user_id": "sparky_user_123",
                "start_date": "2024-01-01",
                "end_date": "2024-01-07",
                "source": "whoop",
                "data": {
                    "recovery": [
                        {
                            "date": "2024-01-01",
                            "recovery_score": 85,
                            "training_readiness_score": 85
                        }
                    ],
                    "sleep": [
                        {
                            "entry_date": "2024-01-01",
                            "bedtime": "2024-01-01T22:30:00Z",
                            "wake_time": "2024-01-02T07:00:00Z",
                            "duration_in_seconds": 28800
                        }
                    ]
                }
            }
        }


class ActivityData(BaseModel):
    id: Optional[str] = None
    date: str
    activityName: str
    activityType: Optional[str] = None
    strainScore: Optional[float] = None
    calories: Optional[float] = None


class ActivitiesResponse(BaseModel):
    """Response model for activities and workouts"""
    user_id: str
    start_date: str
    end_date: str
    source: str = "whoop"
    activities: List[ActivityData]
    workouts: List[dict] = Field(default_factory=list)
    note: Optional[str] = None
    
    class Config:
        schema_extra = {
            "example": {
                "user_id": "sparky_user_123",
                "start_date": "2024-01-01",
                "end_date": "2024-01-07",
                "source": "whoop",
                "activities": [
                    {
                        "date": "2024-01-01",
                        "activityName": "Workout",
                        "strainScore": 15.5,
                        "calories": 750
                    }
                ],
                "workouts": [],
                "note": "Whoop provides limited activity details"
            }
        }