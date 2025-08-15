import numpy as np
from datetime import datetime
from typing import Dict, List, Any
import logging

from ..processors.signal_decomposer import SignalDecomposer
from ..processors.fourier_analyzer import FourierAnalyzer
from ..processors.spike_detector import SpikeDetector

class TrafficModeler:
    """Main class for modeling traffic patterns from time series data"""
    
    def __init__(self, wavelet_type: str = 'db4', spike_threshold: float = 3.0):
        self.decomposer = SignalDecomposer(wavelet_type=wavelet_type)
        self.fourier_analyzer = FourierAnalyzer()
        self.spike_detector = SpikeDetector(threshold_sigma=spike_threshold)
        self.logger = logging.getLogger(__name__)
    
    def model(self, traffic_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate complete traffic model from time series data
        
        Args:
            traffic_data: Dictionary containing timestamps, values, and metadata
            
        Returns:
            Complete traffic model dictionary
        """
        try:
            values = np.array(traffic_data['values'])
            timestamps = np.array(traffic_data['timestamps'])
            
            self.logger.info('🌊 Performing wavelet decomposition...')
            
            # 1. Wavelet decomposition to separate signal components
            decomposed = self.decomposer.decompose(values)
            
            self.logger.info('🎵 Analyzing periodic patterns with Fourier transform...')
            
            # 2. Fourier analysis on smooth baseline component
            baseline = self.fourier_analyzer.analyze(
                decomposed['approximation'],
                sample_rate=1/traffic_data['step']  # Convert step to Hz
            )
            
            self.logger.info('⚡ Detecting traffic spikes...')
            
            # 3. Spike detection using both original signal and detail components
            spikes = self.spike_detector.detect(values, decomposed['details'])
            
            # 4. Pattern classification
            pattern = self._classify_pattern(baseline, spikes, timestamps, traffic_data['step'])
            
            # 5. Statistical summary
            statistics = self._calculate_statistics(values)
            
            # 6. Assemble complete model
            model = {
                'version': '1.0.0',
                'metadata': {
                    'source': 'prometheus',
                    'metric': traffic_data['metric'],
                    'duration': traffic_data['duration'],
                    'samples': len(values),
                    'step': traffic_data['step'],
                    'timestamp': datetime.now().isoformat()
                },
                'baseline': baseline,
                'spikes': spikes,
                'pattern': pattern,
                'statistics': statistics,
                'decomposition': {
                    'wavelet_type': decomposed['wavelet_type'],
                    'levels': decomposed['levels'],
                    'smoothness_ratio': decomposed['smoothness_ratio'],
                    'energy_distribution': decomposed['energy_distribution']
                }
            }
            
            self.logger.info(f'✅ Model generated successfully')
            self.logger.info(f'   Pattern type: {pattern["type"]} (confidence: {pattern["confidence"]:.2f})')
            self.logger.info(f'   Baseline mean: {baseline["mean"]:.2f} req/s')
            self.logger.info(f'   Periodic components: {len(baseline["coefficients"])}')
            self.logger.info(f'   Spike events: {len(spikes["events"])}')
            
            return model
            
        except Exception as e:
            self.logger.error(f'❌ Traffic modeling failed: {e}')
            raise
    
    def _classify_pattern(self, baseline: Dict[str, Any], spikes: Dict[str, Any], 
                         timestamps: np.ndarray, step: int) -> Dict[str, Any]:
        """Classify the overall traffic pattern type
        
        Args:
            baseline: Fourier analysis results
            spikes: Spike detection results
            timestamps: Array of timestamps
            step: Time step in seconds
            
        Returns:
            Pattern classification dictionary
        """
        # Analyze periodic components for daily/weekly patterns
        daily_confidence = 0.0
        weekly_confidence = 0.0
        seasonal_confidence = 0.0
        
        for coeff in baseline['coefficients']:
            period_hours = coeff['period_minutes'] / 60
            confidence = coeff['confidence']
            
            # Daily pattern detection (24 hours ± 4 hours tolerance)
            if 20 <= period_hours <= 28:
                daily_confidence = max(daily_confidence, confidence)
            
            # Weekly pattern detection (7 days ± 1 day tolerance)
            elif 144 <= period_hours <= 192:  # 6-8 days in hours
                weekly_confidence = max(weekly_confidence, confidence)
            
            # Seasonal patterns (monthly, quarterly)
            elif period_hours >= 600:  # > 25 days
                seasonal_confidence = max(seasonal_confidence, confidence)
        
        # Analyze spike frequency
        total_duration_hours = len(timestamps) * step / 3600
        spike_rate_per_day = len(spikes['events']) / (total_duration_hours / 24) if total_duration_hours > 0 else 0
        
        if spike_rate_per_day > 10:
            spike_frequency = 'frequent'
        elif spike_rate_per_day > 2:
            spike_frequency = 'occasional'
        elif spike_rate_per_day > 0.1:
            spike_frequency = 'rare'
        else:
            spike_frequency = 'none'
        
        # Determine pattern type and confidence
        pattern_type, confidence = self._determine_pattern_type(
            daily_confidence, weekly_confidence, seasonal_confidence, 
            spike_frequency, baseline['std'], baseline['mean']
        )
        
        return {
            'type': pattern_type,
            'confidence': confidence,
            'daily': daily_confidence > 0.3,
            'weekly': weekly_confidence > 0.3,
            'seasonal': seasonal_confidence > 0.3,
            'spike_frequency': spike_frequency
        }
    
    def _determine_pattern_type(self, daily_conf: float, weekly_conf: float, 
                              seasonal_conf: float, spike_freq: str,
                              baseline_std: float, baseline_mean: float) -> tuple:
        """Determine specific pattern type and confidence
        
        Returns:
            Tuple of (pattern_type, confidence)
        """
        # Calculate coefficient of variation for stability assessment
        cv = baseline_std / baseline_mean if baseline_mean > 0 else float('inf')
        
        # Business hours patterns
        if daily_conf > 0.6:
            if spike_freq in ['frequent', 'occasional']:
                return 'business-hours-heavy', daily_conf
            else:
                return 'business-hours-normal', daily_conf
        
        # Weekly batch patterns
        elif weekly_conf > 0.5:
            return 'weekly-batch', weekly_conf
        
        # Spike-driven patterns
        elif spike_freq == 'frequent':
            return 'bursty', 0.8
        
        # Steady patterns (low variability)
        elif spike_freq == 'none' and cv < 0.3:
            return 'steady', 0.9
        
        # Seasonal patterns
        elif seasonal_conf > 0.4:
            return 'seasonal', seasonal_conf
        
        # Default to mixed pattern
        else:
            # Calculate confidence based on available evidence
            max_conf = max(daily_conf, weekly_conf, seasonal_conf)
            confidence = max(0.3, max_conf)  # Minimum confidence for mixed
            return 'mixed', confidence
    
    def _calculate_statistics(self, values: np.ndarray) -> Dict[str, float]:
        """Calculate comprehensive traffic statistics
        
        Args:
            values: Time series values
            
        Returns:
            Dictionary of statistical measures
        """
        values_clean = values[~np.isnan(values)]  # Remove NaN values
        
        if len(values_clean) == 0:
            return {
                'mean': 0.0, 'std': 0.0, 'variance': 0.0,
                'p50': 0.0, 'p95': 0.0, 'p99': 0.0,
                'min': 0.0, 'max': 0.0
            }
        
        return {
            'mean': float(np.mean(values_clean)),
            'std': float(np.std(values_clean)),
            'variance': float(np.var(values_clean)),
            'p50': float(np.percentile(values_clean, 50)),
            'p95': float(np.percentile(values_clean, 95)),
            'p99': float(np.percentile(values_clean, 99)),
            'min': float(np.min(values_clean)),
            'max': float(np.max(values_clean))
        }
    
    def validate_model(self, model: Dict[str, Any]) -> List[str]:
        """Validate generated model for completeness and consistency
        
        Args:
            model: Generated traffic model
            
        Returns:
            List of validation warnings (empty if all good)
        """
        warnings = []
        
        # Check for required fields
        required_fields = ['version', 'metadata', 'baseline', 'spikes', 'pattern', 'statistics']
        for field in required_fields:
            if field not in model:
                warnings.append(f'Missing required field: {field}')
        
        # Validate baseline
        if 'baseline' in model:
            baseline = model['baseline']
            if baseline.get('mean', 0) < 0:
                warnings.append('Negative baseline mean detected')
            if len(baseline.get('coefficients', [])) == 0:
                warnings.append('No periodic components found - signal may be too noisy')
        
        # Validate pattern confidence
        if 'pattern' in model:
            pattern = model['pattern']
            confidence = pattern.get('confidence', 0)
            if confidence < 0.3:
                warnings.append(f'Low pattern confidence ({confidence:.2f}) - results may be unreliable')
        
        # Check data quality
        if 'metadata' in model:
            samples = model['metadata'].get('samples', 0)
            if samples < 100:
                warnings.append(f'Low sample count ({samples}) - consider longer time period')
        
        return warnings