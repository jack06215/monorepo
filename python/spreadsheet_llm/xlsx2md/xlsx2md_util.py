"""Contains a SheetImageLoader class that allow you to loadimages from a sheet."""

import base64
import io
import string
from typing import Any

import openpyxl.cell
import openpyxl.drawing.image
import openpyxl.worksheet
import openpyxl.worksheet.worksheet
from PIL import Image


def get_pil_image_as_bytes(image: Image.Image) -> bytes:
    """Return Pillow image as bytes."""
    with io.BytesIO() as pxl_pil_buffered:
        image.save(pxl_pil_buffered, format="PNG")
        return base64.b64encode(pxl_pil_buffered.getvalue())


class SheetImageLoader:
    """Loads all images in a sheet."""

    def __init__(self, sheet: openpyxl.worksheet.worksheet.Worksheet) -> None:
        """Loads all sheet images."""
        self._images: dict[str, Any] = {}

        sheet_images: list[openpyxl.drawing.image.Image] = sheet._images
        for image in sheet_images:
            row = image.anchor._from.row + 1
            col = string.ascii_uppercase[image.anchor._from.col]
            self._images[f"{col}{row}"] = image._data

    def has_image_in_cell(self, cell: openpyxl.cell.Cell) -> bool:
        """Checks if there's an image in specified cell."""
        return cell.coordinate in self._images

    def get_image(self, cell: openpyxl.cell.Cell) -> Image.Image:
        """Retrieves image data from a cell."""
        if cell.coordinate not in self._images:
            raise ValueError(f"Cell {cell} doesn't contain an image")
        else:
            image = io.BytesIO(self._images[cell.coordinate]())
            return Image.open(image)
