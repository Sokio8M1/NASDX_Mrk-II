"""
Optimized Speech Engine
- Async TTS for non-blocking speech
- Sentence-level interruption support
- Memory-efficient audio streaming
- Fallback engine support
"""

import asyncio
import os
import tempfile
from pathlib import Path

class SpeechEngine:
    """Optimized TTS engine with multiple backends"""
    
    def __init__(self, config=None):
        self.config = config or {}
        self.rate = self.config.get('voice_rate', 170)
        self.volume = self.config.get('voice_volume', 1.0)
        self.engine_type = None
        self.engine = None
        self._is_speaking = False
        self._interrupt_flag = False
        
        # Try to initialize best available engine
        self._initialize_engine()
    
    def _initialize_engine(self):
        """Initialize TTS engine (lazy)"""
        
        # Try Edge-TTS first (best quality, async-native)
        try:
            import edge_tts
            self.engine_type = "edge"
            self.voice_id = "en-US-EricNeural"
            print("[Speech] ✓ Edge-TTS initialized (neural voice)")
            return
        except ImportError:
            pass
        
        # Fallback to pyttsx4
        try:
            import pyttsx4
            self.engine = pyttsx4.init()
            self.engine.setProperty('rate', self.rate)
            self.engine.setProperty('volume', self.volume)
            self.engine_type = "pyttsx4"
            print("[Speech] ✓ pyttsx4 initialized (system voice)")
            return
        except:
            pass
        
        # Last resort: espeak (Linux)
        if os.name != "nt":
            import shutil
            if shutil.which("espeak"):
                self.engine_type = "espeak"
                print("[Speech] ✓ espeak initialized (basic voice)")
                return
        
        print("[Speech] ⚠ No TTS engine available - text-only mode")
        self.engine_type = None
    
    async def speak_async(self, text, allow_interrupt=True):
        """
        Async speech output
        Allows concurrent operations while speaking
        """
        if not text:
            return
        
        self._is_speaking = True
        self._interrupt_flag = False
        
        print(f"Jarvis: {text}")
        
        if self.engine_type == "edge":
            await self._speak_edge(text, allow_interrupt)
        elif self.engine_type == "pyttsx4":
            await self._speak_pyttsx4(text, allow_interrupt)
        elif self.engine_type == "espeak":
            await self._speak_espeak(text)
        
        self._is_speaking = False
    
    async def _speak_edge(self, text, allow_interrupt):
        """Edge-TTS implementation (streaming)"""
        import edge_tts
        
        # Split into sentences for interruption points
        sentences = self._split_sentences(text) if allow_interrupt else [text]
        
        for sentence in sentences:
            if self._interrupt_flag:
                break
            
            # Create temp file for audio
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
                tmp_path = tmp.name
            
            try:
                # Generate speech
                communicate = edge_tts.Communicate(
                    sentence,
                    voice=self.voice_id,
                    rate=f"+{int((self.rate - 170) / 2)}%"
                )
                await communicate.save(tmp_path)
                
                # Play audio (async)
                await self._play_audio_async(tmp_path)
                
            finally:
                # Cleanup
                try:
                    os.remove(tmp_path)
                except:
                    pass
    
    async def _speak_pyttsx4(self, text, allow_interrupt):
        """pyttsx4 implementation (blocking, run in executor)"""
        sentences = self._split_sentences(text) if allow_interrupt else [text]
        
        loop = asyncio.get_event_loop()
        
        for sentence in sentences:
            if self._interrupt_flag:
                break
            
            # Run in thread pool to avoid blocking
            await loop.run_in_executor(
                None,
                self._pyttsx4_speak_blocking,
                sentence
            )
    
    def _pyttsx4_speak_blocking(self, text):
        """Blocking pyttsx4 call"""
        try:
            self.engine.say(text)
            self.engine.runAndWait()
        except:
            pass
    
    async def _speak_espeak(self, text):
        """espeak implementation (subprocess)"""
        process = await asyncio.create_subprocess_exec(
            "espeak",
            text,
            "-s", str(self.rate),
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL
        )
        await process.wait()
    
    async def _play_audio_async(self, audio_path):
        """Play audio file asynchronously"""
        try:
            # Try pygame first (non-blocking)
            import pygame
            pygame.mixer.init()
            pygame.mixer.music.load(audio_path)
            pygame.mixer.music.play()
            
            # Wait for playback to finish (with interrupt check)
            while pygame.mixer.music.get_busy():
                if self._interrupt_flag:
                    pygame.mixer.music.stop()
                    break
                await asyncio.sleep(0.1)
            
        except ImportError:
            # Fallback to playsound (blocking)
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                self._playsound_blocking,
                audio_path
            )
    
    def _playsound_blocking(self, audio_path):
        """Blocking playsound fallback"""
        try:
            import playsound
            playsound.playsound(audio_path)
        except:
            pass
    
    def _split_sentences(self, text):
        """Split text into sentences for interruption"""
        import re
        sentences = re.split(r'[.!?]+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def interrupt(self):
        """Stop current speech"""
        self._interrupt_flag = True
        
        if self.engine_type == "pyttsx4" and self.engine:
            try:
                self.engine.stop()
            except:
                pass
    
    @property
    def is_speaking(self):
        """Check if currently speaking"""
        return self._is_speaking

# Singleton instance
_speech_engine = None

def get_speech_engine(config=None):
    """Get or create speech engine instance"""
    global _speech_engine
    if _speech_engine is None:
        _speech_engine = SpeechEngine(config)
    return _speech_engine

# Convenience async function
async def speak(text, allow_interrupt=True):
    """Quick async speak function"""
    engine = get_speech_engine()
    await engine.speak_async(text, allow_interrupt)

if __name__ == "__main__":
    # Test speech engine
    async def test():
        engine = SpeechEngine()
        
        print("Testing speech engine...")
        await engine.speak_async("Hello Sir. This is a test of the optimized speech system.")
        
        print("\nTesting interruption...")
        task = asyncio.create_task(
            engine.speak_async(
                "This is a long sentence that should be interrupted. "
                "It has multiple parts and will be split for testing. "
                "You should not hear this final part."
            )
        )
        
        await asyncio.sleep(2)
        engine.interrupt()
        await task
        
        print("\nSpeech test complete!")
    
    asyncio.run(test())