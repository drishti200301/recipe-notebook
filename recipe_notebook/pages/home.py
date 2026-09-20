"""
pages/home.py - the home screen and the whole "cooking" flow:
  idle -> listening -> choose folder -> recipe shown + read aloud

Everything happens on ONE page (swapping what's shown) instead of jumping
between pages. Reason: browsers only allow text-to-speech after you've
tapped something on the CURRENT page. Staying on the same page keeps that
permission alive, so the recipe can be read aloud automatically.
"""
from nicegui import ui

from .. import config, database, speech, tidy
from ..summary import summarize
from ..ui_components import (header_banner, image_button, page_frame,
                             set_background, show_image)
from ..voice_logic import VoiceSession
from .recipe import render_recipe

MODE_LABELS = {
    "idle": "Listening... say “today we are cooking ...”",
    "name": "Listening for the recipe name...",
    "ingredients": "Writing down ingredients",
    "steps": "Writing down steps",
}


@ui.page("/")
def home_page():
    speech.install_bridge()

    # Per-visitor state. A plain dict keeps things simple to read.
    state = {"view": "idle", "heard": "", "status": "", "counts": "", "recipe": None,
             "summary": "", "ai_used": False}
    session = VoiceSession()

    # ---------- what happens when the browser sends us a sentence ---------
    async def on_voice_text(e):
        if state["view"] != "listening":
            return                              # ignore stragglers after we've stopped
        # e.args is the dict the JavaScript sent: {"text": "..."}
        text = e.args["text"]
        state["heard"] = text
        done = session.feed(text)
        d = session.draft
        state["status"] = MODE_LABELS[session.mode]
        state["counts"] = (f"Recipe: {d.name or '—'}  |  "
                           f"{len(d.ingredients)} ingredients  |  {len(d.steps)} steps")
        if done:
            await finish_recording()

    def on_voice_error(e):
        err = e.args["error"]
        messages = {
            "not-allowed": "Microphone blocked. Allow it in Chrome's site settings and try again.",
            "service-not-allowed": "Microphone blocked. Allow it in Chrome's site settings and try again.",
            "unsupported": "This browser can't do speech recognition. Try Chrome on Android or desktop.",
            "network": "Speech recognition needs an internet connection.",
        }
        ui.notify(messages.get(err, f"Voice error: {err}"), type="negative", multi_line=True)
        if err in ("not-allowed", "service-not-allowed", "unsupported", "network"):
            state["view"] = "idle"
            body.refresh()

    ui.on("voice_text", on_voice_text)
    ui.on("voice_error", on_voice_error)

    # ---------- actions ----------------------------------------------------
    async def start_cooking():
        if not await speech.is_supported():
            ui.notify("This browser doesn't support speech recognition. "
                      "Use Chrome on Android, or Chrome on a laptop.", type="negative")
            return
        session.reset()                        # start a fresh, empty session
        state.update(view="listening", heard="", summary="", ai_used=False,
                     counts="Recipe: —  |  0 ingredients  |  0 steps",
                     status=MODE_LABELS["idle"])
        speech.start_listening()               # the first tap = the permission moment
        body.refresh()

    async def stop_manually():
        await finish_recording()

    async def finish_recording():
        if state["view"] != "listening":
            return                              # already finishing - don't do it twice
        speech.stop_listening()
        session.finalize()                      # rule-based sorting of anything not dictated
        d = session.draft
        if session.is_empty:
            ui.notify("Nothing was captured.")
            state["view"] = "idle"
            body.refresh()
            return

        # Optional: let an AI model clean up mishearings (needs ANTHROPIC_API_KEY).
        if tidy.is_enabled():
            state["view"] = "tidying"
            body.refresh()
            result = await tidy.tidy_recipe(d.name, d.ingredients, d.steps, d.transcript)
            if result:
                d.name = result["name"] or d.name
                d.ingredients = result["ingredients"] or d.ingredients
                d.steps = result["steps"] or d.steps
                state["summary"] = result["summary"]
                state["ai_used"] = True
            else:
                ui.notify("AI clean-up wasn't available - using the basic sorting.",
                          type="warning")

        if not state["summary"]:                # offline / fallback summary
            state["summary"] = summarize(d.name or "This recipe", d.ingredients, d.steps)
        state["view"] = "filing"
        body.refresh()

    def save_and_read(folder_id: int | None, new_folder_name: str, recipe_name: str,
                      ingredients_text: str, steps_text: str, summary_text: str):
        if new_folder_name.strip():
            folder_id = database.create_folder(new_folder_name)
        if not folder_id:
            ui.notify("Pick a folder or type a new folder name.", type="warning")
            return
        # One item per line in the text boxes -> Python lists.
        ingredients = [ln.strip() for ln in ingredients_text.splitlines() if ln.strip()]
        steps = [ln.strip() for ln in steps_text.splitlines() if ln.strip()]
        name = recipe_name.strip() or session.draft.name or "Untitled recipe"
        recipe_id = database.save_recipe(folder_id, name, ingredients, steps,
                                         " ".join(session.draft.transcript),
                                         summary_text.strip())
        state["recipe"] = database.get_recipe(recipe_id)
        state["view"] = "recipe"
        body.refresh()
        speech.speak(speech.recipe_to_chunks(state["recipe"]))

    def go_idle():
        speech.stop_speaking()
        state["view"] = "idle"
        body.refresh()

    # ---------- the screens ----------------------------------------------
    # @ui.refreshable turns a function into something we can redraw by
    # calling body.refresh() - that's how we switch between screens.
    @ui.refreshable
    def body():
        set_background(plain=(state["view"] == "recipe"))
        view = state["view"]

        if view == "idle":
            header_banner("Recipe Notebook")
            with ui.column().classes("panel w-full items-center"):
                image_button(config.IMG_START_COOKING, "Start Cooking", start_cooking, 240)
                ui.label("Tap once, then just talk. Say “done” when finished.").classes("text-center")
            ui.button("My Folders", icon="folder",
                      on_click=lambda: ui.navigate.to("/folders")).props("rounded size=lg")

        elif view == "listening":
            with ui.column().classes("panel w-full items-center"):
                show_image(config.IMG_LISTENING_COMPANION, 150)
                show_image(config.IMG_MIC_LISTENING, 100, classes="pulse")
                # bind_text_from keeps the label in sync with the state dict.
                ui.label().bind_text_from(state, "status").classes("text-h6 text-center")
                ui.label().bind_text_from(state, "counts").classes("text-center")
                ui.label().bind_text_from(state, "heard", lambda t: f"Heard: “{t}”" if t else ""
                                          ).classes("text-caption text-center")
                image_button(config.IMG_STOP, "Stop", stop_manually, 150)

        elif view == "tidying":
            with ui.column().classes("panel w-full items-center"):
                ui.spinner("dots", size="xl")
                ui.label("Tidying up your recipe...").classes("text-h6")

        elif view == "filing":
            d = session.draft
            with ui.column().classes("panel w-full items-center"):
                ui.label("Check your recipe").classes("text-h5 text-bold")
                note = ("I cleaned this up with AI. Items marked (?) were unclear - please check them."
                        if state["ai_used"] else
                        "I sorted what you said. Fix anything - one item per line.")
                ui.label(note).classes("text-caption text-center")
                recipe_name = ui.input("Recipe name", value=d.name).classes("w-full")
                summary_box = ui.textarea("Summary", value=state["summary"]).classes("w-full")
                ing_box = ui.textarea("Ingredients (one per line)",
                                      value="\n".join(d.ingredients)).classes("w-full")
                step_box = ui.textarea("Steps (one per line)",
                                       value="\n".join(d.steps)).classes("w-full")
                with ui.expansion("What I heard").classes("w-full"):
                    ui.label(" ".join(d.transcript)).classes("text-caption")
                folders = database.list_folders()
                choice = ui.select({f["id"]: f["name"] for f in folders},
                                   label="Choose a folder",
                                   value=folders[0]["id"] if folders else None).classes("w-full")
                new_name = ui.input("…or create a new folder").classes("w-full")
                ui.button("Save & read it to me", icon="save",
                          on_click=lambda: save_and_read(choice.value, new_name.value,
                                                         recipe_name.value,
                                                         ing_box.value, step_box.value,
                                                         summary_box.value))

        elif view == "recipe":
            render_recipe(state["recipe"], on_back=go_idle, on_deleted=go_idle)

    with page_frame():
        body()
