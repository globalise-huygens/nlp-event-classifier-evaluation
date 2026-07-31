"""
Token-level (sequence labeling) classification via an open-source LLM served
through an OpenAI-compatible API (Together AI, Fireworks, OpenRouter, Groq,
a local vLLM/Ollama server, etc. -- just change base_url and model).

Input:  a list of pre-tokenised words, e.g. ["Barack", "Obama", "was", "born", "in", "Hawaii"]
Output: a list of labels, one per token, e.g. ["B-PER", "I-PER", "O", "O", "O", "B-LOC"]

The hard part with LLMs + token labeling is ALIGNMENT: the model can merge,
split, drop, or reorder tokens if you just ask it to "label this sentence".
This script forces alignment by making the model return labels indexed to
literal token positions, and validates length + index integrity before
accepting a response.

Install:
    pip install openai

Set your API key as an environment variable

THIS CODE WAS WRITTEN BY CLAUDE
DATA WAS ADDED BY AUTHORS
"""

import os
import json
import time
from collections import OrderedDict
from typing import List, Dict, Optional

from openai import OpenAI


# ---------------------------------------------------------------------------
# 1. Configuration -- swap these for whichever provider/model you're using
# ---------------------------------------------------------------------------

with open("OPENAI_API_KEY.env") as f:
    OPENAI_API_KEY = f.readline().strip()

CLIENT = OpenAI(
    api_key=OPENAI_API_KEY,
    base_url="https://api.openai.com/v1",   # OpenAI's own endpoint (no need to override for their models)
)

MODEL_NAME = "gpt-5.1"

DEFAULT_LABEL = "O"  # fallback label used if the model skips a token

# ---------------------------------------------------------------------------
# 1b. Load label set + definitions from an external file (JSON or Markdown)
#
# JSON format -- flat {label: definition} map:
#   { "LABEL_NAME": "definition of when to use this label", ... }
#
# Markdown format -- lets you group labels into categories, which also gives
# a more model-friendly glossary structure than one long flat list:
#   ## Category Name
#   ### LABEL_NAME
#   Definition text (can span multiple lines/paragraphs).
#
#   ### ANOTHER_LABEL
#   ...
#
# Loading from an external file (rather than hardcoding in the prompt
# string) makes it easy to version, review, and update your label set
# without touching the classification code.
# ---------------------------------------------------------------------------

LABEL_DEFINITIONS_PATH = "genllm/label_definitions.md"  # or "label_definitions.json"


def _parse_markdown_labels(path: str) -> "OrderedDict[str, Dict]":
    """
    Parses a markdown file of the form:
        ## Category
        ### LABEL
        Definition text...

    Returns an ordered dict: {label: {"definition": str, "category": str}}
    Category is optional -- labels with no preceding '##' get category=None.
    """
    labels: "OrderedDict[str, Dict]" = OrderedDict()
    current_category = None
    current_label = None
    buffer: List[str] = []

    def flush():
        if current_label is not None:
            labels[current_label] = {
                "definition": " ".join(buffer).strip(),
                "category": current_category,
            }

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if stripped.startswith("### "):
                flush()
                current_label = stripped[4:].strip()
                buffer = []
            elif stripped.startswith("## "):
                flush()
                current_label = None
                buffer = []
                current_category = stripped[3:].strip()
            elif current_label is not None:
                if stripped:
                    buffer.append(stripped)
        flush()

    return labels


def load_label_definitions(path: str) -> Dict[str, str]:
    """
    Loads label definitions from either a .json (flat map) or .md
    (category-grouped) file. Returns a flat {label: definition} dict for use
    in validation, and stashes category info on LABEL_CATEGORIES for use in
    glossary formatting.
    """
    global LABEL_CATEGORIES

    if path.endswith(".json"):
        with open(path, "r", encoding="utf-8") as f:
            flat = json.load(f)
        LABEL_CATEGORIES = {label: None for label in flat}
        return flat

    elif path.endswith(".md"):
        parsed = _parse_markdown_labels(path)
        LABEL_CATEGORIES = {label: info["category"] for label, info in parsed.items()}
        return {label: info["definition"] for label, info in parsed.items()}

    else:
        raise ValueError(f"Unsupported label definitions file type: {path}")


LABEL_CATEGORIES: Dict[str, Optional[str]] = {}  # populated by load_label_definitions
LABEL_DEFINITIONS: Dict[str, str] = load_label_definitions(LABEL_DEFINITIONS_PATH)
LABELS = list(LABEL_DEFINITIONS.keys())  # the valid label set, derived from the file


def _format_label_glossary(definitions: Dict[str, str]) -> str:
    """
    Formats the glossary for the prompt. If category info is available
    (i.e. loaded from markdown), groups labels under category headers --
    this reads more reliably for large label sets than one flat list.
    """
    if not any(LABEL_CATEGORIES.values()):
        return "\n".join(f"- {label}: {definition}" for label, definition in definitions.items())

    grouped: "OrderedDict[Optional[str], List[str]]" = OrderedDict()
    for label, definition in definitions.items():
        category = LABEL_CATEGORIES.get(label)
        grouped.setdefault(category, []).append(f"- {label}: {definition}")

    sections = []
    for category, lines in grouped.items():
        header = category if category else "Other"
        sections.append(f"{header}:\n" + "\n".join(lines))
    return "\n\n".join(sections)


# ---------------------------------------------------------------------------
# 2. Prompt construction
#
# Key trick: number every token and ask for {"labels": {"0": "...", "1": "...", ...}}
# instead of a flat list. A dict keyed by index survives the model dropping or
# doubling a token much more gracefully than a positional list would, and it's
# trivial to validate: every key from 0..N-1 must be present and every value
# must be a legal label.
#
# IMPORTANT for caching: keep this SYSTEM_PROMPT string byte-for-byte
# identical across every request (build it once, at import time, as done
# here). At 100+ labels this glossary can easily run several thousand
# tokens, so caching meaningfully affects both cost and latency:
#
#   - Anthropic's native API: mark the glossary block explicitly with
#     `cache_control: {"type": "ephemeral"}` on that content block.
#   - OpenAI-compatible endpoints (Together, Fireworks, OpenRouter, etc.):
#     many auto-cache repeated prefixes with no code change, but support
#     varies by provider -- check their docs for "prompt caching" and
#     confirm your SYSTEM_PROMPT is being sent as a stable prefix (i.e.
#     nothing dynamic like a timestamp gets prepended to it).
#   - Local vLLM: enable via `--enable-prefix-caching`.
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = f"""You are a precise token-level sequence labeler (e.g. NER-style tagging).

You will receive a numbered list of tokens from a single sentence, already
split -- do NOT merge, split, reorder, add, or remove tokens.

Assign exactly one label to each token index, using ONLY the labels defined
below. Each label's definition tells you exactly when to use it:

{_format_label_glossary(LABEL_DEFINITIONS)}

Respond with ONLY a JSON object, no other text, no markdown fences, in this
exact shape:
{{"labels": ["<label for token 0>", "<label for token 1>", ..., "<label for token N-1>"]}}

The array must contain exactly one label per token, in the same order as
the numbered tokens above -- position i in the array is the label for token i.
"""


def estimate_prompt_tokens(text: str) -> int:
    """
    Rough token count for cost/caching planning. Uses tiktoken if available
    and reachable; falls back to a ~4 chars/token heuristic for English text
    (a reasonable approximation for planning purposes, not exact billing).
    """
    try:
        import tiktoken
        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
    except Exception:
        return len(text) // 4




FEW_SHOT_EXAMPLES = [
    (["de", "Hollanders", "na", "Carta", "soura", "de", "ningrat", "gebragt", ",", "en", "Is", "zonder", "des", "sousou", "hounang", "te", "spreecken", "stilletjes", "\u2014", "Wederom", "met", "Jaer", "afgecomen", ",", "dies", "sullen", "w", "'", "uw", "roer", "Wegnemen", ";", "dese", "klagten", ",", "en", "sijn", "gevoelen", "wegens", "den", "souson", "hounang", "hebben", "wij", "verzogt", ",", "dat", "zoodanig", "den", "uwer", "Ed", ":", "mogte", "ges", ".", "Werden", "gelijk", "hij't", "ons", "gezegt", "heeft", ",", "dog", "zoo", "van", "tersijden", "verstaan", "hebben", "isser", "gants", "niet", "van", "grept", ";", "hij", "heeft", "ons", "oog", "verzogt", "bij", "uwer", "Ed.", "te", "willen", "aanhouden", "dat", "sijn", "suster", "die", "aantommagon", "souranata", "getrouwt", "Is", "verschoont", "en", "herwaerts", "aan", "mogte", "vervoert", "werden", ",", "off", "dit", "nu", "te", "grabbel", "gegooijt", "wert", "om", "ons", "te", "proberen", ",", "connen", "niet", "bedencken", ",", "dog", "w", "'", "hebben", "ten", "antwoorde", "gegeven", ",", "tot", "nog", "toe", "van", "geen", "oorlog", "te", "weten", ",", "en", "schoon", "genomen", "het", "gebeurden", "dat", "de", "vrouwlijden", ",", "alomme", "van", "ons", "verschoont", "wierden", ",", "Indien", "Hij", "van", "vijanden", "wist", ",", "dat", "ons", "off", "uwer", "Ed", ":", "zoude", "believen", "te", "waerschouwen", "Wijders", "hebben", "geen", "quaataerdigheijt", "aan", "hen", "off", "ijmant", "Connen", "bespeuren", "oog", "leven", "de", "broeders", "vreedsaam", "onder", "malkanderen", "daerwij", "het", "bij", "sullen", "zoeken", "te", "Houden"], ["O", "O", "O", "O", "O", "O", "O", "B-Transportation", "O", "O", "O", "O", "O", "O", "O", "O", "B-Communication", "O", "O", "O", "O", "O", "B-Leaving", "O", "O", "O", "O", "O", "B-TakingUnderControl", "I-TakingUnderControl", "I-TakingUnderControl", "O", "O", "O", "O", "O", "O", "O", "O", "O", "O", "O", "O", "O", "B-Request", "O", "O", "O", "O", "O", "O", "O", "O", "O", "O", "O", "O", "O", "O", "B-Communication", "O", "O", "O", "O", "O", "O", "B-Communication", "O", "O", "O", "O", "O", "B-Communication", "O", "O", "O", "O", "O", "B-Request", "O", "O", "O", "O", "O", "B-Request", "O", "O", "B-BeingInARelationship", "O", "O", "O", "B-BeingInARelationship", "O", "B-AlteringARelationship", "O", "O", "O", "O", "B-Transportation", "O", "O", "O", "O", "O", "O", "O", "O", "O", "O", "O", "O", "O", "O", "O", "O", "O", "O", "O", "O", "O", "O", "B-Communication", "I-Communication", "I-Communication", "O", "O", "O", "O", "O", "O", "B-BeingInConflict", "O", "O", "O", "O", "O", "O", "O", "O", "O", "O", "O", "O", "O", "O", "O", "B-AlteringARelationship", "O", "O", "O", "O", "O", "B-BeingInConflict", "O", "O", "O", "O", "O", "O", "O", "O", "O", "O", "O", "B-Collaboration", "O", "O", "O", "B-BeingInConflict", "O", "O", "O", "O", "O", "O", "O", "O", "O", "O", "B-BeingAtPeace", "O", "O", "O", "O", "O", "O", "O", "O", "O"]),
    (["onderzeil", ",", "benevens", "het", "schip", "Landskroon", "en", "'t", "Copjagt", "de", "olijftak", ",", "beide", "gehoorende", "het", "de", "Commissie", ",", "als", "mede", "de", "bantamsche", "gezanten", ",", "salueerende", "Concordia", "het", "Casteel", "Batavia", "met", "17", "schoten", ",", "dog", "wierden", "niet", "bedankt", ",", "bij", "het", "passeeren", "van", "de", "terrhede", "leggende", "Engelische", "scheepen", "Indianqueen", "en", "\u201e", "wierd", "de", "Commissaris", "van", "het", "eerste", "met", "elf", "schooten", "gesalueert", ",", "dat", "met", "zeven", "schoten", "wierd", "bedankt"], ["B-Leaving", "O", "O", "O", "O", "O", "O", "O", "O", "O", "O", "O", "O", "B-HavingInPossession", "O", "O", "O", "O", "O", "O", "O", "O", "O", "O", "O", "O", "O", "O", "O", "O", "O", "O", "O", "O", "O", "O", "O", "O", "O", "O", "B-Encounter", "O", "O", "O", "B-BeingAtAPlace", "O", "O", "O", "O", "O", "O", "O", "O", "O", "O", "O", "O", "O", "O", "O", "O", "O", "O", "O", "O", "O", "O"]),
    (["De", "grootmoeder", "van", "den", "overleden", "Candiesen", "vorst", "met", "het", "2:e", "vaartuijg", "alhier", "aangekomen", ",", "bevind", "zig", "tot", "als", "nog", "op", "marticattij", ",", "en", "die", "zoo", "genaamde", "grootmoeder", "op", "Bakenburg", ":", "en", "zal", "uwel", "Edele", "groot", "agtb", ":", "betuij", "\u201e", "gen", ",", "dat", "op't", "gecommuniceerde", "bij", "brief", "van", "den", "10", ":", "'", "deser", "namentlijk", "die", "op", "Bakenburg", "zijn", ",", "ten", "eijgen", "Coste", "onderhoud", "heb", "gegeven", ",", "en", "haar", "woon", "met", "linnen", "doen", "bekleden", ",", "gelijk", "haar", "nog", "zal", "onderhouden", "tot", "haar", "vertrek", "dat", "zij"], ["O", "O", "O", "O", "B-BeingDead", "O", "O", "O", "O", "O", "O", "O", "B-Arriving", "O", "B-BeingAtAPlace", "B-BeingAtAPlace", "O", "O", "O", "O", "O", "O", "O", "O", "O", "O", "O", "O", "O", "O", "O", "O", "O", "O", "O", "O", "O", "B-SocialInteraction", "I-SocialInteraction", "I-SocialInteraction", "O", "O", "O", "O", "O", "O", "O", "O", "O", "O", "O", "O", "O", "O", "O", "O", "B-BeingAtAPlace", "O", "O", "O", "O", "O", "O", "B-Giving", "O", "O", "O", "O", "O", "O", "O", "O", "O", "O", "O", "O", "O", "O", "O", "O", "B-Leaving", "O", "O"])
]


