import argparse
import json
import logging
from dataclasses import dataclass

from common.execute import aws_cli


@dataclass
class Args:
    profile: str


def list_assumable_role(profile: str) -> list[str]:
    result: list[str] = []
    marker: str | None = None

    while True:
        cmd = ["--profile", profile, "iam", "list-roles"]
        if marker:
            cmd += ["--marker", marker]

        resp = aws_cli(cmd)

        for role in resp.get("Roles", []):
            statements = role.get("AssumeRolePolicyDocument", {}).get("Statement", [])

            # JMESPath equivalent of: Statement[].Principal.AWS != null
            aws_projection = [
                stmt.get("Principal", {}).get("AWS")
                for stmt in statements
                if "Principal" in stmt
            ]

            if aws_projection is not None:
                result.append(role["RoleName"])

        if not resp.get("IsTruncated"):
            break
        marker = resp.get("Marker")

    return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    argparser = argparse.ArgumentParser()
    argparser.add_argument("--profile", required=True)
    args = Args(**vars(argparser.parse_args()))

    roles = list_assumable_role(args.profile)
    print(json.dumps(roles, indent=2, ensure_ascii=False))
