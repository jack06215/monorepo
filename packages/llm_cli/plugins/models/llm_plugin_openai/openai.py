"""My impl for OpenAI provider."""

import json
import os
from collections.abc import Iterator
from typing import Any, cast

import llm
from llm import Attachment, Conversation, KeyModel, Prompt, Response, Tool
from llm.default_plugins.openai_models import _Shared
from llm.utils import logging_client, remove_dict_none_values, simplify_usage_dict
from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam
from openai.types.chat.chat_completion_message_function_tool_call import (
    ChatCompletionMessageFunctionToolCall,
)


# =================================================
# Tool to OpenAI schema
# =================================================
def tool_to_openai_schema(tool: Tool) -> dict[str, Any]:
    schema = getattr(tool, "input_schema", None)
    if callable(schema):
        schema = schema()
    if not isinstance(schema, dict):
        schema = {
            "type": "object",
            "properties": {},
        }
    json.dumps(schema)
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description or "",
            "parameters": schema,
        },
    }


# =================================================
# Attachments
# =================================================
def _attachment(attachment: Attachment) -> dict[str, Any]:
    url = attachment.url
    if not url:
        url = f"data:{attachment.resolve_type()};base64,{attachment.base64_content()}"
    return {
        "type": "image_url",
        "image_url": {
            "url": url,
        },
    }


def redact_data(data: Any) -> Any:
    if isinstance(data, dict):
        for k, v in data.items():
            if (
                k == "image_url"
                and isinstance(v, dict)
                and v.get("url", "").startswith("data:")
            ):
                v["url"] = "data:..."
            else:
                redact_data(v)
    elif isinstance(data, list):
        for i in data:
            redact_data(i)
    return data


# =================================================
# Shared Azure base
# =================================================
class OpenAIShared(_Shared):
    needs_key = None
    key_env_var = None

    def __init__(
        self,
        model_id: str,
        model_name: str,
        endpoint: str | None = None,
        api_key_name: str | None = None,
        org_id: str | None = None,
        project_id: str | None = None,
        **kwargs: Any,
    ):
        self.model_id = model_id
        self.model_name = model_name
        self.org_id = org_id
        self.project_id = project_id
        self.endpoint = endpoint

        if self.endpoint is not None:
            self.endpoint = self.endpoint.rstrip("/")
        if self.org_id is not None:
            os.environ["OPENAI_ORG_ID"] = self.org_id
        if self.project_id is not None:
            os.environ["OPENAI_PROJECT_ID"] = self.project_id

        if api_key_name:
            self.needs_key = api_key_name
            self.key_env_var = f"LLM_{api_key_name.upper()}_KEY"

        super().__init__(
            model_id=model_id,
            model_name=model_name,
            supports_tools=True,
            vision=True,
            **kwargs,
        )

        self.attachment_types.update(
            {
                "image/png",
                "image/jpeg",
                "image/webp",
                "image/gif",
            }
        )

    def get_client(self, key: str, *, async_: bool = False) -> OpenAI:
        if not key:
            raise RuntimeError(
                f"API key required (expected env var {self.key_env_var})"
            )

        client_kwargs: dict[str, Any] = {
            "api_key": key,
            "organization": self.org_id,
            "project": self.project_id,
        }

        if os.environ.get("LLM_OPENAI_SHOW_RESPONSES"):
            client_kwargs["http_client"] = logging_client()

        # NOTE: llm.execute() is synchronous; async client is not supported here.
        return OpenAI(**client_kwargs)

    def build_kwargs(self, prompt: Prompt, stream: bool) -> dict[str, Any]:
        kwargs: dict[str, Any] = {}

        opts = prompt.options
        for name in ("temperature", "max_tokens", "top_p"):
            val = getattr(opts, name, None)
            if val is not None:
                kwargs[name] = val

        if prompt.schema:
            kwargs["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": "output",
                    "schema": prompt.schema,
                },
            }

        if prompt.tools:
            kwargs["tools"] = [tool_to_openai_schema(t) for t in prompt.tools]

        return kwargs


