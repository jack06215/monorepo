import sys

from common.execute import run_command

JQ_FILTER = r"""
.[]
| {
    system: (
      .prompt_json.messages[]
      | select(.role=="system")
      | .content
      | if type=="string" then .
        else .["$r"][1]
        end
    ),
    response: .response
  }
| select(.response != "")
"""


def main() -> None:
    data = sys.stdin.read()
    if not data.strip():
        return

    result = run_command(
        ["jq", "-r", JQ_FILTER],
        input=data,
        text=True,
        check=True,
    )

    sys.stdout.write(result.stdout)


if __name__ == "__main__":
    main()
