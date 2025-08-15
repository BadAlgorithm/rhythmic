import logging
import sys
from typing import Optional

def setup_logger(verbose: bool = False, name: Optional[str] = None) -> logging.Logger:
    """Setup logger with appropriate level and formatting"""
    logger = logging.getLogger(name or 'rhythmic')
    
    # Prevent duplicate handlers
    if logger.handlers:
        return logger
    
    # Set level
    level = logging.DEBUG if verbose else logging.INFO
    logger.setLevel(level)
    
    # Create formatter
    if verbose:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    else:
        formatter = logging.Formatter('%(message)s')
    
    # Create console handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    handler.setFormatter(formatter)
    
    logger.addHandler(handler)
    
    return logger