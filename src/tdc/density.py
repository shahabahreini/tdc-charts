import numpy as np
from scipy.stats import skew, kurtosis
from typing import Tuple, Dict

def compute_density_profile(ticks: np.ndarray, low: float, high: float, nbins: int, volume: np.ndarray = None) -> Tuple[np.ndarray, np.ndarray]:
    """
    Computes the density profile of a given tick array.
    """
    if high == low:
        # Zero-range bar
        return np.ones(nbins), np.linspace(low, low + 1e-5, nbins + 1)
        
    bins = np.linspace(low, high, nbins + 1)
    
    if volume is not None and len(volume) == len(ticks):
        counts, _ = np.histogram(ticks, bins=bins, weights=volume)
    else:
        counts, _ = np.histogram(ticks, bins=bins)
        
    max_count = np.max(counts)
    if max_count == 0:
        density = np.zeros(nbins)
    else:
        density = counts / max_count
        
    return density, bins

def compute_profile_stats(ticks: np.ndarray, density: np.ndarray, bins: np.ndarray) -> Dict:
    """
    Computes statistical features for the density profile.
    """
    bin_centers = (bins[:-1] + bins[1:]) / 2
    
    if np.sum(density) == 0:
        poc_price = bin_centers[len(bin_centers)//2]
        concentration_ratio = 0.0
    else:
        poc_price = bin_centers[np.argmax(density)]
        concentration_ratio = np.max(density) / np.mean(density)
        
    # Value area (68% mass)
    total_mass = np.sum(density)
    target_mass = total_mass * 0.68
    
    # Sort bins by density descending to accumulate mass (Market Profile method)
    sorted_idx = np.argsort(density)[::-1]
    accumulated_mass = 0.0
    va_indices = []
    
    for idx in sorted_idx:
        accumulated_mass += density[idx]
        va_indices.append(idx)
        if accumulated_mass >= target_mass:
            break
            
    if not va_indices:
        val, vah = bins[0], bins[-1]
    else:
        val = bins[min(va_indices)]
        vah = bins[max(va_indices) + 1]

    # Handle single constant value arrays for skew/kurtosis
    if len(np.unique(ticks)) <= 1:
        s, k = 0.0, 0.0
    else:
        s = float(skew(ticks, bias=False))
        k = float(kurtosis(ticks, bias=False))
        
    return {
        "poc_price": poc_price,
        "skew": s,
        "kurtosis": k,
        "value_area_low": val,
        "value_area_high": vah,
        "concentration_ratio": concentration_ratio
    }
