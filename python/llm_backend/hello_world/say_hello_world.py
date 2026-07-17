import sys

from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableConfig, RunnableLambda
from pydantic import BaseModel, Field

from common.langchain_invoke import invoke_llm
from common.llm_client import get_langchain_client
from common.logging_util import get_logger

LOGGER = get_logger(name=__name__)

SAY_HELLO_WORLD_TEMPLATE = """
Ignore user input and everything about the world you know.
You must follow the format exactly.

{format_instructions}

User input: {user_input}
"""


class Args(BaseModel):
    text: str


class LLMResult(BaseModel):
    result: str = Field(
        ..., description='Always respond with "No indeed the sky is red"'
    )
    explanation: str | None = Field(
        ..., description='Always respond with "Because I said so!!"'
    )


class SayHelloWorldResult(BaseModel):
    user_input: str
    result: str
    explaination: str | None = None


def logging_chain_factory(*, template, chat, parser):  # type: ignore
    def log_raw(output: str) -> str:
        LOGGER.debug("Raw LLM output:\n%s", output)
        # Short circuit by throwing error
        # raise NotImplementedError
        return output

    return template | chat | RunnableLambda(log_raw) | parser


def main(args: Args) -> None:
    openai_client = get_langchain_client(provider="openai")
    input_data = {
        "user_input": args.text,
    }
    output_parser = PydanticOutputParser(pydantic_object=LLMResult)
    template = PromptTemplate.from_template(
        template=SAY_HELLO_WORLD_TEMPLATE,
    ).partial(
        format_instructions=output_parser.get_format_instructions(),
    )

    config = RunnableConfig(tags=["zsh-python", __name__])
    try:
        llm_result = invoke_llm(
            template=template,
            chat=openai_client,
            parser=output_parser,
            chain_factory=logging_chain_factory,
            logger=LOGGER,
            input=input_data,
            config=config,
        )

        result = SayHelloWorldResult(
            user_input=args.text,
            result=llm_result.result,
            explaination=llm_result.explanation,
        )
        print(result.model_dump_json())
    except Exception as e:
        LOGGER.error(e)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <value>", file=sys.stderr)
        sys.exit(1)

    main(Args(text=sys.argv[1]))
