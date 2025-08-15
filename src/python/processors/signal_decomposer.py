import numpy as np
import pywt
from typing import Dict, List, Any
import logging

from ..utils.math_utils import calculate_energy, pad_to_power_of_two

class SignalDecomposer:
    """Decomposes signals using wavelet transforms"""
    
    def __init__(self, wavelet_type: str = 'db4'):
        self.wavelet_type = wavelet_type
        self.logger = logging.getLogger(__name__)
        
        # Validate wavelet type
        if wavelet_type not in pywt.wavelist():
            self.logger.warning(f'Unknown wavelet {wavelet_type}, using db4')
            self.wavelet_type = 'db4'
    
    def decompose(self, signal: np.ndarray, levels: int = 5) -> Dict[str, Any]:
        """Decompose signal using wavelet transform
        
        Args:
            signal: Input signal array
            levels: Number of decomposition levels
            
        Returns:
            Dictionary containing decomposition results
        """
        if len(signal) < 4:
            raise ValueError('Signal too short for wavelet decomposition')
        
        # Ensure signal is 1D
        signal = np.asarray(signal).flatten()
        original_length = len(signal)
        
        # Pad signal if needed for wavelet decomposition
        min_length = 2 ** levels
        if len(signal) < min_length:
            signal = np.pad(signal, (0, min_length - len(signal)), 
                          mode='edge')  # Pad with edge values
        
        try:
            # Perform wavelet decomposition
            coeffs = pywt.wavedec(signal, self.wavelet_type, level=levels)
            
            # coeffs[0] is approximation, coeffs[1:] are details
            approximation = coeffs[0]
            details = coeffs[1:]
            
            # Calculate energy distribution
            total_energy = calculate_energy(signal)
            approx_energy = calculate_energy(approximation)
            detail_energies = [calculate_energy(detail) for detail in details]
            
            # Smoothness ratio (energy in approximation vs details)
            detail_total_energy = sum(detail_energies)
            smoothness_ratio = approx_energy / (approx_energy + detail_total_energy) if total_energy > 0 else 0
            
            # Energy distribution as percentages
            energy_dist = [approx_energy] + detail_energies
            energy_percentages = [e / total_energy * 100 if total_energy > 0 else 0 for e in energy_dist]
            
            self.logger.debug(f'Decomposed signal into {levels} levels')
            self.logger.debug(f'Approximation energy: {approx_energy:.2f} ({energy_percentages[0]:.1f}%)')
            
            return {
                'approximation': approximation,
                'details': details,
                'levels': len(details),
                'wavelet_type': self.wavelet_type,
                'original_length': original_length,
                'smoothness_ratio': smoothness_ratio,
                'energy_distribution': energy_percentages,
                'coefficients': coeffs  # Keep for reconstruction if needed
            }
            
        except Exception as e:
            self.logger.error(f'Wavelet decomposition failed: {e}')
            # Fallback: return signal as approximation
            return {
                'approximation': signal,
                'details': [],
                'levels': 0,
                'wavelet_type': self.wavelet_type,
                'original_length': original_length,
                'smoothness_ratio': 1.0,
                'energy_distribution': [100.0],
                'coefficients': [signal]
            }
    
    def reconstruct(self, coefficients: List[np.ndarray], original_length: int = None) -> np.ndarray:
        """Reconstruct signal from wavelet coefficients
        
        Args:
            coefficients: Wavelet coefficients from decompose()
            original_length: Original signal length to truncate to
            
        Returns:
            Reconstructed signal
        """
        try:
            reconstructed = pywt.waverec(coefficients, self.wavelet_type)
            
            if original_length is not None:
                reconstructed = reconstructed[:original_length]
                
            return reconstructed
            
        except Exception as e:
            self.logger.error(f'Signal reconstruction failed: {e}')
            # Return approximation if reconstruction fails
            return coefficients[0] if coefficients else np.array([])
    
    def get_high_frequency_component(self, details: List[np.ndarray]) -> np.ndarray:
        """Get combined high-frequency components for spike detection
        
        Args:
            details: Detail coefficients from decomposition
            
        Returns:
            Combined high-frequency signal
        """
        if not details:
            return np.array([])
        
        # Combine detail levels (higher levels = higher frequency)
        # Weight higher frequency components more
        combined = np.zeros_like(details[-1])
        
        for i, detail in enumerate(reversed(details)):
            weight = 2 ** i  # Higher weight for higher frequencies
            if len(detail) == len(combined):
                combined += weight * detail
            else:
                # Resize to match if needed
                resized = np.interp(np.linspace(0, 1, len(combined)),
                                  np.linspace(0, 1, len(detail)), detail)
                combined += weight * resized
        
        return combined