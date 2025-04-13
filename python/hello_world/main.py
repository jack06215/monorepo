import pydantic


class HelloWordMode(pydantic.BaseModel):
    """Hello world dataclass."""

    message: str


def main() -> None:
    res = HelloWordMode(message="Hello world")
    print(res)


if __name__ == "__main__":
    main()
