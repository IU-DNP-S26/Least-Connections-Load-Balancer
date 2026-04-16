import os
import mistune
from weasyprint import HTML, CSS
from bs4 import BeautifulSoup
from PIL import Image
import time
from pygments import highlight
from pygments.lexers import get_lexer_by_name, TextLexer
from pygments.formatters import HtmlFormatter


# Markdown to PDF renderer with a support
# for code highlighting
class HighlightRenderer(mistune.HTMLRenderer):
    def block_code(self, code, info=None):
        # info: language name after ```
        # e.g. ```python
        if info:
            try:
                lexer = get_lexer_by_name(info.strip(), stripall=True)
            except Exception:
                lexer = TextLexer()
        else:
            # Use the default text lexer
            lexer = TextLexer()

        formatter = HtmlFormatter(nowrap=False)
        return highlight(code, lexer, formatter)


def adaptive_image_sizes(html_body, base_dir):
    soup = BeautifulSoup(html_body, "html.parser")

    # Shrink big images
    for img in soup.find_all("img"):
        src = img.get("src")
        if not src:
            continue

        img_path = os.path.join(base_dir, src) # type: ignore
        try:
            with Image.open(img_path) as i:
                width, _ = i.size

            # Determine the appropriate scaling
            if width < 600:
                percent = 50
            elif width < 1000:
                percent = 70
            elif width < 1600:
                percent = 95
            else:
                percent = 100

            img["style"] = f"width: {percent}%; height: auto;"
        except Exception:
            img["style"] = "max-width: 100%; height: auto;"

    return str(soup)


def convert_to_pdf(path_to_md: str) -> str:
    output_path = f'output_{time.time()}.pdf'

    # Read the markdown file
    with open(path_to_md, "r", encoding="utf-8") as f:
        md_text = f.read()

    # Create a parser with a custom renderer
    renderer = HighlightRenderer()
    markdown = mistune.create_markdown(
        renderer=renderer,
        plugins=["table", "strikethrough", "footnotes"]
    )

    # Convert source Markdown to HTML
    html_body = markdown(md_text)

    # Scale images to have equal sizes
    base_dir = os.path.dirname(os.path.abspath(path_to_md))
    html_body = adaptive_image_sizes(html_body, base_dir)

    # Get the formatter style
    pygments_css = HtmlFormatter().get_style_defs(".highlight")

    # Compose the result HTML
    full_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
        {pygments_css}
        </style>
    </head>
    <body>
        {html_body}
    </body>
    </html>
    """

    # Path to the stylesheet
    base_css_path = os.path.join("converters", "style.css")

    # Convert HTML to PDF and write the result PDF
    HTML(string=full_html, base_url=f"file://{base_dir}/").write_pdf(
        output_path,
        stylesheets=[CSS(filename=base_css_path)]
    )

    return output_path
