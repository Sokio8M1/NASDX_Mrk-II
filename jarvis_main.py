#!/usr/bin/env python3
"""
Jarvis v1.7r - Optimized Core (fixed)
Performance-focused refactor with modular architecture
"""

import os
import sys
import asyncio
import signal
from pathlib import Path
import psutil
import time

# Lazy modules
_speech_engine = None
_voice_recognizer = None
_ai_clients = {}

# Try to import legacy core (graceful if it fails)
LEGACY_AVAILABLE = False
try:
    # Many legacy filenames include characters that can't be used as module names.
    # If your legacy file is literally named "Jarvis_v1.7r_core.py" Python import
    # will fail (dot in name). Rename the file to a valid module name or import via importlib.
    import importlib
    spec_name = "Jarvis_v1_7r_core"  # try this variant first
    legacy = importlib.import_module(spec_name)
    LEGACY_AVAILABLE = True
except Exception as e:
    # fallback: try import by filename using importlib (if file exists)
    try:
        import importlib.util
        candidate = Path(__file__).parent / "Jarvis_v1.7r_core.py"
        if candidate.exists():
            spec = importlib.util.spec_from_file_location("legacy_core", str(candidate))
            legacy = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(legacy)
            LEGACY_AVAILABLE = True
        else:
            print("[LEGACY MODULE] Not found or import failed:", e)
    except Exception as e2:
        print("[LEGACY MODULE] import failed:", e2)
        LEGACY_AVAILABLE = False

# Paths & config
SCRIPT_DIR = Path(__file__).parent
CONFIG_PATH = SCRIPT_DIR / "config.json"
DATA_PATH = SCRIPT_DIR / "assistant_data.json"

# Global state
_is_running = True
_is_muted = False
_current_ai = "openrouter"

class PerformanceMonitor:
    """Track resource usage"""
    def __init__(self):
        self.process = psutil.Process()
        self.start_time = time.time()
        self.baseline_memory = self.process.memory_info().rss / 1024 / 1024
        
    def get_stats(self):
        mem = self.process.memory_info().rss / 1024 / 1024
        return {
            'cpu_percent': self.process.cpu_percent(interval=0.1),
            'memory_mb': mem,
            'memory_delta': mem - self.baseline_memory,
            'uptime': time.time() - self.start_time
        }

monitor = PerformanceMonitor()

def lazy_import_speech():
    """Lazy load TTS engine"""
    global _speech_engine
    if _speech_engine is None:
        from core.speech import SpeechEngine
        _speech_engine = SpeechEngine()
    return _speech_engine

def lazy_import_voice():
    """Lazy load voice recognition"""
    global _voice_recognizer
    if _voice_recognizer is None:
        from core.voice import VoiceRecognizer
        _voice_recognizer = VoiceRecognizer()
    return _voice_recognizer

def lazy_import_ai(model_name):
    """Lazy load AI clients"""
    global _ai_clients
    if model_name not in _ai_clients:
        from core.ai_interface import AIInterface
        _ai_clients[model_name] = AIInterface(model_name)
    return _ai_clients[model_name]

async def run_blocking(fn, *args, **kwargs):
    """Run a blocking function in a thread to avoid blocking the event loop."""
    return await asyncio.to_thread(fn, *args, **kwargs)

async def speak(text, allow_interrupt=True):
    """Unified async speak: prefer new engine, fallback to legacy blocking speak."""
    global _is_muted
    if _is_muted:
        print(f"[MUTED] {text}")
        return

    # Prefer new lazy engine if available
    try:
        engine = lazy_import_speech()
    except Exception:
        engine = None

    if engine:
        try:
            # The engine should provide speak_async(text, allow_interrupt)
            await engine.speak_async(text, allow_interrupt)
            return
        except Exception as e:
            print("[speak] new engine failed:", e)

    # Fallback to legacy's blocking speak (if available)
    if LEGACY_AVAILABLE:
        try:
            await run_blocking(getattr(legacy, "speak", lambda *a, **k: print("Jarvis:", a[0])), text, allow_interrupt)
            return
        except Exception as e:
            print("[speak] legacy speak failed:", e)

    # Last fallback: quick print
    print("Jarvis:", text)

async def listen():
    """Unified async listen: prefer new async recognizer, fallback to legacy blocking listen."""
    try:
        recognizer = lazy_import_voice()
        return await recognizer.listen_async()
    except Exception:
        # fallback to legacy blocking listen which may block; run in thread
        if LEGACY_AVAILABLE:
            try:
                if hasattr(legacy, "listen"):
                    return await run_blocking(legacy.listen)
            except Exception as e:
                print("[listen] legacy listen failed:", e)
        # Final fallback: input prompt (non-blocking via thread)
        try:
            return await asyncio.to_thread(input, "You: ")
        except Exception:
            return ""

