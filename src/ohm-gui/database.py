from fnmatch import fnmatchcase
from functools import partial
from typing import Final

from probe import call_read_probe
from probe import offered_pairs
from probe import plain_pairs
from probe import stepped_values


APP_VERSION: Final[str] = "0.1.0"
APP_AUTHOR: Final[str] = "pythonlover02"
APP_LICENSE: Final[str] = "GPL 3.0 License"
APP_DESCRIPTION: Final[str] = "My Linux Kernel Settings Modifier"

DEFAULT_VALUE: Final[str] = "default"
DEFAULT_PROFILE: Final[str] = "default"
DEFAULT_STEP: Final[int] = 1
GLOBAL_INSTANCE: Final[str] = "global"
SECTION_SEP: Final[str] = "."
WIDGET_SEP: Final[str] = ":"
TAG_OPEN: Final[str] = " ("
TAG_CLOSE: Final[str] = ")"

TAB_CATEGORIES: Final[dict] = {"CPU": "cpu", "Memory": "memory", "Disk": "disk", "PCIe": "pcie", "Network": "network"}
PROFILE_TABS: Final[tuple] = tuple(TAB_CATEGORIES)
ALL_TABS: Final[tuple] = PROFILE_TABS + ("Options", "About")
SCALE_LOW: Final[float] = 0.8
SCALE_HIGH: Final[float] = 2.0


SETTINGS_DB: Final[dict] = {
    "CPU": {
        "current_governor": {
            "instance": GLOBAL_INSTANCE,
            "key": "current_governor",
            "label": "Idle Governor",
            "description": "How deeply a core sleeps when there is nothing to run. A deeper sleep saves more power and takes longer to wake from, and this picks who makes that call. teo guesses from a longer history than menu; ladder just steps down one level at a time.",
        },
        "scaling_governor": {
            "instance": "policy*",
            "key": "scaling_governor",
            "label": "Governor",
            "description": "How this core picks its clock. performance holds the top speed and burns power for it, powersave holds the bottom, and the rest read the load and move between them. schedutil reads the scheduler's own figure, so it reacts fastest. One card per policy: cores that share a clock share a policy, and the kernel decides which.",
        },
        "scaling_min_freq": {
            "instance": "policy*",
            "key": "scaling_min_freq",
            "step": 1000,
            "label": "Minimum Frequency",
            "description": "The slowest this core may run, in kHz. Raising it cuts the time spent waking up from idle and costs power the whole time. Cannot go above the maximum.",
        },
        "scaling_max_freq": {
            "instance": "policy*",
            "key": "scaling_max_freq",
            "step": 1000,
            "label": "Maximum Frequency",
            "description": "The fastest this core may run, in kHz. Lowering it caps heat and noise and costs you the top of the clock range. Cannot go below the minimum.",
        },
    },
    "Memory": {
        "enabled": {
            "instance": GLOBAL_INSTANCE,
            "key": "enabled",
            "label": "Huge Pages",
            "description": "Back memory with large pages instead of many small ones. Fewer address lookups, at the cost of stalling while the kernel finds a large page free. always uses them everywhere, madvise only where a program asked for them, never turns them off.",
        },
        "defrag": {
            "instance": GLOBAL_INSTANCE,
            "key": "defrag",
            "label": "Huge Page Defrag",
            "description": "What happens when no large page is free. always waits while the kernel makes one, which is where huge pages cost you a stutter. defer hands out small pages now and compacts in the background, never gives up immediately. Only does something where Huge Pages is on.",
        },
        "shmem_enabled": {
            "instance": GLOBAL_INSTANCE,
            "key": "shmem_enabled",
            "label": "Huge Pages For Shared Memory",
            "description": "The same for shared memory and tmpfs, which is where a game's shader cache and /dev/shm live. within_size only uses a large page where the mapping is big enough to fill it.",
        },
        "hugepages_enabled": {
            "instance": "hugepages-*",
            "key": "enabled",
            "label": "Huge Pages",
            "description": "Huge pages at this size specifically. inherit follows the setting above it, which is where most sizes should stay: your CPU only has hardware for one or two of these.",
        },
        "hugepages_shmem_enabled": {
            "instance": "hugepages-*",
            "key": "shmem_enabled",
            "label": "Huge Pages For Shared Memory",
            "description": "Shared memory huge pages at this size specifically. inherit follows the setting above it.",
        },
    },
    "Disk": {
        "scheduler": {
            "instance": "*",
            "key": "scheduler",
            "label": "I/O Scheduler",
            "description": "How reads and writes are ordered before they reach this drive. none sends them straight through, which suits an SSD that reorders on its own. mq-deadline stops any one request waiting forever, bfq shares bandwidth between processes so a background copy cannot starve a game. One card per drive.",
        },
    },
    "PCIe": {
        "aspm_policy": {
            "instance": GLOBAL_INSTANCE,
            "key": "policy",
            "label": "PCIe Power Policy",
            "description": "How eagerly PCIe links drop into low-power states between transfers. performance keeps them awake, which trims latency on the GPU and NVMe links and costs a little power. powersave and powersupersave sleep them sooner. Some firmware keeps this for itself, and there the write is refused.",
        },
    },
    "Network": {
        "tcp_congestion_control": {
            "instance": GLOBAL_INSTANCE,
            "key": "tcp_congestion_control",
            "label": "TCP Congestion Control",
            "description": "How a TCP connection backs off when the network gets busy. cubic is the long-standing choice, bbr measures the path and keeps queues short, which helps downloads on a loaded link. Games mostly talk UDP, so this moves launchers and downloads rather than the game itself. The list is what this kernel has loaded.",
        },
    },
}

