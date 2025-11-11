from datetime import datetime
from typing import Tuple

def _month_to_season(month: int) -> str:
    # seasons: winter(Jan-Mar), spring(Apr-Jun), summer(Jul-Sep), fall(Oct-Dec)
    if month in (12, 1, 2):
        return "winter"
    if month in (3, 4, 5):
        return "spring"
    if month in (6, 7, 8):
        return "summer"
    return "fall"

def get_current_season(now: datetime = None) -> Tuple[int, str]:
    now = now or datetime.utcnow()
    month = now.month
    season = _month_to_season(month)
    year = now.year
    # If it's December and it's winter mapping to next year, keep year+1 for winter if desired.
    # Most MAL seasonal endpoints use year+season where winter is the year (e.g., winter 2025 is Jan-Mar 2025)
    # So we will not bump year for December in this implementation.
    return year, season

def get_next_season(now: datetime = None) -> Tuple[int, str]:
    now = now or datetime.utcnow()
    month = now.month
    year = now.year
    # determine next season by month
    if month in (12, 1, 2):
        # currently winter -> next is spring
        next_season = "spring"
        if month == 12:
            # December -> next season's year may be next year for some interpretations; keep same year for simplicity
            year = year + 1 if month == 12 else year
    elif month in (3, 4, 5):
        next_season = "summer"
    elif month in (6, 7, 8):
        next_season = "fall"
    else:
        next_season = "winter"
        if month >= 10:
            year = year + 1
    return year, next_season
