import numpy as np
from scipy import stats
from sklearn.cluster import DBSCAN
from typing import Dict, List, Any, Tuple
import logging

class SpikeDetector:
    """Detects and analyzes traffic spikes in time series data"""
    
    def __init__(self, threshold_sigma: float = 3.0):
        self.threshold_sigma = threshold_sigma
        self.logger = logging.getLogger(__name__)
    
    def detect(self, original_signal: np.ndarray, detail_coeffs: List[np.ndarray] = None) -> Dict[str, Any]:
        """Detect spikes in signal
        
        Args:
            original_signal: Original time series signal
            detail_coeffs: High-frequency detail coefficients from wavelet decomposition
            
        Returns:
            Dictionary containing spike detection results
        """
        signal = np.asarray(original_signal).flatten()
        
        if len(signal) < 10:
            return self._empty_spike_result()
        
        # Calculate signal statistics
        signal_stats = self._calculate_statistics(signal)
        
        # Determine threshold for spike detection
        threshold = signal_stats['mean'] + self.threshold_sigma * signal_stats['std']
        
        # Method 1: Direct spike detection on original signal
        spikes_direct = self._detect_direct_spikes(signal, threshold, signal_stats)
        
        # Method 2: Spike detection on high-frequency components if available
        spikes_wavelet = []
        if detail_coeffs:
            high_freq_signal = self._combine_detail_coefficients(detail_coeffs, len(signal))
            if len(high_freq_signal) > 0:
                spikes_wavelet = self._detect_wavelet_spikes(high_freq_signal, signal)
        
        # Combine and cluster spikes
        all_spikes = spikes_direct + spikes_wavelet
        clustered_spikes = self._cluster_spikes(all_spikes)
        
        # Analyze spike distribution
        distribution = self._analyze_spike_distribution(clustered_spikes)
        
        self.logger.debug(f'Detected {len(clustered_spikes)} spike events')
        
        return {
            'threshold': float(threshold),
            'events': clustered_spikes,
            'distribution': distribution
        }
    
    def _calculate_statistics(self, signal: np.ndarray) -> Dict[str, float]:
        """Calculate comprehensive signal statistics"""
        return {
            'mean': float(np.mean(signal)),
            'std': float(np.std(signal)),
            'variance': float(np.var(signal)),
            'p50': float(np.percentile(signal, 50)),
            'p95': float(np.percentile(signal, 95)),
            'p99': float(np.percentile(signal, 99)),
            'min': float(np.min(signal)),
            'max': float(np.max(signal))
        }
    
    def _detect_direct_spikes(self, signal: np.ndarray, threshold: float, 
                            stats: Dict[str, float]) -> List[Dict[str, Any]]:
        """Detect spikes directly from signal values"""
        spikes = []
        
        for i, value in enumerate(signal):
            if value > threshold:
                spike = {
                    'index': i,
                    'timestamp': i * 60 * 1000,  # Convert to milliseconds (assuming 1min intervals)
                    'magnitude': float(value),
                    'deviation': float((value - stats['mean']) / stats['std']) if stats['std'] > 0 else 0,
                    'method': 'direct'
                }
                spikes.append(spike)
        
        return spikes
    
    def _combine_detail_coefficients(self, detail_coeffs: List[np.ndarray], 
                                   target_length: int) -> np.ndarray:
        """Combine wavelet detail coefficients into single high-frequency signal"""
        if not detail_coeffs:
            return np.array([])
        
        # Start with the highest frequency detail (last coefficient)
        combined = np.zeros(target_length)
        
        for level, detail in enumerate(detail_coeffs):
            if len(detail) == 0:
                continue
                
            # Upsample detail coefficient to match target length
            upsampled = np.interp(
                np.linspace(0, 1, target_length),
                np.linspace(0, 1, len(detail)),
                detail
            )
            
            # Weight higher frequency components more
            weight = 2 ** level
            combined += weight * upsampled
        
        return combined
    
    def _detect_wavelet_spikes(self, high_freq_signal: np.ndarray, 
                             original_signal: np.ndarray) -> List[Dict[str, Any]]:
        """Detect spikes in high-frequency wavelet components"""
        spikes = []
        
        if len(high_freq_signal) == 0:
            return spikes
        
        # Calculate statistics for high-frequency signal
        hf_mean = np.mean(high_freq_signal)
        hf_std = np.std(high_freq_signal)
        
        if hf_std == 0:
            return spikes
        
        # Use adaptive threshold based on signal characteristics
        hf_threshold = hf_mean + self.threshold_sigma * hf_std
        
        for i, hf_value in enumerate(high_freq_signal):
            if abs(hf_value) > abs(hf_threshold):
                # Check if this corresponds to an actual spike in original signal
                if i < len(original_signal):
                    spike = {
                        'index': i,
                        'timestamp': i * 60 * 1000,
                        'magnitude': float(original_signal[i]),
                        'hf_magnitude': float(hf_value),
                        'deviation': float(hf_value / hf_std) if hf_std > 0 else 0,
                        'method': 'wavelet'
                    }
                    spikes.append(spike)
        
        return spikes
    
    def _cluster_spikes(self, spikes: List[Dict[str, Any]], 
                       max_gap_minutes: int = 10) -> List[Dict[str, Any]]:
        """Cluster nearby spikes into events"""
        if len(spikes) < 2:
            return [self._format_spike_event(spike) for spike in spikes]
        
        # Sort spikes by timestamp
        sorted_spikes = sorted(spikes, key=lambda x: x['timestamp'])
        
        # Group spikes by proximity
        clusters = []
        current_cluster = [sorted_spikes[0]]
        
        for spike in sorted_spikes[1:]:
            time_gap = (spike['timestamp'] - current_cluster[-1]['timestamp']) / (60 * 1000)  # minutes
            
            if time_gap <= max_gap_minutes:
                current_cluster.append(spike)
            else:
                clusters.append(current_cluster)
                current_cluster = [spike]
        
        clusters.append(current_cluster)
        
        # Merge each cluster into a single event
        events = []
        for cluster in clusters:
            events.append(self._merge_spike_cluster(cluster))
        
        return events
    
    def _merge_spike_cluster(self, cluster: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Merge a cluster of spikes into a single event"""
        if len(cluster) == 1:
            return self._format_spike_event(cluster[0])
        
        # Calculate cluster statistics
        magnitudes = [spike['magnitude'] for spike in cluster]
        timestamps = [spike['timestamp'] for spike in cluster]
        
        # Use peak magnitude and median timestamp
        peak_magnitude = max(magnitudes)
        total_magnitude = sum(magnitudes)
        median_timestamp = int(np.median(timestamps))
        duration_minutes = (max(timestamps) - min(timestamps)) / (60 * 1000)
        
        return {
            'timestamp': median_timestamp,
            'magnitude': float(total_magnitude / len(cluster)),  # Average magnitude
            'peak_magnitude': float(peak_magnitude),
            'duration_minutes': float(max(1, duration_minutes)),  # At least 1 minute
            'spike_count': len(cluster)
        }
    
    def _format_spike_event(self, spike: Dict[str, Any]) -> Dict[str, Any]:
        """Format single spike as event"""
        return {
            'timestamp': spike['timestamp'],
            'magnitude': spike['magnitude'],
            'peak_magnitude': spike['magnitude'],
            'duration_minutes': 1.0,  # Single point
            'spike_count': 1
        }
    
    def _analyze_spike_distribution(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze temporal distribution of spike events"""
        if len(events) < 2:
            return {
                'type': 'insufficient-data',
                'count': len(events)
            }
        
        # Calculate inter-arrival times
        timestamps = [event['timestamp'] for event in events]
        timestamps.sort()
        
        intervals = []
        for i in range(1, len(timestamps)):
            interval_ms = timestamps[i] - timestamps[i-1]
            interval_minutes = interval_ms / (60 * 1000)
            intervals.append(interval_minutes)
        
        if not intervals:
            return {
                'type': 'insufficient-data',
                'count': len(events)
            }
        
        mean_interval = np.mean(intervals)
        
        # Test for exponential distribution (Poisson process)
        # Use Kolmogorov-Smirnov test
        try:
            # Fit exponential distribution
            lambda_param = 1 / mean_interval if mean_interval > 0 else 1
            
            # Generate expected exponential distribution
            expected_intervals = np.random.exponential(mean_interval, len(intervals))
            
            # Simple distribution classification
            cv = np.std(intervals) / mean_interval if mean_interval > 0 else float('inf')
            
            if cv < 0.5:
                dist_type = 'regular'
            elif 0.5 <= cv <= 1.5:
                dist_type = 'exponential'
            else:
                dist_type = 'bursty'
            
        except Exception:
            dist_type = 'unknown'
            lambda_param = 1 / mean_interval if mean_interval > 0 else 1
        
        return {
            'type': dist_type,
            'lambda': float(lambda_param),
            'mean_interval_minutes': float(mean_interval),
            'count': len(events),
            'total_events': len(events)
        }
    
    def _empty_spike_result(self) -> Dict[str, Any]:
        """Return empty spike detection result"""
        return {
            'threshold': 0.0,
            'events': [],
            'distribution': {
                'type': 'none',
                'count': 0
            }
        }