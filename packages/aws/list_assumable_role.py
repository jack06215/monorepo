import json

from pydantic import BaseModel

from packages.common.execute import aws_cli


class Args(BaseModel):
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


def main(args: Args) -> None:
    roles = list_assumable_role(args.profile)
    print(json.dumps(roles, indent=2, ensure_ascii=False))
