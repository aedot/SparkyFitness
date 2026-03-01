"""
Activities and workouts data routes
"""

import logging
from fastapi import APIRouter, HTTPException
from datetime import datetime

from models.schemas import ActivitiesRequest, ActivitiesResponse
from services.whoop_client import WhoopClient
from services.data_transformer import transform_whoop_to_activities
from config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/activities_and_workouts", response_model=ActivitiesResponse)
async def get_activities_and_workouts(request_data: ActivitiesRequest):
    """
    Retrieve activities and workouts data from Whoop
    
    Note: Whoop has limited activity details compared to Garmin.
    Activities are inferred from Strain metric (only includes days with significant strain).
    
    Args:
        request_data: ActivitiesRequest with user_id, tokens, date range
    
    Returns:
        ActivitiesResponse with activities and workouts
    
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
        
        logger.info(f"Fetching activities for user {user_id} from {start_date} to {end_date}")
        
        # Initialize Whoop client
        whoop = WhoopClient(
            access_token=access_token,
            base_url=settings.WHOOP_API_BASE,
            timeout=settings.REQUEST_TIMEOUT
        )
        
        # Fetch cycles to infer activities
        logger.info("Fetching Whoop cycles for activity inference")
        cycles_response = whoop.get_cycles(start_date, end_date)
        cycles = cycles_response.get("records", [])
        
        if not cycles:
            logger.warning(f"No cycles found for date range {start_date} to {end_date}")
        else:
            logger.info(f"Retrieved {len(cycles)} cycles")
        
        # Transform to activities
        logger.info("Transforming cycles to activities")
        activities_data = transform_whoop_to_activities(cycles, start_date, end_date)
        
        # Log summary
        logger.info("=" * 50)
        logger.info(f"ACTIVITIES SYNC SUMMARY")
        logger.info(f"User: {user_id}")
        logger.info(f"Date Range: {start_date} to {end_date}")
        logger.info(f"Total Cycles: {len(cycles)}")
        logger.info(f"Activities Found: {len(activities_data.get('activities', []))}")
        logger.info("=" * 50)
        
        return ActivitiesResponse(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            source="whoop",
            activities=activities_data.get("activities", []),
            workouts=activities_data.get("workouts", []),
            note=activities_data.get("note")
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error fetching activities: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch activities and workouts: {str(e)}"
        )


@router.get("/activities/info")
async def get_activities_info():
    """
    Get information about Whoop activity data limitations
    
    Returns:
        JSON with details about what activity data Whoop provides
    """
    return {
        "provider": "whoop",
        "capabilities": {
            "strain": "Yes - daily training load metric (0-21)",
            "activity_details": "Limited - only inferred from strain",
            "activity_types": "Generic - all workouts classified as 'Mixed'",
            "duration": "Estimated from kilojoules",
            "calories": "Estimated from strain score",
            "gps_data": "Not available",
            "elevation": "Not available",
            "detailed_splits": "Not available"
        },
        "limitations": [
            "Whoop does not provide detailed activity history like Garmin",
            "Activities are inferred only when strain score > 5",
            "Activity types are not available - all labeled as 'Mixed'",
            "Duration and calories are estimates based on strain",
            "GPS tracking and route data not available",
            "For detailed activities, consider keeping Garmin integration"
        ],
        "recommendation": "Use Whoop for recovery/readiness metrics and Garmin for activity details (dual integration)"
    }