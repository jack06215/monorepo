import os
import subprocess


def find_buildifier():
    runfiles_dir = os.environ.get("RUNFILES_DIR") or os.path.dirname(__file__)
    for root, dirs, files in os.walk(runfiles_dir):
        for f in files:
            if f == "buildifier.exe":
                return os.path.join(root, f)
    raise FileNotFoundError("Could not locate buildifier.exe in runfiles")


def main():
    buildifier_path = find_buildifier()

    print(f"Using buildifier at: {buildifier_path}")

    # Find all Bazel files recursively
    for root, _, files in os.walk("."):
        for name in files:
            if name.endswith((".bzl", ".bazel")) or name in (
                "BUILD",
                "BUILD.bazel",
                "WORKSPACE",
            ):
                full_path = os.path.join(root, name)
                print(f"Formatting {full_path}")
                subprocess.run(
                    [buildifier_path, "-mode=fix", full_path],
                    check=True,
                )


if __name__ == "__main__":
    main()