def _format_tokens(tokens: List[str]) -> str:
    numbered = [f"{i}: {tok}" for i, tok in enumerate(tokens)]
    return "\n".join(numbered)


def _labels_to_json(labels: List[str]) -> str:
    return json.dumps({"labels": labels})


def build_messages(tokens: List[str]) -> List[Dict]:
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for example_tokens, example_labels in FEW_SHOT_EXAMPLES:
        messages.append({"role": "user", "content": _format_tokens(example_tokens)})
        messages.append({"role": "assistant", "content": _labels_to_json(example_labels)})
    messages.append({"role": "user", "content": _format_tokens(tokens)})
    return messages


def build_response_schema(n: int) -> Dict:
    """
    Builds a strict JSON Schema requiring exactly `n` labels, in token order,
    each drawn from the LABELS enum.

    IMPORTANT DESIGN NOTE: with a large label set (159 labels here), a schema
    that repeats the full enum once per token index balloons badly -- e.g.
    ~21KB for a 7-token sentence, ~91KB for 30 tokens, since the same list of
    159 label strings gets duplicated at every index. Instead, this defines
    the enum ONCE inside a fixed-length array ("minItems"/"maxItems" = n),
    which keeps schema size roughly constant regardless of sequence length
    while still structurally guaranteeing: exactly n labels, in order, each
    a valid label. The trade-off is that array position (not an explicit
    index key) carries the alignment -- see build_messages/SYSTEM_PROMPT,
    which instruct the model to preserve token order 1:1.
    """
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "token_labels",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "labels": {
                        "type": "array",
                        "items": {"type": "string", "enum": LABELS},
                        "minItems": n,
                        "maxItems": n,
                    }
                },
                "required": ["labels"],
                "additionalProperties": False,
            },
        },
    }


# ---------------------------------------------------------------------------
# 3. Classification call with retries + strict alignment validation
# ---------------------------------------------------------------------------

def classify_tokens(tokens: List[str], max_retries: int = 3) -> Optional[List[str]]:
    """
    Label each token in `tokens`. Returns a list of labels the same length as
    `tokens`, or None if the model failed to produce a valid aligned response
    after all retries.
    """
    n = len(tokens)

    for attempt in range(max_retries):
        try:
            response = CLIENT.chat.completions.create(
                model=MODEL_NAME,
                messages=build_messages(tokens),
                temperature=0,
                max_completion_tokens=max(50, n * 10),  # scale budget with sequence length
                response_format=build_response_schema(n),
            )
            raw = response.choices[0].message.content.strip()
            parsed = json.loads(raw)
            label_list = parsed["labels"]

            # Defense in depth: the schema already enforces length == n and
            # enum membership in strict mode, but re-validate here too, both
            # as a safeguard against providers that don't fully enforce
            # strict mode server-side and to fail loudly with a clear error
            # if something upstream ever changes.
            if len(label_list) != n:
                raise ValueError(f"Expected {n} labels, got {len(label_list)}")
            for i, label in enumerate(label_list):
                if label not in LABELS:
                    raise ValueError(f"Invalid label '{label}' at position {i}")

            return label_list

        except (json.JSONDecodeError, ValueError, KeyError, TypeError) as e:
            print(f"[attempt {attempt + 1}] parse/validation error: {e}. Retrying...")
            time.sleep(1)
        except Exception as e:
            print(f"[attempt {attempt + 1}] API error: {e}. Retrying...")
            time.sleep(2 ** attempt)

    print(f"Failed to align/label after {max_retries} attempts for tokens: {tokens[:10]}...")
    # Graceful fallback: return default label for every token rather than None,
    # if you'd rather always get a same-length list back. Comment out if not desired.
    # return [DEFAULT_LABEL] * n
    return None


# ---------------------------------------------------------------------------
# 4. Batch helper -- operates over a list of token lists
# ---------------------------------------------------------------------------

def classify_batch(token_lists: List[List[str]]) -> List[Optional[List[str]]]:
    return [classify_tokens(tokens) for tokens in token_lists]


