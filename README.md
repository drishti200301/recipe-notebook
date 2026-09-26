# Recipe Notebook 🍳

A voice-controlled recipe notebook. Tap **Start Cooking**, talk while you cook,
say "done" - the app files your recipe into a folder and reads it back.
Built with Python + [NiceGUI](https://nicegui.io). Speech uses the browser's
built-in speech tools (no paid API).

## Deploy your own copy (free, one click)
[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/drishti200301/recipe-notebook)

1. Click the button above and sign in to Render with GitHub.
2. Confirm the settings and click **Apply** / **Create**.
3. After a few minutes you get your own link, e.g. `https://recipe-notebook-xxxx.onrender.com`.

Your copy is separate from everyone else's. Note: on Render's free plan a copy
sleeps when idle (about 50 seconds to wake) and its saved recipes are erased
when it restarts.

## Run it locally
```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python main.py
```
Open http://localhost:8080 in **Chrome**.

## Voice phrases
| Say | Effect |
|---|---|
| "today we are cooking / making ..." or "we're making ..." | sets the recipe name |
| "note down the ingredients" / "ingredient list" / "ingredients" | each sentence becomes an ingredient |
| "cooking now" / "beginning" / "let's start" / "let's cook" / "cooking start" | each sentence becomes a numbered step |
| "done" / "over" (as its own sentence) | stops and saves |

## Your data is yours
Nothing you say is sent anywhere. Recipe sorting happens with plain Python,
locally, in your own copy of the app - no outside AI service is used, no
audio or transcript ever leaves your deployment.

Recipes and folders live in a SQLite file (`data/recipes.db`) that is
**never committed to git** (see `.gitignore`). If someone clones this repo and
deploys their own copy, they get a **fresh, empty notebook** - each
deployment has its own separate database, and cloning the code gives no access
to anyone else's saved recipes. Nobody, including the person who wrote this
app, can see what you record.

## Customising the art
Images live in `assets/images/`, fonts in `assets/fonts/`. Every filename is a
named variable in `recipe_notebook/config.py`. Replace a file (same name) or
edit the variable. Any file named `option_N_folder-icon.png` is automatically
used as a random folder colour. Missing images show a labelled placeholder box.

## Project layout
- `main.py` - starts the app
- `recipe_notebook/config.py` - all settings, filenames, colours
- `recipe_notebook/database.py` - SQLite storage
- `recipe_notebook/voice_logic.py` - trigger-phrase parser (pure Python)
- `recipe_notebook/speech.py` - the small browser-microphone/speaker bridge
- `recipe_notebook/ui_components.py` - shared UI pieces
- `recipe_notebook/pages/` - home, folders, recipe screens
