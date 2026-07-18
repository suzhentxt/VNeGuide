"""Tests for lazy LLM environment configuration."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from vneguide.ai.config import LLMConfig, build_llm_provider, load_llm_config
from vneguide.ai.providers import (
    LiteLLMChatCompletionsProvider,
    MockLLMProvider,
    OpenAIResponsesProvider,
    ProviderConfigurationError,
)


class LLMConfigTests(unittest.TestCase):
    def test_defaults_to_lazy_mock_without_credentials(self) -> None:
        config = load_llm_config({})

        self.assertEqual(config.provider, "mock")
        self.assertIsNone(config.model)
        self.assertIsNone(config.api_key)
        self.assertIsInstance(build_llm_provider(config), MockLLMProvider)

    def test_loads_explicit_env_file_and_hides_litellm_key(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            env_file = Path(temporary_directory) / ".env"
            env_file.write_text(
                "\n".join(
                    (
                        "VNEGUIDE_LLM_PROVIDER=litellm",
                        "VNEGUIDE_MODEL=test-model",
                        "VNEGUIDE_LITELLM_BASE_URL=http://127.0.0.1:9207/",
                        "VNEGUIDE_LITELLM_API_KEY=litellm-test-key",
                        "VNEGUIDE_LITELLM_ALLOW_INSECURE_HTTP=yes",
                        "VNEGUIDE_LITELLM_DISABLE_THINKING=1",
                        "VNEGUIDE_LANGUAGE_MODEL_ASSISTED=yes",
                        "VNEGUIDE_SESSION_FACTORY=ignored:value",
                    )
                ),
                encoding="utf-8",
            )

            config = load_llm_config({}, env_file=env_file)

        self.assertEqual(config.provider, "litellm")
        self.assertEqual(config.model, "test-model")
        self.assertEqual(config.api_key, "litellm-test-key")
        self.assertEqual(config.litellm_base_url, "http://127.0.0.1:9207/")
        self.assertTrue(config.litellm_allow_insecure_http)
        self.assertTrue(config.litellm_disable_thinking)
        self.assertTrue(config.language_model_assisted)
        self.assertNotIn("litellm-test-key", repr(config))
        self.assertIsInstance(build_llm_provider(config), LiteLLMChatCompletionsProvider)

    def test_explicit_environment_overrides_file_and_specific_key_wins(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            env_file = Path(temporary_directory) / ".env"
            env_file.write_text(
                "VNEGUIDE_LLM_PROVIDER=mock\nVNEGUIDE_API_KEY=generic-key\n",
                encoding="utf-8",
            )
            config = load_llm_config(
                {
                    "VNEGUIDE_LLM_PROVIDER": "litellm",
                    "VNEGUIDE_MODEL": "override-model",
                    "VNEGUIDE_LITELLM_BASE_URL": "https://gateway.example",
                    "VNEGUIDE_LITELLM_API_KEY": "specific-key",
                },
                env_file=env_file,
            )

        self.assertEqual(config.provider, "litellm")
        self.assertEqual(config.model, "override-model")
        self.assertEqual(config.api_key, "specific-key")

        isolated = load_llm_config(
            {
                "VNEGUIDE_LLM_PROVIDER": "litellm",
                "VNEGUIDE_API_KEY": "openai-only-key",
            }
        )
        self.assertIsNone(isolated.api_key)

    def test_builds_official_openai_without_custom_url(self) -> None:
        provider = build_llm_provider(
            LLMConfig(provider="openai", model="test-model", api_key="test-key")
        )
        self.assertIsInstance(provider, OpenAIResponsesProvider)

    def test_rejects_invalid_boolean_duplicate_env_and_missing_litellm_settings(self) -> None:
        with self.assertRaises(ProviderConfigurationError):
            load_llm_config({"VNEGUIDE_LITELLM_DISABLE_THINKING": "sometimes"})
        with self.assertRaises(ProviderConfigurationError):
            load_llm_config({"VNEGUIDE_LANGUAGE_MODEL_ASSISTED": "sometimes"})

        with tempfile.TemporaryDirectory() as temporary_directory:
            env_file = Path(temporary_directory) / ".env"
            env_file.write_text(
                "VNEGUIDE_MODEL=one\nVNEGUIDE_MODEL=two\n",
                encoding="utf-8",
            )
            with self.assertRaises(ProviderConfigurationError):
                load_llm_config({}, env_file=env_file)

        invalid_configs = (
            LLMConfig(provider="litellm", model=None, api_key=None),
            LLMConfig(provider="litellm", model="test-model", api_key=None),
            LLMConfig(
                provider="http://127.0.0.1:9207",
                model="test-model",
                api_key=None,
            ),
        )
        for config in invalid_configs:
            with self.subTest(config=config), self.assertRaises(ProviderConfigurationError):
                build_llm_provider(config)

    def test_logging_wrapper_applied_when_enabled(self) -> None:
        from vneguide.ai.providers import LoggingProvider

        config = LLMConfig(
            provider="mock",
            model="test-model",
            api_key=None,
            llm_log_enabled=True,
            llm_log_path="logs/test.jsonl",
        )
        provider = build_llm_provider(config)
        self.assertIsInstance(provider, LoggingProvider)

    def test_logging_disabled_by_default(self) -> None:
        config = LLMConfig(provider="mock", model="test-model", api_key=None)
        provider = build_llm_provider(config)
        self.assertIsInstance(provider, MockLLMProvider)

    def test_reads_log_env_vars(self) -> None:
        config = load_llm_config(
            {
                "VNEGUIDE_LLM_PROVIDER": "mock",
                "VNEGUIDE_LLM_LOG": "1",
                "VNEGUIDE_LLM_LOG_PATH": "custom/path.jsonl",
            }
        )
        self.assertTrue(config.llm_log_enabled)
        self.assertEqual(config.llm_log_path, "custom/path.jsonl")


if __name__ == "__main__":
    unittest.main()
