"""
Unified AI Client with Multi-Model Fallback.
Primary: Gemini (Free Tier)
Fallback: Groq (Llama 3 - Free Tier)
"""
import asyncio
import os
from abc import ABC, abstractmethod

import google.generativeai as genai
from groq import AsyncGroq
from rich.console import Console

from config import get_env, CONFIG

console = Console()


class LLMProvider(ABC):
    """Abstract base class for AI providers."""
    
    @abstractmethod
    async def generate(self, prompt: str) -> str:
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        pass


class GeminiProvider(LLMProvider):
    """Google Gemini Provider."""
    
    def __init__(self):
        api_key = get_env("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not set")
            
        genai.configure(api_key=api_key)
        self.model_name = CONFIG.get("ai", {}).get("models", {}).get("gemini", {}).get("name", "gemini-2.5-flash")
        self.model = genai.GenerativeModel(self.model_name)

    @property
    def name(self) -> str:
        return "Gemini"

    async def generate(self, prompt: str) -> str:
        # Run in executor because genai is synchronous (mostly)
        response = await asyncio.to_thread(self.model.generate_content, prompt)
        return response.text


class GroqProvider(LLMProvider):
    """Groq Provider (Llama 3)."""
    
    def __init__(self):
        api_key = get_env("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY not set")
            
        self.client = AsyncGroq(api_key=api_key)
        self.model_name = CONFIG.get("ai", {}).get("models", {}).get("groq", {}).get("name", "llama3-70b-8192")

    @property
    def name(self) -> str:
        return "Groq"

    async def generate(self, prompt: str) -> str:
        chat_completion = await self.client.chat.completions.create(
            messages=[
                {"role": "user", "content": prompt}
            ],
            model=self.model_name,
        )
        return chat_completion.choices[0].message.content


class MultiModelClient:
    """Unified client that handles fallback logic."""
    
    def __init__(self):
        self.providers: list[LLMProvider] = []
        
        # Initialize providers based on config/env
        # Priority 1: Gemini
        try:
            self.providers.append(GeminiProvider())
        except Exception as e:
            console.print(f"[dim yellow]Warning: Gemini not available ({e})[/]")
            
        # Priority 2: Groq
        try:
            self.providers.append(GroqProvider())
        except Exception as e:
            # Only warn if verbose, Groq is optional fallback
            pass
            
        if not self.providers:
            console.print("[red]❌ No AI providers available! Check .env for GEMINI_API_KEY or GROQ_API_KEY[/]")

    async def generate_content(self, prompt: str) -> str:
        """Generate content using the first available provider."""
        if not self.providers:
            raise RuntimeError("No AI providers verified.")

        errors = []
        for provider in self.providers:
            try:
                console.print(f"[dim]🤖 Analyzing with {provider.name}...[/]")
                return await provider.generate(prompt)
            except Exception as e:
                console.print(f"[yellow]⚠️ {provider.name} failed (Rate Limit?): {e}[/]")
                errors.append(f"{provider.name}: {e}")
                continue
        
        raise RuntimeError(f"All AI providers failed: {'; '.join(errors)}")
