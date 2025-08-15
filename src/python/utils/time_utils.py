import re
from typing import int

def parse_duration(duration: str) -> int:
    """Parse duration string into seconds
    
    Args:
        duration: Duration string like '7d', '24h', '30m'
        
    Returns:
        Duration in seconds
        
    Raises:
        ValueError: If duration format is invalid
    """
    pattern = r'^(\d+)([hdwm])$'
    match = re.match(pattern, duration.lower())
    
    if not match:
        raise ValueError(f'Invalid duration format: {duration}. Use: 1h, 7d, 1w, etc.')
    
    value, unit = match.groups()
    value = int(value)
    
    multipliers = {
        'h': 3600,      # hours
        'd': 86400,     # days  
        'w': 604800,    # weeks
        'm': 2592000    # months (30 days)
    }
    
    return value * multipliers[unit]

def seconds_to_minutes(seconds: int) -> float:
    """Convert seconds to minutes"""
    return seconds / 60

def minutes_to_hours(minutes: float) -> float:
    """Convert minutes to hours"""
    return minutes / 60