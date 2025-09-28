#!/usr/bin/env python3
"""
Azure OpenAI Adapter for LLM interactions.

Handles Azure OpenAI API connections using the official SDK.
Uses "Azure Model" as the model name regardless of actual deployment.
"""

import os
from typing import Dict, List, Optional, Any
from util.logging import get_logger, log_function_call, log_error, log_success, log_warning


logger = get_logger("azure_adapter")

try:
    from openai import AzureOpenAI
    AZURE_SDK_AVAILABLE = True
except ImportError:
    AZURE_SDK_AVAILABLE = False
    AzureOpenAI = None
    log_warning(
        "Azure OpenAI SDK not available. Install with: pip install openai", logger)


class AzureAdapter:
    """
    Azure OpenAI API adapter for LLM interactions.

    Handles:
    - API key management
    - Model selection (fixed as "Azure Model")
    - Prompt processing
    - Response handling
    - Error management
    """

    def __init__(self, api_key: Optional[str] = None, endpoint: Optional[str] = None, api_version: Optional[str] = None, deployment: Optional[str] = None):
        """
        Initialize Azure adapter.

        Args:
            api_key: Azure OpenAI API key (required)
            endpoint: Azure endpoint URL (required)
            api_version: Azure API version (optional, defaults to "2024-12-01-preview")
            deployment: Azure deployment name (required)
        """
        try:
            log_function_call("AzureAdapter.__init__", {
                "api_key_provided": api_key is not None,
                "endpoint_provided": endpoint is not None,
                "api_version_provided": api_version is not None,
                "deployment_provided": deployment is not None
            }, logger)

            self.api_key = api_key
            self.endpoint = endpoint
            self.api_version = api_version or "2024-12-01-preview"
            self.deployment = deployment

            if not self.api_key or not self.endpoint or not self.deployment:
                raise ValueError(
                    "Azure API key, endpoint, and deployment are all required")

            self.client = None
            self._is_placeholder = False
            self._is_valid_format = True

            if not all([self.api_key, self.endpoint, self.api_version, self.deployment]):
                missing_vars = []
                if not self.api_key:
                    missing_vars.append("API Key")
                if not self.endpoint:
                    missing_vars.append("Endpoint")
                if not self.api_version:
                    missing_vars.append("API Version")
                if not self.deployment:
                    missing_vars.append("Deployment")

                raise ValueError(
                    f"Missing required Azure OpenAI configuration: {', '.join(missing_vars)}"
                )

            placeholder_values = [
                "your_azure_api_key_here", "your-api-key-here", ""]
            if self.api_key.lower() in placeholder_values:
                self._is_placeholder = True

            if AZURE_SDK_AVAILABLE:
                try:
                    self.client = AzureOpenAI(
                        api_version=self.api_version,
                        azure_endpoint=self.endpoint,
                        api_key=self.api_key,
                    )
                    log_success(
                        f"Azure OpenAI client initialized for deployment: {self.deployment}", logger)
                except Exception as e:
                    log_error(
                        e, "Failed to initialize Azure OpenAI client", logger)
                    self.client = None
            else:
                log_warning("Azure OpenAI SDK not available", logger)

        except Exception as e:
            log_error(e, "Failed to initialize Azure adapter", logger)
            raise

    def is_ready(self) -> tuple[bool, str]:
        """
        Check if the adapter is ready to be used.

        Returns:
            Tuple of (is_ready, error_message)
        """
        if not AZURE_SDK_AVAILABLE:
            return False, "Azure OpenAI SDK not installed. Install with: pip install openai"

        if self._is_placeholder:
            return False, "API key appears to be a placeholder. Please replace with your actual Azure OpenAI API key."

        if not self.client:
            return False, "Azure OpenAI client failed to initialize. Check your API key and endpoint configuration."

        return True, ""

    def get_available_models(self) -> List[str]:
        """
        Get list of available Azure models.

        Returns:
            List of available model names (always returns ["Azure Model"])
        """
        try:
            log_function_call("get_available_models", {}, logger)

            available_models = ["Azure Model"]

            log_success(
                f"Azure adapter provides model: {available_models[0]}", logger)
            return available_models

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
        Create a chat completion with Azure OpenAI.

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
                "system_prompt_provided": system_prompt is not None,
                "deployment": self.deployment
            }, logger)

            if not self.client:
                log_error(Exception("Azure client not initialized"),
                          "Client not available", logger)
                return None

            prepared_messages = []
            if system_prompt:
                prepared_messages.append({
                    "role": "system",
                    "content": system_prompt
                })
            prepared_messages.extend(messages)

            retries = 0
            while retries <= max_retries:
                try:
                    response = self.client.chat.completions.create(
                        messages=prepared_messages,
                        max_completion_tokens=max_tokens,
                        temperature=1.0,
                        top_p=1.0,
                        frequency_penalty=0.0,
                        presence_penalty=0.0,
                        model=self.deployment
                    )

                    if response and response.choices and len(response.choices) > 0:
                        choice = response.choices[0]
                        if choice.message and choice.message.content:
                            response_content = choice.message.content
                            log_success(
                                f"Chat completion created successfully using deployment: {self.deployment}", logger)
                            return response_content
                        else:
                            log_error(Exception("Empty content in response"),
                                      "Azure API returned empty content", logger)
                            return None
                    else:
                        log_error(Exception("No choices in response"),
                                  "Azure API returned no choices", logger)
                        return None

                except Exception as e:
                    error_str = str(e).lower()

                    if "429" in error_str or "rate limit" in error_str or "quota" in error_str:
                        if retries < max_retries:
                            import time
                            retry_delay = retry_base_delay * (2 ** retries)
                            log_warning(
                                f"Rate limit hit, retrying in {retry_delay:.2f} seconds (retry {retries+1}/{max_retries}): {str(e)}", logger)
                            time.sleep(retry_delay)
                            retries += 1
                            continue
                        else:
                            log_error(
                                e, f"Failed after {max_retries} retries due to rate limiting", logger)
                            return None
                    else:

                        log_error(
                            e, f"Azure API error (attempt {retries+1})", logger)
                        return None

            return None

        except Exception as e:
            log_error(e, "Error creating chat completion", logger)
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
                "name": "Azure Model",
                "provider": "Azure OpenAI",
                "type": "chat",
                "api_key_set": bool(self.api_key),
                "endpoint": self.endpoint,
                "api_version": self.api_version,
                "deployment": self.deployment,
                "sdk_available": AZURE_SDK_AVAILABLE,
                "client_ready": self.client is not None
            }

            log_success("Model info retrieved for Azure Model", logger)
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

            if len(prompt) > 100000:
                validation_result["warnings"].append("Prompt is very long")

            if not prompt.strip():
                validation_result["valid"] = False
                validation_result["warnings"].append("Prompt is empty")

            if len(prompt.split()) < 3:
                validation_result["warnings"].append(
                    "Prompt is very short - consider adding more context")

            log_success("Prompt validation completed", logger)
            return validation_result

        except Exception as e:
            log_error(e, "Error validating prompt", logger)
            return {"valid": False, "error": str(e)}
