"""Helpers shared across pages.

Exists to exercise first-party imports in a larger Streamlit app: it is a
`py_library` dep of the binary, so it lands next to `main.py` in the runfiles
tree and `import shared` resolves from every page.
"""

APP_NAME = "Hello Streamlit"


def greeting(name: str) -> str:
    who = name.strip() or "world"
    return f"Hello, {who}! Welcome to {APP_NAME}."
