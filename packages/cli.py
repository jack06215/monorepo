"""packages tools CLI."""

from __future__ import annotations

import argparse
from typing import Callable, TypeVar

import pydantic

from packages.aws import list_assumable_role, list_role_policy
from packages.docx2md import docx2md_cli
from packages.formatting import jira_ticket, jsonl_unescape, kibana_response_stringify
from packages.hello_world import hello_world_cli

ArgsT = TypeVar("ArgsT", bound=pydantic.BaseModel)
Handler = Callable[[argparse.Namespace], None]


def _make_handler(
    args_cls: type[ArgsT],
    main_fn: Callable[[ArgsT], None],
) -> Handler:
    """Build a subparser handler that validates argparse output via `args_cls` and calls `main_fn`."""

    def handler(namespace: argparse.Namespace) -> None:
        kwargs = {
            key: value
            for key, value in vars(namespace).items()
            if key not in {"command", "handler"}
        }
        main_fn(args_cls(**kwargs))

    return handler


def _register_docx2md(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    parser = subparsers.add_parser(
        "docx2md",
        help="Convert a folder of DOCX files to Markdown.",
    )
    parser.add_argument(
        "--folder_path",
        type=str,
        help="Folder path to DOCX files.",
        required=True,
    )
    parser.add_argument(
        "--output_path",
        type=str,
        help="Output folder path.",
        required=True,
    )
    parser.set_defaults(
        handler=_make_handler(
            docx2md_cli.Args,
            docx2md_cli.main,
        )
    )


def _register_hello_world(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    parser = subparsers.add_parser(
        "hello_world",
        help="Print a hello world message.",
    )
    parser.add_argument(
        "--message",
        type=str,
        help="Message to print.",
        default="Hello world",
    )
    parser.set_defaults(
        handler=_make_handler(
            hello_world_cli.Args,
            hello_world_cli.main,
        )
    )


def _register_list_assumable_role(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    parser = subparsers.add_parser(
        "list_assumable_role",
        help="List IAM roles that can be assumed by a principal.",
    )
    parser.add_argument(
        "--profile",
        type=str,
        help="AWS CLI profile to use.",
        required=True,
    )
    parser.set_defaults(
        handler=_make_handler(
            list_assumable_role.Args,
            list_assumable_role.main,
        )
    )


def _register_list_role_policy(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    parser = subparsers.add_parser(
        "list_role_policy",
        help="List inline IAM policies attached to a role.",
    )
    parser.add_argument(
        "--profile",
        type=str,
        help="AWS CLI profile to use.",
        required=True,
    )
    parser.add_argument(
        "--role",
        type=str,
        help="IAM role name.",
        required=True,
    )
    parser.set_defaults(
        handler=_make_handler(
            list_role_policy.Args,
            list_role_policy.main,
        )
    )


def _register_jira_ticket(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    parser = subparsers.add_parser(
        "jira_ticket",
        help="Render a Jira issue JSON (from acli, via stdin) into readable terminal output.",
    )
    parser.set_defaults(
        handler=_make_handler(
            jira_ticket.Args,
            jira_ticket.main,
        )
    )


def _register_jsonl_unescape(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    parser = subparsers.add_parser(
        "jsonl_unescape",
        help="Convert a JSONL file into human-readable UTF-8 JSONL, written to stdout.",
    )
    parser.add_argument(
        "input",
        type=str,
        nargs="?",
        default=None,
        help="Path to the JSONL file (defaults to stdin).",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print each JSON object with indent=2 instead of one line.",
    )
    parser.set_defaults(
        handler=_make_handler(
            jsonl_unescape.Args,
            jsonl_unescape.main,
        )
    )


def _register_kibana_response_stringify(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    parser = subparsers.add_parser(
        "kibana_response_stringify",
        help="Normalize Kibana Dev Tools console output (via stdin) into valid JSON.",
    )
    parser.set_defaults(
        handler=_make_handler(
            kibana_response_stringify.Args,
            kibana_response_stringify.main,
        )
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cli")
    subparsers = parser.add_subparsers(dest="command", required=True)

    _register_docx2md(subparsers)
    _register_hello_world(subparsers)
    _register_jira_ticket(subparsers)
    _register_jsonl_unescape(subparsers)
    _register_kibana_response_stringify(subparsers)
    _register_list_assumable_role(subparsers)
    _register_list_role_policy(subparsers)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    handler: Handler = args.handler
    handler(args)


if __name__ == "__main__":
    main()
