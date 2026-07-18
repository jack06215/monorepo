import os
import unittest
from unittest.mock import patch

from common.llm_client import get_langchain_client


class GetLangchainClientAzureTest(unittest.TestCase):
    def test_creates_azure_client_with_expected_params(self) -> None:
        env = {
            "AZURE_OPENAI_API_KEY": "key",
            "AZURE_OPENAI_DEPLOYMENT_NAME": "gpt-deploy",
            "AZURE_OPENAI_ENDPOINT": "https://example.com",
            "OPENAI_API_VERSION": "2024-01-01",
        }
        with (
            patch.dict(os.environ, env, clear=True),
            patch("common.llm_client.AzureChatOpenAI") as azure_cls,
        ):
            get_langchain_client("azure", temperature=0.2)

        azure_cls.assert_called_once_with(
            verbose=True,
            temperature=0.2,
            AZURE_OPENAI_DEPLOYMENT_NAME="gpt-deploy",
        )

    def test_missing_env_vars_raises_before_client_creation(self) -> None:
        with (
            patch.dict(os.environ, {}, clear=True),
            patch("common.llm_client.AzureChatOpenAI") as azure_cls,
        ):
            with self.assertRaises(ValueError):
                get_langchain_client("azure")

        azure_cls.assert_not_called()


class GetLangchainClientOpenaiTest(unittest.TestCase):
    def test_creates_openai_client_and_maps_zsh_env_vars(self) -> None:
        env = {
            "LLM_ZSH_PYTHON_OPENAI_API_KEY": "zsh-key",
            "LLM_ZSH_PYTHON_OPENAI_MODEL": "gpt-test-model",
        }
        with (
            patch.dict(os.environ, env, clear=True),
            patch("common.llm_client.ChatOpenAI") as openai_cls,
        ):
            get_langchain_client("openai")

            self.assertEqual(os.environ["OPENAI_API_KEY"], "zsh-key")
            self.assertEqual(os.environ["OPENAI_MODEL"], "gpt-test-model")

        openai_cls.assert_called_once_with(
            verbose=True,
            model="gpt-test-model",
        )

    def test_missing_zsh_env_vars_raises(self) -> None:
        with (
            patch.dict(os.environ, {}, clear=True),
            patch("common.llm_client.ChatOpenAI") as openai_cls,
        ):
            with self.assertRaises(ValueError):
                get_langchain_client("openai")

        openai_cls.assert_not_called()


class GetLangchainClientOllamaTest(unittest.TestCase):
    def test_creates_ollama_client_with_expected_model(self) -> None:
        with (
            patch.dict(os.environ, {"OLLAMA_MODEL": "llama3"}, clear=True),
            patch("common.llm_client.ChatOllama") as ollama_cls,
        ):
            get_langchain_client("ollama")

        ollama_cls.assert_called_once_with(verbose=True, model="llama3")

    def test_missing_env_var_raises(self) -> None:
        with (
            patch.dict(os.environ, {}, clear=True),
            patch("common.llm_client.ChatOllama") as ollama_cls,
        ):
            with self.assertRaises(ValueError):
                get_langchain_client("ollama")

        ollama_cls.assert_not_called()


if __name__ == "__main__":
    unittest.main()
