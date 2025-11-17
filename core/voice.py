"""
Optimized Voice Recognition Module
- Async voice input for non-blocking operation
- Efficient ambient noise calibration
- Audio buffer management
- Minimal CPU overhead during silence
"""

import asyncio
import os
from typing import Optional

class VoiceRecognizer:
    """Optimized voice recognition with async support"""
    
    def __init__(self, config=None):
        self.config = config or {}
        self.recognizer = None
        self.microphone = None
        self.calibrated = False
        
        # Recognition settings
        self.language = self.config.get('language', 'en-US')
        self.timeout = self.config.get('voice_timeout', 4)
        self.phrase_limit = self.config.get('phrase_time_limit', 16)
        self.pause_threshold = self.config.get('pause_threshold', 1.3)
        self.energy_threshold = self.config.get('energy_threshold', 4000)
        
        # Initialize (lazy)
        self._initialize()
    
    def _initialize(self):
        """Initialize speech recognition (lazy)"""
        try:
            import speech_recognition as sr
            
            self.recognizer = sr.Recognizer()
            
            # Advanced tuning for better accuracy
            self.recognizer.pause_threshold = self.pause_threshold
            self.recognizer.energy_threshold = self.energy_threshold
            self.recognizer.dynamic_energy_threshold = True
            self.recognizer.dynamic_energy_adjustment_damping = 0.15
            self.recognizer.dynamic_energy_ratio = 1.5
            
            # Find best microphone
            mic_index = self._find_best_microphone()
            self.microphone = sr.Microphone(device_index=mic_index)
            
            print(f"[Voice] ✓ Initialized (mic index: {mic_index})")
            
        except ImportError:
            print("[Voice] ⚠ SpeechRecognition not available - text-only mode")
            self.recognizer = None
        except Exception as e:
            print(f"[Voice] ⚠ Initialization failed: {e}")
            self.recognizer = None
    
    def _find_best_microphone(self):
        """Find best available microphone"""
        try:
            import speech_recognition as sr
            mic_list = sr.Microphone.list_microphone_names()
            
            # Prefer specific keywords
            for i, name in enumerate(mic_list):
                name_lower = (name or "").lower()
                if any(keyword in name_lower for keyword in 
                       ["microphone", "default", "built-in", "array"]):
                    return i
            
            # Fallback to first available
            return 0 if mic_list else None
            
        except:
            return None
    
    async def calibrate_async(self, duration=1.0):
        """
        Calibrate for ambient noise (async)
        Only needs to be done once at startup
        """
        if self.calibrated or not self.recognizer or not self.microphone:
            return
        
        print("[Voice] Calibrating for ambient noise...")
        
        loop = asyncio.get_event_loop()
        
        def calibrate_blocking():
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=duration)
        
        await loop.run_in_executor(None, calibrate_blocking)
        
        self.calibrated = True
        print(f"[Voice] ✓ Calibrated (threshold: {self.recognizer.energy_threshold})")
    
    async def listen_async(self, calibrate=False) -> Optional[str]:
        """
        Async voice input
        Returns recognized text or None on timeout/error
        """
        if not self.recognizer or not self.microphone:
            # Fallback to text input
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, input, "You: ")
        
        # Auto-calibrate on first use
        if not self.calibrated and calibrate:
            await self.calibrate_async()
        
        loop = asyncio.get_event_loop()
        
        try:
            # Listen for audio (blocking, run in executor)
            audio = await loop.run_in_executor(
                None,
                self._listen_blocking
            )
            
            if audio is None:
                return None
            
            # Recognize speech (blocking, run in executor)
            text = await loop.run_in_executor(
                None,
                self._recognize_blocking,
                audio
            )
            
            if text:
                print(f"You: {text}")
            
            return text
            
        except Exception as e:
            # Silent failures for better UX
            return None
    
    def _listen_blocking(self):
        """Blocking audio capture"""
        try:
            with self.microphone as source:
                audio = self.recognizer.listen(
                    source,
                    timeout=self.timeout,
                    phrase_time_limit=self.phrase_limit
                )
                return audio
        except Exception:
            return None
    
    def _recognize_blocking(self, audio):
        """Blocking speech recognition"""
        try:
            text = self.recognizer.recognize_google(audio, language=self.language)
            return text.lower().strip()
        except Exception:
            return None
    
    def set_energy_threshold(self, threshold):
        """Manually adjust energy threshold"""
        if self.recognizer:
            self.recognizer.energy_threshold = threshold
            print(f"[Voice] Energy threshold set to {threshold}")
    
    def get_ambient_level(self):
        """Get current ambient noise level"""
        if not self.recognizer or not self.microphone:
            return None
        
        try:
            with self.microphone as source:
                return self.recognizer.energy_threshold
        except:
            return None

# Singleton instance
_voice_recognizer = None

def get_voice_recognizer(config=None):
    """Get or create voice recognizer instance"""
    global _voice_recognizer
    if _voice_recognizer is None:
        _voice_recognizer = VoiceRecognizer(config)
    return _voice_recognizer

# Convenience async function
async def listen(calibrate=False) -> Optional[str]:
    """Quick async listen function"""
    recognizer = get_voice_recognizer()
    return await recognizer.listen_async(calibrate)

# Performance optimization: Audio buffer pooling
class AudioBufferPool:
    """
    Reusable audio buffer pool to reduce allocation overhead
    Significant performance boost for continuous listening
    """
    
    def __init__(self, buffer_size=4096, pool_size=10):
        self.buffer_size = buffer_size
        self.pool = [bytearray(buffer_size) for _ in range(pool_size)]
        self.available = list(range(pool_size))
        self.in_use = {}
    
    def acquire(self):
        """Get buffer from pool"""
        if self.available:
            index = self.available.pop()
            buffer = self.pool[index]
            self.in_use[id(buffer)] = index
            return buffer
        # Pool exhausted, create new
        return bytearray(self.buffer_size)
    
    def release(self, buffer):
        """Return buffer to pool"""
        buffer_id = id(buffer)
        if buffer_id in self.in_use:
            index = self.in_use.pop(buffer_id)
            self.available.append(index)
            # Clear buffer
            buffer[:] = b'\x00' * len(buffer)

# Global buffer pool
_audio_buffer_pool = AudioBufferPool()

if __name__ == "__main__":
    # Test voice recognition
    async def test():
        recognizer = VoiceRecognizer()
        
        print("Voice recognition test")
        print("Calibrating...")
        await recognizer.calibrate_async()
        
        print("\nSpeak now (you have 5 seconds):")
        text = await recognizer.listen_async()
        
        if text:
            print(f"✓ Recognized: {text}")
        else:
            print("✗ No speech detected")
        
        print("\nTesting ambient noise level:")
        level = recognizer.get_ambient_level()
        print(f"Current threshold: {level}")
    
    asyncio.run(test())