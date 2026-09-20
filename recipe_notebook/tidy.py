"""
tidy.py - turns the rough, speech-recognition-garbled recipe into a clean one.

TWO LEVELS:
  * WITH an Anthropic API key (optional, costs a tiny amount per recipe):
    a language model reads your whole transcript, works out what you most
    likely meant, and writes clean ingredients, steps and a short summary.
  * WITHOUT a key: nothing breaks. You get the rule-based sorting from
    voice_logic.py plus a simple template summary, and you fix any mistakes
    on the "Check your recipe" screen.

The key is read from an environment variable (a setting outside the code),
so it never appears in your files or on GitHub.
"""
import json
import os
import re

from . import config

SYSTEM_PROMPT = """You clean up recipes that someone dictated out loud while cooking. \
The transcript came from automatic speech recognition, so it contains mishearings \
(for example "stared apart" may mean "started to separate", "Muslim cloth" probably means \
"muslin cloth"), missing punctuation and filler talk.

You get the raw transcript plus a rough automatic attempt at sorting it.

Rules:
- Use ONLY what the transcript supports. Never invent ingredients, quantities, temperatures or steps.
- Fix mishearings when the context makes the intended word clear.
- If a word is genuinely unclear, give your best guess and add " (?)" right after it so the cook can check it.
- ingredients: one item per entry, short and clean. Include quantities only if they were spoken. \
Include ingredients that are only implied by the steps (e.g. "take milk" means milk is an ingredient). \
Do not list kitchen equipment.
- steps: clear instructions in order, one action per step, each starting with a verb, no filler words.
- summary: one or two friendly, plain sentences saying what is being made and how.
- name: a short recipe title (2 to 5 words).

Reply with ONLY a JSON object, no markdown fences, in exactly this shape:
{"name": "...", "summary": "...", "ingredients": ["..."], "steps": ["..."]}"""


def is_enabled() -> bool:
    """True if an API key has been provided."""
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def _parse(text: str) -> dict | None:
    """Turn the model's reply into a checked Python dict, or None if it's malformed."""
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())   # remove ``` fences if present
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None
    try:
        result = {
            "name": str(data["name"]).strip(),
            "summary": str(data["summary"]).strip(),
            "ingredients": [str(x).strip() for x in data["ingredients"] if str(x).strip()],
            "steps": [str(x).strip() for x in data["steps"] if str(x).strip()],
        }
    except (KeyError, TypeError):
        return None
    return result


async def tidy_recipe(name: str, ingredients: list[str], steps: list[str],
                      transcript: list[str]) -> dict | None:
    """Ask the model for a cleaned recipe. Returns None on ANY problem (caller falls back)."""
    try:
        import anthropic          # imported here so the app still runs if it isn't installed

        client = anthropic.AsyncAnthropic(timeout=30)   # reads ANTHROPIC_API_KEY itself
        prompt = (
            f"Raw transcript:\n{' '.join(transcript)}\n\n"
            "Rough automatic attempt (may be wrong):\n"
            f"Name: {name}\nIngredients: {ingredients}\nSteps: {steps}"
        )
        response = await client.messages.create(
            model=config.AI_MODEL,
            max_tokens=1500,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        return _parse(response.content[0].text)
    except Exception as exc:          # network down, bad key, no credit, ...
        print(f"[tidy] AI clean-up failed: {exc!r}")
        return None
