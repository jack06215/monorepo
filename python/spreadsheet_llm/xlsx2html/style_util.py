"""Color resolution and cell-style extraction for xlsx -> HTML conversion.

openpyxl colors come in three flavors that all need different handling to
become a CSS hex value:
  - "rgb":     literal aRGB hex on the cell (drop the alpha byte)
  - "indexed": index into the legacy fixed palette (COLOR_INDEX); indices
               64/65 are "system auto" colors with no fixed value
  - "theme":   index into the workbook theme's color scheme, plus a "tint"
               that lightens (>0) or darkens (<0) the base color per
               ECMA-376's HLS luminance transform
"""

import colorsys
import xml.etree.ElementTree as ET
from typing import Any, Optional, cast

import openpyxl
from openpyxl.cell.cell import Cell
from openpyxl.styles.colors import COLOR_INDEX, Color

# Excel maps theme color index 0/1 to lt1/dk1 (swapped vs. the XML document
# order, which is dk1 first), and 2/3 to lt2/dk2 likewise.
_THEME_SCHEME_ORDER = (
    "lt1",
    "dk1",
    "lt2",
    "dk2",
    "accent1",
    "accent2",
    "accent3",
    "accent4",
    "accent5",
    "accent6",
    "hlink",
    "folHlink",
)

# Office default theme, used when a workbook carries no theme part.
DEFAULT_THEME_PALETTE = (
    "FFFFFF",
    "000000",
    "E7E6E6",
    "44546A",
    "4472C4",
    "ED7D31",
    "A5A5A5",
    "FFC000",
    "5B9BD5",
    "70AD47",
    "0563C1",
    "954F72",
)

_DRAWINGML_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"

# Excel border styles -> closest compact CSS equivalent.
_BORDER_STYLE_CSS = {
    "hair": "1px solid",
    "thin": "1px solid",
    "medium": "2px solid",
    "thick": "3px solid",
    "double": "3px double",
    "dotted": "1px dotted",
    "dashed": "1px dashed",
    "dashDot": "1px dashed",
    "dashDotDot": "1px dashed",
    "mediumDashed": "2px dashed",
    "mediumDashDot": "2px dashed",
    "mediumDashDotDot": "2px dashed",
    "slantDashDot": "2px dashed",
}


def extract_theme_palette(workbook: openpyxl.Workbook) -> tuple[str, ...]:
    """Parse the workbook's theme XML into a hex palette ordered by the
    theme color *index* used by cell styles (see _THEME_SCHEME_ORDER)."""
    theme_xml = getattr(workbook, "loaded_theme", None)
    if not theme_xml:
        return DEFAULT_THEME_PALETTE
    try:
        root = ET.fromstring(theme_xml)
        scheme = root.find(
            f"{{{_DRAWINGML_NS}}}themeElements/{{{_DRAWINGML_NS}}}clrScheme"
        )
        if scheme is None:
            return DEFAULT_THEME_PALETTE
        palette = []
        for name in _THEME_SCHEME_ORDER:
            element = scheme.find(f"{{{_DRAWINGML_NS}}}{name}")
            if element is None or len(element) == 0:
                return DEFAULT_THEME_PALETTE
            child = element[0]
            # sysClr carries the resolved value in lastClr; srgbClr in val.
            palette.append(child.get("lastClr") or child.get("val") or "000000")
        return tuple(palette)
    except ET.ParseError:
        return DEFAULT_THEME_PALETTE


def _apply_tint(hex_rgb: str, tint: float) -> str:
    """ECMA-376 tint: scale the HLS luminance toward black (tint<0) or
    white (tint>0)."""
    r, g, b = (int(hex_rgb[i : i + 2], 16) / 255.0 for i in (0, 2, 4))
    hue, lum, sat = colorsys.rgb_to_hls(r, g, b)
    if tint < 0:
        lum = lum * (1.0 + tint)
    else:
        lum = lum * (1.0 - tint) + tint
    r, g, b = colorsys.hls_to_rgb(hue, lum, sat)
    return f"{round(r * 255):02X}{round(g * 255):02X}{round(b * 255):02X}"


