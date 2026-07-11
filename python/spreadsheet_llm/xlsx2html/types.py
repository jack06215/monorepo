"""Types for Excel to HTML conversion."""

import pydantic


class ParsedWorksheet(pydantic.BaseModel):
    """One worksheet rendered as a token-compact HTML fragment.

    Embedded images are intentionally NOT inlined into the HTML (base64
    data URIs are token-catastrophic for LLM context); cells containing an
    image carry an "[image]" placeholder and the extracted base64 PNGs are
    kept here for separate/multimodal use.
    """

    worksheet_name: str
    html: str
    base64_encoded_images: list[str] = pydantic.Field(default_factory=list)

    def to_html(self) -> str:
        """Return the HTML fragment (<style> block + <table>)."""
        return self.html
