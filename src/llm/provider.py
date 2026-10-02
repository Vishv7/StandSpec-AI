"""
Bounded LLM Provider Interface — StandSpec AI (Phase P1-C.5)
Provides an abstract LLM interface supporting Gemini APIs via google-generativeai SDK,
along with a 100% offline deterministic mock provider.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import os
import json


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    def generate(self, prompt: str, system_instruction: Optional[str] = None, json_mode: bool = False) -> str:
        """Generates response from the LLM."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Returns True if provider is configured and available."""
        pass


class MockLLMProvider(BaseLLMProvider):
    """
    Offline deterministic mock provider.
    Replays deterministic responses for testing under socket blockades.
    """

    def __init__(self, canned_responses: Optional[Dict[str, str]] = None):
        self.canned_responses = canned_responses or {}

    def generate(self, prompt: str, system_instruction: Optional[str] = None, json_mode: bool = False) -> str:
        for key, val in self.canned_responses.items():
            if key in prompt:
                return val

        if json_mode:
            return json.dumps({
                "product": "Extracted Product",
                "material": "Extracted Material",
                "voltage": None,
                "domain": "ELECTROTECHNICAL",
                "summary": "Mock structured extraction output",
            })
        return "Deterministic mock explanation grounded strictly in verified evidence."

    def is_available(self) -> bool:
        return True


class GeminiLLMProvider(BaseLLMProvider):
    """
    Google Gemini LLM Provider (Phase P1-C.5 / V3.0).
    Calls Google GenAI API using the official google-genai SDK (with fallback to google-generativeai).
    Supports bounded timeouts, json_mode, and fail-closed error handling.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        timeout_seconds: Optional[int] = None,
    ):
        _load_env_file()
        self.api_key = api_key or os.environ.get("STANDSPEC_LLM_API_KEY") or os.environ.get("GEMINI_API_KEY")
        self.model_name = model_name or os.environ.get("STANDSPEC_LLM_MODEL", "gemini-3.8-flash")
        timeout_env = os.environ.get("STANDSPEC_LLM_TIMEOUT_SECONDS")
        self.timeout_seconds = timeout_seconds or (int(timeout_env) if timeout_env else 15)
        self._client = None
        self._legacy_configured = False

    def is_available(self) -> bool:
        llm_enabled = os.environ.get("STANDSPEC_LLM_ENABLED", "").lower() in ("1", "true", "yes")
        return llm_enabled and bool(self.api_key)

    def _get_client(self):
        if self._client is None:
            try:
                from google import genai
                from google.genai import types
                self._client = genai.Client(
                    api_key=self.api_key,
                    http_options=types.HttpOptions(timeout=self.timeout_seconds * 1000)
                )
            except ImportError:
                self._client = False
        return self._client

    def generate(self, prompt: str, system_instruction: Optional[str] = None, json_mode: bool = False) -> str:
        if not self.is_available():
            raise RuntimeError("GeminiLLMProvider unavailable: LLM is disabled or API key is not configured.")

        try:
            client = self._get_client()
            if client:
                from google.genai import types
                config = types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    response_mime_type="application/json" if json_mode else None,
                )
                response = client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config=config,
                )
                if response and response.text:
                    return response.text
                raise RuntimeError("Gemini returned empty response.")
            else:
                # Fallback to legacy SDK if google-genai is not installed
                import google.generativeai as genai
                if not self._legacy_configured:
                    genai.configure(api_key=self.api_key)
                    self._legacy_configured = True

                generation_config = {}
                if json_mode:
                    generation_config["response_mime_type"] = "application/json"

                model = genai.GenerativeModel(
                    model_name=self.model_name,
                    system_instruction=system_instruction,
                    generation_config=generation_config,
                )

                response = model.generate_content(
                    prompt,
                    request_options={"timeout": self.timeout_seconds},
                )
                if response and response.text:
                    return response.text
                raise RuntimeError("Gemini returned empty response.")
        except Exception as e:
            err_msg = str(e)
            if self.api_key and self.api_key in err_msg:
                err_msg = err_msg.replace(self.api_key, "[REDACTED_API_KEY]")
            raise RuntimeError(f"Gemini LLM generation failed: {err_msg}")


class OpenAICompatibleLLMProvider(BaseLLMProvider):
    """
    OpenAI-compatible LLM Provider supporting Groq, Ollama, OpenRouter, Together AI, Mistral.
    Uses standard POST /chat/completions payload with Bearer authentication and bounded timeout.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        timeout_seconds: Optional[int] = None,
    ):
        self.base_url = (base_url or os.environ.get("STANDSPEC_LLM_BASE_URL", "https://api.groq.com/openai/v1")).rstrip("/")
        self.api_key = api_key or os.environ.get("STANDSPEC_LLM_API_KEY") or os.environ.get("GROQ_API_KEY") or os.environ.get("OPENAI_API_KEY", "")
        raw_model = model_name or os.environ.get("STANDSPEC_LLM_MODEL", "openai/gpt-oss-120b")
        if raw_model in ("llama-3.3-70b-versatile", "llama-3.1-70b-versatile"):
            raw_model = "openai/gpt-oss-120b"
        self.model_name = raw_model
        timeout_env = os.environ.get("STANDSPEC_LLM_TIMEOUT_SECONDS")
        self.timeout_seconds = timeout_seconds or (int(timeout_env) if timeout_env else 15)

    def is_available(self) -> bool:
        llm_enabled = os.environ.get("STANDSPEC_LLM_ENABLED", "").lower() in ("1", "true", "yes")
        has_key_or_local = bool(self.api_key) or "localhost" in self.base_url or "127.0.0.1" in self.base_url
        return llm_enabled and has_key_or_local

    def generate(self, prompt: str, system_instruction: Optional[str] = None, json_mode: bool = False) -> str:
        if not self.is_available():
            raise RuntimeError("OpenAICompatibleLLMProvider unavailable: LLM is disabled or credentials not configured.")

        import httpx

        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})

        headers = {
            "Content-Type": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload = {
            "model": self.model_name,
            "messages": messages,
            "temperature": 0.0,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        endpoint = f"{self.base_url}/chat/completions"
        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                resp = client.post(endpoint, json=payload, headers=headers)
                if resp.status_code != 200:
                    raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:200]}")
                data = resp.json()
                choice = data.get("choices", [{}])[0]
                text = choice.get("message", {}).get("content", "")
                if not text:
                    raise RuntimeError("Empty response content from OpenAI-compatible provider.")
                return text
        except Exception as e:
            err_msg = str(e)
            if self.api_key and self.api_key in err_msg:
                err_msg = err_msg.replace(self.api_key, "[REDACTED_API_KEY]")
            raise RuntimeError(f"OpenAI-compatible LLM generation failed: {err_msg}")


