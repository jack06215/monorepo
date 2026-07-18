# Packages

- List of targets

```sh
bazel query "//packages/..."
```

- List of target labels

```sh
bazel query "//packages/hello_world:*"
```

## Python-specific command

- Output `requirements.txt` from poetry

```sh
poetry export -f requirements.txt -o requirements.txt --without-hashes
```
