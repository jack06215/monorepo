import os
from typing import Any, Literal, overload

from langchain_ollama import ChatOllama
from langchain_openai import AzureChatOpenAI, ChatOpenAI

from common.logging_util import get_logger
from common.sys_util import (
    check_environ_azure_openai,
    check_environ_ollama,
    check_environ_openai,
)

LOGGER = get_logger(__name__)

Provider = Literal["azure", "ollama", "openai"]


@overload
def get_langchain_client(
    provider: Literal["azure"],
    **kwargs: Any,
) -> AzureChatOpenAI: ...


@overload
def get_langchain_client(
    provider: Literal["openai"],
    **kwargs: Any,
) -> ChatOpenAI: ...


@overload
def get_langchain_client(
    provider: Literal["ollama"],
    **kwargs: Any,
) -> ChatOllama: ...


def get_langchain_client(
    provider: Provider,
    **kwargs: Any,
) -> AzureChatOpenAI | ChatOpenAI | ChatOllama:
    LOGGER.info("Creating LangChain client: provider=%s", provider)

    params: dict[str, Any] = {"verbose": True} | kwargs

    match provider:
        case "azure":
            check_environ_azure_openai()
            params["AZURE_OPENAI_DEPLOYMENT_NAME"] = os.getenv(
                "AZURE_OPENAI_DEPLOYMENT_NAME", ""
            )
            return AzureChatOpenAI(**params)

        case "openai":
            os.environ["OPENAI_API_KEY"] = os.getenv(
                "LLM_ZSH_PYTHON_OPENAI_API_KEY",
                "",
            )
            os.environ["OPENAI_MODEL"] = os.getenv("LLM_ZSH_PYTHON_OPENAI_MODEL", "")

            check_environ_openai()
            params["model"] = os.environ["OPENAI_MODEL"]
            return ChatOpenAI(**params)

        case "ollama":
            check_environ_ollama()
            params["model"] = os.environ["OLLAMA_MODEL"]
            return ChatOllama(**params)