# =================================================
# Chat model
# =================================================
class OpenAIChat(OpenAIShared, KeyModel):  # type: ignore[misc]
    can_stream = True
    vision = True
    supports_tools = True

    def execute(
        self,
        prompt: Prompt,
        stream: bool,
        response: Response,
        conversation: Conversation | None = None,
        key: str | None = None,
    ) -> Iterator[str]:
        client = self.get_client(key or "")

        messages: list[ChatCompletionMessageParam] = []
        current_system: str | None = None

        # ---------------- Conversation history ----------------
        if conversation:
            for prev_base in conversation.responses:
                prev = cast(Response, prev_base)

                if prev.prompt.system and prev.prompt.system != current_system:
                    messages.append(
                        cast(
                            ChatCompletionMessageParam,
                            {
                                "role": "system",
                                "content": prev.prompt.system,
                            },
                        )
                    )
                    current_system = prev.prompt.system

                if prev.prompt.prompt:
                    messages.append(
                        cast(
                            ChatCompletionMessageParam,
                            {
                                "role": "user",
                                "content": prev.prompt.prompt,
                            },
                        )
                    )

                for tr in prev.prompt.tool_results:
                    messages.append(
                        cast(
                            ChatCompletionMessageParam,
                            {
                                "role": "tool",
                                "tool_call_id": tr.tool_call_id,
                                "content": json.dumps(tr.output),
                            },
                        )
                    )

                text = prev.text()
                if text:
                    messages.append(
                        cast(
                            ChatCompletionMessageParam,
                            {
                                "role": "assistant",
                                "content": text,
                            },
                        )
                    )

                tool_calls = prev.tool_calls()
                if tool_calls:
                    messages.append(
                        cast(
                            ChatCompletionMessageParam,
                            {
                                "role": "assistant",
                                "tool_calls": [
                                    {
                                        "type": "function",
                                        "id": tc.tool_call_id,
                                        "function": {
                                            "name": tc.name,
                                            "arguments": json.dumps(tc.arguments),
                                        },
                                    }
                                    for tc in tool_calls
                                ],
                            },
                        )
                    )

        # ---------------- Current prompt ----------------
        if prompt.system and prompt.system != current_system:
            messages.append(
                cast(
                    ChatCompletionMessageParam,
                    {
                        "role": "system",
                        "content": prompt.system,
                    },
                )
            )

        for tr in prompt.tool_results:
            messages.append(
                cast(
                    ChatCompletionMessageParam,
                    {
                        "role": "tool",
                        "tool_call_id": tr.tool_call_id,
                        "content": json.dumps(tr.output),
                    },
                )
            )

        if prompt.attachments:
            content: list[dict[str, Any]] = []
            if prompt.prompt:
                content.append(
                    {
                        "type": "text",
                        "text": prompt.prompt,
                    }
                )
            for att in prompt.attachments:
                content.append(_attachment(att))
            messages.append(
                cast(
                    ChatCompletionMessageParam,
                    {
                        "role": "user",
                        "content": content,
                    },
                )
            )
        elif prompt.prompt:
            messages.append(
                cast(
                    ChatCompletionMessageParam,
                    {
                        "role": "user",
                        "content": prompt.prompt,
                    },
                )
            )

        if prompt.tools:
            stream = False

        kwargs = self.build_kwargs(prompt, stream)

        # ---------------- Streaming ----------------
        if stream:
            completion = client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                stream=True,
                stream_options={
                    "include_usage": True,
                },
                **kwargs,
            )

            usage: dict[str, Any] | None = None
            for chunk in completion:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta
                if delta and delta.content:
                    yield delta.content
                if chunk.usage:
                    usage = chunk.usage.model_dump()

            if usage is not None:
                response.set_usage(
                    input=usage["prompt_tokens"],
                    output=usage["completion_tokens"],
                    details=simplify_usage_dict(usage),
                )
            return

        # ---------------- Non-stream ----------------
        completion = client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            stream=False,
            **kwargs,
        )

        msg = completion.choices[0].message

        for tc in (
            cast(list[ChatCompletionMessageFunctionToolCall], msg.tool_calls) or []
        ):
            response.add_tool_call(
                llm.ToolCall(
                    tool_call_id=tc.id,
                    name=tc.function.name,
                    arguments=json.loads(tc.function.arguments),
                )
            )

        if msg.content:
            yield msg.content

        if completion.usage is not None:
            usage = completion.usage.model_dump()
            response.set_usage(
                input=usage["prompt_tokens"],
                output=usage["completion_tokens"],
                details=simplify_usage_dict(usage),
            )

        response.response_json = remove_dict_none_values(completion.model_dump())
        cast(Any, response)._prompt_json = redact_data({"messages": messages})
