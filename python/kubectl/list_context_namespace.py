import argparse
import json

from common.execute import kubectl_cli
from common.logging_util import get_logger

LOGGER = get_logger(__name__)


def list_contexts() -> list[str]:
    output = kubectl_cli(["config", "get-contexts", "-o", "name"])
    return output.splitlines()


def list_namespaces(context: str) -> list[str]:
    data = kubectl_cli(
        [
            "--context",
            context,
            "get",
            "namespaces",
            "-o",
            "json",
        ],
        output="json",
    )
    return [ns["metadata"]["name"] for ns in data["items"]]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="List Kubernetes namespaces per context"
    )
    parser.add_argument(
        "context",
        nargs="?",
        help="Kubeconfig context name (if omitted, list all contexts)",
    )
    args = parser.parse_args()

    if args.context:
        try:
            namespaces = list_namespaces(args.context)
        except Exception as exc:
            LOGGER.warning(
                "Cannot access namespaces for context=%s: %s",
                args.context,
                exc,
            )
            namespaces = []

        # stdout: machine-readable JSON only
        print(json.dumps({args.context: namespaces}, indent=2))
        return

    # No context provided → list all
    result: dict[str, list[str]] = {}

    for context in list_contexts():
        try:
            result[context] = list_namespaces(context)
        except Exception as exc:
            LOGGER.warning(
                "Cannot access namespaces for context=%s: %s",
                context,
                exc,
            )
            result[context] = []

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
