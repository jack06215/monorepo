# Python projects

- List of targets

```sh
bazel query "//python/..."
```

- List of target labels

```sh
bazel query "//python/hello_world:*"
```

## Python-specific command

- Output `requirements.txt` from poetry

```sh
poetry export -f requirements.txt -o requirements.txt --without-hashes
```
