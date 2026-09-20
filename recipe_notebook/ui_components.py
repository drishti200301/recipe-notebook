"""
ui_components.py - small reusable building blocks shared by every page:
the page frame (background, font, layout), image buttons with placeholder
fallback, and the delete-confirmation dialog.
"""
from contextlib import contextmanager

from nicegui import ui

from . import config


def _global_css() -> str:
    font_face = ""
    if config.FONT_FILE and (config.FONTS_DIR / config.FONT_FILE).exists():
        font_face = (
            f"@font-face {{ font-family: '{config.FONT_FAMILY}'; "
            f"src: url('{config.ASSETS_URL}/fonts/{config.FONT_FILE}'); }}"
        )
    return f"""
    <style>
      {font_face}
      body, .q-btn, .q-field {{ font-family: '{config.FONT_FAMILY}', {config.FALLBACK_FONTS}; }}
      body {{ color: {config.COLOR_TEXT}; }}
      .panel {{ background: {config.COLOR_PANEL}; border-radius: 18px; padding: 16px; }}
      .pulse {{ animation: pulse 1.4s ease-in-out infinite; }}
      @keyframes pulse {{ 0%,100% {{ transform: scale(1); }} 50% {{ transform: scale(1.08); }} }}
    </style>
    """


def set_background(plain: bool) -> None:
    """Whimsical illustrated background, or plain colour for the recipe page."""
    if plain:
        css = f"background: {config.COLOR_PLAIN_PAGE};"
    else:
        url = config.asset_url(config.IMG_MAIN_BACKGROUND)
        css = (
            f"background: url('{url}') center / cover fixed no-repeat, {config.COLOR_PLACEHOLDER};"
            if url else f"background: {config.COLOR_PLACEHOLDER};"
        )
    ui.query("body").style(css)


@contextmanager
def page_frame(plain: bool = False):
    """Wrap a page's content: sets background/font and centres a column.

    Mobile-first: the column is full-width on a phone, but max 640px wide,
    so on a laptop/iPad it stays a comfortable centred column.
    """
    ui.add_head_html(_global_css())
    set_background(plain)
    with ui.column().classes("w-full items-center gap-3 p-3").style(
        "max-width: 640px; margin: 0 auto;"
    ):
        yield


def placeholder(label: str, width: int, height: int | None = None) -> None:
    """A clearly labelled coloured box standing in for a missing image."""
    with ui.element("div").style(
        f"width:{width}px; height:{height or int(width * 0.6)}px;"
        f"background:{config.COLOR_PLACEHOLDER}; border:3px dashed #8a5a5a;"
        "display:flex; align-items:center; justify-content:center;"
        "text-align:center; font-size:12px; padding:4px; border-radius:12px;"
    ):
        ui.label(f"PLACEHOLDER: {label}")


def show_image(filename: str, width: int, classes: str = "") -> None:
    """Show an image from assets/images, or a placeholder if it's missing."""
    url = config.asset_url(filename)
    if url:
        ui.image(url).style(f"width:{width}px;").classes(classes)
    else:
        placeholder(filename, width)


def image_button(filename: str, label: str, on_click, width: int = 170) -> None:
    """A tappable picture with a caption underneath."""
    with ui.column().classes("items-center gap-0 cursor-pointer").on("click", on_click):
        show_image(filename, width)
        ui.label(label).classes("text-lg text-bold")


def header_banner(title: str) -> None:
    """The leafy banner across the top of home/folder screens, with the title on it."""
    url = config.asset_url(config.IMG_HEADER_BANNER)
    bg = f"url('{url}') center / cover" if url else config.COLOR_PLACEHOLDER
    with ui.element("div").classes("w-full").style(
        f"background: {bg}; height: 120px; border-radius: 18px;"
        "display:flex; align-items:center; justify-content:center;"
    ):
        ui.label(title).classes("text-h4 text-bold").style(
            "background: rgba(255,250,235,0.85); padding: 4px 16px; border-radius: 12px;"
        )


def confirm_delete(what: str, on_confirm) -> None:
    """Pop up 'are you sure?' before deleting anything."""
    with ui.dialog() as dialog, ui.card():
        ui.label(f"Delete {what}? This can't be undone.")
        with ui.row():
            ui.button("Cancel", on_click=dialog.close).props("flat")
            ui.button("Delete", color="red", on_click=lambda: (dialog.close(), on_confirm()))
    dialog.open()
