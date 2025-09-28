#!/usr/bin/env python3
"""
OpenAI Adapter for LLM interactions.

Handles OpenAI API connections, model parameters, and prompt processing.
No temperature control - uses deterministic responses.
"""

import os
import json
import requests
from typing import Dict, List, Optional, Any
from util.logging import get_logger, log_function_call, log_error, log_success, log_warning


logger = get_logger("openai_adapter")


class OpenAIAdapter:
    """
    OpenAI API adapter for LLM interactions.

    Handles:
    - API key management
    - Model selection
    - Prompt processing
    - Response handling
    - Error management
    """

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """
        Initialize OpenAI adapter.

        Args:
            api_key: OpenAI API key (required)
            model: Model to use (if not provided, defaults to gpt-4.1)
        """
        try:
            log_function_call("OpenAIAdapter.__init__", {
                "api_key_provided": api_key is not None,
                "model_provided": model is not None
            }, logger)

            self.api_key = api_key
            if not self.api_key:
                raise ValueError(
                    "OpenAI API key not provided")

            self.model = model or "gpt-4.1"
            self.base_url = "https://api.openai.com/v1"

            self._is_placeholder = False
            self._is_valid_format = True

            placeholder_values = [
                "your_openai_api_key_here", "your-api-key-here", ""]
            if self.api_key.lower() in placeholder_values:
                self._is_placeholder = True

            if not self.api_key.startswith("sk-"):
                self._is_valid_format = False

            log_success(
                f"OpenAI adapter initialized with model: {self.model}", logger)

        except Exception as e:
            log_error(e, "Failed to initialize OpenAI adapter", logger)
            raise

    def is_ready(self) -> tuple[bool, str]:
        """
        Check if the adapter is ready to be used.

        Returns:
            Tuple of (is_ready, error_message)
        """
        if self._is_placeholder:
            return False, "API key appears to be a placeholder. Please replace with your actual OpenAI API key."

        if not self._is_valid_format:
            return False, "API key format is invalid. OpenAI keys should start with 'sk-'."

        return True, ""

    def _get_max_tokens_param(self, model_name: str) -> str:
        """
        Determine which max tokens parameter to use based on model version.

        Args:
            model_name: The model name to check

        Returns:
            Parameter name: "max_tokens" for older models, "max_completion_tokens" for newer models
        """

        if model_name.startswith("gpt-5") or model_name.startswith("gpt/5"):
            return "max_completion_tokens"

        return "max_tokens"

    def get_available_models(self) -> List[str]:
        """
        Get list of available OpenAI models.

        Returns:
            List of available model names
        """
        try:
            log_function_call("get_available_models", {}, logger)

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            response = requests.get(
                f"{self.base_url}/models", headers=headers, timeout=30)

            if response.status_code == 200:
                models_data = response.json()
                available_models = [model["id"]
                                    for model in models_data.get("data", [])]
                log_success(
                    f"Retrieved {len(available_models)} available models from OpenAI API", logger)
                return available_models
            else:
                log_error(Exception(
                    f"API error: {response.status_code}"), f"Failed to get models: {response.text}", logger)
                return []

        except Exception as e:
            log_error(e, "Error getting available models", logger)
            return []

    def create_chat_completion(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 1024,
        system_prompt: Optional[str] = None,
        max_retries: int = 3,
        retry_base_delay: float = 1.0
    ) -> Optional[str]:
        """
        Create a chat completion with OpenAI.

        Args:
            messages: List of message dictionaries with 'role' and 'content'
            max_tokens: Maximum tokens in response
            system_prompt: Optional system prompt to prepend
            max_retries: Maximum number of retries on rate limit errors
            retry_base_delay: Base delay for exponential backoff (in seconds)

        Returns:
            Response content or None if error
        """
        try:
            log_function_call("create_chat_completion", {
                "message_count": len(messages),
                "max_completion_tokens": max_tokens,
                "system_prompt_provided": system_prompt is not None
            }, logger)

            prepared_messages = []
            if system_prompt:
                prepared_messages.append({
                    "role": "system",
                    "content": system_prompt
                })
            prepared_messages.extend(messages)

            max_tokens_param = self._get_max_tokens_param(self.model)
            log_success(
                f"Using parameter '{max_tokens_param}' for model {self.model}", logger)
            payload = {
                "model": self.model,
                "messages": prepared_messages,
                max_tokens_param: max_tokens
            }

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            retries = 0
            while retries <= max_retries:
                try:
                    response = requests.post(
                        f"{self.base_url}/chat/completions",
                        headers=headers,
                        json=payload,
                        timeout=30
                    )

                    if response.status_code == 200:
                        response_data = response.json()

                        if not response_data.get("choices") or len(response_data["choices"]) == 0:
                            log_error(Exception("No choices in response"),
                                      "API returned no choices", logger)
                            return None

                        if "message" not in response_data["choices"][0]:
                            log_error(Exception("No message in first choice"),
                                      "API returned no message", logger)
                            return None

                        if "content" not in response_data["choices"][0]["message"] or not response_data["choices"][0]["message"]["content"]:
                            log_error(Exception("Empty content in message"),
                                      "API returned empty content", logger)
                            return None

                        response_content = response_data["choices"][0]["message"]["content"]
                        log_success(
                            f"Chat completion created successfully", logger)
                        return response_content
                    elif response.status_code == 429:

                        retry_after = 1
                        try:
                            error_data = response.json()
                            error_message = error_data.get(
                                "error", {}).get("message", "")

                            import re
                            retry_match = re.search(
                                r"try again in (\d+\.\d+|\d+)s", error_message, re.IGNORECASE)
                            if retry_match:
                                retry_after = float(retry_match.group(1))
                                retry_after = min(max(retry_after, 1), 60)
                        except Exception:

                            retry_after = retry_base_delay * (2 ** retries)

                        if retries < max_retries:
                            import time
                            log_warning(
                                f"Rate limit hit, retrying in {retry_after:.2f} seconds (retry {retries+1}/{max_retries})", logger)
                            time.sleep(retry_after)
                            retries += 1
                            continue
                        else:
                            log_error(Exception(f"API error: {response.status_code}"),
                                      f"Failed after {max_retries} retries: {response.text}", logger)
                            return None
                    else:
                        log_error(Exception(f"API error: {response.status_code}"),
                                  f"Failed to create chat completion: {response.text}", logger)
                        return None

                except requests.RequestException as e:
                    if retries < max_retries:
                        import time
                        retry_delay = retry_base_delay * (2 ** retries)
                        log_warning(
                            f"Request failed, retrying in {retry_delay:.2f} seconds (retry {retries+1}/{max_retries}): {str(e)}", logger)
                        time.sleep(retry_delay)
                        retries += 1
                        continue
                    else:
                        log_error(
                            e, f"Request failed after {max_retries} retries", logger)
                        return None

            return None

        except Exception as e:
            log_error(e, "Error creating chat completion", logger)
            return None

    def create_completion(
        self,
        prompt: str,
        max_tokens: int = 1024,
        stop_sequences: Optional[List[str]] = None
    ) -> Optional[str]:
        """
        Create a text completion with OpenAI.

        Args:
            prompt: Text prompt to complete
            max_tokens: Maximum tokens in response
            stop_sequences: Optional sequences to stop generation

        Returns:
            Response content or None if error
        """
        try:
            log_function_call("create_completion", {
                "prompt_length": len(prompt),
                "max_tokens": max_tokens,
                "stop_sequences": stop_sequences
            }, logger)

            max_tokens_param = self._get_max_tokens_param(self.model)
            payload = {
                "model": self.model,
                "prompt": prompt,
                max_tokens_param: max_tokens
            }

            if stop_sequences:
                payload["stop"] = stop_sequences

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            response = requests.post(
                f"{self.base_url}/completions",
                headers=headers,
                json=payload,
                timeout=60
            )

            if response.status_code == 200:
                response_data = response.json()
                response_content = response_data["choices"][0]["text"]
                log_success(f"Text completion created successfully", logger)
                return response_content
            else:
                log_error(Exception(f"API error: {response.status_code}"),
                          f"Failed to create text completion: {response.text}", logger)
                return None

        except Exception as e:
            log_error(e, "Error creating text completion", logger)
            return None

    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the current model.

        Returns:
            Dictionary with model information
        """
        try:
            log_function_call("get_model_info", {}, logger)

            model_info = {
                "name": self.model,
                "provider": "OpenAI",
                "type": "chat" if "gpt" in self.model else "completion",
                "api_key_set": bool(self.api_key),
                "base_url": self.base_url
            }

            log_success(f"Model info retrieved for {self.model}", logger)
            return model_info

        except Exception as e:
            log_error(e, "Error getting model info", logger)
            return {}

    def validate_prompt(self, prompt: str) -> Dict[str, Any]:
        """
        Validate a prompt for the current model.

        Args:
            prompt: Prompt to validate

        Returns:
            Dictionary with validation results
        """
        try:
            log_function_call("validate_prompt", {
                              "prompt_length": len(prompt)}, logger)

            validation_result = {
                "valid": True,
                "length": len(prompt),
                "estimated_tokens": len(prompt.split()) * 1.3,
                "warnings": []
            }

            if len(prompt) > 10000:
                validation_result["warnings"].append("Prompt is very long")

            if not prompt.strip():
                validation_result["valid"] = False
                validation_result["warnings"].append("Prompt is empty")

            log_success(f"Prompt validation completed", logger)
            return validation_result

        except Exception as e:
            log_error(e, "Error validating prompt", logger)
            return {"valid": False, "error": str(e)}