def resolve_color(
    color: Optional[Color], palette: tuple[str, ...]
) -> Optional[str]:
    """Resolve any openpyxl Color to a CSS '#RRGGBB' string, or None when
    the color is absent/automatic (i.e. carries no explicit value)."""
    if color is None:
        return None
    # openpyxl-stubs doesn't model Color's type/rgb/indexed/theme/tint
    # descriptors, so drop to Any for the attribute access.
    c: Any = color
    if c.type == "rgb":
        rgb = c.rgb
        if not isinstance(rgb, str) or len(rgb) < 6:
            return None
        return f"#{rgb[-6:].upper()}"
    if c.type == "indexed":
        index = c.indexed
        if not isinstance(index, int) or not 0 <= index < len(COLOR_INDEX):
            return None  # 64/65 are system-auto colors
        return f"#{COLOR_INDEX[index][-6:].upper()}"
    if c.type == "theme":
        theme = c.theme
        if not isinstance(theme, int) or not 0 <= theme < len(palette):
            return None
        base = palette[theme]
        tint = c.tint or 0.0
        return f"#{(_apply_tint(base, tint) if tint else base).upper()}"
    return None  # "auto"


def _trim_number(value: float) -> str:
    return str(int(value)) if float(value).is_integer() else str(value)


def cell_css(cell: Cell, palette: tuple[str, ...]) -> dict[str, str]:
    """Extract a cell's non-default visual properties as a CSS dict.

    Only deviations from a plain default cell are emitted, so unstyled
    cells cost zero tokens. Font family, column widths, and row heights
    are deliberately ignored (no semantic value for an LLM reader).
    """
    css: dict[str, str] = {}
    if not cell.has_style:
        return css

    font = cell.font
    if font.b:
        css["font-weight"] = "bold"
    if font.i:
        css["font-style"] = "italic"
    decorations = []
    if font.u and font.u != "none":
        decorations.append("underline")
    if font.strike:
        decorations.append("line-through")
    if decorations:
        css["text-decoration"] = " ".join(decorations)
    font_color = resolve_color(font.color, palette)
    if font_color and font_color != "#000000":  # default text color is noise
        css["color"] = font_color
    if font.sz and float(font.sz) != 11.0:
        css["font-size"] = f"{_trim_number(float(font.sz))}pt"

    # cell.fill is a StyleProxy, so duck-type instead of isinstance; only
    # solid pattern fills map cleanly to a CSS background.
    fill = cell.fill
    if getattr(fill, "patternType", None) == "solid":
        background = resolve_color(fill.fgColor, palette)
        if background:
            css["background"] = background

    border = cell.border
    side_css = {}
    for side_name in ("top", "right", "bottom", "left"):
        side = getattr(border, side_name)
        if side is not None and side.style:
            style = _BORDER_STYLE_CSS.get(side.style, "1px solid")
            side_color = resolve_color(side.color, palette) or "#000000"
            side_css[side_name] = f"{style} {side_color}"
    if len(side_css) == 4 and len(set(side_css.values())) == 1:
        css["border"] = next(iter(side_css.values()))
    else:
        for side_name, value in side_css.items():
            css[f"border-{side_name}"] = value

    alignment = cell.alignment
    if alignment.horizontal in ("left", "center", "right", "justify"):
        css["text-align"] = str(alignment.horizontal)
    if alignment.vertical in ("top", "center", "bottom"):
        vertical = alignment.vertical
        css["vertical-align"] = "middle" if vertical == "center" else str(vertical)
    if alignment.wrap_text:
        css["white-space"] = "pre-wrap"

    return css


class StyleRegistry:
    """Deduplicates CSS dicts into sequential class names (s1, s2, ...) so
    repeated cell styles are defined once in a <style> block."""

    def __init__(self) -> None:
        self._class_by_css: dict[str, str] = {}

    def class_for(self, css: dict[str, str]) -> Optional[str]:
        if not css:
            return None
        key = ";".join(f"{prop}:{value}" for prop, value in sorted(css.items()))
        existing = self._class_by_css.get(key)
        if existing is not None:
            return existing
        class_name = f"s{len(self._class_by_css) + 1}"
        self._class_by_css[key] = class_name
        return class_name

    def style_block(self) -> str:
        if not self._class_by_css:
            return ""
        rules = "".join(
            f".{class_name}{{{css}}}"
            for css, class_name in self._class_by_css.items()
        )
        return f"<style>{rules}</style>"
