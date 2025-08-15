import requests
import logging
from typing import Dict, List, Any
from datetime import datetime, timedelta

from ..utils.time_utils import parse_duration

class PrometheusCollector:
    """Collects time series data from Prometheus"""
    
    def __init__(self, base_url: str, timeout: int = 30):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.logger = logging.getLogger(__name__)
        
    def fetch_metrics(self, query: str, duration: str, step: int = 60) -> Dict[str, Any]:
        """Fetch time series metrics from Prometheus
        
        Args:
            query: Prometheus metric query
            duration: Lookback duration (e.g., '7d', '24h')
            step: Data resolution in seconds
            
        Returns:
            Dictionary containing timestamps, values, and metadata
        """
        # Calculate time range
        end_time = datetime.now()
        duration_seconds = parse_duration(duration)
        start_time = end_time - timedelta(seconds=duration_seconds)
        
        # Build query with rate function for counters
        if not query.startswith('rate(') and not query.startswith('increase('):
            if '_total' in query or '_count' in query:
                prometheus_query = f'rate({query}[1m])'
            else:
                prometheus_query = query
        else:
            prometheus_query = query
            
        # Prepare request parameters
        params = {
            'query': prometheus_query,
            'start': int(start_time.timestamp()),
            'end': int(end_time.timestamp()),
            'step': f'{step}s'
        }
        
        url = f'{self.base_url}/api/v1/query_range'
        
        try:
            self.logger.info(f'Fetching metrics: {prometheus_query}')
            self.logger.debug(f'Query params: {params}')
            
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('status') != 'success':
                error_msg = data.get('error', 'Unknown error')
                raise RuntimeError(f'Prometheus query failed: {error_msg}')
            
            result = data.get('data', {}).get('result', [])
            
            if not result:
                raise ValueError(f'No data found for query: {prometheus_query}')
            
            # Use first result series
            series = result[0]
            values_raw = series.get('values', [])
            
            if not values_raw:
                raise ValueError(f'No values found for query: {prometheus_query}')
            
            # Parse timestamps and values
            timestamps = []
            values = []
            
            for timestamp_str, value_str in values_raw:
                try:
                    timestamps.append(int(float(timestamp_str) * 1000))  # Convert to ms
                    values.append(float(value_str))
                except (ValueError, TypeError) as e:
                    self.logger.warning(f'Skipping invalid data point: {e}')
                    continue
            
            if not timestamps:
                raise ValueError('No valid data points found')
            
            self.logger.info(f'Successfully fetched {len(timestamps)} data points')
            
            return {
                'timestamps': timestamps,
                'values': values,
                'metric': query,
                'duration': duration,
                'step': step,
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat(),
                'prometheus_query': prometheus_query,
                'series_labels': series.get('metric', {})
            }
            
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f'Failed to connect to Prometheus at {url}: {e}')
        except Exception as e:
            raise RuntimeError(f'Error fetching metrics: {e}')
    
    def test_connection(self) -> bool:
        """Test if Prometheus is reachable"""
        try:
            url = f'{self.base_url}/api/v1/query'
            params = {'query': 'up'}
            response = requests.get(url, params=params, timeout=5)
            return response.status_code == 200
        except:
            return False