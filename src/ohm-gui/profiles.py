import os

from functools import partial
from functools import reduce
from pathlib import Path
from typing import Any
from typing import Final

from database import DEFAULT_PROFILE
from database import DEFAULT_VALUE
from database import WIDGET_SEP
from database import build_widget_key
from probe import PROBE_FILE

CONFIG_DIR: Final[str] = "~/.config/ohm-gui"
OPTIONS_FILE: Final[str] = "options.toml"
PROFILE_SUFFIX: Final[str] = ".toml"
PAIR_SEP: Final[str] = " = "
RESERVED_STEMS: Final[tuple] = (
    DEFAULT_PROFILE,
    OPTIONS_FILE.removesuffix(PROFILE_SUFFIX),
    PROBE_FILE.removesuffix(PROFILE_SUFFIX))


def build_config_dir() -> Path:
    return Path(os.path.expanduser(CONFIG_DIR))


def build_profile_path(profile_name: str) -> Path:
    return build_config_dir() / (profile_name + PROFILE_SUFFIX)


def build_options_path() -> Path:
    return build_config_dir() / OPTIONS_FILE


def is_reserved_profile_name(profile_name: str) -> bool:
    return profile_name.strip().lower() in RESERVED_STEMS


def is_profile_file(file_path: Path) -> bool:
    return not is_reserved_profile_name(file_path.stem)


def call_all_profiles() -> tuple:
    match build_config_dir().exists():
        case False:
            return (DEFAULT_PROFILE,)
        case True:
            found = filter(is_profile_file, build_config_dir().glob("*" + PROFILE_SUFFIX))
            return (DEFAULT_PROFILE,) + tuple(sorted(path.stem for path in found))


def _quoted(value: str) -> str:
    return '"' + value + '"'


def _section_of(widget_key: str) -> str:
    return widget_key.partition(WIDGET_SEP)[0]


def _key_of(widget_key: str) -> str:
    return widget_key.partition(WIDGET_SEP)[2]


def _section_lines(values: dict, section: str) -> tuple:
    return ("[" + section + "]",) + tuple(
        _key_of(widget_key) + PAIR_SEP + _quoted(value)
        for widget_key, value in values.items()
        if _section_of(widget_key) == section) + ("",)


def serialize_profile(values: dict) -> str:
    return "\n".join(
        line
        for section in dict.fromkeys(map(_section_of, values))
        for line in _section_lines(values, section))


def _classify_line(line: str) -> tuple:
    match (line.startswith("["), PAIR_SEP.strip() in line, line.startswith("#"), line):
        case (_, _, True, _) | (_, _, _, ""):
            return ("skip",)
        case (True, _, _, _):
            return ("section", line.strip("[]").strip())
        case (False, True, _, _):
            return ("pair", line.split("=", 1)[0].strip(), line.split("=", 1)[1].strip().strip('"'))
        case _:
            return ("skip",)


def _fold_line(state: tuple, line: str) -> tuple:
    match _classify_line(line.strip()):
        case ("section", name):
            return (name, state[1])
        case ("pair", key, value):
            return (state[0], state[1] + ((build_widget_key(state[0], key), value),))
        case _:
            return state


def parse_profile_text(text: str) -> dict:
    return dict(reduce(_fold_line, text.splitlines(), ("", ()))[1])


def widget_value(widget: Any) -> str:
    match widget.currentData():
        case None:
            return DEFAULT_VALUE
        case data:
            return data


def process_widget_value_update(widget: Any, display_value: str) -> bool:
    match widget.findData(display_value):
        case -1:
            widget.setCurrentIndex(0)
            return False
        case index:
            widget.setCurrentIndex(index)
            return True


def process_profile_widgets_block_signals(widget_collection: dict, should_block: bool) -> None:
    for widget in widget_collection.values():
        widget.blockSignals(should_block)
    return None


def process_profile_widgets_reset(widget_collection: dict) -> None:
    for widget in widget_collection.values():
        widget.setCurrentIndex(0)
    return None


def collect_widget_values(widget_collection: dict) -> dict:
    return {
        widget_key: widget_value(widget)
        for widget_key, widget in widget_collection.items()}


def call_read_profile(profile_name: str) -> dict:
    match build_profile_path(profile_name).exists():
        case False:
            return {}
        case True:
            return parse_profile_text(build_profile_path(profile_name).read_text(encoding="utf-8"))


def _dropped(widget_collection: dict, item: tuple) -> bool:
    widget_key, value = item
    match (value == DEFAULT_VALUE, widget_collection.get(widget_key)):
        case (True, _):
            return False
        case (False, None):
            return True
        case (False, widget):
            return not process_widget_value_update(widget, value)


def process_profile_widget_load(widget_collection: dict, profile_name: str) -> tuple:
    process_profile_widgets_block_signals(widget_collection, True)
    process_profile_widgets_reset(widget_collection)
    dropped = tuple(
        widget_key
        for widget_key, _ in filter(
            partial(_dropped, widget_collection), call_read_profile(profile_name).items()))
    process_profile_widgets_block_signals(widget_collection, False)
    return dropped


def call_write_profile(values: dict, profile_name: str) -> None:
    build_config_dir().mkdir(parents=True, exist_ok=True)
    build_profile_path(profile_name).write_text(serialize_profile(values), encoding="utf-8")
    return None


def process_profile_save(widget_collection: dict, profile_name: str) -> None:
    call_write_profile(collect_widget_values(widget_collection), profile_name)
    return None


def process_profile_delete(profile_name: str) -> bool:
    match (profile_name == DEFAULT_PROFILE, build_profile_path(profile_name).exists()):
        case (True, _) | (_, False):
            return False
        case (False, True):
            build_profile_path(profile_name).unlink()
            return True