# ---------------------------------------------------------------------------
# 5. Usage
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print(f"[info] {len(LABELS)} labels loaded from {LABEL_DEFINITIONS_PATH}")
    print(f"[info] Estimated system prompt size: ~{estimate_prompt_tokens(SYSTEM_PROMPT)} tokens "
          f"(sent on every call unless your provider caches the prefix)\n")

    samples = [['Batavia'], ['Aan', 'zijn', 'Hoogedelheid', 'der', 'Hoogedelen', 'Groot', 'achtbaaren', 'Heer', 'M', ':', 'r', 'Willem', 'Arnold', 'Alling', ',', 'Gouverneur', 'Generaal', ',', 'benevens', 'de', 'Weledele', 'Gestrenge', 'Heeren', 'Raaden', 'van', 'Nederlandsch', 'Indie'], ['Hoogedele', 'Groot', 'Achtbaere', 'Heer', 'Wel', 'Edele', 'gestrenge', 'Heeren', '.'], ['Bij', 'onzen', 'thans', 'overgaanden', 'Eisch', 'hebben', 'wij', '1200', 'lasten', 'rijst', 'gesteld', ',', 'en', 'wij', 'gebruken', 'de', 'vrijheid', 'de', 'volstrekte', 'noodzaakelijkheid', 'daar', 'van', 'hier', 'mede', 'nader', 'eerbiedig', 'aan', 'te', 'toonen', ':', 'De', 'gesteldheid', 'van', 'de', 'Rust', 'Kormandel', ',', 'die', 'steets', 'onze', 'graan', 'schuur', 'is', ',', 'geweest', 'is', 'zoo', 'onzeeker', ',', 'dat', 'daarop', 'geen', 'de', 'minste', 'staat', 'te', 'maaken', 'is', '.', 'Daar', 'bij', 'is', 'het', 'land', 'zodanig', 'verwoest', ',', 'dat', 'men', 'aldaar', 'zelfs', ',', 'en', 'niet', 'zonder', 'reeden', ',', 'Voor', 'een', 'honger', 'nood', 'beducht', 'is', ',', 'dus', 'kunnen', 'wij', 'van', 'daar', 'geen', 'de', 'minste', 'onder', 'stand', 'verwach', '„'], ['De', 'heer', 'Kommandeur', 'van', 'Angelbeek', 'heeft', 'ons', 'Wel', 'seshonderd', 'lasten', 'rijst', 'toegezegd', ',', 'doch', 'dezelve', 'moeten', 'in', 'de', 'aanstaande', 'maand', 'April', 'Worden', 'afgehaald', ',', 'Wijl', 'ner', 'laater', 'geen', 'schip', 'op', 'de', 'koettjiensche', 'rheede', 'durf', 'vertrouwen', ',', 'en', 'daar', 'toe', 'zien', 'wij', 'geen', 'mogelijkheid', ',', 'Vermits', 'wij', 'geen', 'scheepen', 'tot', 'den', 'afhaal', 'aan', 'harden'], ['hebben', 'en', 'Wanneer', 'Wij', 'dezelve', 'ook', 'hadden', ',', 'zonden', 'ze', 'dog', 'zonder', 'een', 'goed', 'konvooij', 'niet', 'gewaagd', 'Worden', ',', 'Wijl', 'de', 'Bombaijsche', 'fregatten', 'nog', 'bestendig', 'op', 'de', 'hoogte', 'van', 'koetsjien', 'kruissen', '.', 'Wat', 'er', 'te', 'gen', 'de', 'opere', 'Vaart', '/', ':', 'die', 'niet', 'Voor', 'half', 'Oktober', 'gerekend', 'mag', 'Worden:/', 'op', 'Mallabaar', 'Voorvallen', 'kan', ',', 'mogen', 'wij', 'niet', 'gissen', ',', 'en', 'zoo', 'Wij', 'deeze', 'zelkonder-', 'lasten', 'Mallabaers', 'rijst', 'kreegen', ',', 'bij', 'de', 'geeischte', 'Javasche', ',', 'zoude', 'onze', 'Voorraad', 'naar', 'maatig', 'zijn', ',', 'Wijl', 'de', 'Fransche', 'Vloot', 'zeken', 'on', 'rijst', 'zal', 'vraagen', ',', 'en', 'de', 'gemeente', 'geen', 'aanvoer', 'uit', 'Boengaale', 'hoopen', 'kan', '.', 'Om', 'deeze', 'reedenen', 'verzoeken', 'Wij', 'Uwe', 'Hoog', 'Edelheeden', 'nogmaals', 'op', 'het', 'ootmoedigste', ',', 'om', 'onzer', 'voormelden', 'Eisch', 'kompleet', 'te', 'Willen', 'voldoen', ',', 'Wijl', 'wij', 'andersints', 'in', 'een', 'indoorkonelijke', 'Verleegerheid', 'zouden', 'VerVallen', '.', 'Een', 'schip', 'Voor', 'Gale', 'en', 'een', 'Voor', 'Kolombo', ',', 'zouden', 'in', 'Juri', 'dienen', 'te', 'Vertrekken', ',', 'om', 'tijding', 'in', 'Augustus', 'hier', 'te', 'weezen', 'zij', 'komen', 'bewesten', 'de', 'Maldivos', 'en', 'mag', 'de', 'reize', 'dus', 'op', 'niet', 'minder', 'dan', 'twee', 'maanden', 'bereekend', 'Worden', '.', 'Wanneer', 'UWe', 'Hoogedelheeden', ',', 'gelijk', 'doorgaans', ',', 'groote', 'scheepen', 'tot', 'deezer', 'togt', 'uit', 'kiezen', ',', 'zal', 'nog', 'een', 'derde', 'niet', 'alleen', 'de', 'gevraagde', 'rijst', ',', 'maar', 'ook', 'de', 'overige', 'goederen', 'kunnen', 'mede', 'neemen', ',', 'Vermits', 'wij', 'zo', 'lang', 'de', 'oorlog', 'duurt', ',', 'op', 'geen', 'onderlaag', 'voor', 'de', 'retourscheepen', 'denken', 'mogen', '.', 'Wij', 'verzoeken', 'dan', ',', 'dat', 'ook', 'dit', 'derde', 'schip', 'de', 'twee', 'anderen', 'spoedig', 'volge', ',', 'op', 'dat', 'het', 'in', 'september', 'hier', 'zij', ',', 'Voor', 'dat', 'de', 'goede', 'Moesson', 'Vijandelijke', 'kruissers', 'na', 'deezer', 'kant', 'doe', 'Verschijnen', ',', 'en', 'dat', 'alle', 'drie', 'scheepen', 'last', 'krijgen', 'om', 'de', 'Mallabaarsche', 'kust', ',', 'na', 'dat', 'zij', 'het', 'karaal', 'tusschen', 'de', 'Maldivos', 'en', 'LakkeriVes', 'doorgevaaren', 'zijn', ',', 'op', 'eene', 'voorzigtige', 'Wijze', 'te', 'Verkennen', ',', 'en', 'na', '„'], ['de', 'Ceilonsche', 'Wal', 'over', 'te', 'steeken', ',', 'en', 'dat', 'de', 'Engelschen', 'bij', 'Mannapaar', 'zouden', 'kunnen', 'kruissers', 'houden', '.', 'De', 'over', 'heden', 'Van', 'beide', 'schepen', ',', 'maar', 'voor', 'al', 'Van', 't', 'geene', 'Voor', 'Gale', 'gedestineerd', 'is', ',', 'Verzoeken', 'wij', 'boven', 'des', 'te', 'onderrigten', ',', 'dat', 'de', 'stroomen', 'in', 'de', 'Zuid', 'moessen', 'voor', 'Gale', 'zo', 'hevig', 'om', 'de', 'Zuid', 'Oost', 'looper', ',', 'dat', 'een', 'schip', 't', 'Welk', 'maar', 'even', 'beneeden', 'de', 'baai', 'is', ',', 'met', 'geen', 'mogelijkheid', 'de', 'haven', 'bezeilen', 'kan', ',', 'en', 'dat', 'zij', 'dus', 'alle', 'Voorzorgen', 'moeten', 'gebruiken', ',', 'om', 'boven', 'Wind', 'en', 'stroom', 'van', 'Gale', 'te', 'komen', ',', 'en', 'daar', 'of', 'ten', 'anker', 'komen', 'of', 'het', 'onder', 'zeil', 'houden', ',', 'na', 'dat', 'de', 'geleegenheid', 'toelaat', ',', 'tot', 'een', 'loots', 'buiten', 'komt', 'om', 'hen', 'binnen', 'de', 'haven', 'te', 'brengen', ';', 'en', 'dat', ',', 'indier', 'zij', 'tegen', 'alle', 'hunne', 'gebruikte', 'Voorzorgen', 'beneden', 'de', 'baai', 'van', 'Gale', 'mogten', 'Vervallen', ',', 'zij', 'het', 'onder', 'de', 'Wal', 'het', 'zij', 'Voor', 'Gale', 'of', 'Mature', 'moeten', 'tragten', 'te', 'houden', ',', 'en', 'sein', 'doen', ',', 'Wanneer', 'hen', 'ten', 'eersten', 'een', 'loots', 'zal', 'worden', 'toegezonden', ',', 'om', 'hen', 'in', 'de', 'baai', 'Van', 'Nilewelle', 'te', 'brengen', ',', 'alwaar', 'een', 'schip', 'Voor', 'de', 'Zuide', 'Winden', 'Veilig', 'leggen', 'kan', ',', 'en', 'de', 'eerste', 'Verandering', 'van', 'Wind', 'en', 'Stroon', 'Kan', 'Waarneemen', 'om', 'na', 'Gale', 'te', 'Zeilen', '.', 'Bij', 'onzen', 'eerbiedigen', 'van', 'den', '12:e', 'februari', 'hebben', 'wij', 'de', 'eer', 'gehad', 'Uwe', 'Hoog', 'Edelheeden', 'te', 'bedeelen', ',', 'de', 'verslagenheid', 'van', 'het', 'Randiasche', 'Hof', 'over', 'den', 'voorspoed', 'van', 'de', 'Engelsche', 'Wapenen', ',', 'en', 'dat', 'het', 'zelve', 'ons', 'kennis', 'had', 'gegeeven', 'van', 'een', 'gezantschap', 'van', 'den', 'Engelschen', ',', 't', 'Welk', 'zoude', 'moeten', 'aangenomen', 'Worden', 'om', 'hen', 'niet', 'te', 'Verstooren', 'maar', 'de', 'aankomst', 'van', 'een', 'aanzienelijke', 'Fransche', 'Vloot', 'schijnt', 't', 'Hof', 'Van', 'zijne', 'ontsteltenis', 'weder', 'hersteld', 'te', 'hebben', ',', 'Want', 'straks', 'na', 'der', 'ontvangst', 'van', 'deeze', 'gewigtige', 'tijding', 'gaf', 'het', 'zelve', 'ons', 'kennisdat', 'zij', 'der', 'Engelschen', 'gezant', 'na', 'dat', 'hij', 'twintig', 'dagen', 'Was', 'opgehouden', ','], ['nu', 'hadden', 'Verwittigd', 'dat', 'hij', 'moeste', 'Vertrekken', ',', 'maar', 'dat', 'hij', 'geantwoord', 'had', ',', 'dat', ',', 'Wijl', 'hij', 'door', 'den', 'heer', 'Gouverneur', 'Van', 'Madras', 'en', 'den', 'Nabab', 'gezonden', 'Was', ',', 'hij', 'niet', 'konde', 'vertrekken', 'zonder', 'aan', 't', 'Hof', 'te', 'komen', ',', 'al', 'zoude', 'hij', 'ook', 'gedood', 'Worden', 'en', 'dat', 'wijl', 't', 'Verblijf', 'van', 'zulke', 'wenscher', 'in', 't', 'land', 'schadelijk', 'was', ',', 't', 'Hofbeslooten', 'had', 'den', 'Engelschen', 'gezant', 'te', 'ontvangen', 'en', 'te', 'hooren', ',', 'met', 'bijvoeging', ',', 'dat', 'ons', 't', 'Verhandelde', 'zoude', 'bedeele', 'Worden', '.', 'Dit', 'heeft', 't', 'Hof', 'wij', 'omstandig', 'gedaan', 'bij', 'twee', 'brieven', ',', 'die', 'met', 'de', 'daar', 'op', 'gepaste', 'antwoorden', 'onder', 'de', 'bijlaagen', 'overgaan', '.', 'Hier', 'uit', 'blijkt', ',', 'dat', 't', 'Hlof', 'bij', 'zijne', 'gevoelens', 'tot', 'aankleeving', 'aan', 'onze', 'belangen', 'onveranderlijk', 'blijft', 'volharden', ',', 't', 'Welk', 'ons', 'tot', 'groote', 'gerustheid', 'strekt', 'in', 'de', 'presente', 'Kritike', 'tijdsgesteldheid', ',', 'maar', 'het', 'is', 'echter', 'niet', 'te', 'twijffelen', 'of', 't', 'Hof', 'zal', 'door', 'de', 'opruijingen', 'van', 'de', 'Engelschen', 'zich', 'gesterkt', 'Vinder', ',', 'om', 'zijne', 'vorige', 'eischen', 'tot', 'terugge', 'erlanging', 'van', 'de', 'bevorens', 'bezetene', 'stranden', 'en', 'tot', 'herstelling', 'van', 'het', 'oude', 'afgeschafte', 'Ceremonieel', ',', 'bij', 'deeze', 'geleegenheid', 'met', 'meerder', 'nadruk', 'door', 'te', 'zetten', 'en', 'zulx', 'te', 'meer', ',', 'wijl', 'de', 'Engelsche', 'gezant', ',', 'zo', 'als', 'de', 'hofsgroten', 'met', 'veel', 'Waarschijnelijkheid', 'voorgeeven', ',', 'zig', 'aan', 'het', 'afgeschafte', 'Ceremonieel', 'onder', 'Worpen', ',', 'en', 'ook', 'alle', 'landen', 'aan', 'den', 'Koning', 'aangeboden', 'heeft', ':', 'en', 'hoewel', 'Wij', 'bij', 'deeze', 'geleegendheid', 'in', 'het', 'stuk', 'van', 'de', 'eerbewijzing', 'aan', 'den', 'koning', 'niet', 'minder', 'zullen', 'hunnen', 'doen', 'dan', 'de', 'Engelschen', ',', 'is', 'echter', 'de', 'koopman', 'Billingdie', 'Volgens', 'het', 'bedeelde', 'bij', '§', '5', '.', 'Van', 'onzer', 'heeden', 'afgaanden', 'gemeenen', 'brief', 'is', 'na', 'Randia', 'Vertrokken', ',', 'om', 'den', 'nieuwen', 'Koning', 'met', 'desselfs', 'komst', 'op', 'den', 'troon', 'te', 'vergeluken', ',', 'geinstrueerd', 'alle', 'middelen', 'van', 'overreding', 'aan', 'te', 'Wenden', ',', 'om', 'de', 'zaaken', 'op', 'den', 'ouden', 'Voet', 'te', 'houden', ',', 'en', 'Voor', 'al', 'tot', 'geen', 'meer', 'Ceremonien', 'Verplicht', 'te', 'worden', ','], ['dan', 'door', 'de', 'Engelschen', 'ingewilligd', 'is', '.', 'Het', 'stuk', 'van', 'de', 'Stranden', 'is', 'echter', 'een', 'zaak', 'van', 'veel', 'meer', 'gewigt', ',', 'en', 'onze', 'gezant', 'is', 'gelast', ',', 'de', 'eisschen', 'daar', 'toe', 'met', 'alle', 'omzichtigheid', 'te', 'ontlegger', ',', 'en', 'indien', 'geen', 'en', 'kele', 'overredingen', 'van', 'vrugt', 'zijn', ',', 'te', 'beproeven', 'om', 'de', 'Hofsgrooten', 'van', 'het', 'meeste', 'aanzien', 'door', 'geschenken', 'en', 'beloften', 'van', 'meerder', 'daar', 'van', '#', 'te', 'doen', 'afzien', 'een', 'afschrift', 'van', 'de', 'instruksie', 'voor', 'gemelden', 'gezant', 'p', 'nevens', 'een', 'kopij', 'Van', 'den', 'brief', 'aan', 'den', 'Koning', 'Word', 'Uwe', 'Hoogedel', 'heeden', 'onder', 'de', 'bijlaager', 'aangebooden', 'De', 'te', 'Gale', 'binnen', 'geloopene', 'Fransche', 'artillerij', '-', 'kommandant', 'heeft', 'Verzoek', 'gedaan', 'om', 'geassisteerd', 'te', 'Worden', 'met', 'geschut', ',', 'ammunitie', 'goederen', 'en', 'kruit', ',', 'in', 'steede', 'van', 't', 'geen', 'zij', 'met', 'het', 'transportschip', 'Lauriston', 'Verloren', 'hebben', 'onze', 'voorraad', 'van', 'geschut', 'en', 'Verde', 're', 'ammunitie', 'goederen', 'is', 'zo', 'klein', ',', 'dat', 'Wij', 'hen', 'Weirig', 'assistent', 'sie', 'zullen', 'kunnen', 'bewijzen', 'maar', 'kruit', 'hebben', 'wij', 'Vijftig', 'duizend', 'ponden', 'moeten', 'belooven', ',', 'schoon', 'onze', 'Voorraad', 'te', 'Kolombo', ',', 'Gale', 'en', 'Jaffenapatnam', 'niet', 'veel', 'boven', 'de', 'vierde', 'halfhonderd', 'duizend', 'is', 'beloopen', 'zal', ',', 'hoe', 'veel', 'kolombo', 'alleen', 'behoorde', 'in', 'zijne', 'magazijnen', 'te', 'hebben', '.', 'Onze', 'kruitmolens', 'zijn', 'niet', 'in', 'staat', 'een', 'toereikende', 'quantiteit', 'in', 'Voorraad', 'te', 'brengen', ',', 'door', 'gebrek', 'aan', 'Zwavel', 'zoo', 'Wel', 'als', 'door', 'de', 'gesteldheid', 'van', 'de', 'molens', 'zelvendie', 'Voor', 'geen', 'Zwaare', 'leverancien', 'gemaakt', 'zijn', '.', 'Wij', 'Verzoeken', 'derhalven', 'ootmoedig', ',', 'dat', 'UWe', 'Hoogedelheeden', 'ons', 'zo', 'niet', '5', '.', 'p', 'meer', ',', 'ter', 'minsten', 'andere', 'Vijftig', 'duizend', 'ponden', 'kruit', 'gelieven', 'toete', 'zenden', ',', 'en', 'dat', 'indien', 'dit', 'kruit', 'in', 'de', 'drie', 'schepen', 'niet', '#', 'geheel', 'mocht', 'hunnen', 'geborgen', 'worden', ',', 'daar', 'toe', 'worden', 'gebuukt', 'een', 'of', 'twee', 'sloepen', ',', 'die', 'Wij', 'buiten', 'des', 'zeer', 'nodig', 'hebben', '.'], ['De', 'Franschen', 'hebben', 'zoo', 'men', 'hoord', 'niet', 'veel', 'geld', 'meede', 'gebragt', ',', 'en', 'zullen', 'dus', 'ongetwijffeld', 'spoedig', 'bij', 'ons', 'aanzoe', 'k', 'er', 'om', 'doen', ',', 'en', 'wij', 'zullen', 'het', 'hen', ',', 'om', 'het', 'groot', 'nut', ',', 't', 'geen', 'wij', 'in', 'den', 'tegenwoordigen', 'tijd', 'van', 'hun', 'verblijf', 'in', 'deeze', 'gewesten', 'treken', ',', 'niet', 'kunnen', 'Weigeren', '.', 'Wij', 'Verzoeken', 'derhalven', 'dat', 'onze', 'eisch', 'van', 'geld', 'niet', 'moge', 'verminderd', 'Worden', ',', 'alzo', 'er', 'geen', 'Vertier', 'is', 'van', 'koopmanschappen', 'en', 'wij', 'in', 'tijd', 'van', 'rood', 'bij', 'partikulieren', 'Weinig', 'geld', 'zonder', 'Vinder', '.', 'Na', 'dat', 'Wij', 'tijding', 'erlangden', 'Wegens', 'de', 'verovering', 'van', 'Trinkonomale', 'schreefde', 'eerstgeteekende', 'een', 'brief', 'aan', 'den', 'aldaar', 'kommandeerenden', 'Engelschen', 'officier', ',', 'Waar', 'bij', 'hij', 'hem', 'Verzogt', 'dat', 'de', 'getrouwde', 'Kompanies', 'dienaren', 'niet', 'mogten', 'na', 'Madras', 'Worden', 'vervoerd', 'en', 'dat', 'het', 'fonds', 'van', 'de', 'dia', 'konij', 'onaengeroerd', 'nogt', 'blijven', '.', 'De', 'heer', 'Admiraal', 'Hughes', ',', 'die', 'inmiddels', 'met', 'zijn', 'Vloot', 'na', 'Madras', 'Was', 'vertrokken', ',', 'dog', 'den', '23', '.', 'febr', ':', 'net', 'tien', 'scheeper', 'te', 'rugge', 'k', 'Wan', ',', 'heeft', 'bij', 'een', 'beleefden', 'brief', 'Van', 'den', '28:e', 'febr', ':', 'daar', 'op', 'geantwoord', ',', 'dat', 'hij', 'door', 'staat', 'kurdige', 'noodzakelijkheid', 'gedwongen', 'genoodzaakt', 'was', 'geweest', ',', 'veelen', 'zo', '5', 'getrouwden', 'als', 'ongetrouwden', 'na', 'Madras', 'op', 'te', 'zenden', ',', 'maar', 'dat', 'zij', 'met', 'groote', 'edelmoedigheid', 'behandeld', 'Waren', ',', 'Wijl', 'hunne', 'huisen', 'niet', 'geplunderd', 'en', 'hunne', 'goederen', 'aan', 'hen', 'in', 'eigendom', 'gehoorende', 'aan', 'hen', 'gelaaten', 'waaren', ',', 'en', 'dat', 't', 'fords', 'van', 'de', 'armen', 'onaangeroerd', 'was', 'gebleeven', 'en', 'aangelegd', 'konde', 'Worden', 'tot', 'nut', 'Van', 'de', 'geenen', ',', 'Waar', 'toe', 'het', 'bestend', 'was', '.', 'Wij', 'hebben', 'de', 'eer', 'een', 'afschrift', 'van', 'deezen', 'brief', 'met', 'een', 'Nederduitsche', 'Vertaaling', 'onder', 'de', 'bijlaagen', 'aan', 'tebieder', '.'], ['Voorts', 'hebben', 'Wij', 'de', 'eer', 'UWe', 'Hoog', 'Edelheeden', 'hier', 'nevens', 'aan', 'te', 'bieder', 'kopijen', 'van', 'twee', 'schreete', 'brieven', 'van', 'koetsjiem', 'van', 'den', '24', ':', " '", 'Iunuarij', 'en', '12:e', 'deezer', ',', 'met', 'een', 'portugeesch', 'Vaartuig', 'alhier', 'aangebragt', ',', 'Waar', 'uit', 'blijkt', ',', 'dat', 'de', 'Engelschen', 'door', 'het', 'Vernielen', 'van', 'het', 'leger', 'van', 'Huider', 'Ali', 'bij', 'Pallicheri', 'Zig', 'meester', 'van', 'het', 'geheele', 'Samarijnsche', 'land', 'gemaakt', 'hebben', ',', 't', 'Welk', 'die', 'van', 'koetssien', 'bedugt', 'heeft', 'gemaakt', 'voor', 'een', 'beleegering', ',', 'Welke', 'beduchting', 'tans', 'echter', 'werkelijk', 'is', 'verminderd', 'nu', 'de', 'fransche', 'Vloot', 'is', 'aangekoomen', '.', 'Onder', 'het', 'sluijter', 'deezes', 'ontvangen', 'Wij', 'berigt', 'Van', 'Manaar', 'dat', 'de', 'Engelschen', 'den', '19', '.', " '", 'februari', 'met', '500', '.', 'sipahis', 'bezit', 'van', 'ons', 'fort', 'te', 'Tutu', 'Roeijn', 'hebben', 'genomen', ',', 'en', 'dat', 'dezelve', 'reets', 'bezig', 'waren', ',', 'om', 'hetzelve', 'te', 'ondermijnen', 'ten', 'einde', 'het', 'te', 'doen', 'springen', ';', 'en', 'Voorts', 'dat', 'nog', 'Vier', 'man', 'van', 'de', 'agtergelatene', 'bezetting', 'te', 'Manaar', 'Waren', 'aangekomen', 'Wij', 'hebben', 'de', 'Eer', 'met', 'schuldige', 'eerbied', 'en', 'trouwe', 'te', 'zijn', '/:onderstond:/', 'Hoog', 'Edele', 'Groot', 'Achtbaere', 'Heer', 'Wel', 'Edele', 'Gestrenge', 'Heeren', '/:Lager:/', 'Uwer', 'Hoog', 'Edelheeden', 'zeer', 'onderdanige', 'en', 'gehoorzaeme', 'Dienaars', '/:Was', 'geteekend:/', 'Sm', ':', 'Will', ':', 'Pack', ',', 'Daniel', 'de', 'Bok', ',', 'C', ':', 's', 'de', 'Cock', 'en', 'J', ':', 'J', ':', 'Coquart', '/:in', 'margine:/', 'Kolombo', 'den', '23', '.', 'Maart', '1782', '.'], ['Accordeert'], ['D.', 'Van', 'Haak'], ['debvoir', 'kennise', 'te', 'laten', 'toecomen', ',', 'Even', 'als', 'wij', 'bij', 'die', 'van', 'den', '20„e', 'xb', ':', 'haer', 'nopende', 'de', 'zijde', 'Leverantie', 'voor', 'dit', '9', 'Jaer', 'hebben', 'gedaen', ',', 'en', "g'ordonneerd", ',', 'die', 'des', 'mogelijk', 'in', 'de', 'moolen', 'te', 'helpen', ',', 'ook', 'gequalificeerd', ',', 'soo', 'dat', 'niet', 'Lucken', 'wilde', ';', 'en', 'mier', 'sahit', 'inhamet', 'halsterrig', 'en', 'oneanderlijk', 'op', 'de', 'zijde', 'Leverantie', 'aendrong', 'die', 'te', 'ontfangen', ',', 'sampt', 'bij', 'die', 'van', 'den', '29„e', 'daer', 'aen', 'volgende', 'en', '15„e', 'Jan', ':', 'haer', 'indagtigd', ',', 'want', 'dat', 'was', 'al', 'meede', 'vergecten', ',', 'niet', 'tegenstaende', 'haer', 'op', 'den', '15„e', 'maij', 'daer', 'over', 'gebruijkte', 'breeder', 'resonnementen', ',', 'miet', 'sahit', 'inhamed', 'op', 'ontfangst', 'van', 'dat', '„', 'schrijvens', ',', 'dato', '29„e', 'xb', ':', 'te', 'laten', 'versoecken', ',', 'dat', 'hij', 'ten', 'Eersten', 'zomee', 'conconerenordre', 'geliefde', 'te', 'stellen', ',', 'aen', 'wie', 'dat', 'men', ',', 'de', 'gestipuleerde', 'recognitie', 'goederen', 'nu', 'geeven', 'bal', ',', 'en', 'niet', 'verpligt', ',', 'als', 'pro', 'dato', 'soo', 'Lange', 'aen', 'tehouden', ',', 'sulx', 'thans', 'de', 'zijde', 'buijten', 'belastinge', 'daer', 'van', 'overgaet', ',', 'en', 'na', 'deesen', 'dat', 'bedragen', ',', 'eerst', 'het', 'comptoir', 'generael', 'aengereekend', ';', 'en', 'ten', 'Lasten', 'gebragt', 'sal', 'kunnen', 'werden', ',', 'met', 'ons', 'wijders', 'voor', 'soo', 'veel', 't', 'comp', ':', 's', 'spahan', 'belangd', ',', 'aen', 'de', 'verwisselde', 'en', 'nu', 'in', 'Copia', 'overgaende', 'brieven', 'te', 'gedraagen', ',', 'gelijk', 'ook', 'in', 'alle', 'onderdanigh', '„', 't', ',', 'met', 'die', 'nu', 'na', 'de', 'westerse', 'Comp', '=', 'e', 'ver', 'werdenff', 'erersonden', ',', 'geschied', ',', 'en', 'bestaet', 'het', 'affgeladene', 'ede', 'te', 'tegenwoordig', 'in', 'de', '2', 'meerged', '„', 'te', 'scheepen', ',', 'in', 'het', 'volgende', 'teweeten'], ['„', 'de', 'de', 'geslipuleerde', 'revognitie', 'penningen', '.'], ['wat', 'bij', 'de', 'bediendens', 'tot', 'pahan', ',', 'weegens', 'de', 'Leverantie', 'van', 'dat', 'gebp', 'in', ',', 'voorhet', 'aenstaende', 'jaer', 'hebben'], ['voor', 's', 'vaderland', 'Jn', 'de', 'prins', 'Lugenuss', '.', '22140', 'lb', 'kirmanse', '2vol', 'in', '246', 'balen', '27000', '„', 'zijde', 'in', '180', 'voor', 'batavia', 'Totx', 'paerden', 'vaer', 'van', 'dat', 'er', '4', 'voor', 'bengalen', 'zijn', '.', '3000', '„', 'disse', 'bocke', 'vellen', '38', '„', 'phelpen', '116', 'lb', 'thuijn', 'Laden', '1000', '„', 'kraek', 'amandelen', '9', '600', '„', 'pistasjes', '6600', '„', 'gemeene', 'amandelen', '2500', '„', 'rosijnen', '.', '4000', '„', 'kismis', '702', '„', 'pruijmen', '50', '„', 'geconfijte', 'moernagelen', '50', '„', 'pruijmellen', '100', 'stx', 'glase', 'lampen', '130', '„', 'divse', 'glaswercken', '60', 'kassen', 'rosewater', '17', '„', '1', 'clarst', 'zijn', 'het', 'affgescheepte', 'in', 'Engeen', 'beloopt', '.', '.', '.', 'ƒ153179', '.', '17', '.', '8', '.', "In't", 'schip', 'abbekerk', 'C', 'voor', 'Ceijlon', '9000', 'p', '„', 's', 'goude', 'Europeaense', 'ducaten', '200', 'lb', 'kraak', 'amasdelen', '1400', '„', 'gemeene', 'd', '„', 'o', '10', 'kassen', 'rosewater', '204', 'lb', 'veruijmen', '35', 'kassen', ',', 'als', '25', 'd', '„', 'o', 'clareten', '10', '„', 'ordinarie', 'costende', '.', '.', 'ƒ', '38830:12:00', ':', '8', '.', 'voor', 'Cormandel', '100', 'lb', 'kraek', 'amandel', 'en', '700', '„', 'gemeene', 'd', '„', 'o', '50', '„', 'sruijmen', '36', 'kassen', 'wijn', ',', 'als', '10', 'd', '„', 'os', 'clareten', '26', '„', 'ordinarie', 'wijn', 'belopen', '„', '901', ':', '6', ':', '8', '.', 'Voor', 'mallabaer', '13000', 'p', '„', 's', 'goude', 'ducaten', '10', 'kassen', 'roservater', '110', 'lb', 'hasenoten', '—', '40', '„', 'wal', 'nooten', '120', '„', 'pruijmellen', '172', '„', 'kraek', 'amandelen', '425', '„', 'gemeene', 'd', '„', 'o', '82', '„', 'pruijmen', '22', 'kassen', 'wijn', 'als', '18', 'd', '„', 'o', 'clareten', '4„o', 'ord', '„', 'o', 'wijn', 'monteerende', '„', '84016', ':', 'p', ':', '8', 'Het', 'geladene', 'in', 'abbekerk', 'beloopt', 'In', 't', 'versondene', 'tesamen', '.', '.', '.', '.', '.', '.', '.', '.', 'p', '296927', '.', '17:-', '.'], ['_', ':', '2ƒ43747:19:8', '.'], ['t', 'geladene', 'in', 'dese', '2', 'bodems', '.'], ['Sulx', 'dat', " '", 'er', 'buijten', 'de', 'Chirase', 'wijnen', 'die', 'men', 'van', 'ginderna', 'herrew', '=', 's', 'door', 'gebrek', 'van', 'Last', 'beesten', 'niet', 'tijdelijk', 'heeft', 'van', 'batavia', 'mauquend', ':', 'kunnen', 'affkrijgen', ',', 'met', 'het', 'affgescheepte', 'voor', 'batavia', 'niet', 'dan', '4', 'kx', 'hengs', 'tpaerden', '6', 'p', '„', 's', 'wvolle', 'alcatijven', ',', 'en', '120', 'p', '„', 's', 'muscovische', 'jugten', 'komen', 'te', 'gebreeken,/', 'ter', 'oorsake', 'd', ':o', 'alcatijven', ',', 'niet', 'affgeweeven', ',', 'ende', 'Jugten', 'uijt', 'de', 'bovenlanden', 'nog', 'niet', 'waren', 'affgecomen', ',', 'terwijl', 'het', 'al', 'versondene', 'van', 'dit', 'mousson', 'met', 'deese', 'en', 'de', '2', 'vorige', 'bodems', 'sommeerd', 'ƒ794585', '.', '18', '.', '—', '.', 'en', 'den', 'almogende', 'gebeeden', 'blijffd', ',', 'haer', 'van', 'hier', 'vfesonden', '.', '—', '.', '.', 'een', 'spoedige', 'en', 'behoude', 'reijse', 'te', 'willen', 'verleenen', 'deese', 'in', 'dus', 'verreklaer', 'en', 'in', 'gereeth', '„', 't', 'gebragt', 'weesende', 'soo', 'wierd', 'ons', 'op', 'den', '15„e', 'feb', ':', 'p', '„', 'r', 'Coopmans', 'boode', ',', 'een', 'brief', 'dspalan', ',', 'door', 'den', 'onderaop9', 'van', 'den', 'ondercoopm', '=', 'r', 'en', 'spahans', 'secunde', 'Willem', 'brooks', 'toe', '„', 'gesonden', '.', '„', 'gebragt', ',', 'zijnde', 'van', 'den', '24„e', 'Januarij', ',', 'en', 'een', 'antwoord', 'opden', 'onsen', 'van', 'den', '20„en', 'decemb', ':', ',', 'beneevens', 'een', 'Ledige', 'en', 'wel', 'geresonneerde', 'verantwoordinge', 'op', 'het', 'geene', 'dat', 'men', 'hem', 'bij', 'het', 'wegens', 't', 'aan', 'hem', 'een', 'ppahanse', 'schrijvens', 'van', 'den', '5', '„', " '", 'gb', ':', 'ten', 'Lasten', 'Leij', ',', 'dog', 'dewijl', 'd', '„', 'o', 'missive', 'in', 'Copia', 'is', 'overgaende', ',', 'sullen', 'w', " '", 'ons', 'daer', 'aen', 'onder', 't', 'welneemen', 'van', 'uhoog', 'Ed', '„', 'e', 'agtb', ':', 'gedragen', ',', 'niet', 'alleen', 'te', 'seggen', ',', 'dat', 'de', 'onreedelijke', 'wijse', 'op', 'welke', 'daturen', 'dese', 'persoon', 'bij', 'arrive', 'heeft', 'comen', 'tehandelen', ',', 'en', 'noghandeld', ',', 'en', 'in', 't', 'vervolg', 'getragt', 'verdagt', 'te', 'maken', ',', 'daer', 'uijt', 'seer', 'Evidend', 'consteerd', 'en', 'niet', 'te', 'defereeren'], ['deselfs', 'verantwoordinge', 'N', 'H', 'Lasten', 'gelegde', '.'], ['rereptie', 'van', 'een', 'brief', 'uijt', '—', 'omanbrooks', 'herw', '„', 'ts', 'aen', '„'], ['ook', 'wat', 'Cap', '„', 'l', ',', 'dit', 'moussan'], ['Comt', ',', 'van', 'de', 'gedagten', 'die', 'wij', 'daer', 'over', 'bij', 'den', 'onsen', 'van', 'den', '12„e', 'xl', ':', 'hadden', ',', 'mitsg', '„', 's', 'dat', 'ons', 'voorneemen', 'tendeerd', ',', 'om', 'sulcke', 'connosele', 'kreegelheeden', ',', 'als', 'men', 'tegen', 'voordagte', 'oudercoopman', 'heeft', 'aengelegd', ',', 'geen', 'verdere', 'stoff', 'te', 'geeven', ',', 't', 'hier', 'bij', 'te', 'laten', 'berusten', ',', 'en', 'onder', 'het', 'renoveeren', 'van', 'een', 'goede', 'zegt', 'debenoudens', 'bij', 'het', 'huijshoudinge', 'en', 'minnelijk', 'gedrag', 'bij', 'eerste', 'afftegane', '„', 'sschrijvens', ',', 'van', 'hier', 'na', 'derrew', '„', 's', 'ook', 'ordre', 'op', 'geene', 'en', 'deese', 'kleenigheeden', 'te', 'stellen', ',', 'waer', 'na', ',', 'en', 'dit', 'ontfangene', 'schrijvens', ',', 'ons', 'al', 'verder', 'op', 'den', '18„e', 'daer', 'aen', 'p', '=', 'r', 'addresse', 'der', 'Engelsche', 'is', 'toegebragt', ',', 'een', 'Vaderlands', 'pacquet', 'met', 'brieven', ',', 'insluijtende', 'behalven', 'een', 'cinculair', 'briefje', 'van', 'p', '„', 'mo', 'gb', ':', '1709', '.', 'en', 'Extract', 'uijt', 'den', 'Eijsch', 'van', 'retouren', 'voor', 'dit', 'Lopende', 'Jaer', ',', 'soo', 'veel', 'persien', 'concerneerd', ',', 'nog', 'vijff', 'pacquetten', 'voor', 'de', 'westerse', 'comptoiren', ',', 'als', 'ceijlon', ',', 'Wat', 'geschriften', 'daer', 'van', 'Cormandel', ',', 'bengalen', ',', 'bouratte', 'en', 'cochim', ',', 'die', 'wij', 'bij', 'deese', 'geleegendheijd', 'versenden', ',', 'alhoewel', 'wij', 'vertrouwende', 'vrunden', 'van', 'derselver', 'teneur', 'al', 'sullen', 'weesen', 'gediend', ',', 'gemerkt', 'die', 'voor', 'deese', 'directie', ',', 'ons', 'al', 'over', ',', 'mallabaer', 'zijn', 'toegecomen', ',', 'gelijk', 'voorwaerts', 'genoteerd', 'gensteerd', 'geworden', 'is', ',', 'intusschen', 'dat', 'den', 'ondercoopman', 'Coorte', 'tot', 'hoeden', 'ondercoopman', 'sood', 'dato', 'nog', 'niet', 'vernomen', 'werdende', ',', 'nu', 'tot', 'een', 'Last', 'Comt', ',', 'en', 'tot', 'de', 'naest', 'van', 'deese', 'directie', 'de', 'naestvolgende', 'scheepen', 'sal', 'moeten', 'inwagten', ',', 'en', 'hier', 'overblijven', ',', 'dat', 'wij', 'Liever', 'anders'], ['nog', 'niet', 'te', 'voorschijn', 'besending', 'zal', 'moeten', 'blijven'], ['voorde', 'woesterse', 'comp', '=', 'es', 'zijn', '.'], ['ontfangst', 'van', 'een', 'pacquet', 'vaderlandsche', 'papieren', ',', 'en', 'p', ':', 'r', 'Wiens', 'addaes'], ['aff', 'tegaene', ',', 'hrijvens', 'sullen', 'recommandeeren', 'engelasten', '.'], ['hadden', 'gesien', ',', 'in', 'opsigt', 'hij', 'meeste', 'ziekelijck', 'en', 'daer', 'bij', 'natgierig', '(', 't', 'welk', 'eijgentz', ':', 'zijn', 'jndispositie', 'was', ',', 'waer', 'door', 'hij', 'despahanse', 'brief', 'van', 'den', '13„e', 'feb', ':', '1710', '.', 'niet', 'teekenen', 'kon', ',', 'en', 'wel', 'seeven', 'Etmalen', 'geduurd', 'hadde', ',', 'dE', 'Comp', ':', 'van', 'wijnig', 'nutte', 'weesen', 'kan', ',', 'maer', 'd', " '", 'affreekening', 'der', 'Wol', 'die', 'ons', 'dus', 'Lange', 'onts', 'Lond', ',', 'hebben', 'wij', 'ten', 'Laesten', 'op', 'Eergisteren', 'ontfangen', ',', 'soo', 'dat', 'de', 'nu', 'overgaende', 'niet', 'bij', 'Calculatie', ',', 'maer', 'onder', 'hare', 'waere', 'Costende', 'versonden', 'avend', ',', 'belopende', 'de', 'man', 'van', '6', 'lx', '=', 's', 'm', 'as', '8', '.', '13¾.', 'ruijm', ',', 'off', 'ƒ', '3:13:13½.', 'ruijm', ',', 't', 'welk', 'm', '=', 'as', '-', '3/0', 'off', 'ƒ', '—', '.', '5', ':', '3', '¾', 'ruijm', ',', 'veel', 'met', 'die', "van't", '8', 'duurder', 'is', ',', 'dan', 'die', 'van', 'a', '=', 'o', 'pass', '„', 'o', ',', 'en', 'niet', '8', 'stp', '„', 's', '8', 'penn', ':', 'gelijck', 'de', 'kirmanse', 'bediendens', 'eerst', 'gisten', ',', 'en', 'uhoog', 'Ed', '„', 'e', 'agtb', ':', 'sub', 'dato', 'primo', 'aug', '=', 'o', 'in', 'alle', 'submissie', 'bedeeld', 'en', 'voor', 'oogen', 'gebragt', 'is', ',', 'onder', 'verdere', 'aankundigingh', 'van', 'die', 'van', 'kirman', ',', 'datse', 'nog', 'een', 'parthijtje', 'van', '28', '.', '–', '.', 'balen', 'inhoudende', '2520', '.', '–', '.', 'lb', 'hadden', 'uijtgeseth', ',', 'dog', 'gelijk', 'die', 'veelheijd', 'niet', 'voor', 'd', " '", 'aenstaende', 'maand', 'hier', 'kan', 'weesen', ',', 'oversuden', '.', 'en', 'dat', 'de', 'scheepen', 'in', 'gereetheijt', 'zijn', 'gebragt', ',', 'mitsg', ':', 's', 'haer', 'tijd', 'wel', 'sullen', 'benodigen', ',', 'om', 'tijdig', 'op', 'batavia', 'te', 'weesen', ',', 'hebben', 'wij', 'niet', 'derven', 'besluijten', ',', 'die', 'daer', 'na', 'op', 'tehouden', ',', 'en', 'haer', 'reijse', 'te', 'doen', 'vertragen', ',', 'wes', 'die', 'op', 'weg', 'zijnde', 'wol', 'niet', 'voor', 'de', 'naeste', 'besendinge', 'staet', 'te', 'volgen', 'en', 'aff', 'te', 'gaen', '.', 'Waer', 'meede', 'P', '„', 'a', '&', '„', 'a', '(', 'onderstond', ')', 'hoog', 'Edele', 'gebiedende'], ['wat', 'quantiteijt', 'er', 'nog', 'op', 'weg', 'is', ',', 'waer', 'na', 'de', 'scheepen', 'niet', 'derven'], ['tot', 'wat', 'prijs', 'de', 'deesen', '7', 'Jaerse', 'beloopt', ',', 'en', 'hoe', 'vorige', 'diffoneerd', '.'], ['ontfangst', 'der', 'reek', ':', 'van', 'des', 'irmanse', 'wvol', '.'], ['heeren', '(', 'Lager', ')', 'uw', 'hoog', 'Edele', 'agtb', '=', 're', 'onderdanige', 'en', 'getrouwe', 'dienaren', '(', 'was', 'geteekent', ')', 'W', ':', 'm', 'backer', 'Jacobsz', ':', ',', 'Jan', 'Oets', ',', 'matth', '„', 's', 'van', 'Iongeren', ',', 'adriaan', 'Van', 'biesum', ',', 'N', '„', 'o', 'van', 'Hoorn', '(', 'in', 'margine', ')', 'gamron', 'den', '26„e', 'februarij', 'a', '„', 'o', '1711', '.', '(', 'en', 'daer', 'onder', ')', 'P', ':', 'S', ':', '28', 'kassen', 'Chiraese', 'Claretwijn', ',', 'zoo', 'Even', 'komende', 'aen', 'telanden', ',', 'hebben', 'niet', 'mogen', 'affwesen', ',', 'nog', 'in', 'Vugeen', 'voor', 'de', 'hooffd', 'plaets', 'tescheepen', ',', 'des', 't', 'versondene', 'nu', 'Loord', " '", '„', 'met', 'ƒ153741:6:—.', ',', 'dat', 'van', 'de', '2', 'bodems', 'ƒ', '297489', '.', '5', '.', '8', ',', 'en', 'de', 'vier', 'te', 'samen', 'ƒ', '795147', '.', '6', '.', '8', '.'], ['Gamron', 'Aan', 'd', " '", 'Edele', 'Heer', 'Willem', 'backer', 'Jacobsz', ',', 'directeur', 'over', 's', 'Comp', '„', 's', 'aansienlijkke', 'belangen', 'in', 't', 'Rijk', 'van', 'Persia', ',', 'mitsg', '„', 's', 'den', 'Raad', '.'], ['Bij', 'ons', 'Laetst', 'gedienstig', 'schrijvens', 'van', 'den', '19', '„', " '", 'der', 'verweeken', 'maand', '9b', ':', 'copielyk', 'neevens', 'desen', 'Leggende', ','], ['_', '„', 'te', 'Edele', ',', 'Erntfeste', ',', 'manh=', 'Wel', 'wijse', ':/', 'voorsienige', ',', 'en', 'seer', 'Genereuse', 'Heer'], ['ee', 'eee', 'phemmeer', 'uit', 'algem', '.', 'Voestuur', '1628', '.', 'devemb', 'Reteuir', 'ut', 'Ohna', '.', 'Hlaux', 'na', 'Redel', '.', 'affvanden', '6January', 'ƒ', 'd', '1e', 'ee', 'en', 'vee', 'ee', 've', 'e', 'ee', 'Ed', ':', 'Erentfebte', ',', 'Achtbare', ',', 'wijse', ',', 'voorsienige', 'seer', 'discrete', 'Heeren', 'Qulans'], ['Tsedert', 'onsen', 'Jongsten', 'hier', 'neuens', 'in', 'copie', 'gaende', ')', 'met', 'de', 'Schepen', 'Frederick', 'Benrick', ',', 'Bollandia', ',', 'Twdapen', 'van', 'Eelff', ',', "s'landts", 'hollandia', 'ende', 'de', 'Galias', 'den', '12en', 'November', 'past', 'in', 'Compe', 'van', 'Battania-', 'gescheijden', ',', 'ende', 'den', '15en', '.', 'do', 'door', 'de', 'strate', 'Sunda', 'geraeckt', 'sijn', 'hier', 'Godt', 'loff', 'den', '17en', '.', 'ende', '21e', '.', 'l.', 'van', 'Teijouhan', 'ende', 'Jappan', 'successiue-', 'wel', 'aengecomen', "t'Jacht", 'Erabinus', 'ende', "t'Schip", 'de', 'Vreede', "t'samen", 'geladen', 'met', '840', '.', 'pica', 'rouwe', 'Chineesche', 'sijde', ',', 'ende', '332', 'xxi0', '.', 'copter', '.', 'e.', 'e', 'e'], ['Op', "d'aencompete", 'gemelter', 'Schepen', 'hebben', ',', 'dadelijck', 'met', 'den', 'Raedt', 'ouerleijdt', ',', 'off', 'niet', 'oorbaer', 'ende', 'raedtsaem', 'soude', 'wesen', ',', 'noch', 'een', 'Schap', 'met', 'partije', 'sijde', ',', 'beneffens', 'de', 'becomene', 'aduijsen', 'van', 'Teijouhan', ',', 'ende', '—', 'Japan', ',', 'opt', 'nan', 'spoedichste', 'de', 'bouen', 'gemelte', 'Vloote', 'nae', 'te', 'seijnden', ',', 'om', 'deselue', 'noch', "t'sij", 'dan', 'aende', 'Cabo', 'ofte', 'St.', 'Sdelena', 'te', 'mogen', 'beloopen', '.', '&', 'Waerop', 'aen', 'd‛een', 'sijde', 'Ingesien', 'sijnde', ',', 'hoe', 'voor', "t'verloop", 'vanden', 'gelimiteerden', 'tijdt', 'op', "d'affvaerdinge", 'der', 'Retour', 'Schepen', 'naer', 't', 'nan', 'Naderslandt', ',', '(', 'achtervolgende', 'V', 'Ed', ':', 'aduisen', 'met', 'Bollandia', 'Jongst', 'van', 'daer', 'becomen', 'niet', 'wel', 'doenlijck', 'soude', 'sijn', 'een', 'Schip', 'tot', 'gemelte', 'Voijagie', 'seijl', 'reedt', 'te', 'crijgen', ';', 'daer', 'beneffens', 'dat', 'Jegenwoordich', 'geen', 'andere', 'RetourSchepen', 'bijder', 'handt', 'hebben', 'als', 'Vianen', 'ende', "t'wapen", 'van', 'Boorn', ',', 'alleen', ',', 'behaluen', 'dat', 'van', "t'wapens", 'suffirante', 'tot', 't', 'nan', 'Voijagie', 'nae', 'tvaderblandt', 'seer', 'getwijffelt', 'werdt', '.', 'Item', 'dat', 'Jegenwoordich', 'ouer', 'Gants', 'Jndia', 'seer', 'schaers', 'van', 'Varend', 'nan', 'volck', 'voorsien', ',', 'sijn', '.', 'Ende', 'sal', 'men', "d'ordinarij", 'handel', 'plaetsen', 'naer', 'behooren', 'waernemen', ',', 'het', 'sober', 'getal', 'vandien', 'niet', 'meer', 'dient', 'te', 'attenueren', ';'], ['Noch', 'principal', 'ende', 'bouen', 'al', ',', 'dat', 'men', 'vreest', 'v.', 'Ed', ':', 'ordre', 'van', 'ter', 'bequamer', 'tijt', 'op', 'onse', 'Landen', 'comende', ',', 'achter', 'Engelandt', ',', 'om', 'te', 'loopen', ',', 'door', 'de', 'moetwil', 'ende', 'rebellije', "van't", 'Scheepsvolck', '(', 'welck', 'gemeenl', 'op', 'de', 'thuijs-reijse', 'de', 'meester', 'maeckt', ',', 'ende', "d'Ouericheijt", 'Hetten', 'voorschrijft', 'niet', 'behoorlijck', 'achtervolcht', ',', 'maer', 'de', 'cours', 'recht', 'door', "t'Canael", 'nae', 'Nederlandt', 'gestelt', 'mocht', 'werden', ',', 'al', 'schoon', 'het', 'tijts', 'genouch', 'eynam', 'om', 'achter', 'om', 'te', 'loopen', '.', 'In', 'voegen', ',', 'dat', 'ons', 'om', 'voorverhaelde', 'consideratien', 'eenichsints', 'beswaert', 'woirden', 'de', 'syde', 'dus', 'laet', 'met', 'een', 'Schip', 'ouer', 'teseijnden', '.', 'Doch', 'aen', "d'ander", 'sijde', 'ouerwogen', ',', 'soo', 'noodich', 'het', 'sij', 'V', 'Ed', ':', 'tegen', 'haere', 'Excessiue', 'lasten', ',', 'met', 'soulagenbele', '—', 'Recouren', ',', 'soo', 'veel', 'mogelijck', 'verlicht', 'werden', ',', 'gelijck', 'mede', 'dat', 'het', 'U', 'Ed', ':', 'animeren', 'sal', 'omme', 'de', 'requisite', 'capitalen', ',', 'tot', 'Vigorenter', 'vervolch', 'vandien', 'aduantagieusen', 'handel', 'int', 'nan', 'aenstaende', 'des', "t'onbecrompener", 'te', 'fourneren', ',', 'hebben', 'euenwel', 'goedt', 'gevonden', ',', "t'Schip", 'Vranen', 'opt', 'nan', 'spoedichste', 'met', '384½.', 'Nicol', 'sijde', '1', '331', '...', 'r.', 'd', '#ERROR!', 'o.', 'cooper', '7972', '...', 'Sacken', ',', 'perper', '20', '6', '1', '8', '..', 'lb', '.', 'Salpeter', ':', 'beneffens', 'de', 'noodige', 'aduisen', ',', 'ende', 'bescheijden', 'aff', 'te', 'vaerdigen', '.', 'Almogende', 'gelieue', 'UEd', ':', 'e', 'dit', 'ende', 'de', 'vooraffgebondene', 'Schepen', 'in', 'salko', 'te', 'laten', 'toecomen', '.', '22', '.'], ['Otp', '20en', '.', 'Nouembr', '.', 'is', 'hier', 'van', 'Patane', 'wel', 'aengecomen', 't', 'nan', 'Jacht', 'de', 'Griffoen', '(:', 'geladen', 'met', '670', '.', 'Baren', 'Ppeper', ',', 'welck', 'vrij', 'wat', 'dier', 'connot', 'denen', 'W', ':', 'Curt', 'Sumatsa', '.', 'o', '1', 'e', 'de', 'CCormandel', ':', 'te', 'staen', ',', 'ten', 'aensien', 'de', 'cleeden', 'seer', 'goeden', 'coop', 'daer', 'tegen', 'verhandelt', 'sijn', 'soo', 'dat', 'voor', 'dees', 'tijt', 'in', 'dat', 'quartier', 'gants', 'weijnichte', 'doen', 'is', ',', 'ende', 'niet', 'noodich', 'wesen', 'sal', ',', "t'naeste", 'Jaer', 'derrewaerts', 'weder', 'teseijnder', 'De', 'Rijs', 'was', 'daer', 'uijt', 'der', 'maten', 'dier', ';', 'De', 'toataneten', 'vreesen', 'alsnoch', 'dat', 'den', 'Atchinder', 'van', 'Gueda', 'te', 'Lande', 'te', 'lande', 'decieitiersn', 'comen', 'sal', ',', 'daer', 'ons', 'bedunckt', 'niet', 'veel', 'apparentie', 'toe', 'en', 'is', 'eeee'], ['Vande', 'Westcust', 'van', 'Sumatra', 'is', 'hier', 'den', '25.en', 'd.o', '.', 'mede', 'abel', 'aengecomen', 'de', 'fluijt', 'Amstervoen', ',', 'met', '900', '.', 'bharen', 'ppever', 'aldaer', ',', 'tegen', 'cleeden', 'verhandelt', ',', 'vrij', 'wat', 'proffitabelder', 'dan', 'opde', 'custe', 'van', 'Patans', ',', 'alsoo', 'daer', '8o', 'O', 'cento', 'aduance', 'geuen', ',', 'ende', 'in', 'Tatane', 'niet', 'meer', 'als', '30', '.', 'Ot', 'FL', 'W.', 'Cust', 'was', 'opt', 'vtreck', 'van', 'gemelte', 'Jacht', 'van', 'daer', ',', 'noch', 'goede', 'partije', 'peper', 'te', 'becomen', ',', 'ende', 'dat', 'tot', 'redelijcken', 'prus', ':', 'Ooch', 'hebben', 'geldt', 'noch', 'cleeden', 'om', 'derrewaerts', 'ie', 'mogen', 'seijnden', '.'], ['e.', 'e', 'En', 'D.o', 'S.r', 'Is', 'sier', 'van', 'Masilipats.n', 'ende', 'Paliacaite', 'wel', 'aengecomen', 't', 'nan', 'Jacht', 'D', 'Battania', 'met', '300', '.', 'Clauen', 'ende', '134', '-', 'packen', 'cleeden', ',', 'blesde', 'sorteringe', ',', 'alsoo', 'den', 'tijt', 'te', 'cort', 'was', ',', 'omme', 'voor', 'de', 'becomene', 'comrtsr', '.', 'van', 'hier', 'met', 'de', 'Jachten', 'Grootenbrouck', 'Brouwershauen', ',', 'ende', 'Battr', '.', 'eenich', 'ander', 'slach', 'ofte', 'meerder', 'quantiteijt', 'cleeden', ',', 'te', 'becomen', ',', 'ende', 'dit', 'Jaer', 'hebben', 'oock', 'niet', 'anders', 'te', 'verwachten', ',', 'Soo', 'dat', 'de', 'Molucq', ',', 'Amboina', 'ende', 'Banida', 'gelijck', 'mede', 'wij', 'hier', 'in', 'Battra', '.', 'noch', 'een', 'Jaer', 'onvoorsien', 'sullen', 'moeten', 'blijven', '.', 'Ofs', 'oock', 'acpparent', 'dat', 'V.', 'Ed', ':', 'mede', 'in', 'twee', 'Jaeren', 'geen', 'retour', 'van', 'daer', 'becomen', 'sullen', 'ende', 'dat', 'vermidts', 'V', 'Ed', ':', 'eijgen', 'deffectueusheijt', 'int', 'derrewaerts', 'beschicken', 'van', 'de', 'Jaerlijcx', 'geeijschte', 'capitalen', '...', "d'E", 'Leeuwwinne', 'ende', 'Kemphaen', 'waren', 'op', '2en', 'Novemb', '.', 'pasro', 'doen', "d'Engelsche", 'Abigael', 'van', 'daer', 'vertrock', ',', 'aldaer', 'noch', 'niet', 'verlcheinen', ',', 'Ende', 'is', 'apparent', 'dat', 'geduerende', "t'noorder", 'Mouson', ',', 'daer', 'oock', 'niet', 'sullen', 'connen', 'comen', '—', '.', 'De', 'Paliacatsche', 'sorteringe', 'welck', 'al', 'geschilderde', 'doecken', 'sijn', ';', 'sal', 'niet', 'eerder', 'dan', 'in', 'Maij', 'a.o', '.', '1628', '.', 'gereedt', 'wesen', ';', 'Ouer', 'de', '32', '.', 'E', 'Pagoden', 'hadden', "d'onse", 'op', 'leueringe', 'gegeven', 'ee', 'Om', 'de', 'Zuijdt', 'waren', 'de', 'drije', 'Naijcken', 'vereinicht', ',', 'waer', 'door', 'aipparent', 'is', 'den', 'Standt', 'in', 'die', 'Quartieren', 'vrij', 'wat', 'beteren', 'dat', 'ende', 'datmen', 'metter', 'tijt', 'goede', 'partije', 'sal', 'peter', 'sal', 'connen', 'becomen', '.'], ['eeeee', 'Isen', 'Calliacatte', 'geeft', 'het', 'Goudt', 'van', 'Guinea', '10½', '8r', '.', 'cento', 'advance', 'ende', 'was', "t'Cattoen", 'daer', 'soo', 'dier', ',', 'als', 'in', 'lange', 'Jaren', 'niet', 'geweest', 'is', 'Pr.', 'Madilwals', '.', 'continueerden', 'de', 'Mooren', 'haere', 'Monovolien', 'ende', 'Qquardt', 'tractement', "t'ontwaerts", ';', 'Met', 'niemant', 'anders', 'dan', 'met', 'drije', 'deee', 'pachters', ',', 'mochten', "d'onse", 'aldaer', 'handelen', ';', 'Ende', 'noch', 'werdt', 'haer', 'opgedicongen', 'sulcken', 'sorteringe', 'als', 'sij', 'selfs', 'willen', ':', 'Waer', 'tegen', 'met', 'soete', 'middelen', 'niet', 'te', 'doen', 'is', '.', 'Soo', 'de', 'liberteijt', 'vanden', 'handel', 'gelijck', 'mede', 'voldoeninge', 'van', "d'affgedrongen", 'U', 'E', 'Nagoden', ',', 'ende', 'van', 'andere', 'geledene', 'schaden', 'ende', 'Interesten', 'meer', ',', 'begeeren', 'bebonnen', 'niet', 'anders', 'te', 'doen', 'als', 'ons', 'volck', 'ende', 'goederen', 'voor', 'reen', 'tijt', 'e', '1', '„', '90', 't', 'ked', 'ee', '.'], ['ve', 'een', 'Diamanten', 'sijn', 'daer', 'noch', 'wel', 'te', 'becomen', ',', 'maer', 'dier'], ['eeen', 'tijt', 'van', 'masilupats', '.', 'te', 'lichten', 'ende', 'eenige', 'Scheepen', 'in', 'de', 'mlaenden', 'Februarij', 'ende', 'Meert', 'daer', 'voor', 'te', 'houden', ',', 'om', 'ons', 'van', "t'iloorsche", '-', 'Vaertuijch', 'te', 'verseeckeren', ',', 'en', 'de', 'Grooten', 'bij', 'dien', 'middel', 'te', 'constringeren', 'tot', 'restauratie', 'vande', 'geleden', 'Interesten', 'ende', 'schaden', ',', 'mitsgaders', 'Dat', 'ons', 'den', 'vrijen', 'ende', 'onbecommerden', 'handel', 'in', 'Masilicat', 'nam', 'gedoogen', '.', 'Nae', "d'onse", 'vande', 'custe', 'aduiseren', ',', 'behoeuen', 'met', 'eens', 'sbaricheijt', 'daer', 'in', 'te', 'maecken', ',', 'alsoo', 'den', 'handel', 'in', 'Malilipals', ',', 'daer', 'door', 'niet', 'lange', 'sullen', 'deruen', ':', 'De', 'Grootste', 'Mooren', 'die', 'ons', 'de', 'meeste', 'ouerlast', 'doen', ',', 'sijn', 'de', 'geene', ',', 'twelcke', 'de', 'voorneemste', 'capitalen', 'nae', 'Mocha', ',', 'Atchin', ',', 'Regu', 'ende', 'elders', 'teiqueren', ',', 'sij', 'mogen', 'den', 'handel', 'op', 'dese', 'Quartieren', 'veel', 'min', 'dan', 'Wij', 'Marilwats', '.', 'deruen', '.', 'U', 'Ed', ':', 'aduijs', 'aengaende', "t'redres", 'van', 'dese', 'saecke', ',', 'sullen', 'daerop', 'gaerne', 'hooren', '.'], ['eeveee', 'Der', 'neuens', 'gaende', 'copie', 'van', 'missiue', 'ouer', 'de', 'Custe', 'Choromme', '.', 'van', 'Surarte', 'becomen', ',', 'sullen', 'u', 'Ed', ':', 'dien', 'hoe', "d'onse", 'aldaer', 'sonder', 'Negotie', 'saten', ',', 'belast', 'sijnde', 'met', '200', 'O', 'gl', '.', 'a', 'deposito', 'gelicht', ',', 'waer', 'voor', 'grooten', 'Interest', 'moeten', 'betalen', 'Ede', 'specerijen', 'Nagelen', ',', 'Nooten', 'ende', 'foelije', 'waren', 'meer', 'dan', '50', '.', 'Rcento', 'in', 'prijs', 'gedaelt', ',', 'conden', 'geene', 'vercoopen', ',', 'dan', 'tot', 'leegen', 'Phris', 'Ambeine', 'Banda', 'Js', 'Almigon', 'eicht', 'bij', 'paliacatte', 'drijuen', "d'Engelschen", 'haren', 'handel', ',', 'welcke', 'plaetse', 'haer', 'soo', ':', 'dienstich', 'is', ',', 'als', 'ons', 'Paliacatte', '.', 'Op', 'haer', 'versouck', 'is', "d'onse", 'den', 'handel', 'aldaer', 'verboden', ',', 'hebben', 'daer', 'een', 'steenen', 'Huijs', 'geboudt', 'met', 'een', 'aerden', 'weal', 'omtrocken', ',', 'ende', 'geuen', '-', '.', 'uijt', 'aldaer', 'fortificeren', 'sullen'], ['Met', 'onse', 'Jongste', 'is', 'uEd', ':', 'geaduiseert', 'hoe', 'van', 'hier', 'door', 'de', 'Strate', 'van', 'Mallacca', 'nae', 'Masilipats', '.', 'geboorden', 'hadden', 't', 'nan', 'Jacht', 'Wedenblycq', 'met', 'een', 'Capitael', 'van', 'l', '120885', '„', '15', '„', 'Waer', 'mede', 'oock', 'ouergegaen', 'is', ',', 'Mousabeeck', ',', 'Ambassadeur', 'des', 'Conincks', 'van', 'Pertia', '.', 'Onise', 'cruijssende', 'Jachten', 'hebben', "t'selue", 'den', '35e', 'Octob', '.', 'pasto', '.', 'omtrent', 'ppoulo', '-', 'Vercelaer', 'bij', 'Noorden', 'Mallacca', 'gerescontreert', '.', 'Waer', 'ouer', 'aipvarent', 'is', ',', 'dat', 'een', 'spoedige', 'reijs', 'doen', 'sal', ',', 'twelck', 'Godt', 'gene', 'dr', '21e', '.', 'Septembris', 'pasen', '.', 'was', "t'Jacht", 'Grombershanen', 'van', 'Masilivas', '.', 'naer', 'Arraccan', 'vertrocken', 'met', 'een', 'Cargasoen', 'van', 'ƒ', '3900', '.', 'om', 'tselue', 'aen', 'blauen', ',', 'otterijs', 'te', 'besteden', ',', 'met', 'ordre', 'dat', 'tegen', 'hal', 'ff', 'December', 'weder', 'voor', 'Masilipats', '.', 'Keere', '.', 'uo', '16en', '.', 'Decemb', '.', 'passaco', 'hebben', 'van', 'hier', 'naer', 'Amboina', ',', 'ende', 'Gaudamet', 'de', 'Noodige', 'comptanten', 'coopmanschappen', 'ende', 'prouisien', 'gesonden', 'de', 'Schepen', 'Suijdthollandt', 'ende', 'den', 'Arent', ',', 'met', 'ordre', 'dat', 'in', 'compen', '.', 'Amboina', 'sullen', 'aendoen', ',', 'ende', 'dat', 'het', 'Shp', 'Hollandt', 'van', 'daer', 'voorts', 'naer', 'Banda', 'sal', 'loopen', ',', 'soo', 'haest', 'in', 'Amboina', 'gemust', '_', '.', 'can', 'worden'], ['Met', 'gemelte', 'Schepen', 'hebben', 'wij', 'naer', 'Amboina', 'ende', 'Banda', 'affgevaerdicht', 'als', 'onse', 'expresse', 'Gecommitteerde', 'den', 'Oppercoopman', 'Gregorius', 'Cornelij', 'ermmate', 'Etr', 'ende', 'Capn', '.', 'Marten', 'Jansz', 'Vogel', ',', 'omme', 'in', 'd‛een', 'ende', "d'ander", 'plaets', 'te', 'bevoirderen', 'sulcx', 'als', 'den', 'meesten', 'dienst', 'ende', 'woelstandt', 'vande', 'Compen', '.', 'aldaer', 'vereijscht', ',', 'Insonderheijt', 'inde', 'Quartieren', 'van', 'Amboina', ',', 'alwaer', 'wbij', 'bevinden', 'volgens', "t'schriftelijck", 'verbael', 'vanden', 'Commissaris', 'Gillis', 'Seijs', ',', 'In', 'April', 'pase', '.', 'aende', 'cant', 'van', '616', '.', 'blancke', 'coppen', 'in', 'dienst', 'ende', 'gagie', 'vande', 'Compnie', '.', 'gehouden', 'wierden', ',', 'beneffens', '208', '.', 'slanen', 'sijnde', 'voorwaer', 'een', 'groot', 'getal', ',', 'daer', 'mede', 'de', 'Compene', '.', 'in', 'Amboina', 'buijten', 'Proportie', ',', 'met', 'ouer', 'groote', 'lasten', ',', 'ende', 'euenwel', 'niet', 'merckelijcken', 'affganck', 'ende', 'verachteringe', 'in', 'haere', 'Negotie', 'en', 'Nagel', 'retour', 'beswaert', 'sit', ',', 'hebbende', 'in', 'voortijden', ',', 'doen', 'sij', 'miet', 'ongebiender', 'macht', 'te', 'weeten', 'van', '150', '.', 'Coppen', 'ten', 'hoochsten', ',', 'aldaer', 'geseten', 'wais', 'ongelijck', 'meerder', 'ontsach', ',', 'vorderlijcker', 'handel', 'ende', 'treffelycker', 'nagel', 'retour', 'van', 'daer', 'becomen', ';', 'Van', 'welcke', '616', '.', 'coppen', ',', '162', '.', 'Tsoonen', ',', 'ende', 'dat', 'apparent', 'vande', 'ervarenste', 'ende', 'loeckste', 'Soldaten', ',', 'op', 'acht', 'verscheijden', 'plaetsen', 'in', 'Garnisoen', 'verdeelt', 'sij', 'Behaluen', 'dat', 'met', 'voorsz', 'verdeelinge', 'tot', 'Compes', '.', 'progres', 'ende', 'Goulagiement', 'in', 'gemelte', 'Quartieren', 'gants', 'niet', 'gevoirdert', 'Werct', 'soo', 'is', 'oock', 'deselue', 'niet', 'bastandt', ',', 'omme', "d'ffiuasien", 'van', 'externer', 'Vijanden', 'te', 'connen', 'resisteren', ',', 'nochte', 'oock', "d'Imboonders", 'alsse', 'ontrouw', 'Wesen', 'willen', ',', 'in', 'ontsach', 'ende', 'dwang', 'te', 'houden', ',', 'Gelijck', 'als', 'op', 'Bouro', 'ende', 'inde', 'Manipes', 'met', 'schande', 'ende', 'verlies', 'van', 'Volck', 'ende', 'goedt', 'gebleecken', ',', 'is', ';', 'Derhaluen', 'gemelte', 'Gecommitteerde', 'precise', 'ordre', 'gegeuen', 'hebben', ',', 'omme', 'de', 'verspreijde', 'macht', '(', 'twelck', 'buijten', 'onse', 'kennisse', 'ende', 'last', ',', 'geschiet', 'is', ')', 'weder', 'in', 'te', 'trecken', ',', 'met', 'expres', 'Verboth', 'dat', 'int', 'nan', 'aenstaende', 'geene', 'extensie', 'van', 'Garnisoenen', 'ofte', 'fortificatien', 'meer', 'voorgenomen', 'werden', ',', 'sonder', 'alvooren', 'daer', 'toee', 'speciale', 'last', 'ende', 'ordre', 'van', 'ons', 'becomen', 'Is', 'hebben'], ['Visitate', 'ge', '.'], ['Ende', 'dewijle', 'men', 'door', 'extremiteijt', 'van', 'wapenen', '(', 'twelck', 'doch', 'niet', 'dan', 'groote', 'lasten', ',', 'onseeckere', 'uijtcompsten', ',', 'horrible', 'bloetstorting', ',', 'Herderff', 'van', 'menschen', 'ende', 'Landen', ',', 'hadije', 'ende', 'emulatie', 'van', 'nabuijren', 'mitsgaders', 'voor', 'eerst', 'groote', 'verachtering', 'in', 'des', 'Compes', '.', 'nootwendich', 'soulaes', '(', 'den', 'Nagelhandel', ')', 'naer', 'hem', 'is', 'bleijpende', ')', 'Jegenwoordich', 'niet', 'gedisponeert', 'is', ',', 'den', 'vervallen', 'Stadt', 'inde', 'Quartieren', 'van', 'Ambr', '.', 'naer', 'behooren', 'te', 'restaureren', 'ende', 'te', 'verseeckeren', ',', 'ende', 'dat', 'het', 'in', 'aller', 'manieren', 'geradender', 'ende', 'voor', 'de', 'presente', 'gestaltenisser', 'vande', 'Compe', '.', 'nitter', 'sij', 'te', 'bimuleren', ',', 'hebben', 'wij', 'voors', 'Gecommitteerde', 'mede', 'geladt', 'ende', 'beuolen', ',', 'alle', 'vlijt', 'ende', 'Industrieuseijt', 'aen', 'te', 'wenden', ',', 'omme', 'door', 'supportabelder', 'middel', ',', 'bij', 'wege', 'van', 'bevreding', 'tot', 'beslechtinge', 'van', 'alle', 'gepasseerde', 'misverstanden', ',', 'ende', 'onlusten', ',', 'met', 'die', 'van', 'Bittoe', ',', 'Loeboe', ',', 'Combello', ',', 'dessidi', ',', 'Orang', 'ende', 'consorten', ',', 'als', 'onse', 'oude', 'Bondtgenoten', ',', 'in', 'termen', 'van', 'nieuwe', 'vruntschap', 'te', 'geraecken', ',', 'daer', 'door', 'de', 'gealtereerde', 'ende', 'verwijderde', 'gemoederen', 'in', 'voorige', 'gerustheijt', 'ende', 'patisique', 'posture', 'herstelt', ',', 'ende', 'alsoo', "t'vervoeren", 'vande', 'Nagelen', 'int', 'aenstaende', 'mochte', 'voorgecomen', 'werden', ',', 'soo', 'lange', 'niet', 'gedisponeert', 'sijn', "t'selue", 'anders', 'te', 'beletten'], ['Schhtervolgende', 'V', 'Ed', ':', 'Instructie', 'tot', 'de', 'Visite', 'van', 'V.', 'Ed', ':', 'Gouuernements', ',', 'Directien', ',', 'Comptoiren', 'ende', 'Residentien', 'in', 'Jndia', 'bij', 'sonder', 'beraemt', ',', 'ende', 'met', 'hollandia', 'becomen', ',', 'hebben', 'wij', 'dvoors', 'de', 'tromme', '1', 'Aoor', 'bij', 'enen', '3', 'eeen', 'Gecommitteerde', 'mede', 'gelast', 'UEd', ':', 'ordre', 'desen', ',', 'raeckende', 'in', 'gemelte', 'Quartieren', 'van', 'gelijcken', 'te', 'bevoirderen', 'ende', 'waer', 'te', 'nemen', ',', 'gelijck', 'V', 'Ed', ':', 'bij', 'neuensgaende', 'copie', 'van', 'onse', 'Instructie', ',', 'aende', 'selue', 'mede', 'gegeuen', ',', 'van', 'd‛een', 'ende', "d'ander", 'naerder', 'onderrichtinge', 'sult', 'connen', 'becomen', ',', 'Waer', 'aen', 'ons', 'voirder', 'gedraegen'], ['Van', 'Jambij', 'sijn', 'hier', 'den', '15', '.', 'en', '13.en', 'December', 'aengecomen', 'de', 'Jachten', 'Beuerwijck', 'ende', 'de', 'Bare', 'geladen', 'met', '5100', 'xi', '.', 'P', 'ever', '„', 'aen', 'geldt', ',', 'ende', 'coopmanschappen', ',', 'resteerde', 'bij', "t'comptoir", 'aldaer', 'noch', 'omtrent', 'soo', 'veele', ',', 'dat', 'ongeveerlijck', '150', '.', 'lasten', 'Peper', 'souden', 'connen', 'procureren', '.', '(', 'T‛sedert', 'hebben', 'verstaen', ',', 'hoe', 'alles', 'aen', 'Epper', 'besteedt', 'was', ',', 'Waer', 'ouer', "d'onse", '150', '.', 'a', '200', '.', 'pagqe', '.', 'vleeden', 'niet', 'eenich', 'geldt', 'versoucken', ',', 'gissing', 'maeckende', ',', 'soo', 'die', 'gesonden', 'werden', ',', 'dat', 'tegen', 'Martij', 'toecomende', 'omtrent', '5000', '.', 'tpicol', 'wever', 'in', 'Doorraedt', 'sullen', 'hebben', '.', 'Noch', 'geldt', 'noch', 'cleeden', 'connen', 'derrewaerts', 'seijnden', 'voor', 'dat', 'nieuw', 'secours', 'van', 'Nederlandt', 'ende', 'Choromandel', 'becomen', '„', '32', '„', '4', '.', '#ERROR!', 'Den', 'oppercoopman', 'van', 'Jambij', 'Cornelis', 'vander', 'Hoeff', 'aduiseert', 'ons', ',', 'hoe', 'vanden', 'Coninck', 'van', 'Jambij', 'versocht', 'heeft', 'recompense', 'voor', 'onsen', 'gepresteerden', 'dienst', ',', 'opt', 'nan', 'Exploict', 'naer', 'Dalimban', ',', 'maer', 'heeft', 'niet', 'anders', 'connen', 'obtineren', 'dan', 'uijtstel', 'van', 'betalinge', 'des', 'Tols', ',', 'tot', 'dat', 'de', 'Coninck', 'Antwoordt', 'op', 'sijn', 'versouck', 'van', 'Nieuw', 'secours', 'tegen', 'Palimban', 'becompt', ';', 'Velck', 'secours', 'den', 'Coninck', 'van', 'ons', 'ongetwijffelt', ',', 'met', 'dier', 'Intentie', 'versoeckt', ',', 'als', 'wel', 'e', 'e', 'vn', 'e', 'weetende', ',', 'niet', 'becomen', 'en', 'sal', ',', 'op', 'dat', 'bij', 'onse', 'beijgeringh', 'oorsaecke', 'mocht', 'capteren', ',', 'ons', 'de', 'belooffde', 'vrijheijt', 'van', 'toll', 'voor', '10', '.', 'a', '12', '.', 'Jaren', 'te', 'ontseggen', ',', 'ofte', 'soo', 'schoon', 'andermael', 'eenich', 'secours', 'sonden', ',', 'dat', 'het', 'selue', 'emmers', 'dog', 'vruchteloos', 'als', "t'voorgaen", 'soude', 'doen', 'slijten', 'ende', 'eventeren', ';', 'DWijle', 'wij', 'voorseecker', 'souden', 'dat', 'het', 'die', 'van', 'Jambij', 'met', 'die', 'van', 'Palimban', 'in', 'ernst', 'niet', 'en', 'meenen', ',', 'ende', 'oock', 'rbel', 'van', 'daer', 'sullen', 'blijven', '.', 'Voor', 'tedoen', 'van', 'dEngelschen', 'sijn', 'voor', 'desen', 'Ingeleijdt', 'geweest', ',', 'anders', 'souden', 'dien', 'folije', 'niet', 'begonnen', 'hebben', '.', 'Voor', 'die', 'van', 'Palimban', 'sijn', 'de', 'Jambinesen', 'tegenwoordich', 'vrij', 'wat', 'bevreest', ',', 'oor', 'desen', 'hebben', "d'onse", 'verscheijden', 'Schepen', 'ledich', 'van', 'daer', 'herwaertse', 'gesonden', ',', 'ende', 'nu', 'versoecken', 'sij', 'andere', ',', 'soo', 'om', 'de', 'Peper', 'van', 'daer', 'te', 'lichten', ',', 'als', 'om', 'Compes', 'Volck', 'ende', 'restanten', 'aldaer', 'te', 'mogen', 'verseeckeren'], ['Onse', 'tfachten', 'Int', 'nan', 'vaerwater', 'van', 'Mallacca', 'cruijssende', ',', 'hadden', ',', 'niet', 'anders', 'verricht', ',', 'dan', 'met', 'onse', 'Jongste', 'geaduiseert', 'is', ';', 'E.', 'ober', 'deeen', 'sijn', 'vande', 'Noort', 'naer', 'Pedra', 'branca', ',', 'om', 'de', 'Zuijdt', 'vertrocken', 'C', '#ERROR!', 'a', 'sog', 'om', 'de', 'Maccausche', 'dravetten', 'daer', 'omtrent', 'te', 'cruijssen', 'Vooren', 'Is', 'geseijdt', 'hoe', 'hier', 'van', 'Teijouhan', 'ende', 'Japan', 'Godtloff', '.', 'abel', 'aengecomen', 'sijn', 'de', 'Schepen', 'Brasimus', 'ende', 'de', 'Vreede', '.', 't', 'Schip', ',', 'de', 'Vreede', 'heel', 'mastelaos', ',', 'sijnde', 'op', '5â', 'Draden', 'bij', 'N.', 'den', 'Aquinoctiael', 'alle', 'de', 'masten', 'ouer', 'boort', 'geblingert', ',', 'ende', 'in', 'groot', 'perijckel', 'geweest', '.', 'hebben', 'door', 'haer', 'verstaen', ',', 'hoe', "d'heere", 'bij', 'geleeft']]

    results = classify_batch(samples)
    for tokens, labels in zip(samples, results):
        if labels is None:
            print(f"{tokens} -> FAILED")
        else:
            print
            #print(list(zip(tokens, labels)))
            print(labels)
    
    with open("gpt5-1_output-few-shot-2.json", "a") as outfile:
        json.dump(results, outfile)