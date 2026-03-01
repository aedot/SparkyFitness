"""
Data Transformation Service
Converts Whoop data to SparkyFitness format
"""

import logging
from typing import Dict, List, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


def map_recovery_to_mood(recovery_score: float) -> Tuple[int, str]:
    """
    Map Whoop Recovery (0-100) to SparkyFitness mood scale
    
    Recovery Score → Mood Value & Category
    0-20: Fatigued/Tired
    21-40: Stressed
    41-60: Neutral
    61-80: Good/Confident
    81-100: Excellent/Excited
    """
    if recovery_score >= 81:
        return 95, "Excited"
    elif recovery_score >= 61:
        return 75, "Confident"
    elif recovery_score >= 41:
        return 55, "Neutral"
    elif recovery_score >= 21:
        return 35, "Worried"
    else:
        return 15, "Tired"


def estimate_calories_from_strain(strain_score: float) -> int:
    """
    Estimate calories burned from Whoop Strain score
    
    Whoop Strain (0-21) → Estimated calories
    Approximation: ~50 calories per strain point
    """
    return max(100, int(strain_score * 50))


def transform_whoop_cycles_to_health_data(cycles: List[Dict], start_date: str, end_date: str) -> Dict:
    """
    Transform Whoop cycles data to SparkyFitness health_and_wellness format
    
    Maps:
    - Whoop Strain → training load / intensity minutes
    - Whoop Recovery → training readiness / body battery
    - Whoop Sleep → sleep metrics
    - Whoop Heart Rate → HR metrics / HRV
    
    Args:
        cycles: List of Whoop cycle objects
        start_date: Start date string (for logging)
        end_date: End date string (for logging)
    
    Returns:
        Dict with transformed health metrics
    """
    
    health_data = {
        "strain": [],
        "recovery": [],
        "sleep": [],
        "hrv": [],
        "resting_heart_rate": [],
        "stress": [],
        "body_battery": [],
        "intensity_minutes": [],
        "training_readiness": [],
    }
    
    logger.info(f"Transforming {len(cycles)} cycles from {start_date} to {end_date}")
    
    for cycle in cycles:
        try:
            cycle_start = cycle.get("start", "").split("T")[0]
            
            # ====== STRAIN DATA ======
            if cycle.get("strain"):
                strain_data = _transform_strain(cycle["strain"], cycle_start)
                health_data["strain"].append(strain_data)
                
                # Derived: Intensity Minutes from Strain
                intensity_data = _transform_intensity_minutes(cycle["strain"], cycle_start)
                if intensity_data:
                    health_data["intensity_minutes"].append(intensity_data)
            
            # ====== RECOVERY DATA ======
            if cycle.get("recovery"):
                recovery_data = _transform_recovery(cycle["recovery"], cycle_start)
                health_data["recovery"].append(recovery_data)
                
                # Derived: Stress (inverse of recovery)
                stress_data = _transform_stress_from_recovery(cycle["recovery"], cycle_start)
                health_data["stress"].append(stress_data)
                
                # Derived: Body Battery (proxy for recovery)
                battery_data = _transform_body_battery(cycle["recovery"], cycle_start)
                health_data["body_battery"].append(battery_data)
            
            # ====== SLEEP DATA ======
            if cycle.get("sleep"):
                sleep_data = _transform_sleep(cycle["sleep"], cycle_start)
                health_data["sleep"].append(sleep_data)
            
            # ====== HEART RATE & HRV DATA ======
            if cycle.get("heart_rate"):
                # Heart rate data
                hr_data = _transform_heart_rate(cycle["heart_rate"], cycle_start)
                health_data["resting_heart_rate"].append(hr_data)
                
                # HRV data (extracted from heart_rate)
                hrv_data = _transform_hrv(cycle["heart_rate"], cycle_start)
                if hrv_data:
                    health_data["hrv"].append(hrv_data)
        
        except Exception as e:
            logger.warning(f"Error transforming cycle {cycle.get('id')}: {e}")
            continue
    
    # Filter out empty entries
    final_data = {k: v for k, v in health_data.items() if v}
    
    logger.info(f"Transformation complete. Metrics collected: {list(final_data.keys())}")
    for metric, entries in final_data.items():
        logger.debug(f"  {metric}: {len(entries)} entries")
    
    return final_data


def _transform_strain(strain_obj: Dict, cycle_date: str) -> Dict:
    """Transform Whoop strain data"""
    return {
        "date": cycle_date,
        "value": strain_obj.get("score", 0),
        "percent_recorded": strain_obj.get("percent_recorded"),
        "kilojoules": strain_obj.get("kilojoules"),
        "average_heart_rate": strain_obj.get("average_heart_rate"),
        "max_heart_rate": strain_obj.get("max_heart_rate"),
        "notes": f"Whoop Strain Score: {strain_obj.get('score', 0):.1f}/21"
    }


def _transform_recovery(recovery_obj: Dict, cycle_date: str) -> Dict:
    """Transform Whoop recovery data"""
    recovery_score = recovery_obj.get("score", 50)
    
    return {
        "date": cycle_date,
        "recovery_score": recovery_score,
        "training_readiness_score": recovery_score,
        "rhr_delta": recovery_obj.get("rhr_delta"),
        "hrv_delta": recovery_obj.get("hrv_delta"),
        "spo2_delta": recovery_obj.get("spo2_delta"),
        "skin_temp_delta": recovery_obj.get("skin_temp_delta"),
        "notes": f"Whoop Recovery: {recovery_score}/100"
    }