async def contextual_prompts_loop():
    """Background loop to run legacy contextual prompts if available."""
    while _is_running:
        try:
            if LEGACY_AVAILABLE and hasattr(legacy, "check_contextual_prompts"):
                # legacy.check_contextual_prompts may expect a speak function; pass legacy.speak if available
                if hasattr(legacy, "check_contextual_prompts"):
                    await run_blocking(legacy.check_contextual_prompts, getattr(legacy, "speak", None))
            else:
                # nothing to do if no legacy module
                await asyncio.sleep(60)
        except Exception as e:
            print("[contextual_prompts_loop] error:", e)
            await asyncio.sleep(10)
        # run every 60 seconds in normal operation
        await asyncio.sleep(60)

async def process_command_async(query):
    """Async command processor"""
    if not query:
        return
    
    query_lower = query.lower()
    
    # Fast path for common commands
    # Properly check for both words
    if "time" in query_lower and "what" in query_lower:
        from datetime import datetime
        await speak(f"The current time is {datetime.now().strftime('%I:%M %p')}, Sir.")
        return
    
    if "weather" in query_lower:
        # try fast weather module, else fallback
        try:
            from modules.weather import get_weather_fast
            weather = await get_weather_fast()
            await speak(weather)
            return
        except Exception:
            # fallback to legacy weather handler (blocking) if available
            try:
                if LEGACY_AVAILABLE and hasattr(legacy, "handle_weather_query"):
                    info = await run_blocking(legacy.handle_weather_query, query)
                    if isinstance(info, dict):
                        summary = f"Weather in {info.get('city','unknown')}: {info.get('condition','n/a')}, {info.get('temperature','n/a')}°C"
                        await speak(summary)
                    else:
                        # if legacy already spoke or returned text
                        await speak(str(info))
                    return
            except Exception as e:
                print("[weather fallback] error:", e)
            await speak("Weather information is not available right now.")
            return
    
    # You can add more command parsers here...

    # AI fallback
    try:
        ai = lazy_import_ai(_current_ai)
        response = await ai.chat_async(query)
    except Exception as e:
        print("[AI] client failed:", e)
        response = "Sorry, I couldn't process that right now."
    await speak(response)

async def main_loop():
    """Main event loop - optimized"""
    global _is_running

    # Start contextual prompts background task
    asyncio.create_task(contextual_prompts_loop())

    try:
        if LEGACY_AVAILABLE and hasattr(legacy, "jarvis_boot_sequence"):
            try:
                await run_blocking(legacy.jarvis_boot_sequence, version="v17")
            except Exception as e:
                print("[legacy boot] failed:", e)
                await speak("Jarvis online. Optimized core active.")
        else:
            await speak("Jarvis online. Optimized core active.")
    except Exception as e:
        print("Boot sequence error:", e)

    print("Jarvis Optimized Core - Starting...")
    stats = monitor.get_stats()
    print(f"Baseline Memory: {stats['memory_mb']:.2f} MB")
    
    # Boot phrase (keep it short)
    await speak("Jarvis online. Optimized core active.")
    
    # Voice indicator subprocess (some implementations return coroutine)
    indicator_process = None
    try:
        from core.visual import start_voice_indicator
        indicator_process = await start_voice_indicator()
    except Exception as e:
        print("[visual] start_voice_indicator failed:", e)

    try:
        while _is_running:
            # Listen for wake word
            command = await listen()
            
            if not command:
                await asyncio.sleep(0.1)  # Reduce CPU spinning
                continue
            
            if "jarvis" not in command.lower():
                continue
            
            # Process command
            await process_command_async(command)
            
            # Periodic stats (print roughly every 5 minutes)
            if int(time.time()) % 300 == 0:
                stats = monitor.get_stats()
                print(f"[Stats] CPU: {stats['cpu_percent']:.1f}% | "
                      f"Mem: {stats['memory_mb']:.1f}MB (+{stats['memory_delta']:.1f}MB)")
            await asyncio.sleep(0.05)

    finally:
        # Clean up
        try:
            if indicator_process:
                indicator_process.terminate()
        except Exception:
            pass

        try:
            if LEGACY_AVAILABLE and hasattr(legacy, "jarvis_shutdown_sequence"):
                await run_blocking(legacy.jarvis_shutdown_sequence)
        except Exception as e:
            print("[legacy shutdown] failed:", e)

        await speak("Jarvis shutting down.")

def signal_handler(sig, frame):
    """Graceful shutdown request handler"""
    global _is_running
    print("\nShutdown signal received...")
    _is_running = False
    # do not call sys.exit here; let main loop exit cleanly

if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        print("\nJarvis terminated by user.")
    except Exception as e:
        print("[main] unhandled exception:", e)
