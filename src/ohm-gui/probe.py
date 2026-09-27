import os

from functools import reduce
from math import ceil
from math import floor
from pathlib import Path
from typing import Final
from typing import Optional

PROBE_FILE: Final[str] = "probe.toml"
PROBE_DIR: Final[str] = "~/.config/ohm-gui"
PROBE_SEP: Final[str] = ";"
PAIR_SEP: Final[str] = "="
CHOICES_SUFFIX: Final[str] = ".choices"
BOUNDS_SUFFIX: Final[str] = ".bounds"
UNIT_EPSILON: Final[float] = 1e-9
STEP_DIGITS: Final[int] = 6


def build_probe_path() -> Path:
    return Path(os.path.expanduser(PROBE_DIR)) / PROBE_FILE


def _classify_line(line: str) -> tuple:
    match (line.startswith("["), PAIR_SEP in line, line.startswith("#"), line):
        case (_, _, True, _) | (_, _, _, ""):
            return ("skip",)
        case (True, _, _, _):
            return ("section", line.strip("[]").strip())
        case (False, True, _, _):
            return ("pair",
                    line.split(PAIR_SEP, 1)[0].strip(),
                    line.split(PAIR_SEP, 1)[1].strip().strip('"'))
        case _:
            return ("skip",)


def _with_section(sections: tuple, name: str) -> tuple:
    return sections + ((name, {}),)


def _with_pair(sections: tuple, key: str, value: str) -> tuple:
    match sections:
        case ():
            return ()
        case _:
            return sections[:-1] + ((sections[-1][0], {**sections[-1][1], key: value}),)


def _fold_line(state: tuple, line: str) -> tuple:
    match _classify_line(line.strip()):
        case ("section", name):
            return _with_section(state, name)
        case ("pair", key, value):
            return _with_pair(state, key, value)
        case _:
            return state


def parse_probe_text(text: str) -> tuple:
    return reduce(_fold_line, text.splitlines(), ())


def call_read_probe() -> tuple:
    match build_probe_path().exists():
        case False:
            return ()
        case True:
            return parse_probe_text(build_probe_path().read_text(encoding="utf-8"))


def probe_text(values: dict, key: str) -> str:
    return values.get(key, "")


def probe_list(values: dict, key: str) -> tuple:
    return tuple(v for v in probe_text(values, key).split(PROBE_SEP) if v != "")


def plain_pairs(values: tuple) -> tuple:
    return tuple((v, v) for v in values)


def _low_units(low: float, step: float) -> int:
    return ceil(low / step - UNIT_EPSILON)


def _high_units(high: float, step: float) -> int:
    return floor(high / step + UNIT_EPSILON)


def _step_text(units: int, step: float) -> str:
    match step:
        case int():
            return str(units * step)
        case _:
            return str(round(units * step, STEP_DIGITS))


def stepped_values(low: float, high: float, step: float) -> tuple:
    return tuple(
        _step_text(units, step)
        for units in range(_low_units(low, step), _high_units(high, step) + 1))


def bounds_ladder(low: int, high: int, step: int) -> tuple:
    return tuple(
        str(value)
        for value in dict.fromkeys(
            (low,) + tuple(range((low // step + 1) * step, high, step)) + (high,)))


def _offered_bounds(values: dict, key: str) -> Optional[tuple]:
    match probe_list(values, key + BOUNDS_SUFFIX):
        case (low, high) if low.isdigit() and high.isdigit() and int(low) <= int(high):
            return (int(low), int(high))
        case _:
            return None


def offered_pairs(values: dict, key: str, step: int) -> tuple:
    match (probe_list(values, key + CHOICES_SUFFIX), _offered_bounds(values, key)):
        case ((), None):
            return ()
        case ((), (low, high)):
            return plain_pairs(bounds_ladder(low, high, step))
        case (choices, _):
            return plain_pairs(choices)
