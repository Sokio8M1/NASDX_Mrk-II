"""
Unified AI Interface
Supports multiple AI models with async operations
"""

import asyncio
import aiohttp
import json
from typing import List, Dict, Optional

class AIInterface:
    """Unified interface for multiple AI models"""
    
    def __init__(self, model_name: str, config: dict = None):
        self.model_name = model_name
        self.config = config or {}
        self.chat_history: List[Dict] = []
        self.client = None
        self._session = None
        
        # System prompt
        self.system_prompt = (
            "You are JARVIS, Tony Stark's AI assistant. "
            "Your persona is polite, witty, and exceptionally intelligent with a formal British tone. "
            "Always address the user as 'Sir'. "
            "Keep answers concise and never use emoji. "
            "You are proactive, efficient, and occasionally humorous."
        )
        
        # Initialize model-specific client
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize model-specific client"""
        if self.model_name == "gpt":
            try:
                from openai import AsyncOpenAI
                api_key = self.config.get("api_keys", {}).get("open_ai")
                if api_key:
                    self.client = AsyncOpenAI(api_key=api_key)
            except ImportError:
                print("[AI] OpenAI library not installed")
        
        elif self.model_name == "gemini":
            try:
                import google.generativeai as genai
                api_key = self.config.get("api_keys", {}).get("gemini")
                if api_key:
                    genai.configure(api_key=api_key)
                    self.client = genai.GenerativeModel('gemini-pro')
            except ImportError:
                print("[AI] Google GenAI library not installed")
        
        elif self.model_name in ["openrouter", "mistral"]:
            # HTTP-based, no special client needed
            pass
    
    async def chat_async(self, query: str) -> str:
        """
        Send query to AI model and get response
        Async implementation for non-blocking operation
        """
        if self.model_name == "gpt":
            return await self._chat_gpt(query)
        elif self.model_name == "gemini":
            return await self._chat_gemini(query)
        elif self.model_name == "openrouter":
            return await self._chat_openrouter(query)
        elif self.model_name == "mistral":
            return await self._chat_mistral(query)
        else:
            return "AI model not configured, Sir."
    
    async def _chat_gpt(self, query: str) -> str:
        """GPT implementation"""
        if not self.client:
            return "GPT is not configured, Sir."
        
        try:
            messages = [
                {"role": "system", "content": self.system_prompt}
            ] + self.chat_history + [
                {"role": "user", "content": query}
            ]
            
            response = await self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                max_tokens=200,
                temperature=0.7
            )
            
            reply = response.choices[0].message.content
            
            # Update history
            self.chat_history.append({"role": "user", "content": query})
            self.chat_history.append({"role": "assistant", "content": reply})
            
            # Keep history manageable
            if len(self.chat_history) > 10:
                self.chat_history = self.chat_history[-10:]
            
            return reply
            
        except Exception as e:
            return f"GPT error: {str(e)}"
    
    async def _chat_gemini(self, query: str) -> str:
        """Gemini implementation"""
        if not self.client:
            return "Gemini is not configured, Sir."
        
        try:
            # Gemini doesn't have native async, run in executor
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                self.client.generate_content,
                query
            )
            
            reply = response.text
            
            # Update history
            self.chat_history.append({"role": "user", "content": query})
            self.chat_history.append({"role": "assistant", "content": reply})
            
            if len(self.chat_history) > 10:
                self.chat_history = self.chat_history[-10:]
            
            return reply
            
        except Exception as e:
            return f"Gemini error: {str(e)}"
    
    async def _chat_openrouter(self, query: str) -> str:
        """OpenRouter implementation"""
        api_key = self.config.get("api_keys", {}).get("open_router")
        if not api_key:
            return "OpenRouter API key not configured, Sir."
        
        try:
            messages = [
                {"role": "system", "content": self.system_prompt}
            ] + self.chat_history[-8:] + [  # Last 8 messages for context
                {"role": "user", "content": query}
            ]
            
            payload = {
                "model": "nvidia/nemotron-nano-9b-v2:free",
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 160,
                "top_p": 0.9
            }
            
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            # Create session if needed
            if not self._session:
                self._session = aiohttp.ClientSession()
            
            async with self._session.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                response.raise_for_status()
                data = await response.json()
                reply = data['choices'][0]['message']['content']
                
                # Update history
                self.chat_history.append({"role": "user", "content": query})
                self.chat_history.append({"role": "assistant", "content": reply})
                
                if len(self.chat_history) > 10:
                    self.chat_history = self.chat_history[-10:]
                
                return reply
        
        except aiohttp.ClientError as e:
            return "Network issue connecting to AI service, Sir."
        except Exception as e:
            return f"AI error: {str(e)}"
    
    async def _chat_mistral(self, query: str) -> str:
        """Mistral via OpenRouter"""
        api_key = self.config.get("api_keys", {}).get("mistral")
        if not api_key:
            return "Mistral API key not configured, Sir."
        
        try:
            messages = [
                {"role": "system", "content": self.system_prompt}
            ] + self.chat_history[-8:] + [
                {"role": "user", "content": query}
            ]
            
            payload = {
                "model": "mistralai/mistral-7b-instruct:free",
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 200
            }
            
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            if not self._session:
                self._session = aiohttp.ClientSession()
            
            async with self._session.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                response.raise_for_status()
                data = await response.json()
                reply = data['choices'][0]['message']['content']
                
                self.chat_history.append({"role": "user", "content": query})
                self.chat_history.append({"role": "assistant", "content": reply})
                
                if len(self.chat_history) > 10:
                    self.chat_history = self.chat_history[-10:]
                
                return reply
        
        except Exception as e:
            return f"Mistral error: {str(e)}"
    
    def clear_history(self):
        """Clear chat history"""
        self.chat_history = []
    
    async def close(self):
        """Close async session"""
        if self._session:
            await self._session.close()
    
    def __del__(self):
        """Cleanup"""
        if self._session and not self._session.closed:
            try:
                asyncio.create_task(self._session.close())
            except:
                pass

# Convenience function
async def chat(query: str, model: str = "openrouter", config: dict = None) -> str:
    """Quick chat function"""
    ai = AIInterface(model, config)
    try:
        response = await ai.chat_async(query)
        return response
    finally:
        await ai.close()

if __name__ == "__main__":
    # Test AI interface
    async def test():
        config = {
            "api_keys": {
                "open_router": "your_key_here"
            }
        }
        
        ai = AIInterface("openrouter", config)
        
        print("Testing AI interface...")
        response = await ai.chat_async("Hello, what's the weather like?")
        print(f"AI: {response}")
        
        await ai.close()
    
    asyncio.run(test())