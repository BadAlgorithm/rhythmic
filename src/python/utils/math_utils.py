import numpy as np
from typing import List, Tuple

def calculate_energy(signal: np.ndarray) -> float:
    """Calculate signal energy (sum of squares)"""
    return float(np.sum(signal ** 2))

def normalize_signal(signal: np.ndarray) -> np.ndarray:
    """Normalize signal to zero mean and unit variance"""
    mean = np.mean(signal)
    std = np.std(signal)
    if std == 0:
        return signal - mean
    return (signal - mean) / std

def find_peaks_simple(signal: np.ndarray, threshold: float = 0.5) -> List[int]:
    """Find simple peaks in signal above threshold"""
    peaks = []
    for i in range(1, len(signal) - 1):
        if (signal[i] > signal[i-1] and 
            signal[i] > signal[i+1] and 
            signal[i] > threshold):
            peaks.append(i)
    return peaks

def smooth_signal(signal: np.ndarray, window_size: int = 5) -> np.ndarray:
    """Apply simple moving average smoothing"""
    if window_size <= 1:
        return signal
    
    kernel = np.ones(window_size) / window_size
    return np.convolve(signal, kernel, mode='same')

def pad_to_power_of_two(signal: np.ndarray) -> Tuple[np.ndarray, int]:
    """Pad signal to next power of 2 for FFT efficiency
    
    Returns:
        Tuple of (padded_signal, original_length)
    """
    original_length = len(signal)
    next_power = 2 ** int(np.ceil(np.log2(original_length)))
    
    if next_power == original_length:
        return signal, original_length
    
    # Pad with last value to avoid discontinuities
    last_value = signal[-1] if len(signal) > 0 else 0
    padded = np.pad(signal, (0, next_power - original_length), 
                   mode='constant', constant_values=last_value)
    
    return padded, original_length