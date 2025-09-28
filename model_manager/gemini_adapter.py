#!/usr/bin/env python3
"""
Google Gemini Adapter for LLM interactions.

Handles Google Gemini API connections, model parameters, and prompt processing.
"""

import os
import json
import time
from typing import Dict, List, Optional, Any
from util.logging import get_logger, log_function_call, log_error, log_success, log_warning


logger = get_logger("gemini_adapter")


class GeminiAdapter:
    """
    Google Gemini API adapter for LLM interactions.

    Handles:
    - API key management
    - Model selection
    - Prompt processing
    - Response handling
    - Error management
    """

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """
        Initialize Gemini adapter.

        Args:
            api_key: Google Gemini API key (required)
            model: Model to use (if not provided, defaults to gemini-2.5-flash)
        """
        try:
            log_function_call("GeminiAdapter.__init__", {
                "api_key_provided": api_key is not None,
                "model_provided": model is not None
            }, logger)

            self.api_key = api_key
            if not self.api_key:
                raise ValueError(
                    "Gemini API key not provided")

            self._is_placeholder = False
            self._is_valid_format = True

            placeholder_values = [
                "your_gemini_api_key_here", "your-api-key-here", ""]
            if self.api_key.lower() in placeholder_values:
                self._is_placeholder = True
                log_warning(
                    "Gemini API key appears to be a placeholder", logger)

            self.model = model or "gemini-2.5-flash"

            self.is_thinking_model = "-thinking" in self.model

            self.base_model = self.model.replace("-thinking", "")

            try:
                from google import genai
                self.client = genai.Client(api_key=self.api_key)
                log_success(
                    f"Gemini client configured for model: {self.model}", logger)
            except ImportError as e:

                self.client = None
                log_warning(
                    "google.genai module not found - will be reported when model is used", logger)
            except Exception as e:

                self.client = None
                log_warning(
                    f"Failed to configure Gemini client: {str(e)}", logger)

        except Exception as e:
            log_error(e, "Failed to initialize Gemini adapter", logger)
            raise

    def is_ready(self) -> tuple[bool, str]:
        """
        Check if the adapter is ready to be used.

        Returns:
            Tuple of (is_ready, error_message)
        """
        if self._is_placeholder:
            return False, "API key appears to be a placeholder. Please replace with your actual Gemini API key."

        if self.client is None:
            return False, "Gemini client failed to initialize. Check if google-generativeai package is installed and API key is valid."

        return True, ""

    def get_available_models(self) -> List[str]:
        """
        Get list of available Gemini models.

        Returns:
            List of available model names
        """
        try:
            log_function_call("get_available_models", {}, logger)

            try:

                models = self.client.models.list()
                available_models = [model.name.replace(
                    "models/", "") for model in models]
                log_success(
                    f"Retrieved {len(available_models)} available models from Gemini API", logger)
                return available_models
            except Exception as e:
                log_error(e, "Error fetching models from Gemini API", logger)
                return ["gemini-2.5-flash", "gemini-2.5-pro"]

        except Exception as e:
            log_error(e, "Error getting available models", logger)
            return ["gemini-2.5-flash", "gemini-2.5-pro"]

    def create_chat_completion(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 1024,
        system_prompt: Optional[str] = None,
        max_retries: int = 3,
        retry_base_delay: float = 1.0
    ) -> Optional[str]:
        """
        Create a chat completion with Gemini.

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

            retries = 0
            while retries <= max_retries:
                try:

                    chat = self.client.chats.create(model=self.base_model)

                    if system_prompt:

                        chat.send_message(system_prompt)

                    for i, message in enumerate(messages[:-1]):
                        if message["role"] == "user":
                            chat.send_message(message["content"])
                        elif message["role"] == "assistant":

                            pass

                    if messages and messages[-1]["role"] == "user":
                        response = chat.send_message(messages[-1]["content"])
                    else:
                        response = chat.send_message(
                            "Please continue the conversation.")

                    if response and response.text:
                        response_content = response.text
                        log_success(
                            "Chat completion created successfully", logger)
                        return response_content
                    else:
                        log_error(Exception("Empty response from Gemini"),
                                  "API returned empty response", logger)
                        return None

                except Exception as e:
                    error_str = str(e).lower()

                    if "rate limit" in error_str or "quota" in error_str or "429" in error_str:
                        if retries < max_retries:
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
                            e, f"Gemini API error (attempt {retries+1})", logger)
                        if retries < max_retries:
                            retries += 1
                            continue
                        return None

            return None

        except Exception as e:
            log_error(e, "Error creating chat completion", logger)
            return None

    def _convert_messages_to_gemini_format(self, messages: List[Dict[str, str]], system_prompt: Optional[str] = None) -> List[Dict[str, str]]:
        """
        Convert standard chat messages to Gemini format.

        Note: This method is deprecated in favor of the new chat API,
        but kept for backwards compatibility.

        Args:
            messages: List of messages with 'role' and 'content'
            system_prompt: Optional system prompt

        Returns:
            List of messages in Gemini format
        """
        gemini_messages = []

        if system_prompt:
            gemini_messages.append({
                "role": "user",
                "parts": [system_prompt]
            })
            gemini_messages.append({
                "role": "model",
                "parts": ["Understood. I'll follow these instructions."]
            })

        for message in messages:
            role = message["role"]
            content = message["content"]

            if role == "user":
                gemini_role = "user"
            elif role == "assistant":
                gemini_role = "model"
            else:
                continue

            gemini_messages.append({
                "role": gemini_role,
                "parts": [content]
            })

        return gemini_messages

    def create_completion(
        self,
        prompt: str,
        max_tokens: int = 1024,
        stop_sequences: Optional[List[str]] = None,
        temperature: float = 0.0
    ) -> Optional[str]:
        """
        Create a text completion with Gemini.

        Args:
            prompt: Text prompt to complete
            max_tokens: Maximum tokens in response
            stop_sequences: Optional sequences to stop generation
            temperature: Temperature for response generation

        Returns:
            Response content or None if error
        """
        try:
            log_function_call("create_completion", {
                "prompt_length": len(prompt),
                "max_completion_tokens": max_tokens,
                "stop_sequences": stop_sequences,
                "temperature": temperature
            }, logger)

            from google.genai import types

            config = types.GenerateContentConfig(
                max_output_tokens=max_tokens,
                temperature=temperature,
                stop_sequences=stop_sequences or []
            )

            if "2.5" in self.base_model:
                if self.is_thinking_model:

                    config.thinking_config = types.ThinkingConfig(
                        thinking_budget=8196)
                else:

                    config.thinking_config = types.ThinkingConfig(
                        thinking_budget=0)

            response = self.client.models.generate_content(
                model=self.base_model,
                contents=prompt,
                config=config
            )

            if response and response.text:
                response_content = response.text
                log_success("Text completion created successfully", logger)
                return response_content
            else:
                log_error(Exception("Empty response from Gemini"),
                          "API returned empty response", logger)
                return None

        except Exception as e:
            log_error(e, "Error creating text completion", logger)
            return None

    def create_completion_with_system_instruction(
        self,
        prompt: str,
        system_instruction: str,
        max_tokens: int = 1024,
        temperature: float = 0.0
    ) -> Optional[str]:
        """
        Create a text completion with system instruction.

        Args:
            prompt: Text prompt to complete
            system_instruction: System instruction to guide behavior
            max_tokens: Maximum tokens in response
            temperature: Temperature for response generation

        Returns:
            Response content or None if error
        """
        try:
            log_function_call("create_completion_with_system_instruction", {
                "prompt_length": len(prompt),
                "system_instruction_length": len(system_instruction),
                "max_completion_tokens": max_tokens,
                "temperature": temperature
            }, logger)

            from google.genai import types

            config = types.GenerateContentConfig(
                system_instruction=system_instruction,
                max_output_tokens=max_tokens,
                temperature=temperature
            )

            if "2.5" in self.base_model:
                if self.is_thinking_model:

                    config.thinking_config = types.ThinkingConfig(
                        thinking_budget=32768)
                else:

                    config.thinking_config = types.ThinkingConfig(
                        thinking_budget=0)

            response = self.client.models.generate_content(
                model=self.base_model,
                contents=prompt,
                config=config
            )

            if response and response.text:
                response_content = response.text
                log_success(
                    "Text completion with system instruction created successfully", logger)
                return response_content
            else:
                log_error(Exception("Empty response from Gemini"),
                          "API returned empty response", logger)
                return None

        except Exception as e:
            log_error(
                e, "Error creating text completion with system instruction", logger)
            return None

    def create_streaming_completion(
        self,
        prompt: str,
        max_tokens: int = 1024,
        temperature: float = 0.0
    ):
        """
        Create a streaming text completion with Gemini.

        Args:
            prompt: Text prompt to complete
            max_tokens: Maximum tokens in response
            temperature: Temperature for response generation

        Yields:
            Response chunks as they arrive
        """
        try:
            log_function_call("create_streaming_completion", {
                "prompt_length": len(prompt),
                "max_completion_tokens": max_tokens,
                "temperature": temperature
            }, logger)

            from google.genai import types

            config = types.GenerateContentConfig(
                max_output_tokens=max_tokens,
                temperature=temperature
            )

            if "2.5" in self.base_model:
                if self.is_thinking_model:

                    config.thinking_config = types.ThinkingConfig(
                        thinking_budget=32768)
                else:

                    config.thinking_config = types.ThinkingConfig(
                        thinking_budget=0)

            response_stream = self.client.models.generate_content_stream(
                model=self.base_model,
                contents=prompt,
                config=config
            )

            for chunk in response_stream:
                if chunk and chunk.text:
                    yield chunk.text

            log_success("Streaming completion created successfully", logger)

        except Exception as e:
            log_error(e, "Error creating streaming completion", logger)
            yield None

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
                "provider": "Google Gemini",
                "type": "chat",
                "api_key_set": bool(self.api_key),
                "supports_streaming": True,
                "supports_system_instructions": True,
                "supports_multimodal": "2.5" in self.base_model or "1.5" in self.base_model,
                "thinking_enabled": self.is_thinking_model,
                "thinking_budget": 32768 if self.is_thinking_model else 0
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

    def test_connection(self) -> bool:
        """
        Test the connection to Gemini API.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            log_function_call("test_connection", {}, logger)

            test_response = self.create_completion("Hello", max_tokens=10)

            if test_response:
                log_success("Gemini API connection test successful", logger)
                return True
            else:
                log_error(Exception("Connection test failed"),
                          "No response from API", logger)
                return False

        except Exception as e:
            log_error(e, "Error testing Gemini API connection", logger)
            return False