OPTIONS_DB: Final[dict] = {
    "application_theme": {
        "label": "Application Theme",
        "description": "Color theme for the application. default is cachyos. Takes effect on program restart.",
        "options": (DEFAULT_VALUE, "cachyos", "amd", "intel", "nvidia"),
        "fallback": "cachyos",
    },
    "qt_platform": {
        "label": "Display Backend Preference",
        "description": "Which Qt platform plugin the interface prefers. default lets Qt pick: wayland on a Wayland session, xcb on X11. Either choice falls back to the other where the one you pick is unavailable, so xcb on a session without XWayland still opens a window. Takes effect on program restart.",
        "options": (DEFAULT_VALUE, "xcb", "wayland"),
        "fallback": "",
    },
    "window_transparency": {
        "label": "Window Transparency",
        "description": "Window background transparency. default is off. Only does something under xcb: Wayland has no window opacity protocol, so set Display Backend Preference to xcb for this to land. Takes effect on program restart.",
        "options": (DEFAULT_VALUE, "on", "off"),
        "fallback": "off",
    },
    "interface_scale_factor": {
        "label": "Interface Scale Factor",
        "description": "UI scaling multiplier, in steps of 0.1. default is 1.0. Takes effect on program restart.",
        "step": 0.1,
        "options": (DEFAULT_VALUE,),
        "fallback": "1.0",
    },
    "start_window_maximized": {
        "label": "Start Window Maximized",
        "description": "Start the window in maximized state. default is off. Takes effect on program restart.",
        "options": (DEFAULT_VALUE, "on", "off"),
        "fallback": "off",
    },
    "start_window_minimized": {
        "label": "Start Window Minimized",
        "description": "Start the window minimized to tray. default is off. Takes effect on program restart.",
        "options": (DEFAULT_VALUE, "on", "off"),
        "fallback": "off",
    },
    "system_tray_behavior": {
        "label": "System Tray",
        "description": "Show icon in the system tray. default is off. Takes effect on program restart.",
        "options": (DEFAULT_VALUE, "on", "off"),
        "fallback": "off",
    },
    "welcome_message_display": {
        "label": "Welcome Message",
        "description": "Show the welcome message on startup. default is on. Takes effect on program restart.",
        "options": (DEFAULT_VALUE, "on", "off"),
        "fallback": "on",
    },

}


def _scale_options(step: float) -> tuple:
    return stepped_values(SCALE_LOW, SCALE_HIGH, step)


STEPPED_OPTIONS: Final[dict] = {
    "interface_scale_factor": _scale_options,
}


ACCENT_COLORS: Final[dict] = {
    "amd": ("#E31937", "#FF2D4A", "#B81430"),
    "intel": ("#0068B5", "#1A8CFF", "#004D87"),
    "nvidia": ("#76B900", "#8ED11A", "#5A8F00"),
}
DEFAULT_ACCENT: Final[tuple] = ("#80dbcb", "#9ae4d8", "#66b0a2")


def find_settings_for_tab(tab_name: str) -> dict:
    return SETTINGS_DB.get(tab_name, {})


def find_category_tab(category: str) -> str:
    return next((tab_name for tab_name, held in TAB_CATEGORIES.items() if held == category), "")


