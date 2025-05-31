import pandas
import pydantic


class HelloWordMode(pydantic.BaseModel):
    """Hello world dataclass. Test."""

    message: str


def main() -> None:
    res = HelloWordMode(message="Hello world")
    print(res)
    print(pandas.__version__)


if __name__ == "__main__":
    main()
