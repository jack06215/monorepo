"""Invoke a LangChain LLM with retry logic using Tenacity."""

import logging
from collections.abc import Callable
from typing import Any, Protocol, TypeAlias, TypeVar, overload

from langchain_core.callbacks import BaseCallbackManager
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_core.output_parsers import PydanticOutputParser, StrOutputParser
from langchain_core.prompts import (
    BasePromptTemplate,
    ChatPromptTemplate,
    PromptTemplate,
)
from langchain_core.runnables import RunnableConfig, RunnableSerializable
from openai import RateLimitError
from pydantic import BaseModel
from tenacity import (
    RetryCallState,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_random_exponential,
)

ChatLLM: TypeAlias = RunnableSerializable[Any, BaseMessage]
T = TypeVar("T", bound=BaseModel)

logger = logging.getLogger(__name__)


class ChainFactory(Protocol):
    def __call__(
        self,
        *,
        template: BasePromptTemplate[str],
        chat: ChatLLM,
        parser: RunnableSerializable[Any, Any],
    ) -> RunnableSerializable[Any, Any]: ...


def before_sleep_with_title(
    logger_: logging.Logger,
) -> Callable[[RetryCallState], None]:
    def _hook(retry_state: RetryCallState) -> None:
        title = retry_state.kwargs.get("title", "<title>")
        exc = retry_state.outcome.exception() if retry_state.outcome else None
        logger_.warning(
            "Retrying LLM invocation (attempt %d) for %s due to %s",
            retry_state.attempt_number,
            title,
            type(exc).__name__ if exc else "unknown error",
        )

    return _hook


@retry(
    retry=(
        retry_if_exception_type(RateLimitError) | retry_if_exception_type(ValueError)
    ),
    wait=wait_random_exponential(multiplier=1, max=20),
    stop=stop_after_attempt(6),
    before_sleep=before_sleep_with_title(logger),
    reraise=True,
)
def _invoke_with_retry(
    *,
    chain_factory: ChainFactory,
    template_holder: dict[str, BasePromptTemplate[str]],
    chat: ChatLLM,
    parser: RunnableSerializable[Any, Any],
    input_data: dict[str, Any],
    config: RunnableConfig,
    title: str,
) -> Any:
    try:
        chain = chain_factory(
            template=template_holder["template"],
            chat=chat,
            parser=parser,
        )
        return chain.invoke(input_data, config)

    except ValueError as e:
        template = template_holder["template"]
        err_msg = f"\nError in {title} ({type(e).__name__}): {e}"

        if isinstance(template, PromptTemplate):
            template_holder["template"] = PromptTemplate.from_template(
                template.template + err_msg
            )

        elif isinstance(template, ChatPromptTemplate):
            template_holder["template"] = ChatPromptTemplate.from_messages(
                [*template.messages, HumanMessage(content=err_msg)]
            )

        raise


def _default_chain_factory(
    *,
    template: BasePromptTemplate[str],
    chat: ChatLLM,
    parser: RunnableSerializable[Any, Any],
) -> RunnableSerializable[Any, Any]:
    return template | chat | parser


@overload
def invoke_llm(
    *,
    template: BasePromptTemplate[str],
    chat: ChatLLM,
    parser: StrOutputParser,
    logger: logging.Logger,
    chain_factory: ChainFactory | None = None,
    input: dict[str, Any] | None = None,
    config: RunnableConfig | None = None,
    title: str | None = None,
) -> str: ...


@overload
def invoke_llm(
    *,
    template: BasePromptTemplate[str],
    chat: ChatLLM,
    parser: PydanticOutputParser[T],
    logger: logging.Logger,
    chain_factory: ChainFactory | None = None,
    input: dict[str, Any] | None = None,
    config: RunnableConfig | None = None,
    title: str | None = None,
) -> T: ...


def invoke_llm(
    *,
    template: BasePromptTemplate[str],
    chat: ChatLLM,
    parser: RunnableSerializable[Any, Any],
    logger: logging.Logger,
    chain_factory: ChainFactory | None = None,
    input: dict[str, Any] | None = None,
    config: RunnableConfig | None = None,
    title: str | None = None,
) -> Any:
    """Invoke an LLM with retry logic.
    Accepts an external chain_factory for custom chain composition.
    """
    config = config or RunnableConfig()
    input_data = input or {}

    normalized_title = title or input_data.get("title", "<title>")
    assert isinstance(normalized_title, str)

    callbacks = config.get("callbacks", [])
    if callbacks is None or isinstance(callbacks, list):
        callbacks = BaseCallbackManager(handlers=callbacks or [])
    config["callbacks"] = callbacks

    factory = chain_factory or _default_chain_factory

    logger.info("Invoking LLM chain for %s...", normalized_title)

    template_holder: dict[str, BasePromptTemplate[str]] = {
        "template": template
    }

    try:
        return _invoke_with_retry(
            chain_factory=factory,
            template_holder=template_holder,
            chat=chat,
            parser=parser,
            input_data=input_data,
            config=config,
            title=normalized_title,
        )

    except Exception:
        logger.exception(
            "LLM invocation failed after retries for %s",
            normalized_title,
        )
        raise
