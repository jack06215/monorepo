import argparse

from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableConfig, RunnableLambda
from pydantic import BaseModel, Field

from common.execute import run_command
from common.langchain_invoke import invoke_llm
from common.llm_client import get_langchain_client
from common.logging_util import get_logger

LOGGER = get_logger(name=__name__)


SYSTEM_TEMPLATE = """
You are writing a GitHub Pull Request description.

Rules:
- You MUST output valid JSON that matches the schema exactly.
- You MUST fill the markdown template by replacing placeholders like {change_1}.
- Keep sections "QA" and "References" empty as-is (do not add content).
- Be concise and specific.
- Only use information supported by the git diff and template context.
- If the diff is too large or unclear, summarize at a high level and mark details as "TBD".
"""


PROMPT_TEMPLATE = """
{system_instructions}

Markdown template (fill this):
---
{md_template}
---

Git diff:
---
{git_diff}
---

Write everything required to create a GitHub Pull Request.
Return JSON only.

{format_instructions}
"""


class Args(BaseModel):
    template_path: str
    base: str = "origin/master"
    head: str = "HEAD"
    max_diff_chars: int = 60000  # safety cap


class PRCreateResult(BaseModel):
    """Everything required to create a PR via gh."""

    title: str = Field(
        ...,
        description=(
            "A concise GitHub Pull Request title (max ~72 chars). "
            "Start with a verb in imperative mood (e.g., 'Upgrade', 'Fix', 'Add'). "
            "Must summarize the primary change."
        ),
    )

    body: str = Field(
        ...,
        description=(
            "A complete GitHub Pull Request body in Markdown. "
            "It MUST be the provided template with placeholders replaced. "
            "Do NOT add additional sections. "
            "Leave the '## QA' section empty (keep the heading only) and "
            "leave the '## References' section empty (keep the heading only)."
        ),
    )


def read_text_file(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


def get_git_diff(base: str, head: str) -> str:
    # You can tweak flags:
    # --minimal / --patience, or add -- . for scope, etc.
    return run_command(["git", "diff", f"{base}...{head}"]).stdout


def logging_chain_factory(*, template, chat, parser):  # type: ignore
    def log_raw(output: str) -> str:
        LOGGER.debug("Raw LLM output:\n%s", output)
        return output

    return template | chat | RunnableLambda(log_raw) | parser


def generate_pr_create_payload(*, template_md: str, git_diff: str) -> PRCreateResult:
    openai_client = get_langchain_client(provider="openai")

    output_parser = PydanticOutputParser(pydantic_object=PRCreateResult)

    prompt = PromptTemplate.from_template(PROMPT_TEMPLATE).partial(
        system_instructions=SYSTEM_TEMPLATE.strip(),
        format_instructions=output_parser.get_format_instructions(),
    )

    input_data = {
        "md_template": template_md,
        "git_diff": git_diff,
    }

    config = RunnableConfig(tags=["pr-create-gen", __name__])

    return invoke_llm(
        template=prompt,
        chat=openai_client,
        parser=output_parser,
        chain_factory=logging_chain_factory,
        logger=LOGGER,
        input=input_data,
        config=config,
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("template_path", help="Path to markdown template file")
    ap.add_argument(
        "--base",
        default="origin/master",
        help="Base ref for diff (default: origin/main)",
    )
    ap.add_argument("--head", default="HEAD", help="Head ref for diff (default: HEAD)")
    ap.add_argument(
        "--max-diff-chars", type=int, default=60000, help="Cap diff size passed to LLM"
    )
    ns = ap.parse_args()

    args = Args(
        template_path=ns.template_path,
        base=ns.base,
        head=ns.head,
        max_diff_chars=ns.max_diff_chars,
    )

    try:
        template_md = read_text_file(args.template_path)
        diff = get_git_diff(args.base, args.head)

        if len(diff) > args.max_diff_chars:
            LOGGER.warning(
                "Diff is large (%d chars), truncating to %d chars",
                len(diff),
                args.max_diff_chars,
            )
            diff = diff[: args.max_diff_chars] + "\n\n# NOTE: diff truncated\n"

        payload = generate_pr_create_payload(
            template_md=template_md,
            git_diff=diff,
        )

        # stdout = machine-readable JSON only
        print(payload.model_dump_json())
        return 0
    except Exception as e:
        LOGGER.error("%s", e)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
