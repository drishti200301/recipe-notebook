"""
voice_logic.py - turns a stream of spoken sentences into a structured recipe.

PURE PYTHON: no NiceGUI, no browser, no database - easy to read and test.

TWO WAYS a recipe gets sorted:
  1. TRIGGER PHRASES (explicit): say "ingredients" or "let's start" and every
     sentence after it is filed in that section.
  2. AUTO-ORGANIZE (automatic): if you just talk naturally without trigger
     phrases, finalize() reads everything you said and works out the
     ingredients and steps by itself, using simple word-spotting rules.
     It is free and offline, but rule-based - so the app shows a review
     screen where you can fix anything before saving.
"""
import re
from dataclasses import dataclass, field

IDLE, NAME, INGREDIENTS, STEPS = "idle", "name", "ingredients", "steps"

# ---------- 1. Trigger phrases ---------------------------------------------
# Regex quick guide:  (?:a|b) = "a" or "b"   \s+ = spaces   \b = word edge
# Triggers only count at the START of a sentence (after little filler words),
# so "add the ingredients to the pot" doesn't flip the mode.
FILLER = r"^(?:(?:okay|ok|so|now|and|alright|all right|well|um|uh)[,\s]+)*"
WE_ARE = r"we(?:'re|\s+are)"


def _trigger(body: str) -> re.Pattern:
    return re.compile(FILLER + r"(?:" + body + r")\b", re.IGNORECASE)


TRIGGERS = [
    (STEPS, _trigger(
        r"(?:(?:today\s+)?" + WE_ARE + r"\s+)?cooking\s+now"
        r"|beginning|let's\s+start|let's\s+cook|lets\s+start|lets\s+cook"
        r"|let\s+us\s+start|cooking\s+start"
    )),
    (NAME, _trigger(r"(?:today\s+)?" + WE_ARE + r"\s+(?:cooking|making)")),
    (INGREDIENTS, _trigger(
        r"note\s+down\s+(?:the\s+)?ingredients|(?:the\s+)?ingredient\s+list"
        r"|(?:the\s+)?ingredients"
    )),
]

# "done"/"over" only count when they are the WHOLE sentence.
STOP_RX = re.compile(
    r"^(?:(?:okay|ok|so|alright|all right|i'm|we're|that's it|all)[,\s]+)*"
    r"(?:done|over)[.!\s]*$",
    re.IGNORECASE,
)


def _tidy(text: str) -> str:
    """Trim spaces/punctuation and capitalise the first letter."""
    text = text.strip(" \t\n,.:;-!")
    return text[:1].upper() + text[1:] if text else ""


# ---------- 2. Auto-organize -----------------------------------------------
COOKING_VERBS = [
    "take", "add", "put", "pour", "mix", "stir", "boil", "heat", "cook", "fry",
    "bake", "chop", "cut", "slice", "mash", "blend", "whisk", "knead", "simmer",
    "drain", "strain", "squeeze", "press", "leave", "cool", "wait", "serve",
    "garnish", "sprinkle", "fold", "roast", "grill", "steam", "rinse", "wash",
    "peel", "grate", "tear", "separate", "switch", "turn", "keep", "place",
    "cover", "season", "toss", "rest", "spread", "roll", "flip", "melt",
    "reduce", "remove", "combine", "transfer", "fill", "pat", "shape", "set", "let",
]
# Matches a verb plus common endings: boil / boils / boiled / boiling.
_VERB_ALT = "|".join(COOKING_VERBS)
VERB_RX = re.compile(rf"\b(?:{_VERB_ALT})(?:s|es|ed|d|ing)?\b", re.IGNORECASE)

# Where to cut a long run-on sentence into separate clauses. The (?=...)
# "lookahead" means: cut BEFORE these words but keep them with the next clause.
CLAUSE_SPLIT = re.compile(
    r"\s+(?=(?:and then|then|after that|next|once|now|so|or else)\b)"
    rf"|\s+and\s+(?=(?:{_VERB_ALT})(?:s|es|ed|d|ing)?\b)",
    re.IGNORECASE,
)
LEADING_FILLER = re.compile(
    r"^(?:and then|and|then|so basically|so|basically|next|now|after that|or else|okay|ok|um|uh)\b[,\s]*",
    re.IGNORECASE,
)

DROP_LEADING = {"the", "a", "an", "some", "our", "my", "more", "extra", "all"}


