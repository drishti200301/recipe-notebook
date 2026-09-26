"""
config.py - every "setting" for the app lives here.

Why a config file? So that when you swap in your real artwork or fonts,
you change ONE line in ONE place, instead of hunting through the code.
"""
import os
from pathlib import Path

# ---------- Paths ----------------------------------------------------------
# __file__ is "this file's location". .parent goes up one folder.
# config.py is in recipe_notebook/, so .parent.parent is the project root.
BASE_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = BASE_DIR / "assets"
IMAGES_DIR = ASSETS_DIR / "images"
FONTS_DIR = ASSETS_DIR / "fonts"

# The web address prefix the browser uses to fetch files from /assets.
ASSETS_URL = "/assets"

# Where the SQLite database file lives. os.environ.get(NAME, default) reads
# an "environment variable" (a setting supplied by the computer/host) and
# falls back to the default if it isn't set. This lets a host like Render
# point the database somewhere else without changing any code.
DB_PATH = Path(os.environ.get("RECIPE_DB_PATH", BASE_DIR / "data" / "recipes.db"))

# ---------- Image files (all inside assets/images/) ------------------------
# To swap art later: replace the file, keep the name. Or change the name here.
IMG_MAIN_BACKGROUND = "main-background.png"
IMG_HEADER_BANNER = "header-banner.png"
IMG_START_COOKING = "start-cooking-button.png"
IMG_STOP = "stop-button.png"
IMG_MIC_IDLE = "mic-idol-icon.png"        # (sic - matches the filename you uploaded)
IMG_MIC_LISTENING = "mic-listening-icon.png"
IMG_LISTENING_COMPANION = "listening-companion.png"
IMG_NEW_FOLDER = "new-folder-button.png"
IMG_NEW_RECIPE = "new-recipe-button.png"
IMG_DELETE = "delete-icon.png"
IMG_READ_ALOUD = "read-aloud-button.png"  # not used: recipe page is intentionally plain
IMG_RECIPE_CARD_BG = "recipe-card-bg.png"  # not supplied yet -> placeholder colour is used

# Folder colours: ANY file matching this pattern counts as a folder colour.
# Drop in option_4_folder-icon.png, option_5_...  and it's picked up
# automatically, no code changes. (You originally said folder-1-closed.png;
# your uploaded files are named option_N_folder-icon.png, so I matched those.)
FOLDER_ICON_GLOB = "option_*_folder-icon.png"

# ---------- Font -----------------------------------------------------------
# Put your font file in assets/fonts/ and set the filename here, e.g.
# "MyHandwriting.ttf". While this is None, a fallback font is used.
FONT_FILE = None
FONT_FAMILY = "RecipeFont"
FALLBACK_FONTS = "'Trebuchet MS', 'Comic Sans MS', sans-serif"

# ---------- Placeholder colours (used when an image file is missing) -------
COLOR_PLACEHOLDER = "#f4c2c2"
COLOR_RECIPE_CARD = "#fff3d6"
COLOR_PLAIN_PAGE = "#fafafa"     # the plain recipe page background
COLOR_PANEL = "rgba(255, 250, 235, 0.68)"   # soft panel behind text on art
COLOR_TEXT = "#4a2f27"


def asset_url(filename: str) -> str | None:
    """Return the browser URL for an image, or None if the file doesn't exist.

    Returning None (instead of crashing) is what makes the placeholder
    boxes work: the UI code asks "is there a real image?" and draws a
    coloured box if the answer is None.
    """
    if filename and (IMAGES_DIR / filename).exists():
        return f"{ASSETS_URL}/images/{filename}"
    return None


def list_folder_icons() -> list[str]:
    """Return the filenames of every folder-colour image currently on disk."""
    return sorted(p.name for p in IMAGES_DIR.glob(FOLDER_ICON_GLOB))
