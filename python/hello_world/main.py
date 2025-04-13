import pydantic
import pandas


class HelloWordMode(pydantic.BaseModel):
    """Hello world dataclass."""

    message: str


def main() -> None:
    res = HelloWordMode(message="Hello world")
    print(res)
    print(pandas.__version__)


if __name__ == "__main__":
    main()
