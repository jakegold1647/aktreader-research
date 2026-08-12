"""Additive name-retrieval aids that never rewrite a recorded name.

The first P4 slice is a Daitch-Mokotoff Soundex encoder.  A shared code is a
reason to inspect two spellings, not evidence that they identify one person or
family.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass

_MAX_CODE_LENGTH = 6
_VOWELS = frozenset("aeiou")


@dataclass(frozen=True)
class _Rule:
    pattern: str
    at_start: tuple[str, ...]
    before_vowel: tuple[str, ...]
    otherwise: tuple[str, ...]

    def replacements(self, context: str, *, at_start: bool) -> tuple[str, ...]:
        if at_start:
            return self.at_start
        next_index = len(self.pattern)
        if next_index < len(context) and context[next_index] in _VOWELS:
            return self.before_vowel
        return self.otherwise


@dataclass(frozen=True)
class _Branch:
    code: str = ""
    last_replacement: str | None = None

    def append(self, replacement: str, *, force: bool) -> _Branch:
        code = self.code
        if (
            replacement
            and len(code) < _MAX_CODE_LENGTH
            and (
                force
                or self.last_replacement is None
                or not self.last_replacement.endswith(replacement)
            )
        ):
            code = (code + replacement)[:_MAX_CODE_LENGTH]
        return _Branch(code=code, last_replacement=replacement)


def _alternatives(value: str) -> tuple[str, ...]:
    return tuple(value.split("|"))


def _rule(pattern: str, at_start: str, before_vowel: str, otherwise: str) -> _Rule:
    return _Rule(
        pattern=pattern,
        at_start=_alternatives(at_start),
        before_vowel=_alternatives(before_vowel),
        otherwise=_alternatives(otherwise),
    )


# Daitch-Mokotoff coding chart. Longer patterns are selected before shorter
# ones, so ``szt`` is one sound and is not processed as ``sz`` + ``t``.
_RULES = (
    _rule("a", "0", "", ""),
    _rule("e", "0", "", ""),
    _rule("i", "0", "", ""),
    _rule("o", "0", "", ""),
    _rule("u", "0", "", ""),
    _rule("b", "7", "7", "7"),
    _rule("d", "3", "3", "3"),
    _rule("f", "7", "7", "7"),
    _rule("g", "5", "5", "5"),
    _rule("h", "5", "5", ""),
    _rule("k", "5", "5", "5"),
    _rule("l", "8", "8", "8"),
    _rule("m", "6", "6", "6"),
    _rule("n", "6", "6", "6"),
    _rule("p", "7", "7", "7"),
    _rule("q", "5", "5", "5"),
    _rule("r", "9", "9", "9"),
    _rule("s", "4", "4", "4"),
    _rule("t", "3", "3", "3"),
    _rule("v", "7", "7", "7"),
    _rule("w", "7", "7", "7"),
    _rule("x", "5", "54", "54"),
    _rule("y", "1", "", ""),
    _rule("z", "4", "4", "4"),
    _rule("ţ", "3|4", "3|4", "3|4"),
    _rule("ț", "3|4", "3|4", "3|4"),
    _rule("ę", "", "", "|6"),
    _rule("ą", "", "", "|6"),
    _rule("schtsch", "2", "4", "4"),
    _rule("schtsh", "2", "4", "4"),
    _rule("schtch", "2", "4", "4"),
    _rule("shtch", "2", "4", "4"),
    _rule("shtsh", "2", "4", "4"),
    _rule("stsch", "2", "4", "4"),
    _rule("ttsch", "4", "4", "4"),
    _rule("zhdzh", "2", "4", "4"),
    _rule("shch", "2", "4", "4"),
    _rule("scht", "2", "43", "43"),
    _rule("schd", "2", "43", "43"),
    _rule("stch", "2", "4", "4"),
    _rule("strz", "2", "4", "4"),
    _rule("strs", "2", "4", "4"),
    _rule("stsh", "2", "4", "4"),
    _rule("szcz", "2", "4", "4"),
    _rule("szcs", "2", "4", "4"),
    _rule("ttch", "4", "4", "4"),
    _rule("tsch", "4", "4", "4"),
    _rule("ttsz", "4", "4", "4"),
    _rule("zdzh", "2", "4", "4"),
    _rule("zsch", "4", "4", "4"),
    _rule("chs", "5", "54", "54"),
    _rule("csz", "4", "4", "4"),
    _rule("czs", "4", "4", "4"),
    _rule("drz", "4", "4", "4"),
    _rule("drs", "4", "4", "4"),
    _rule("dsh", "4", "4", "4"),
    _rule("dsz", "4", "4", "4"),
    _rule("dzh", "4", "4", "4"),
    _rule("dzs", "4", "4", "4"),
    _rule("sch", "4", "4", "4"),
    _rule("sht", "2", "43", "43"),
    _rule("szt", "2", "43", "43"),
    _rule("shd", "2", "43", "43"),
    _rule("szd", "2", "43", "43"),
    _rule("tch", "4", "4", "4"),
    _rule("trz", "4", "4", "4"),
    _rule("trs", "4", "4", "4"),
    _rule("tsh", "4", "4", "4"),
    _rule("tts", "4", "4", "4"),
    _rule("ttz", "4", "4", "4"),
    _rule("tzs", "4", "4", "4"),
    _rule("tsz", "4", "4", "4"),
    _rule("zdz", "2", "4", "4"),
    _rule("zhd", "2", "43", "43"),
    _rule("zsh", "4", "4", "4"),
    _rule("ai", "0", "1", ""),
    _rule("aj", "0", "1", ""),
    _rule("ay", "0", "1", ""),
    _rule("au", "0", "7", ""),
    _rule("cz", "4", "4", "4"),
    _rule("cs", "4", "4", "4"),
    _rule("ds", "4", "4", "4"),
    _rule("dz", "4", "4", "4"),
    _rule("dt", "3", "3", "3"),
    _rule("ei", "0", "1", ""),
    _rule("ej", "0", "1", ""),
    _rule("ey", "0", "1", ""),
    _rule("eu", "1", "1", ""),
    _rule("fb", "7", "7", "7"),
    _rule("ia", "1", "", ""),
    _rule("ie", "1", "", ""),
    _rule("io", "1", "", ""),
    _rule("iu", "1", "", ""),
    _rule("ks", "5", "54", "54"),
    _rule("kh", "5", "5", "5"),
    _rule("mn", "66", "66", "66"),
    _rule("nm", "66", "66", "66"),
    _rule("oi", "0", "1", ""),
    _rule("oj", "0", "1", ""),
    _rule("oy", "0", "1", ""),
    _rule("pf", "7", "7", "7"),
    _rule("ph", "7", "7", "7"),
    _rule("sh", "4", "4", "4"),
    _rule("sc", "2", "4", "4"),
    _rule("st", "2", "43", "43"),
    _rule("sd", "2", "43", "43"),
    _rule("sz", "4", "4", "4"),
    _rule("th", "3", "3", "3"),
    _rule("ts", "4", "4", "4"),
    _rule("tc", "4", "4", "4"),
    _rule("tz", "4", "4", "4"),
    _rule("ui", "0", "1", ""),
    _rule("uj", "0", "1", ""),
    _rule("uy", "0", "1", ""),
    _rule("ue", "0", "1", ""),
    _rule("zd", "2", "43", "43"),
    _rule("zh", "4", "4", "4"),
    _rule("zs", "4", "4", "4"),
    _rule("c", "4|5", "4|5", "4|5"),
    _rule("ch", "4|5", "4|5", "4|5"),
    _rule("ck", "5|45", "5|45", "5|45"),
    _rule("rs", "4|94", "4|94", "4|94"),
    _rule("rz", "4|94", "4|94", "4|94"),
    _rule("j", "1|4", "|4", "|4"),
)

_RULES_BY_INITIAL: dict[str, tuple[_Rule, ...]] = {}
for _initial in {rule.pattern[0] for rule in _RULES}:
    _RULES_BY_INITIAL[_initial] = tuple(
        sorted(
            (rule for rule in _RULES if rule.pattern[0] == _initial),
            key=lambda rule: len(rule.pattern),
            reverse=True,
        )
    )

_DIRECT_FOLDINGS = {
    "ß": "s",
    "æ": "a",
    "ð": "d",
    "ø": "o",
    "þ": "b",
    "ł": "l",
}
_PRESERVED_LETTERS = frozenset({"ą", "ę", "ţ", "ț"})
_SUPPORTED_LETTERS = frozenset(_RULES_BY_INITIAL)


def _clean_name(name: str) -> str:
    if not isinstance(name, str):
        raise TypeError("Daitch-Mokotoff input must be a string")

    cleaned: list[str] = []
    for raw_character in unicodedata.normalize("NFC", name).lower():
        if raw_character.isspace() or not raw_character.isalpha():
            continue
        if raw_character in _PRESERVED_LETTERS:
            candidates = raw_character
        elif raw_character in _DIRECT_FOLDINGS:
            candidates = _DIRECT_FOLDINGS[raw_character]
        else:
            candidates = "".join(
                character
                for character in unicodedata.normalize("NFKD", raw_character)
                if not unicodedata.combining(character)
            )
        for character in candidates:
            if character not in _SUPPORTED_LETTERS:
                raise ValueError(
                    "Daitch-Mokotoff currently accepts Latin-script names; "
                    f"transliterate unsupported character {raw_character!r} first"
                )
            cleaned.append(character)

    if not cleaned:
        raise ValueError("Daitch-Mokotoff input must contain a Latin-script letter")
    return "".join(cleaned)


def daitch_mokotoff_codes(name: str) -> tuple[str, ...]:
    """Return every six-digit Daitch-Mokotoff code for ``name``.

    Ambiguous sounds branch into multiple codes. Punctuation and spacing are
    ignored, while unsupported scripts fail closed instead of collapsing to a
    misleading all-zero key.
    """

    cleaned = _clean_name(name)
    branches = (_Branch(),)
    index = 0
    previous_character: str | None = None

    while index < len(cleaned):
        context = cleaned[index:]
        character = cleaned[index]
        rule = next(
            candidate
            for candidate in _RULES_BY_INITIAL[character]
            if context.startswith(candidate.pattern)
        )
        replacements = rule.replacements(context, at_start=index == 0)
        force = (previous_character, character) in {("m", "n"), ("n", "m")}
        next_branches = {
            branch.append(replacement, force=force)
            for branch in branches
            for replacement in replacements
        }
        branches = tuple(
            sorted(
                next_branches,
                key=lambda branch: (branch.code, branch.last_replacement or ""),
            )
        )
        previous_character = rule.pattern[-1]
        index += len(rule.pattern)

    return tuple(sorted({branch.code.ljust(_MAX_CODE_LENGTH, "0") for branch in branches}))
