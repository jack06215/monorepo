import argparse
import json
import logging
from dataclasses import dataclass
from typing import Any

from common.execute import aws_cli


@dataclass
class Args:
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


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    argparser = argparse.ArgumentParser()
    argparser.add_argument("--profile", required=True)
    argparser.add_argument("--role", required=True)
    args = Args(**vars(argparser.parse_args()))

    policies = list_role_policy(args.role, args.profile)
    print(json.dumps(policies, indent=2, ensure_ascii=False))
