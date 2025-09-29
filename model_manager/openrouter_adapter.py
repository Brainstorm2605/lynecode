#!/usr/bin/env python3
"""
OpenRouter Adapter for LLM interactions.

Provides an OpenAI-compatible client that targets OpenRouter's unified API
endpoint while adding optional attribution headers (HTTP-Referer, X-Title).
"""

import time
from typing import Dict, List, Optional, Any, Tuple

import requests

from util.logging import (
    get_logger,
    log_function_call,
    log_error,
    log_success,
    log_warning,
)


logger = get_logger("openrouter_adapter")


class OpenRouterAdapter:
    """OpenRouter API adapter for chat completions."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        referer: Optional[str] = None,
        title: Optional[str] = None,
    ):
        """Configure adapter.

        Args:
            api_key: OpenRouter API key (required)
            model: Target model id, defaults to `openrouter/auto`
            referer: Optional URL for OpenRouter attribution
            title: Optional application title for attribution
        """
        try:
            log_function_call(
                "OpenRouterAdapter.__init__",
                {
                    "api_key_provided": api_key is not None,
                    "model_provided": model is not None,
                    "referer_provided": referer is not None,
                    "title_provided": title is not None,
                },
                logger,
            )

            if not api_key:
                raise ValueError("OpenRouter API key not provided")

            self.api_key = api_key
            self.model = model or "openrouter/auto"
            self.base_url = "https://openrouter.ai/api/v1"
            self.referer = referer
            self.title = title

            placeholder_values = {
                "your_openrouter_api_key_here",
                "your-api-key-here",
                "",
            }
            self._is_placeholder = self.api_key.lower() in placeholder_values

            # OpenRouter keys typically begin with "sk-or-"
            self._is_valid_format = self.api_key.startswith("sk-or-")

            log_success(
                f"OpenRouter adapter initialized with model: {self.model}", logger
            )
        except Exception as exc:
            log_error(exc, "Failed to initialize OpenRouter adapter", logger)
            raise

    def is_ready(self) -> Tuple[bool, str]:
        """Verify adapter readiness."""
        if self._is_placeholder:
            return (
                False,
                "API key appears to be a placeholder. Please set your actual OpenRouter API key.",
            )

        if not self._is_valid_format:
            return (
                False,
                "API key format is invalid. OpenRouter keys should start with 'sk-or-'.",
            )

        return True, ""

    def _build_headers(self) -> Dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        if self.referer:
            headers["HTTP-Referer"] = self.referer
        if self.title:
            headers["X-Title"] = self.title

        return headers

    def get_available_models(self) -> List[str]:
        """Fetch the model catalog from OpenRouter."""
        try:
            log_function_call("get_available_models", {}, logger)

            response = requests.get(
                f"{self.base_url}/models", headers=self._build_headers(), timeout=30
            )
            if response.status_code == 200:
                models_payload = response.json()
                items = models_payload.get("data") or models_payload.get("models") or []
                available_models = []
                for item in items:
                    if isinstance(item, dict):
                        model_id = item.get("id") or item.get("slug")
                        if model_id:
                            available_models.append(model_id)
                    elif isinstance(item, str):
                        available_models.append(item)

                log_success(
                    f"Retrieved {len(available_models)} available models from OpenRouter",
                    logger,
                )
                return available_models

            log_error(
                Exception(f"API error: {response.status_code}"),
                f"Failed to get OpenRouter models: {response.text}",
                logger,
            )
            return []
        except Exception as exc:
            log_error(exc, "Error retrieving OpenRouter models", logger)
            return []

    def create_chat_completion(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 1024,
        system_prompt: Optional[str] = None,
        max_retries: int = 3,
        retry_base_delay: float = 1.0,
    ) -> Optional[str]:
        """Send chat completion request to OpenRouter."""
        try:
            log_function_call(
                "create_chat_completion",
                {
                    "message_count": len(messages),
                    "max_completion_tokens": max_tokens,
                    "system_prompt_provided": system_prompt is not None,
                },
                logger,
            )

            prepared_messages: List[Dict[str, Any]] = []
            if system_prompt:
                prepared_messages.append({"role": "system", "content": system_prompt})
            prepared_messages.extend(messages)

            payload = {
                "model": self.model,
                "messages": prepared_messages,
                "max_tokens": max_tokens,
            }

            headers = self._build_headers()
            retries = 0

            while retries <= max_retries:
                try:
                    response = requests.post(
                        f"{self.base_url}/chat/completions",
                        headers=headers,
                        json=payload,
                        timeout=60,
                    )

                    if response.status_code == 200:
                        response_data = response.json()
                        choices = response_data.get("choices", [])
                        if choices:
                            message = choices[0].get("message") or {}
                            content = message.get("content")
                            if content:
                                log_success(
                                    "OpenRouter chat completion succeeded", logger
                                )
                                return content

                        log_error(
                            Exception("Empty response from OpenRouter"),
                            "API returned no choices",
                            logger,
                        )
                        return None

                    # Handle retry-able conditions (rate limiting, transient errors)
                    if response.status_code in {408, 409, 429, 500, 502, 503, 504}:
                        if retries < max_retries:
                            delay = retry_base_delay * (2 ** retries)
                            log_warning(
                                f"OpenRouter transient error {response.status_code}; retrying in {delay:.2f}s",
                                logger,
                            )
                            time.sleep(delay)
                            retries += 1
                            continue

                    log_error(
                        Exception(f"API error: {response.status_code}"),
                        f"OpenRouter completion failed: {response.text}",
                        logger,
                    )
                    return None

                except requests.RequestException as exc:
                    if retries < max_retries:
                        delay = retry_base_delay * (2 ** retries)
                        log_warning(
                            f"OpenRouter request exception; retrying in {delay:.2f}s: {exc}",
                            logger,
                        )
                        time.sleep(delay)
                        retries += 1
                        continue

                    log_error(exc, "OpenRouter request failed after retries", logger)
                    return None

            log_error(
                Exception("Max retries exceeded"),
                "OpenRouter completion failed after retries",
                logger,
            )
            return None

        except Exception as exc:
            log_error(exc, "Error creating OpenRouter chat completion", logger)
            return None

    def get_model_info(self) -> Dict[str, Any]:
        """Return metadata for the configured model."""
        try:
            return {
                "name": self.model,
                "provider": "openrouter",
                "base_url": self.base_url,
                "attribution_headers": {
                    "HTTP-Referer": self.referer or "",
                    "X-Title": self.title or "",
                },
            }
        except Exception as exc:
            log_error(exc, "Error retrieving OpenRouter model info", logger)
            return {
                "name": self.model,
                "provider": "openrouter",
                "error": str(exc),
            }
