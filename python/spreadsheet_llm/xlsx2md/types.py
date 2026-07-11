"""Types for Excel to Markdown conversion."""

import pandas as pd
import pydantic


class ParsedWorksheet(pydantic.BaseModel):
    """Parsed Xlsx DataFrame."""

    worksheet_name: str
    worksheet: pd.DataFrame
    base64_encoded_images: list[str]
    model_config = pydantic.ConfigDict(
        arbitrary_types_allowed=True,
    )

    def to_markdown(self) -> str:
        """Convert DataFrames to Markdown."""
        markdown_str = self.worksheet.to_markdown(index=False) + "\n\n"
        markdown_str += "\n".join(self.base64_encoded_images)
        return markdown_str
