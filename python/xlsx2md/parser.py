"""Converts Excel file to Markdown table."""

from typing import cast

import openpyxl
import pandas as pd

from xlsx2md import types, xlsx2md_util


def drop_nan_values(df: pd.DataFrame) -> pd.DataFrame:
    """Drop rows with NaN values."""
    return df.dropna(how="all")


def fill_nan_values(df: pd.DataFrame) -> pd.DataFrame:
    """Fill NaN values with previous non-NaN value."""
    df = df.ffill()
    df = df.bfill()
    return df


class Xlsx2Markdown:
    """Converts Excel file to Markdown table."""

    def __init__(self, filename: str) -> None:
        """Constructor."""
        self._dataframe = pd.read_excel(filename, sheet_name=None)
        self._pxl_doc = openpyxl.load_workbook(filename)

    def parse(self) -> list[types.ParsedWorksheet]:
        """Convert Excel file to Markdown."""
        res: list[types.ParsedWorksheet] = []
        for sheet_name, df_res in self._dataframe.items():
            pxl_sheet = self._pxl_doc[sheet_name]
            pxl_image_loader = xlsx2md_util.SheetImageLoader(pxl_sheet)
            images: list[str] = []
            image_idx = 1
            for pd_row_idx, pd_row_data in df_res.iterrows():
                for pd_column_idx, _pd_cell_data in enumerate(pd_row_data):
                    # Offset as openpyxl sheets index by one, and also offset the row
                    # index by one more to account for the header row
                    pxl_cell_coord = pxl_sheet.cell(
                        cast(int, pd_row_idx) + 2,
                        pd_column_idx + 1,
                    )
                    if pxl_image_loader.has_image_in_cell(pxl_cell_coord):
                        # We have a cell that contains an image, we want to convert it
                        # to base64
                        pxl_pil_img = pxl_image_loader.get_image(pxl_cell_coord)
                        pxl_pil_img_b64_str = xlsx2md_util.get_pil_image_as_bytes(
                            pxl_pil_img
                        )
                        df_res.iat[pd_row_idx, pd_column_idx] = f"![][image{image_idx}]"

                        images.append(
                            f"[image{image_idx}]:<data:image/png;base64,{pxl_pil_img_b64_str.decode()}>"
                        )
                        image_idx += 1

            df_res = df_res.pipe(drop_nan_values).pipe(fill_nan_values)
            res.append(
                types.ParsedWorksheet(
                    worksheet_name=sheet_name,
                    worksheet=df_res,
                    base64_encoded_images=images,
                )
            )

        return res
