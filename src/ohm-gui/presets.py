from functools import partial
from typing import Any
from typing import Final

from database import DEFAULT_VALUE
from database import find_setting_id
from profiles import process_profile_widgets_block_signals
from profiles import process_profile_widgets_reset
from profiles import process_widget_value_update

PRESET_PLACEHOLDER: Final[str] = "Presets"

PRESET_OVERRIDES: Final[dict] = {
    "Default": {},
    "Power Saving": {
        "CPU:scaling_governor": "powersave",
    },
    "Balanced": {
        "CPU:scaling_governor": "schedutil",
        "Memory:enabled": "madvise",
        "Memory:defrag": "madvise",
    },
    "Performance": {
        "CPU:scaling_governor": "performance",
        "Memory:enabled": "madvise",
        "Memory:defrag": "defer+madvise",
    },
    "Performance Throughput": {
        "CPU:scaling_governor": "performance",
        "Memory:enabled": "always",
        "Memory:defrag": "defer",
    },
}


def get_preset_placeholder_label() -> str:
    return PRESET_PLACEHOLDER


def get_preset_names() -> tuple:
    return tuple(PRESET_OVERRIDES.keys())


def is_valid_preset_name(preset_name: str) -> bool:
    return preset_name in PRESET_OVERRIDES


def build_preset_values(preset_name: str, widget_keys: tuple) -> dict:
    return {
        widget_key: PRESET_OVERRIDES.get(preset_name, {}).get(find_setting_id(widget_key), DEFAULT_VALUE)
        for widget_key in widget_keys}


def process_preset_combo_items(combo_widget: Any) -> None:
    combo_widget.blockSignals(True)
    combo_widget.clear()
    combo_widget.addItem(get_preset_placeholder_label(), get_preset_placeholder_label())
    for preset_name in get_preset_names():
        combo_widget.addItem(preset_name, preset_name)
    combo_widget.blockSignals(False)
    return None


def _widget_dropped(widget_collection: dict, item: tuple) -> bool:
    widget_key, setting_value = item
    match setting_value == DEFAULT_VALUE:
        case True:
            return False
        case False:
            return not process_widget_value_update(widget_collection[widget_key], setting_value)


def _preset_dropped(widget_collection: dict, values: dict) -> tuple:
    dropped = filter(partial(_widget_dropped, widget_collection), values.items())
    return tuple(widget_key for widget_key, _ in dropped)


def process_preset_apply(widget_collection: dict, preset_name: str) -> tuple:
    match is_valid_preset_name(preset_name):
        case False:
            return ()
        case True:
            process_profile_widgets_block_signals(widget_collection, True)
            process_profile_widgets_reset(widget_collection)
            dropped = _preset_dropped(
                widget_collection, build_preset_values(preset_name, tuple(widget_collection)))
            process_profile_widgets_block_signals(widget_collection, False)
            return dropped
