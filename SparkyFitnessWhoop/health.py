"""
Health and wellness data routes
"""

import logging
from fastapi import APIRouter, HTTPException
from datetime import datetime

from models.schemas import HealthAndWellnessRequest, HealthAndWellnessResponse
from services.whoop_client import WhoopClient
from services.data_transformer import transform_whoop_cycles_to_health_data
from config import settings
from routes.auth import get_user_token

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/health_and_wellness", response_model=HealthAndWellnessResponse)
async def get_health_and_wellness(request_data: HealthAndWellnessRequest):
    """
    Retrieve comprehensive health and wellness data from Whoop
    
    Fetches and transforms Whoop's core metrics:
    - Strain (training load): 0-21 scale
    - Recovery (readiness): 0-100 scale
    - Sleep: duration, quality, HRV
    - Heart Rate: resting, average, max
    - HRV: heart rate variability metrics
    
    Args:
        request_data: HealthAndWellnessRequest with user_id, tokens, date range
    
    Returns:
        HealthAndWellnessResponse with transformed data
    
    Raises:
        HTTPException: If data fetch or transformation fails
    """
    user_id = request_data.user_id
    access_token = request_data.tokens
    start_date = request_data.start_date
    end_date = request_data.end_date
    
    try:
        # Validate inputs
        if not all([user_id, access_token, start_date, end_date]):
            raise HTTPException(
                status_code=400,
                detail="Missing required fields: user_id, tokens, start_date, end_date"
            )
        
        # Validate date format
        try:
            datetime.strptime(start_date, "%Y-%m-%d")
            datetime.strptime(end_date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid date format. Use YYYY-MM-DD"
            )
        
        logger.info(f"Fetching health data for user {user_id} from {start_date} to {end_date}")
        
        # Initialize Whoop client
        whoop = WhoopClient(
            access_token=access_token,
            base_url=settings.WHOOP_API_BASE,
            timeout=settings.REQUEST_TIMEOUT
        )
        
        # Fetch cycles (contains all metrics)
        logger.info("Fetching Whoop cycles")
        cycles_response = whoop.get_cycles(start_date, end_date)
        cycles = cycles_response.get("records", [])
        
        if not cycles:
            logger.warning(f"No cycles found for date range {start_date} to {end_date}")
        else:
            logger.info(f"Retrieved {len(cycles)} cycles")
        
        # Transform to SparkyFitness format
        logger.info("Transforming data to SparkyFitness format")
        health_data = transform_whoop_cycles_to_health_data(cycles, start_date, end_date)
        
        # Log summary
        logger.info("=" * 50)
        logger.info(f"HEALTH DATA SYNC SUMMARY")
        logger.info(f"User: {user_id}")
        logger.info(f"Date Range: {start_date} to {end_date}")
        logger.info(f"Total Cycles: {len(cycles)}")
        logger.info("Metrics collected:")
        for metric_name, entries in health_data.items():
            entry_count = len(entries) if isinstance(entries, list) else 1
            logger.info(f"  - {metric_name}: {entry_count} entries")
        logger.info("=" * 50)
        
        return HealthAndWellnessResponse(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            source="whoop",
            data=health_data
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error fetching health data: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch health and wellness data: {str(e)}"
        )


@router.get("/health_and_wellness/schema")
async def get_health_schema():
    """
    Get schema documentation for health_and_wellness response
    
    Returns:
        JSON describing the structure of health data
    """
    return {
        "strain": {
            "description": "Whoop Strain (0-21) - daily training load",
            "fields": ["date", "value", "kilojoules", "average_heart_rate", "max_heart_rate"]
        },
        "recovery": {
            "description": "Whoop Recovery (0-100) - readiness for activity",
            "fields": ["date", "recovery_score", "training_readiness_score", "rhr_delta", "hrv_delta"]
        },
        "sleep": {
            "description": "Sleep metrics - duration, quality, physiological data",
            "fields": ["entry_date", "bedtime", "wake_time", "duration_in_seconds", "sleep_score", "average_spo2_value"]
        },
        "hrv": {
            "description": "Heart Rate Variability - measured during sleep",
            "fields": ["date", "average_overnight_hrv", "lowest_hrv", "highest_hrv", "hrv_status"]
        },
        "resting_heart_rate": {
            "description": "Resting, average, and max heart rate",
            "fields": ["date", "resting_heart_rate", "average_heart_rate", "max_heart_rate"]
        },
        "stress": {
            "description": "Stress level derived from recovery score (inverse relationship)",
            "fields": ["date", "stress_level", "derived_mood_value", "derived_mood_category"]
        },
        "body_battery": {
            "description": "Estimated energy level based on recovery score",
            "fields": ["date", "body_battery_current", "body_battery_highest", "body_battery_lowest"]
        },
        "intensity_minutes": {
            "description": "Estimated intensity minutes derived from strain score",
            "fields": ["date", "total_intensity_minutes"]
        }
    }