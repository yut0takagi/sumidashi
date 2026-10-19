"""DDD-EVT-01: ドメインイベントの名前が過去形（起きた事実）になっていない。"""

from __future__ import annotations

import re

from . import Ctx, finding, register

_EXCLUDED_SUFFIXES = ("Handler", "Listener", "Subscriber", "Bus", "Dispatcher", "Publisher", "Emitter", "Store", "Queue")
_BASE_NAMES = {"Event", "DomainEvent", "BaseEvent", "IntegrationEvent", "AbstractEvent", "EventBase"}
_ED_NOUNS = {
    "Feed", "Seed", "Need", "Speed", "Bed", "Shed", "Red", "Bread", "Thread", "Breed", "Deed", "Weed",
    "Embed", "Hundred",
}
PAST_IRREGULAR = {
    "Sent", "Paid", "Built", "Made", "Held", "Sold", "Bought", "Brought", "Taken", "Given", "Written",
    "Chosen", "Frozen", "Done", "Begun", "Run", "Won", "Lost", "Found", "Left", "Kept", "Set", "Reset",
    "Put", "Cut", "Shut", "Split", "Read", "Met", "Led", "Told", "Shown", "Known", "Drawn", "Withdrawn",
    "Seen", "Gone", "Spent", "Bound", "Hidden", "Broken", "Forgotten", "Stolen", "Spoken", "Driven",
    "Overridden", "Undone", "Rebuilt", "Resent", "Fed", "Bred", "Sped", "Shed", "Hit", "Quit", "Let",
    "Upset", "Bet", "Cast", "Forecast", "Broadcast", "Thought", "Taught", "Caught", "Fought", "Sought",
    "Felt", "Dealt", "Meant", "Sent", "Lent", "Bent", "Slept", "Swept", "Wept", "Crept", "Fled", "Said",
    "Laid", "Mislaid", "Heard", "Sold", "Told", "Stood", "Understood", "Withstood", "Struck", "Stuck",
    "Hung", "Swung", "Spun", "Won", "Shot", "Got", "Gotten", "Forgot", "Rewritten", "Overwritten",
    "Underwritten", "Eaten", "Fallen", "Shaken", "Woken", "Ridden", "Risen", "Arisen", "Proven", "Sworn",
    "Torn", "Worn", "Born", "Borne", "Thrown", "Grown", "Blown", "Flown", "Mown", "Sewn", "Sown",
    "Begotten", "Bitten", "Hidden", "Slid", "Lit", "Fit", "Rid", "Spread", "Shut", "Burst", "Cost",
    "Hurt", "Outrun", "Overrun", "Rerun", "Remade", "Repaid", "Prepaid", "Overpaid", "Underpaid",
    "Resold", "Reread", "Rebound", "Unbound", "Withheld", "Upheld", "Mistaken", "Retaken", "Overtaken",
    "Undertaken", "Forgiven", "Foreseen", "Overseen", "Unseen", "Redone", "Outdone", "Overdone",
    "Begun", "Sung", "Rung", "Sprung", "Drunk", "Sunk", "Shrunk", "Stunk", "Swum", "Come", "Become",
    "Overcome", "Dug", "Clung", "Flung", "Stung", "Strung", "Wrung", "Kept", "Slain", "Lain",
}
_NOMINAL = ("ion", "ment", "al", "ure", "ance", "ence")
_VERSION = re.compile(r"V\d+$")
_WORD = re.compile(r"[A-Z]+(?=[A-Z][a-z])|[A-Z]?[a-z]+|[A-Z]+|\d+")


def split_words(name: str) -> list[str]:
    return _WORD.findall(name)


def is_past_participle(word: str) -> bool:
    w = word[:1].upper() + word[1:].lower() if not word.isupper() else word.capitalize()
    if w in PAST_IRREGULAR:
        return True
    return w.lower().endswith("ed") and w not in _ED_NOUNS and len(w) > 3


def judge(name: str) -> tuple[str | None, list[str]]:
    """(None・'violation'・'borderline', 調べた語)"""
    stem = name[: -len("Event")] if name.endswith("Event") else name
    stem = _VERSION.sub("", stem)
    words = split_words(stem)
    if not words:
        return None, []
    targets = words if len(words) == 1 else words[1:]
    if any(is_past_participle(w) for w in targets):
        return None, targets
    if words[-1].lower().endswith(_NOMINAL):
        return "borderline", targets
    return "violation", targets


def _is_event_type(cls) -> bool:
    if cls.name in _BASE_NAMES or cls.name.endswith(_EXCLUDED_SUFFIXES):
        return False
    if cls.name.endswith("Event"):
        return True
    if cls.kind in ("class", "abstract_class", "interface"):
        return any(b.endswith("Event") for b in cls.bases)
    return False


@register("ddd_evt_01")
def ddd_evt_01(ctx: Ctx) -> list[dict]:
    out = []
    for mod in ctx.modules_in("domain"):
        for cls in mod.classes:
            if not _is_event_type(cls):
                continue
            verdict, words = judge(cls.name)
            if verdict is None:
                continue
            out.append(finding(
                ctx, "DDD-EVT-01", mod, cls.line,
                verdict=verdict,
                summary=(
                    f"ドメインイベント {cls.name} の名前が過去形になっていない"
                    if verdict == "violation"
                    else f"ドメインイベント {cls.name} の名前が名詞で終わっていて、起きた事実か要求かが読み取れない"
                ),
                facts=[f"調べた語: {', '.join(words)}（過去分詞なし）"],
                suggestion="起きた事実を過去形で表す名前にする（例: OrderPlaced・PaymentCompleted）",
                fix_cost="小（名前の変更。発行側・購読側の参照も直す）",
                impact="イベントが命令や要求と区別できず、購読側が「これから起きること」と誤解する",
                files_to_change=2,
            ))
    return out
