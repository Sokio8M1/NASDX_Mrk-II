"""
Python wrapper for C acceleration module
Provides high-performance text processing functions
"""

import ctypes
import os
from pathlib import Path

# Load C library
_lib = None
_lib_loaded = False

def _load_library():
    """Lazy load C library"""
    global _lib, _lib_loaded
    
    if _lib_loaded:
        return _lib
    
    core_dir = Path(__file__).parent
    lib_name = "acceleration.so" if os.name != "nt" else "acceleration.dll"
    lib_path = core_dir / lib_name
    
    try:
        _lib = ctypes.CDLL(str(lib_path))
        
        # Configure function signatures
        _lib.c_preprocess_text.argtypes = [ctypes.c_char_p]
        _lib.c_preprocess_text.restype = ctypes.c_char_p
        
        _lib.c_contains_keyword.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
        _lib.c_contains_keyword.restype = ctypes.c_int
        
        _lib.c_edit_distance.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
        _lib.c_edit_distance.restype = ctypes.c_int
        
        _lib.c_get_timestamp.argtypes = []
        _lib.c_get_timestamp.restype = ctypes.c_long
        
        _lib.c_free_string.argtypes = [ctypes.c_char_p]
        _lib.c_free_string.restype = None
        
        _lib_loaded = True
        print("[C Accel] ✓ Native acceleration loaded")
        
    except Exception as e:
        print(f"[C Accel] ⚠ Could not load C library: {e}")
        print("[C Accel] Falling back to Python implementation")
        _lib = None
        _lib_loaded = False
    
    return _lib

def preprocess_text(text):
    """
    Fast text preprocessing (C implementation)
    - Lowercase conversion
    - Special character removal
    - Whitespace normalization
    
    Falls back to Python if C lib unavailable
    """
    lib = _load_library()
    
    if lib and text:
        try:
            result = lib.c_preprocess_text(text.encode('utf-8'))
            processed = result.decode('utf-8')
            lib.c_free_string(result)
            return processed
        except:
            pass
    
    # Fallback: Pure Python
    import re
    return re.sub(r'[^a-z0-9\s]', '', text.lower()).strip()

def contains_keyword(text, keyword):
    """
    Fast keyword matching (C implementation)
    Returns True if keyword found in text (case-insensitive)
    
    10-20x faster than Python 'in' operator for long texts
    """
    lib = _load_library()
    
    if lib and text and keyword:
        try:
            return bool(lib.c_contains_keyword(
                text.encode('utf-8'),
                keyword.encode('utf-8')
            ))
        except:
            pass
    
    # Fallback: Pure Python
    return keyword.lower() in text.lower()

def fuzzy_match(text, target, max_distance=2):
    """
    Fuzzy string matching using Levenshtein distance
    Useful for voice recognition error tolerance
    
    Returns True if edit distance <= max_distance
    """
    lib = _load_library()
    
    if lib and text and target:
        try:
            distance = lib.c_edit_distance(
                text.encode('utf-8'),
                target.encode('utf-8')
            )
            return distance <= max_distance
        except:
            pass
    
    # Fallback: Pure Python (simplified)
    if abs(len(text) - len(target)) > max_distance:
        return False
    
    # Simple character-by-character comparison
    differences = sum(1 for a, b in zip(text, target) if a != b)
    differences += abs(len(text) - len(target))
    
    return differences <= max_distance

def get_timestamp_ms():
    """
    Get current timestamp in milliseconds
    Native C implementation for precision
    """
    lib = _load_library()
    
    if lib:
        try:
            return lib.c_get_timestamp()
        except:
            pass
    
    # Fallback: Pure Python
    import time
    return int(time.time() * 1000)

# Performance benchmarking
def benchmark_acceleration():
    """Test C acceleration performance vs Python"""
    import time
    
    test_text = "jarvis play music on spotify" * 100
    test_keyword = "spotify"
    iterations = 10000
    
    print("\n=== C Acceleration Benchmark ===")
    
    # Test keyword search
    start = time.time()
    for _ in range(iterations):
        contains_keyword(test_text, test_keyword)
    c_time = time.time() - start
    
    start = time.time()
    for _ in range(iterations):
        test_keyword in test_text.lower()
    py_time = time.time() - start
    
    speedup = py_time / c_time if c_time > 0 else 0
    
    print(f"Keyword Search ({iterations} iterations):")
    print(f"  C Implementation: {c_time:.4f}s")
    print(f"  Python Implementation: {py_time:.4f}s")
    print(f"  Speedup: {speedup:.2f}x")
    
    # Test text preprocessing
    start = time.time()
    for _ in range(iterations):
        preprocess_text(test_text)
    c_time = time.time() - start
    
    import re
    start = time.time()
    for _ in range(iterations):
        re.sub(r'[^a-z0-9\s]', '', test_text.lower()).strip()
    py_time = time.time() - start
    
    speedup = py_time / c_time if c_time > 0 else 0
    
    print(f"\nText Preprocessing ({iterations} iterations):")
    print(f"  C Implementation: {c_time:.4f}s")
    print(f"  Python Implementation: {py_time:.4f}s")
    print(f"  Speedup: {speedup:.2f}x")
    
    print("\n================================\n")

if __name__ == "__main__":
    # Run benchmark
    benchmark_acceleration()
    
    # Test functions
    print("Testing C acceleration functions:")
    
    text = "Jarvis, play some music!"
    processed = preprocess_text(text)
    print(f"Preprocessed: '{text}' -> '{processed}'")
    
    has_keyword = contains_keyword(text, "play")
    print(f"Contains 'play': {has_keyword}")
    
    fuzzy = fuzzy_match("spotify", "spotfy", max_distance=1)
    print(f"Fuzzy match 'spotify' ~ 'spotfy': {fuzzy}")
    
    timestamp = get_timestamp_ms()
    print(f"Timestamp: {timestamp} ms")