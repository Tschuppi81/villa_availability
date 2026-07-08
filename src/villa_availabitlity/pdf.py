"""Render the console tables into a PDF, so a printout survives the terminal.

Nothing in here knows about villas: it takes the lines a `print_*` function
produced and lays them out as monospaced text.
"""
from pathlib import Path

import matplotlib.pyplot as plt

PDF_FONT_SIZE = 8  # points
PDF_LINE_SPACING = 1.4  # multiples of the font size
PDF_MARGIN = 0.3  # inches

# DejaVu Sans Mono -- matplotlib's default monospace -- advances every glyph by
# 0.602 em, so a block of text's size follows from its shape.
_CHAR_WIDTH = 0.602  # em


def write_text_pdf(lines: list[str], filename, title: str = '') -> None:
    """Render console output onto a single monospaced PDF page.

    The page is sized to the text rather than the text to a page: the tables
    run to a few hundred columns, and squeezing those onto an A4 would leave
    the digits unreadable. A PDF has no fixed paper size until it is printed,
    so the reader can zoom, and a printer can scale it down once.
    """
    if not lines:
        return None

    if title:
        lines = [title, ''] + list(lines)
    columns = max(len(line) for line in lines)

    width = 2 * PDF_MARGIN + columns * _CHAR_WIDTH * PDF_FONT_SIZE / 72
    height = 2 * PDF_MARGIN + len(lines) * PDF_LINE_SPACING * PDF_FONT_SIZE / 72

    figure = plt.figure(figsize=(width, height))
    figure.text(PDF_MARGIN / width, 1 - PDF_MARGIN / height, '\n'.join(lines),
                family='monospace', fontsize=PDF_FONT_SIZE,
                linespacing=PDF_LINE_SPACING, va='top', ha='left')

    filename = Path(filename)
    filename.parent.mkdir(exist_ok=True)
    figure.savefig(filename, format='pdf')
    plt.close(figure)
    print(f'Wrote {filename}')
