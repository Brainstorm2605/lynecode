#!/usr/bin/env python3
"""
Model Manager for handling multiple LLM providers.

Handles:
- Model selection and validation
- API key management
- Provider-specific adapters
- Unified interface for different providers
"""

import os
from typing import Dict, List, Optional, Any, Tuple
from util.logging import get_logger, log_function_call, log_error, log_success, log_warning


logger = get_logger("model_manager")


class ModelManager:
    """
    Manages multiple LLM providers and their models.

    Supports:
    - OpenAI models (GPT series)
    - Google Gemini models
    - Model availability validation based on API keys
    - Unified interface for different providers
    """

    def __init__(self):
        """Initialize model manager with available providers."""
        try:
            log_function_call("ModelManager.__init__", {}, logger)

            self.providers = {
                "openai": None,
                "gemini": None,
                "azure": None
            }

            self.model_list = self._load_model_list()
            self.default_models = {
                "openai": "gpt-4.1",
                "gemini": "gemini-2.5-flash",
                "azure": "Azure Model"
            }

            self._initialize_providers()

            log_success("Model manager initialized successfully", logger)

        except Exception as e:
            log_error(e, "Failed to initialize model manager", logger)
            raise

    def _load_model_list(self) -> List[str]:
        """
        Load hardcoded model list (no environment variable support).

        Returns:
            List of available models
        """

        models = [
            "gpt-5", "gpt-5-mini", "gpt-4.1", "gpt-4.1-mini",
            "gemini-2.5-flash", "gemini-2.5-flash-thinking",
            "gemini-2.5-pro", "gemini-2.5-pro-thinking",
            "Azure Model"
        ]
        log_success(
            f"Loaded hardcoded model list with {len(models)} models", logger)
        return models

    def _initialize_providers(self):
        """Initialize available providers based on secure API keys only."""
        try:

            from api_config_menu import SecureConfigManager
            config_manager = SecureConfigManager()

            if config_manager.get_key("openai-api-key"):
                self.providers["openai"] = True
                log_success("OpenAI provider available", logger)

            if config_manager.get_key("gemini-api-key"):
                self.providers["gemini"] = True
                log_success("Gemini provider available", logger)

            if (config_manager.get_key("azure-api-key") and
                config_manager.get_key("azure-endpoint") and
                    config_manager.get_key("azure-deployment")):
                self.providers["azure"] = True
                log_success("Azure OpenAI provider available", logger)

            log_success("Secure provider initialization completed", logger)

        except ImportError:
            log_warning(
                "Secure config not available - no providers initialized", logger)
        except Exception as e:
            log_error(e, "Failed to initialize secure providers", logger)

    def get_available_models(self) -> List[str]:
        """
        Get list of available models based on configured API keys.

        Returns:
            List of available model names
        """
        try:
            log_function_call("get_available_models", {}, logger)

            available_models = []

            for provider_name, provider in self.providers.items():
                if provider:
                    try:
                        provider_models = provider.get_available_models()

                        configured_models = [
                            model for model in provider_models
                            if any(config_model in model for config_model in self.model_list)
                        ]
                        available_models.extend(configured_models)
                        log_success(
                            f"Found {len(configured_models)} available models for {provider_name}", logger)
                    except Exception as e:
                        log_error(
                            e, f"Error getting models for {provider_name}", logger)

            log_success(
                f"Total available models: {len(available_models)}", logger)
            return available_models

        except Exception as e:
            log_error(e, "Error getting available models", logger)
            return []

    def get_all_models_from_list(self) -> List[str]:
        """
        Get all models from the MODEL_LIST environment variable.

        Returns:
            List of all model names from MODEL_LIST
        """
        return self.model_list

    def get_available_providers(self) -> List[str]:
        """
        Get list of available providers (those with API keys configured).

        Returns:
            List of available provider names
        """
        return [name for name, provider in self.providers.items() if provider is not None]

    def get_provider_for_model(self, model_name: str) -> Optional[str]:
        """
        Get the provider name for a given model.

        Args:
            model_name: Name of the model

        Returns:
            Provider name or None if not found
        """
        if "gpt" in model_name.lower() or "openai" in model_name.lower():
            return "openai"
        elif "gemini" in model_name.lower() or "google" in model_name.lower():
            return "gemini"
        elif model_name == "Azure Model":
            return "azure"
        return None

    def create_adapter_for_model(self, model_name: str) -> Optional[Any]:
        """
        Create and return an adapter for the specified model.

        Args:
            model_name: Name of the model to create adapter for

        Returns:
            Adapter instance or None if model not available
        """
        try:
            log_function_call("create_adapter_for_model", {
                              "model_name": model_name}, logger)

            provider_name = self.get_provider_for_model(model_name)
            if not provider_name:
                log_error(
                    Exception(f"No provider found for model: {model_name}"), "", logger)
                return None

            provider = self.providers.get(provider_name)
            if not provider:
                log_error(
                    Exception(f"Provider {provider_name} not available"), "", logger)
                return None

            from api_config_menu import SecureConfigManager
            config_manager = SecureConfigManager()

            if provider_name == "openai":
                api_key = config_manager.get_key("openai-api-key")
                from model_manager.openai_adapter import OpenAIAdapter
                adapter = OpenAIAdapter(api_key=api_key, model=model_name)
            elif provider_name == "gemini":
                api_key = config_manager.get_key("gemini-api-key")
                from model_manager.gemini_adapter import GeminiAdapter
                adapter = GeminiAdapter(api_key=api_key, model=model_name)
            elif provider_name == "azure":
                api_key = config_manager.get_key("azure-api-key")
                azure_endpoint = config_manager.get_key("azure-endpoint")
                azure_api_version = config_manager.get_key("azure-api-version")
                azure_deployment = config_manager.get_key("azure-deployment")
                from model_manager.azure_adapter import AzureAdapter
                adapter = AzureAdapter(
                    api_key=api_key, endpoint=azure_endpoint, api_version=azure_api_version, deployment=azure_deployment)
            else:
                log_error(
                    Exception(f"Unknown provider: {provider_name}"), "", logger)
                return None

            log_success(
                f"Created adapter for model: {model_name} using {provider_name}", logger)
            return adapter

        except Exception as e:
            log_error(
                e, f"Error creating adapter for model {model_name}", logger)
            return None

    def get_default_model(self) -> Optional[str]:
        """
        Get the default model based on available providers.

        Priority: OpenAI > Azure > Gemini

        Returns:
            Default model name or None if no providers available
        """
        available_providers = self.get_available_providers()

        if "openai" in available_providers:
            return self.default_models["openai"]
        elif "azure" in available_providers:
            return self.default_models["azure"]
        elif "gemini" in available_providers:
            return self.default_models["gemini"]
        else:
            return None

    def get_model_info(self, model_name: str) -> Dict[str, Any]:
        """
        Get information about a specific model.

        Args:
            model_name: Name of the model

        Returns:
            Dictionary with model information
        """
        try:
            provider_name = self.get_provider_for_model(model_name)
            adapter = self.create_adapter_for_model(model_name)

            if adapter:
                info = adapter.get_model_info()
                info["manager_provider"] = provider_name
                return info
            else:
                return {
                    "name": model_name,
                    "provider": provider_name or "unknown",
                    "available": False,
                    "error": "Model not available"
                }

        except Exception as e:
            log_error(e, f"Error getting info for model {model_name}", logger)
            return {
                "name": model_name,
                "provider": "unknown",
                "available": False,
                "error": str(e)
            }

    def validate_model_availability(self, model_name: str) -> Dict[str, Any]:
        """
        Validate if a model is available and ready to use.

        Args:
            model_name: Name of the model to validate

        Returns:
            Dictionary with validation results
        """
        try:
            log_function_call("validate_model_availability", {
                              "model_name": model_name}, logger)

            result = {
                "model": model_name,
                "available": False,
                "provider": None,
                "api_key_configured": False,
                "error": None
            }

            provider_name = self.get_provider_for_model(model_name)
            if not provider_name:
                result["error"] = f"No provider found for model: {model_name}"
                return result

            result["provider"] = provider_name

            from api_config_menu import SecureConfigManager
            config_manager = SecureConfigManager()

            if provider_name == "azure":
                api_key = config_manager.get_key("azure-api-key")
                azure_endpoint = config_manager.get_key("azure-endpoint")
                azure_deployment = config_manager.get_key("azure-deployment")
                if not azure_endpoint or not azure_deployment:
                    result["error"] = "Azure OpenAI requires endpoint and deployment configuration."
                    return result
            else:
                api_key = config_manager.get_key(f"{provider_name}-api-key")

            if not api_key:
                result["error"] = f"API key not configured. Use the API Configuration menu to set up your keys."
                return result

            placeholder_values = ["your_openai_api_key_here",
                                  "your_gemini_api_key_here", "your_azure_api_key_here", "your-api-key-here", ""]
            if api_key.lower() in placeholder_values:
                result[
                    "error"] = f"API key appears to be a placeholder. Use the API Configuration menu to set your actual {provider_name.upper()} API key."
                return result

            result["api_key_configured"] = True

            if provider_name not in self.providers or self.providers[provider_name] is None:
                result["error"] = f"Provider {provider_name} failed to initialize. Check your API key format."
                return result

            try:
                adapter = self.create_adapter_for_model(model_name)
                if not adapter:
                    result["error"] = f"Failed to create adapter for model: {model_name}. Check model name and API key."
                    return result

                is_ready, error_msg = adapter.is_ready()
                if not is_ready:
                    result["error"] = error_msg
                    return result

            except Exception as e:
                result["error"] = f"Model initialization failed: {str(e)}"
                return result

            result["available"] = True
            result["error"] = None

            log_success(
                f"Model validation successful for: {model_name}", logger)
            return result

        except Exception as e:
            log_error(e, f"Error validating model {model_name}", logger)
            return {
                "model": model_name,
                "available": False,
                "provider": None,
                "api_key_configured": False,
                "error": str(e)
            }

    def create_chat_completion_with_fallback(
        self,
        model_name: str,
        messages: List[Dict[str, str]],
        max_tokens: int = 1024,
        system_prompt: Optional[str] = None,
        max_retries: int = 3,
        retry_base_delay: float = 1.0
    ) -> Optional[str]:
        try:
            current_provider = self.get_provider_for_model(model_name)
            if not current_provider:
                log_error(
                    Exception(f"No provider found for model: {model_name}"), "", logger)
                return None
            response, is_retryable_failure = self._try_model_completion(
                model_name, messages, max_tokens, system_prompt, max_retries, retry_base_delay
            )

            if response is not None:
                return response

            if not is_retryable_failure:
                log_error(Exception(
                    f"Non-retryable error for {model_name}, not attempting fallback"), "", logger)
                return None

            log_warning(
                f"Model {model_name} failed, attempting fallback", logger)

            fallback_candidates = self._get_all_fallback_models(
                current_model=model_name,
                current_provider=current_provider
            )

            tried = []
            for alt_model in fallback_candidates:
                if alt_model == model_name:
                    continue
                tried.append(alt_model)
                log_warning(f"Switching to {alt_model}", logger)
                alt_response, _ = self._try_model_completion(
                    alt_model, messages, max_tokens, system_prompt, max_retries, retry_base_delay
                )
                if alt_response is not None:
                    log_success(
                        f"Successfully switched to {alt_model}", logger)
                    return alt_response

            log_error(
                Exception(
                    f"All fallback attempts exhausted for {model_name}. Tried: {tried}"),
                "",
                logger,
            )
            return None

        except Exception as e:
            log_error(e, "Error in fallback completion", logger)
            return None

    def _try_model_completion(
        self,
        model_name: str,
        messages: List[Dict[str, str]],
        max_tokens: int,
        system_prompt: Optional[str],
        max_retries: int,
        retry_base_delay: float
    ) -> Tuple[Optional[str], bool]:
        try:
            adapter = self.create_adapter_for_model(model_name)
            if not adapter:
                return None, False

            if hasattr(adapter, 'create_chat_completion'):
                result = adapter.create_chat_completion(
                    messages=messages,
                    max_tokens=max_tokens,
                    system_prompt=system_prompt,
                    max_retries=max_retries,
                    retry_base_delay=retry_base_delay
                )

                if result is not None:
                    return result, True
                else:
                    return None, True

            return None, False

        except Exception as e:
            error_str = str(e).lower()
            if any(keyword in error_str for keyword in ['rate limit', '429', 'too many requests', 'insufficient_quota', 'quota exceeded', 'billing', 'overloaded', 'unavailable', 'timeout']):
                log_warning(
                    f"Retryable error detected for {model_name}: {error_str}", logger)
                return None, True
            else:
                log_error(
                    e, f"Non-retryable error for {model_name}: {error_str}", logger)
                return None, False

    def _get_cross_provider_fallback(self, current_provider: str) -> Optional[str]:
        available_providers = self.get_available_providers()

        if current_provider == "openai":
            if "azure" in available_providers:
                return "Azure Model"
            elif "gemini" in available_providers:
                return "gemini-2.5-flash"
        elif current_provider == "azure":
            if "openai" in available_providers:
                return "gpt-4.1"
            elif "gemini" in available_providers:
                return "gemini-2.5-flash"
        elif current_provider == "gemini":
            if "openai" in available_providers:
                return "gpt-4.1"
            elif "azure" in available_providers:
                return "Azure Model"

        return None

    def _get_same_provider_fallback(self, current_model: str, provider: str) -> Optional[str]:
        if provider == "openai":
            if current_model == "gpt-4.1":
                return "gpt-5"
            elif current_model == "gpt-5":
                return "gpt-4.1-mini"
            elif current_model == "gpt-4.1-mini":
                return "gpt-5-mini"
        elif provider == "gemini":
            if current_model == "gemini-2.5-flash":
                return "gemini-2.5-flash-thinking"
            elif current_model == "gemini-2.5-flash-thinking":
                return "gemini-2.5-pro"
            elif current_model == "gemini-2.5-pro":
                return "gemini-2.5-pro-thinking"

        return None

    def _get_all_fallback_models(self, current_model: str, current_provider: str) -> List[str]:
        """Return an ordered list of all fallback models to try, using _load_model_list order.

        Filters to models whose providers are currently available and excludes the current model.
        """
        available_providers = self.get_available_providers()

        ordered: List[str] = []
        seen = {current_model}

        for model in self.model_list:
            if model in seen:
                continue
            provider = self.get_provider_for_model(model)
            if provider in available_providers:
                ordered.append(model)
                seen.add(model)

        return ordered