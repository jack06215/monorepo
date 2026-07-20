import json
import logging
from typing import Any

from pydantic import BaseModel

from packages.common.execute import aws_cli


class Args(BaseModel):
    profile: str
    role: str


def list_role_policy(role_name: str, profile: str) -> list[dict[str, Any]]:
    list_resp = aws_cli(
        [
            "--profile",
            profile,
            "iam",
            "list-role-policies",
            "--role-name",
            role_name,
        ]
    )

    policy_names = list_resp.get("PolicyNames", [])
    results: list[dict[str, Any]] = []

    # 2. fetch each policy document
    for policy_name in policy_names:
        policy_resp = aws_cli(
            [
                "--profile",
                profile,
                "iam",
                "get-role-policy",
                "--role-name",
                role_name,
                "--policy-name",
                policy_name,
            ]
        )

        results.append(
            {
                "RoleName": role_name,
                "PolicyName": policy_name,
                "PolicyDocument": policy_resp["PolicyDocument"],
            }
        )

    return results


def main(args: Args) -> None:
    logging.basicConfig(level=logging.INFO)
    policies = list_role_policy(args.role, args.profile)
    print(json.dumps(policies, indent=2, ensure_ascii=False))
