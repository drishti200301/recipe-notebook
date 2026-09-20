"""pages/folders.py - the folders screen and the recipe list inside a folder."""
from nicegui import ui

from .. import config, database
from ..ui_components import (confirm_delete, header_banner, image_button,
                             page_frame, show_image, placeholder)


@ui.page("/folders")
def folders_page():
    with page_frame():
        header_banner("My Folders")

        def open_new_folder_dialog():
            with ui.dialog() as dialog, ui.card():
                name = ui.input("Folder name").props("autofocus")

                def create():
                    if name.value.strip():
                        database.create_folder(name.value)
                        dialog.close()
                        ui.navigate.reload()   # redraw the page with the new folder

                ui.button("Create", on_click=create)
            dialog.open()

        with ui.row().classes("w-full justify-around"):
            image_button(config.IMG_NEW_FOLDER, "New Folder", open_new_folder_dialog, 150)
            image_button(config.IMG_NEW_RECIPE, "New Recipe",
                         lambda: ui.navigate.to("/"), 150)

        folders = database.list_folders()
        if not folders:
            with ui.column().classes("panel w-full items-center"):
                ui.label("No folders yet - make one!")
        # A CSS grid: 2 columns on phones, 4 on wider screens.
        with ui.element("div").classes("grid grid-cols-2 md:grid-cols-4 gap-4 w-full"):
            for f in folders:
                with ui.column().classes("items-center gap-0 cursor-pointer").on(
                    "click", lambda f=f: ui.navigate.to(f"/folder/{f['id']}")
                ):
                    show_image(f["icon_file"], 130)
                    ui.label(f["name"]).classes("text-bold text-center")
                    ui.label(f"{f['recipe_count']} recipes").classes("text-caption")
        ui.button("Home", icon="home", on_click=lambda: ui.navigate.to("/")).props("flat")


@ui.page("/folder/{folder_id}")
def folder_page(folder_id: int):
    folder = database.get_folder(folder_id)
    with page_frame():
        if folder is None:
            ui.label("Folder not found.")
            ui.button("Back", on_click=lambda: ui.navigate.to("/folders"))
            return
        header_banner(folder["name"])
        ui.button("All folders", icon="arrow_back",
                  on_click=lambda: ui.navigate.to("/folders")).props("flat")

        recipes = database.list_recipes(folder_id)
        if not recipes:
            with ui.column().classes("panel w-full items-center"):
                ui.label("This folder is empty.")

        card_url = config.asset_url(config.IMG_RECIPE_CARD_BG)
        card_bg = (f"url('{card_url}') center / cover" if card_url
                   else config.COLOR_RECIPE_CARD)
        for r in recipes:
            with ui.row().classes("w-full items-center justify-between cursor-pointer no-wrap").style(
                f"background: {card_bg}; border-radius: 14px; padding: 14px 16px;"
                "min-height: 80px; box-shadow: 0 2px 6px rgba(0,0,0,.2);"
            ).on("click", lambda r=r: ui.navigate.to(f"/recipe/{r['id']}")):
                with ui.column().classes("gap-0"):
                    ui.label(r["name"]).classes("text-h6 text-bold")
                    ui.label(f"{len(r['ingredients'])} ingredients · {len(r['steps'])} steps"
                             ).classes("text-caption")
                # 'click.stop' = handle this click here and don't also open the recipe.
                with ui.element("div").on(
                    "click.stop",
                    lambda r=r: confirm_delete(
                        f"“{r['name']}”",
                        lambda: (database.delete_recipe(r["id"]), ui.navigate.reload()),
                    ),
                ):
                    show_image(config.IMG_DELETE, 36)
