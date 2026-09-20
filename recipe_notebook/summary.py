"""
summary.py - writes a short, plain-English overview of a recipe.

Pure Python again: give it the name/ingredients/steps, get back a string.
"""


def _join(items: list[str]) -> str:
    """['a','b','c'] -> 'a, b and c'"""
    items = [i.lower() for i in items]
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + " and " + items[-1]


def summarize(name: str, ingredients: list[str], steps: list[str]) -> str:
    n_i, n_s = len(ingredients), len(steps)
    parts = [f"{name} has {n_i} ingredient{'s' if n_i != 1 else ''} "
             f"and {n_s} step{'s' if n_s != 1 else ''}."]
    if ingredients:
        shown = ingredients[:6]
        more = " and a few more" if n_i > 6 else ""
        parts.append(f"You'll need {_join(shown)}{more}.")
    if steps:
        first = steps[0].rstrip(".")
        parts.append(f"It starts by: {first[:1].lower() + first[1:]}.")
        if n_s > 1:
            last = steps[-1].rstrip(".")
            parts.append(f"It finishes with: {last[:1].lower() + last[1:]}.")
    return " ".join(parts)