def split_name(text: str) -> tuple[str, str]:
    """Split "paneer so basically take milk..." into ("Paneer", "so basically take milk...").

    A recipe name is short, so we cut at the first "and now the story starts"
    marker word, and never keep more than 6 words.
    """
    # "a recipe called bread and butter" -> "bread and butter"
    text = re.sub(r"^(?:a\s+|the\s+)?(?:recipe|dish)\s+(?:called|named|for|of)\s+(?:a\s+|an\s+|the\s+)?",
                  "", text.strip(), flags=re.IGNORECASE)
    text = re.sub(r"^(?:called|named)\s+(?:a\s+|an\s+|the\s+)?", "", text, flags=re.IGNORECASE)
    words = text.split()
    cut = len(words)
    for i, w in enumerate(words):
        low = w.lower()
        if i >= 1 and (low in {"so", "that", "that's", "it's", "its", "which", "basically",
                               "first", "very", "okay", "for"}
                       or (low == "and" and i + 1 < len(words)
                           and words[i + 1].lower() in {"then", "basically", "so", "first"})):
            cut = i
            break
    cut = min(cut, 6)
    name_words = words[:cut]
    while name_words and name_words[0].lower() in DROP_LEADING:
        name_words = name_words[1:]
    return _tidy(" ".join(name_words)), " ".join(words[cut:])


# Words that usually START a new instruction ("take milk | boil it | let it cool").
STARTERS = {"take", "add", "put", "pour", "switch", "let", "mix", "stir", "heat",
            "leave", "strain", "squeeze", "boil", "cook", "serve", "cut", "chop",
            "bake", "fry", "roast", "grill", "blend", "toast", "simmer", "whisk",
            "spread", "sprinkle", "drain", "garnish", "knead"}
# ...unless the word before them shows they're mid-sentence ("you can add", "to boil").
NOT_BEFORE_STARTER = {"to", "can", "will", "you", "and", "it's", "is", "be", "then",
                      "also", "just", "not", "don't", "we", "i", "let", "or", "should",
                      "must", "first", "please"}


def _split_on_starters(clause: str) -> list[str]:
    words = clause.split()
    parts, current = [], []
    for i, w in enumerate(words):
        if (i >= 2 and current and w.lower() in STARTERS
                and words[i - 1].lower().strip(",.") not in NOT_BEFORE_STARTER):
            parts.append(" ".join(current))
            current = []
        current.append(w)
    if current:
        parts.append(" ".join(current))
    return parts


def split_clauses(text: str) -> list[str]:
    """Break a long run-on into bite-sized clauses."""
    clauses = []
    text = _fix_speech_quirks(text)
    for sentence in re.split(r"(?<=[.!?;])\s+", text):
        for piece in CLAUSE_SPLIT.split(sentence):
            clauses += _split_on_starters(piece)
    return [c.strip(" ,.") for c in clauses if c.strip(" ,.")]


# Speech-to-text often writes "to" when you said "two" ("to slices of bread").
_HOMOPHONE_RX = re.compile(
    r"\b(?:to|too)\s+(?=(?:slices?|cups?|pieces?|cloves?|spoons?|tablespoons?|"
    r"teaspoons?|glasses|drops?|pinch(?:es)?)\b)", re.IGNORECASE)
_REPEAT_RX = re.compile(r"\b(\w+)(\s+\1\b)+", re.IGNORECASE)          # "bread bread" -> "bread"
_FILLER_WORDS_RX = re.compile(r"\b(?:basically|actually|just|yeah|you know)\b\s*", re.IGNORECASE)
# Sentences that are chatter about the video/recipe rather than instructions.
INTRO_RX = re.compile(
    r"\b(recipe|today|called|welcome|hello|guys|introduc\w*|video|channel|subscribe)\b",
    re.IGNORECASE)
# "...and yeah that's your paneer done" - sign-off chatter at the end of a step.
TAIL_RX = re.compile(r"\s+(?:and\s+)?(?:yeah|you know|that's it|that is it|that's how|"
                     r"that is your|that's your)\b.*$", re.IGNORECASE)


def _fix_speech_quirks(text: str) -> str:
    text = _HOMOPHONE_RX.sub("two ", text)
    return _REPEAT_RX.sub(r"\1", text)


