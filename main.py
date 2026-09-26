"""
main.py - the entry point. Run with:  python main.py
Its only jobs: prepare the database, publish the /assets folder, register
the pages, and start the web server.
"""
import os

from nicegui import app, ui

from recipe_notebook import config, database
# Importing these modules registers their @ui.page routes. The "noqa" note
# just tells code checkers we import them on purpose, for that side effect.
from recipe_notebook.pages import folders, home, recipe  # noqa: F401

database.init_db()
app.add_static_files(config.ASSETS_URL, str(config.ASSETS_DIR))

ui.add_head_html(
    '<meta name="description" content="A voice-controlled recipe notebook - '
    'talk while you cook and it files your recipe for you. Each copy is '
    'private: nothing you say is ever sent anywhere or seen by anyone else.">',
    shared=True,
)

# `__mp_main__` is needed because NiceGUI can re-run this file internally.
if __name__ in {"__main__", "__mp_main__"}:
    ui.run(
        title="Recipe Notebook",
        host="0.0.0.0",                              # accept outside connections (needed on Render)
        port=int(os.environ.get("PORT", 8080)),      # Render tells us which port via $PORT
        reload=False,                                # auto-reload is for development only
        show=False,                                  # don't pop open a browser on a server
        favicon="🍳",
    )