def split_section(section: str) -> tuple:
    return tuple(section.partition(SECTION_SEP)[0::2])


def build_widget_key(section: str, key: str) -> str:
    return section + WIDGET_SEP + key


def split_widget_key(widget_key: str) -> tuple:
    return tuple(widget_key.partition(WIDGET_SEP)[0::2])


def build_setting_id(tab_name: str, setting_name: str) -> str:
    return tab_name + WIDGET_SEP + setting_name


def is_setting_for(setting: dict, instance: str) -> bool:
    match (setting["instance"] == GLOBAL_INSTANCE, instance == ""):
        case (True, True):
            return True
        case (False, False):
            return fnmatchcase(instance, setting["instance"])
        case _:
            return False


def find_section_settings(tab_name: str, instance: str) -> tuple:
    return tuple(
        setting_name for setting_name, setting in find_settings_for_tab(tab_name).items()
        if is_setting_for(setting, instance))


def find_setting_id(widget_key: str) -> str:
    section, key = split_widget_key(widget_key)
    category, instance = split_section(section)
    tab_name = find_category_tab(category)
    return next(
        (build_setting_id(tab_name, setting_name)
         for setting_name in find_section_settings(tab_name, instance)
         if SETTINGS_DB[tab_name][setting_name]["key"] == key),
        "")


def build_card_label(label: str, instance: str) -> str:
    match instance == "":
        case True:
            return label
        case False:
            return label + TAG_OPEN + instance + TAG_CLOSE


def build_setting_options(values: dict, setting: dict) -> tuple:
    return ((DEFAULT_VALUE, DEFAULT_VALUE),) + tuple(
        pair for pair in offered_pairs(values, setting["key"], setting.get("step", DEFAULT_STEP))
        if pair[0] != DEFAULT_VALUE)


def build_setting_card(tab_name: str, section: str, values: dict, setting_name: str) -> tuple:
    setting = SETTINGS_DB[tab_name][setting_name]
    return (
        build_widget_key(section, setting["key"]),
        build_card_label(setting["label"], split_section(section)[1]),
        setting["description"],
        build_setting_options(values, setting))


def _in_category(category: str, entry: tuple) -> bool:
    return split_section(entry[0])[0] == category


def _is_instance_section(entry: tuple) -> bool:
    return split_section(entry[0])[1] != ""


def find_category_sections(data: tuple, category: str) -> tuple:
    return tuple(sorted(filter(partial(_in_category, category), data), key=_is_instance_section))


def find_cards_for_tab(tab_name: str, data: tuple) -> tuple:
    return tuple(
        build_setting_card(tab_name, section, values, setting_name)
        for section, values in find_category_sections(data, TAB_CATEGORIES.get(tab_name, ""))
        for setting_name in find_section_settings(tab_name, split_section(section)[1]))


def call_cards_for_tab(tab_name: str) -> tuple:
    return find_cards_for_tab(tab_name, call_read_probe())


def get_option_label(option_key: str) -> str:
    return OPTIONS_DB[option_key]["label"]


def get_option_description(option_key: str) -> str:
    return OPTIONS_DB[option_key]["description"]


def get_option_step(option_key: str) -> float:
    return OPTIONS_DB[option_key]["step"]


def get_option_options(option_key: str) -> tuple:
    match STEPPED_OPTIONS.get(option_key):
        case None:
            return plain_pairs(OPTIONS_DB[option_key]["options"])
        case stepped:
            return plain_pairs(
                OPTIONS_DB[option_key]["options"] + stepped(get_option_step(option_key)))


def get_option_default_value(option_key: str) -> str:
    return OPTIONS_DB[option_key]["options"][0]


def get_option_fallback(option_key: str) -> str:
    return OPTIONS_DB[option_key]["fallback"]


def _option_is_unset(raw_value: str) -> bool:
    return raw_value in ("", DEFAULT_VALUE)


def resolve_option_value(option_key: str, raw_value: str) -> str:
    match _option_is_unset(raw_value):
        case True:
            return get_option_fallback(option_key)
        case False:
            return raw_value


def get_accent_colors(theme_name: str) -> tuple:
    return ACCENT_COLORS.get(theme_name, DEFAULT_ACCENT)


def get_about_data() -> dict:
    return {
        "Description": APP_DESCRIPTION,
        "License": APP_LICENSE,
        "Author": APP_AUTHOR,
        "Version": APP_VERSION,
    }