def extract_steps(clauses: list[str]) -> list[str]:
    """Keep clauses that are real cooking instructions; tidy them into steps."""
    steps = []
    for c in clauses:
        if INTRO_RX.search(c):
            continue                       # "recipe called bread and butter" - not a step
        if not VERB_RX.search(c) or len(c.split()) < 2:
            continue                       # chatter like "its paneer" - skip
        prev = None
        while prev != c:                   # peel off "and then", "so", ...
            prev, c = c, LEADING_FILLER.sub("", c)
        c = re.sub(r"^you can\s+", "", c, flags=re.IGNORECASE)
        c = TAIL_RX.sub("", c)
        c = _FILLER_WORDS_RX.sub("", c)
        c = re.sub(r"\s+(?:and|then|so)$", "", c, flags=re.IGNORECASE)
        step = _tidy(c)
        if step and len(step.split()) >= 2:
            steps.append(step)
    return steps


# ---- Ingredient spotting: a built-in food vocabulary -----------------------
# Only words on this list can become auto-detected ingredients, which is what
# stops garbled speech like "Judgement order" from sneaking in. Add your own
# favourites here any time - it's just a Python set of lowercase words.
FOOD_WORDS = set("""
milk butter bread garlic salt pepper sugar flour egg oil olive onion tomato potato
lemon lime cheese paneer rice dal lentil chilli chili ginger turmeric cumin coriander
cilantro parsley basil oregano thyme mint chicken mutton fish prawn shrimp beef pork
tofu yogurt yoghurt curd cream ghee honey vinegar water vanilla essence cinnamon
cardamom clove noodle pasta spaghetti sauce ketchup mustard mayonnaise mayo carrot
cucumber spinach cabbage cauliflower broccoli pea bean corn capsicum mushroom apple
banana mango orange strawberry chocolate cocoa yeast baking powder soda coconut
peanut almond cashew walnut raisin oats semolina sooji maida atta besan jaggery
tamarind curry leaves masala spice paprika nutmeg sesame seed bun roti dough batter
jam jelly juice tea coffee stock broth flakes bacon sausage ham avocado olive
zucchini eggplant brinjal okra beetroot radish pumpkin celery leek scallion shallot
cornflour cornstarch custard yogurt lassi buttermilk oregano chives dill fennel
saffron cloves pistachio dates fig pear peach grape watermelon pineapple kiwi
""".split())
UNITS = set("""cup cups tablespoon tablespoons tbsp teaspoon teaspoons tsp gram grams g kg ml
litre litres liter liters slice slices piece pieces pinch pinches clove cloves drop drops
bunch handful glass glasses spoon spoons dash can packet""".split())
NUMBER_WORDS = {"one": "1", "two": "2", "three": "3", "four": "4", "five": "5",
                "six": "6", "seven": "7", "eight": "8", "nine": "9", "ten": "10"}
QTY_EXTRA = {"of", "a", "an", "some", "little", "bit", "few", "half", "quarter",
             "more", "extra", "the"}
ADJECTIVES = set("""chopped fresh ripe sliced ground grated minced melted hot cold warm
boiled raw crushed diced whole thick thin small large big medium salted unsalted dry
dried roasted toasted soft hard cooked""".split())
_NUM_RX = re.compile(r"^\d+(?:[./]\d+)?$")


def _food_head(token: str) -> str | None:
    """Return the base food word if `token` is on the list (also plurals), else None."""
    candidates = [token]
    if token.endswith("es"):
        candidates.append(token[:-2])
    if token.endswith("s"):
        candidates.append(token[:-1])
    for cand in candidates:
        if cand in FOOD_WORDS:
            return cand
    return None


# Second words that really do glue onto a food word ("olive OIL", "vanilla ESSENCE").
# Anything else next to a food word is treated as a separate ingredient.
COMPOUND_TAILS = {"oil", "powder", "sauce", "essence", "leaves", "soda", "flakes",
                  "juice", "seed", "seeds", "stock", "broth", "paste", "cheese", "cream"}


def _is_qty(token: str) -> bool:
    return bool(_NUM_RX.match(token) or token in NUMBER_WORDS or token in UNITS
                or token in QTY_EXTRA or token in ADJECTIVES)