def _transform_stress_from_recovery(recovery_obj: Dict, cycle_date: str) -> Dict:
    """
    Transform recovery to stress (inverse relationship)
    Higher recovery = lower stress
    """
    recovery_score = recovery_obj.get("score", 50)
    stress_level = 100 - recovery_score
    mood_value, mood_category = map_recovery_to_mood(recovery_score)
    
    return {
        "date": cycle_date,
        "stress_level": stress_level,
        "derived_mood_value": mood_value,
        "derived_mood_category": mood_category,
        "derived_mood_notes": f"Derived from Whoop Recovery: {recovery_score}/100 ({mood_category})"
    }


def _transform_body_battery(recovery_obj: Dict, cycle_date: str) -> Dict:
    """
    Transform recovery to body battery (proxy metric)
    Recovery score directly maps to body battery readiness (0-100)
    """
    recovery_score = recovery_obj.get("score", 50)
    
    return {
        "date": cycle_date,
        "body_battery_current": recovery_score,
        "body_battery_highest": 100,
        "body_battery_lowest": 0,
        "note": "Estimated from Whoop Recovery score (0-100)"
    }


def _transform_sleep(sleep_obj: Dict, cycle_date: str) -> Dict:
    """Transform Whoop sleep data"""
    
    total_sleep = sleep_obj.get("total", {})
    duration_seconds = total_sleep.get("seconds", 0) if isinstance(total_sleep, dict) else total_sleep
    
    return {
        "entry_date": cycle_date,
        "bedtime": sleep_obj.get("start"),
        "wake_time": sleep_obj.get("end"),
        "duration_in_seconds": duration_seconds,
        "time_asleep_in_seconds": duration_seconds,
        "sleep_score": sleep_obj.get("score"),
        "sleep_performance_percentage": sleep_obj.get("performance_percentage"),
        "average_spo2_value": sleep_obj.get("average_spo2"),
        "average_respiration_value": sleep_obj.get("average_respiration"),
        "average_resting_heart_rate": sleep_obj.get("average_resting_heart_rate"),
        "notes": f"Whoop Sleep Score: {sleep_obj.get('score')}/100"
    }


def _transform_heart_rate(hr_obj: Dict, cycle_date: str) -> Dict:
    """Transform Whoop heart rate data"""
    
    return {
        "date": cycle_date,
        "resting_heart_rate": hr_obj.get("resting"),
        "average_heart_rate": hr_obj.get("average"),
        "max_heart_rate": hr_obj.get("max"),
        "notes": f"Resting HR: {hr_obj.get('resting')} bpm"
    }


def _transform_hrv(hr_obj: Dict, cycle_date: str) -> Dict:
    """
    Transform HRV data (Heart Rate Variability)
    HRV typically measured during sleep
    """
    hrv_data = hr_obj.get("hrv", {})
    
    if not hrv_data:
        return None
    
    avg_hrv = hrv_data.get("average")
    
    if not avg_hrv:
        return None
    
    return {
        "date": cycle_date,
        "average_overnight_hrv": avg_hrv,
        "lowest_hrv": hrv_data.get("min"),
        "highest_hrv": hrv_data.get("max"),
        "hrv_status": "good" if avg_hrv > 40 else "low",
        "notes": f"Average HRV: {avg_hrv} ms"
    }


def _transform_intensity_minutes(strain_obj: Dict, cycle_date: str) -> Dict:
    """
    Estimate intensity minutes from strain score
    Whoop Strain (0-21) → Intensity Minutes (0-30)
    """
    strain_score = strain_obj.get("score", 0)
    
    # Scale strain to intensity minutes
    # Rough mapping: each strain point ≈ 1.5 minutes of intensity
    estimated_intensity_minutes = min(30, int(strain_score * 1.5))
    
    return {
        "date": cycle_date,
        "total_intensity_minutes": estimated_intensity_minutes,
        "note": f"Estimated from Whoop Strain: {strain_score:.1f}/21"
    }


def transform_whoop_to_activities(cycles: List[Dict], start_date: str, end_date: str) -> Dict:
    """
    Transform Whoop cycles to activities format
    
    Note: Whoop has limited activity data. We infer activities from strain.
    Only includes days with significant strain scores (>5).
    
    Args:
        cycles: List of Whoop cycle objects
        start_date: Start date (for logging)
        end_date: End date (for logging)
    
    Returns:
        Dict with activities and workouts
    """
    
    activities = []
    
    logger.info(f"Transforming {len(cycles)} cycles to activities")
    
    for cycle in cycles:
        try:
            cycle_start = cycle.get("start", "").split("T")[0]
            
            if cycle.get("strain"):
                strain_score = cycle["strain"].get("score", 0)
                
                # Only include days with significant strain
                if strain_score > 5:
                    activity = {
                        "id": cycle.get("id"),
                        "date": cycle_start,
                        "activityName": "Workout",
                        "activityType": "Mixed",
                        "startTime": cycle.get("start"),
                        "kilojoules": cycle["strain"].get("kilojoules"),
                        "strainScore": strain_score,
                        "calories": estimate_calories_from_strain(strain_score),
                        "note": "Activity inferred from Whoop Strain score"
                    }
                    activities.append(activity)
        
        except Exception as e:
            logger.warning(f"Error transforming cycle to activity: {e}")
            continue
    
    logger.info(f"Transformed {len(activities)} activities")
    
    return {
        "activities": activities,
        "workouts": [],
        "note": "Whoop provides limited activity details. Activities inferred from Strain metric."
    }