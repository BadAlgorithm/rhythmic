import numpy as np
from scipy.fft import fft, fftfreq
from scipy.signal import find_peaks
from typing import Dict, List, Any
import logging

from ..utils.math_utils import pad_to_power_of_two

class FourierAnalyzer:
    """Analyzes signals using Fourier transforms to find periodic patterns"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def analyze(self, signal: np.ndarray, sample_rate: float = 1/60) -> Dict[str, Any]:
        """Analyze signal for periodic patterns using FFT
        
        Args:
            signal: Input signal array
            sample_rate: Sampling rate in Hz (default: 1/60 = 1 sample per minute)
            
        Returns:
            Dictionary containing Fourier analysis results
        """
        if len(signal) < 4:
            raise ValueError('Signal too short for Fourier analysis')
        
        signal = np.asarray(signal).flatten()
        
        # Remove DC component and normalize
        signal_mean = np.mean(signal)
        signal_std = np.std(signal)
        
        if signal_std == 0:
            # Constant signal
            return {
                'type': 'fourier',
                'mean': float(signal_mean),
                'std': 0.0,
                'coefficients': []
            }
        
        # Center the signal
        centered_signal = signal - signal_mean
        
        # Pad to power of 2 for efficiency
        padded_signal, original_length = pad_to_power_of_two(centered_signal)
        
        # Apply window function to reduce spectral leakage
        window = np.hanning(len(padded_signal))
        windowed_signal = padded_signal * window
        
        # Compute FFT
        fft_values = fft(windowed_signal)
        frequencies = fftfreq(len(padded_signal), 1/sample_rate)
        
        # Take only positive frequencies
        positive_freqs = frequencies[:len(frequencies)//2]
        positive_fft = fft_values[:len(fft_values)//2]
        
        # Calculate magnitudes and phases
        magnitudes = np.abs(positive_fft)
        phases = np.angle(positive_fft)
        
        # Find dominant frequencies
        dominant_coeffs = self._find_dominant_frequencies(
            positive_freqs, magnitudes, phases, count=8
        )
        
        self.logger.debug(f'Found {len(dominant_coeffs)} dominant frequencies')
        
        return {
            'type': 'fourier',
            'mean': float(signal_mean),
            'std': float(signal_std),
            'coefficients': dominant_coeffs
        }
    
    def _find_dominant_frequencies(self, frequencies: np.ndarray, magnitudes: np.ndarray, 
                                 phases: np.ndarray, count: int = 5) -> List[Dict[str, float]]:
        """Find dominant frequency components
        
        Args:
            frequencies: Frequency array
            magnitudes: Magnitude array  
            phases: Phase array
            count: Number of dominant frequencies to return
            
        Returns:
            List of dominant frequency dictionaries
        """
        # Skip DC component (frequency = 0)
        non_dc_mask = frequencies > 1e-10
        
        if not np.any(non_dc_mask):
            return []
        
        freqs_filtered = frequencies[non_dc_mask]
        mags_filtered = magnitudes[non_dc_mask]
        phases_filtered = phases[non_dc_mask]
        
        # Find peaks in the magnitude spectrum
        # Use height threshold as percentage of max magnitude
        peak_threshold = 0.1 * np.max(mags_filtered)
        peak_indices, peak_properties = find_peaks(
            mags_filtered, 
            height=peak_threshold,
            distance=max(1, len(mags_filtered) // 50)  # Minimum distance between peaks
        )
        
        if len(peak_indices) == 0:
            # No significant peaks found, take highest magnitudes
            sorted_indices = np.argsort(mags_filtered)[::-1]
            peak_indices = sorted_indices[:min(count, len(sorted_indices))]
        
        # Sort peaks by magnitude (descending)
        peak_magnitudes = mags_filtered[peak_indices]
        sorted_peak_order = np.argsort(peak_magnitudes)[::-1]
        peak_indices = peak_indices[sorted_peak_order]
        
        # Take top frequencies
        peak_indices = peak_indices[:count]
        
        coefficients = []
        max_magnitude = np.max(mags_filtered)
        
        for idx in peak_indices:
            freq = freqs_filtered[idx]
            magnitude = mags_filtered[idx]
            phase = phases_filtered[idx]
            
            # Calculate confidence based on magnitude relative to max
            confidence = float(magnitude / max_magnitude) if max_magnitude > 0 else 0
            
            # Skip very low confidence frequencies
            if confidence < 0.05:
                continue
            
            # Calculate period in minutes
            period_minutes = (1 / freq) / 60 if freq > 0 else float('inf')
            
            coefficients.append({
                'frequency': float(freq),
                'amplitude': float(magnitude),
                'phase': float(phase),
                'period_minutes': float(period_minutes),
                'confidence': confidence
            })
        
        return coefficients
    
    def synthesize(self, coefficients: List[Dict[str, float]], length: int, 
                  sample_rate: float = 1/60) -> np.ndarray:
        """Synthesize signal from Fourier coefficients
        
        Args:
            coefficients: List of frequency coefficients
            length: Length of signal to generate
            sample_rate: Sampling rate in Hz
            
        Returns:
            Synthesized signal
        """
        if not coefficients:
            return np.zeros(length)
        
        t = np.arange(length) / sample_rate
        signal = np.zeros(length)
        
        for coeff in coefficients:
            freq = coeff['frequency']
            amplitude = coeff['amplitude']
            phase = coeff['phase']
            
            # Add sinusoidal component
            component = amplitude * np.cos(2 * np.pi * freq * t + phase)
            signal += component
        
        return signal
    
    def estimate_noise_level(self, signal: np.ndarray, percentile: float = 95) -> float:
        """Estimate noise level in signal
        
        Args:
            signal: Input signal
            percentile: Percentile for noise estimation
            
        Returns:
            Estimated noise level
        """
        # Use high-frequency components as noise estimate
        padded_signal, _ = pad_to_power_of_two(signal)
        fft_values = fft(padded_signal)
        magnitudes = np.abs(fft_values)
        
        # Take high-frequency half as noise
        high_freq_mags = magnitudes[len(magnitudes)//2:]
        noise_level = np.percentile(high_freq_mags, percentile)
        
        return float(noise_level)