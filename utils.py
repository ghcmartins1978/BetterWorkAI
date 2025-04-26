import os
import logging
import json
import platform
import time
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

def get_os_info():
    """Get information about the operating system"""
    system = platform.system()
    release = platform.release()
    version = platform.version()
    
    return {
        'system': system,
        'release': release,
        'version': version
    }

def cleanup_old_logs(retention_days=7):
    """
    Delete log files older than retention_days
    
    Args:
        retention_days: Number of days to keep logs
    """
    if not os.path.isdir('logs'):
        return
        
    cutoff_date = datetime.now() - timedelta(days=retention_days)
    
    try:
        for filename in os.listdir('logs'):
            if not filename.endswith('.json'):
                continue
                
            file_path = os.path.join('logs', filename)
            
            # Get file creation time
            file_time = datetime.fromtimestamp(os.path.getctime(file_path))
            
            if file_time < cutoff_date:
                try:
                    os.remove(file_path)
                    logger.info(f"Deleted old log file: {filename}")
                except Exception as e:
                    logger.error(f"Error deleting log file {filename}: {e}")
                    
    except Exception as e:
        logger.error(f"Error cleaning up logs: {e}")

def get_app_info():
    """Get information about the application"""
    return {
        'name': 'BettermanAI',
        'version': '0.1.0',
        'description': 'Your Personal Workflow Optimizer',
        'os_info': get_os_info()
    }

def calculate_similarity(seq1, seq2):
    """
    Calculate similarity between two sequences
    
    Args:
        seq1: First sequence
        seq2: Second sequence
        
    Returns:
        Similarity score between 0 and 1
    """
    if not seq1 or not seq2:
        return 0
        
    # Convert sequences to strings for simple comparison
    str1 = json.dumps(seq1)
    str2 = json.dumps(seq2)
    
    # Calculate Levenshtein distance
    m, n = len(str1), len(str2)
    
    # Create distance matrix
    dp = [[0 for _ in range(n+1)] for _ in range(m+1)]
    
    # Initialize first row and column
    for i in range(m+1):
        dp[i][0] = i
    for j in range(n+1):
        dp[0][j] = j
        
    # Fill the matrix
    for i in range(1, m+1):
        for j in range(1, n+1):
            if str1[i-1] == str2[j-1]:
                dp[i][j] = dp[i-1][j-1]
            else:
                dp[i][j] = 1 + min(dp[i-1][j], dp[i][j-1], dp[i-1][j-1])
                
    # Calculate similarity
    max_len = max(m, n)
    if max_len == 0:
        return 1.0
    else:
        return 1.0 - (dp[m][n] / max_len)

def throttle(min_interval):
    """
    Decorator to throttle function calls
    
    Args:
        min_interval: Minimum interval between calls in seconds
    """
    def decorator(func):
        last_called = [0]
        
        def wrapper(*args, **kwargs):
            now = time.time()
            elapsed = now - last_called[0]
            
            if elapsed >= min_interval:
                last_called[0] = now
                return func(*args, **kwargs)
            else:
                # Skip this call
                logger.debug(f"Throttled call to {func.__name__}, elapsed {elapsed:.2f}s < {min_interval}s")
                
        return wrapper
    return decorator