def extract_ingredients(clauses: list[str], exclude: set[str] | None = None) -> list[str]:
    """Find food words, and attach any quantity/adjective just before them.

    "take two slices of bread"  ->  "2 slices of bread"
    "add some chopped garlic"   ->  "chopped garlic"
    """
    found: dict[str, str] = {}
    for clause in clauses:
        text = TAIL_RX.sub("", _fix_speech_quirks(clause)).lower()
        tokens = [t.strip(".,;:!?\"'()") for t in text.split()]
        tokens = [t for t in tokens if t]
        i = 0
        while i < len(tokens):
            if not _food_head(tokens[i]):
                i += 1
                continue
            j = i
            while (j + 1 < len(tokens) and tokens[j + 1] in COMPOUND_TAILS
                   and _food_head(tokens[j + 1])):
                j += 1                       # "olive oil", "baking powder"
            k = i
            while k > 0 and i - k < 4 and _is_qty(tokens[k - 1]):
                k -= 1                       # walk back over "2 slices of"
            phrase = tokens[k:j + 1]
            while phrase and phrase[0] in {"a", "an", "the", "some", "more", "extra", "of"}:
                phrase = phrase[1:]
            phrase = [NUMBER_WORDS.get(t, t) for t in phrase]
            key = _food_head(tokens[j])
            text_out = " ".join(phrase)
            if exclude and key in exclude:
                i = j + 1
                continue
            if key not in found or len(text_out) > len(found[key]):
                found[key] = text_out        # keep the most descriptive mention
            i = j + 1
    return [_tidy(v) for v in found.values()]


@dataclass
class RecipeDraft:
    name: str = ""
    ingredients: list[str] = field(default_factory=list)
    steps: list[str] = field(default_factory=list)
    unsorted: list[str] = field(default_factory=list)   # speech not under any heading
    transcript: list[str] = field(default_factory=list) # everything heard, for review


class VoiceSession:
    """Feed it sentences with .feed(); call .finalize() when finished."""

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.mode = IDLE
        self.draft = RecipeDraft()

    def feed(self, sentence: str) -> bool:
        """Process one sentence. Returns True if the user said 'done'/'over'."""
        text = sentence.replace("\u2019", "'").strip()
        if not text:
            return False
        if STOP_RX.match(text):
            return True
        self.draft.transcript.append(text)

        for mode, pattern in TRIGGERS:
            match = pattern.match(text)
            if match:
                remainder = text[match.end():]
                if mode == INGREDIENTS:
                    remainder = re.sub(r"^\s*(?:are|is)\b", "", remainder)
                self.mode = mode
                self._store(remainder.strip(" ,.:;-!"))
                return False

        self._store(text.strip())
        return False

    def _store(self, text: str) -> None:
        d = self.draft
        if not text:
            return
        if self.mode == NAME:
            d.name, rest = split_name(text)
            if rest:
                d.unsorted.append(rest)
            self.mode = IDLE
        elif self.mode == INGREDIENTS:
            d.ingredients.append(_tidy(text))
        elif self.mode == STEPS:
            d.steps.append(_tidy(text))
        else:                                # IDLE: keep it for auto-organize
            d.unsorted.append(text)

    def finalize(self) -> None:
        """Auto-fill any section you didn't dictate with trigger phrases."""
        d = self.draft
        if not d.steps:
            d.steps = extract_steps(split_clauses(". ".join(d.unsorted)))
        if not d.ingredients:
            clauses = split_clauses(". ".join(d.unsorted)) + d.steps
            # A dish called just "Paneer" shouldn't list paneer as an ingredient.
            name_foods = {_food_head(t) for t in d.name.lower().split()} - {None}
            exclude = name_foods if len(name_foods) == 1 else set()
            d.ingredients = extract_ingredients(clauses, exclude)

    @property
    def is_empty(self) -> bool:
        d = self.draft
        return not (d.name or d.ingredients or d.steps or d.unsorted)


if __name__ == "__main__":
    # Self-test 1: explicit trigger phrases
    s = VoiceSession()
    for line in ["Today we are cooking garlic pasta", "note down the ingredients",
                 "200 grams spaghetti", "four cloves of garlic", "let's start",
                 "boil the water", "stir until the sauce is done", "okay, done"]:
        if s.feed(line):
            break
    s.finalize()
    assert s.draft.name == "Garlic pasta" and len(s.draft.ingredients) == 2
    assert len(s.draft.steps) == 2

    # Self-test 2: one long natural run-on, no trigger phrases (real example)
    s = VoiceSession()
    s.feed("okay today we are cooking thing very simple that is making milk base recipe "
           "so basically its paneer so take some milk in a pan boiled at keypad in lemon "
           "drops to it keypad in till the milk separate and tears apart once it's tired "
           "apart you can add a little bit of little bit of flavour to it like vanilla "
           "essence or something or else leave it like that once the milk is cool down "
           "tear Apartment put that in a cloth and once it's put in the cloth you can "
           "just use it the laptop")
    s.finalize()
    print("NAME       :", s.draft.name)
    print("INGREDIENTS:", s.draft.ingredients)
    for n, st in enumerate(s.draft.steps, 1):
        print(f"STEP {n}     :", st)
