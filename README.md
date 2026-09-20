# Recipe Notebook 🍳

A voice-controlled recipe notebook. Tap **Start Cooking**, talk while you cook,
say "done" - the app files your recipe into a folder and reads it back.
Built with Python + [NiceGUI](https://nicegui.io). Speech uses the browser's
built-in speech tools (no paid API).

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

## Optional: AI clean-up (better ingredients, steps and summary)
Speech recognition mishears words. If you add an Anthropic API key, the app
sends your transcript to Claude, which fixes mishearings from context, writes
clean ingredients/steps and a plain-English summary. Unclear words get a "(?)"
so you can check them. **Without a key everything still works** using simple
rule-based sorting.

1. Create a key at https://console.anthropic.com (API billing is separate from a claude.ai subscription).
2. Copy `.env.example` to `.env` and paste the key after `ANTHROPIC_API_KEY=`.
3. Restart the app. `.env` is git-ignored, so the key is never uploaded.
   (On Render, add `ANTHROPIC_API_KEY` under Environment instead.)

Privacy: with a key set, your spoken recipe text is sent to Anthropic's API.

## Your data is yours
Recipes and folders live in a SQLite file (`data/recipes.db`) that is
**never committed to git** (see `.gitignore`). If someone clones this repo and
deploys their own copy, they get a **fresh, empty notebook** - each
deployment has its own separate database, and cloning the code gives no access
to anyone else's saved recipes.

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
