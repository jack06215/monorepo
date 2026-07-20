import pandas
import pydantic


class HelloWordMode(pydantic.BaseModel):
    """Hello world dataclass."""

    message: str


class Args(pydantic.BaseModel):
    """Command line arguments."""

    message: str = "Hello world"


def main(args: Args) -> None:
    res = HelloWordMode(message=args.message)
    print(res)
    print(pandas.__version__)


if __name__ == "__main__":
    main(Args())