class DisabledLLMProvider(BaseLLMProvider):
    """
    Explicitly disabled LLM provider for zero-LLM / production hardened offline operation.
    Reports is_available() = False with explicit reason code LLM_DISABLED.
    """

    def __init__(self, reason: str = "LLM_DISABLED"):
        self.reason = reason
        self.provider_name = "disabled"

    def is_available(self) -> bool:
        return False

    def generate(self, prompt: str, system_instruction: Optional[str] = None, json_mode: bool = False) -> str:
        raise RuntimeError(f"LLM provider is disabled (reason: {self.reason}). Execution must use deterministic pipeline.")


# Backward compatibility alias
BoundedExternalLLMProvider = GeminiLLMProvider


_ENV_LOADED = False


def _load_env_file(force: bool = False):
    """Lightweight .env loader if present in project root. Loads once to preserve test monkeypatching."""
    global _ENV_LOADED
    if _ENV_LOADED and not force:
        return
    _ENV_LOADED = True
    from pathlib import Path
    env_file = Path(__file__).resolve().parent.parent.parent / ".env"
    if env_file.exists():
        try:
            with open(env_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    key, val = line.split("=", 1)
                    key = key.strip()
                    val = val.strip().strip("'\"")
                    if key and key not in os.environ:
                        os.environ[key] = val
        except Exception:
            pass


# Initial load at import time
_load_env_file()


def get_llm_provider() -> BaseLLMProvider:
    """
    Factory to return the configured LLM provider according to environment variables:
    - STANDSPEC_LLM_ENABLED: ("true", "1", "yes") to activate live LLM. Default False.
    - STANDSPEC_LLM_PROVIDER: "gemini", "openai", "groq", "ollama", "openrouter", "mock", or "disabled".
    """
    _load_env_file()
    enabled = os.environ.get("STANDSPEC_LLM_ENABLED", "").lower() in ("1", "true", "yes")
    provider_name = os.environ.get("STANDSPEC_LLM_PROVIDER", "").lower()

    if provider_name == "mock":
        return MockLLMProvider()

    if not enabled or provider_name == "disabled":
        return DisabledLLMProvider()

    if provider_name in ("openai", "groq", "ollama", "openrouter"):
        return OpenAICompatibleLLMProvider()

    if provider_name in ("gemini", ""):
        return GeminiLLMProvider()
    else:
        return DisabledLLMProvider()
