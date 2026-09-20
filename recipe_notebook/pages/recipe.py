"""
pages/recipe.py - the plain recipe page (feature 3), plus the shared
render_recipe() that the home page also uses right after recording.
"""
from nicegui import ui

from .. import database, speech
from ..summary import summarize
from ..ui_components import confirm_delete, page_frame


def render_recipe(recipe: dict, on_back, on_deleted) -> None:
    """Draw a recipe simply: bold heading, bullet list, numbered list.

    Deliberately NO custom art here. `recipe` is a dict like
    {"name": ..., "ingredients": [...], "steps": [...]}.
    """
    ui.label(recipe["name"]).classes("text-h4 text-bold")

    # Plain-English overview. Newer recipes store their own summary; for older
    # ones we generate a simple one on the fly.
    summary = recipe.get("summary") or summarize(
        recipe["name"], recipe["ingredients"], recipe["steps"])
    with ui.element("div").classes("w-full").style(
        "border: 1px solid #ccc; border-radius: 8px; padding: 12px; background: #fff;"
    ):
        ui.label("Summary").classes("text-bold")
        ui.label(summary)

    # Only draw a section if it has something in it.
    if recipe["ingredients"]:
        ui.label("Ingredients").classes("text-h6 text-bold")
        # <ul> = bulleted list. `for item in list:` repeats the indented code
        # once per item; here each pass adds one bullet.
        with ui.element("ul").style("list-style-type: disc; padding-left: 1.5rem;"):
            for item in recipe["ingredients"]:
                with ui.element("li"):
                    ui.label(item)

    if recipe["steps"]:
        ui.label("Steps").classes("text-h6 text-bold")
        with ui.element("ol").style("list-style-type: decimal; padding-left: 1.5rem;"):
            for step in recipe["steps"]:
                with ui.element("li"):
                    ui.label(step)

    # The raw words Chrome heard, kept so you can double-check the sorting.
    if recipe.get("transcript"):
        with ui.expansion("What I heard").classes("w-full"):
            ui.label(recipe["transcript"]).classes("text-caption")

    with ui.row().classes("gap-2"):
        ui.button("Read it back", icon="volume_up",
                  on_click=lambda: speech.speak(speech.recipe_to_chunks(recipe)))
        ui.button("Stop", icon="stop", on_click=speech.stop_speaking).props("outline")
        ui.button("Back", icon="arrow_back", on_click=on_back).props("flat")
        ui.button("Delete", icon="delete", color="red",
                  on_click=lambda: confirm_delete(
                      f"“{recipe['name']}”",
                      lambda: (database.delete_recipe(recipe["id"]), on_deleted()),
                  )).props("flat")


@ui.page("/recipe/{recipe_id}")
def recipe_page(recipe_id: int):
    # NiceGUI reads {recipe_id} from the web address and hands it to us.
    speech.install_bridge()
    recipe = database.get_recipe(recipe_id)
    with page_frame(plain=True):
        if recipe is None:
            ui.label("Recipe not found.")
            ui.button("Home", on_click=lambda: ui.navigate.to("/"))
            return
        folder_url = f"/folder/{recipe['folder_id']}"
        render_recipe(
            recipe,
            on_back=lambda: ui.navigate.to(folder_url),
            on_deleted=lambda: ui.navigate.to(folder_url),
        )
