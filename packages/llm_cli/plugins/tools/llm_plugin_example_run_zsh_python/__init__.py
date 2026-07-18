import json
from typing import Any

import llm
from llm_plugin_cmd import run_command
from pydantic import BaseModel


class ExampleZshPythonInput(BaseModel):
    text: str


class ExampleZshPythonOutput(BaseModel):
    user_input: str
    result: str
    explaination: str | None = None


class ExampleZshPython(llm.Toolbox):
    input_schema = ExampleZshPythonInput.model_json_schema()
    output_schema = ExampleZshPythonOutput.model_json_schema()

    def explain(self, text: str) -> dict[str, Any]:
        """Explain user query and the result.

        Analyzes the input `user_query` by running the LangChain agent.
        The result is stored in `result`, the `result` may also contains
        a detailed explaination in the `explaination` field.
        contains `None`.

        Args:
            text: A sentence or paragraph to analyze.

        Returns:
            A dictionary with keys "user_input", "result", and "explaination".
        """
        rtn = run_command(["llm_agent_say_hello_world", text])
        data: dict[str, Any] = json.loads(rtn.stdout)

        return ExampleZshPythonOutput(
            user_input=data["user_input"],
            result=data["result"],
            explaination=data.get("explaination", None),
        ).model_dump()


@llm.hookimpl
def register_tools(register):
    register(ExampleZshPython)
