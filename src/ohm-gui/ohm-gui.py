import configparser
import os
import shutil
import signal
import socket
import subprocess
import sys

from functools import partial
from typing import Final
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtCore import QTimer
from PySide6.QtGui import QAction
from PySide6.QtGui import QCloseEvent
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication
from PySide6.QtWidgets import QDialogButtonBox
from PySide6.QtWidgets import QFrame
from PySide6.QtWidgets import QHBoxLayout
from PySide6.QtWidgets import QInputDialog
from PySide6.QtWidgets import QLabel
from PySide6.QtWidgets import QMainWindow
from PySide6.QtWidgets import QMenu
from PySide6.QtWidgets import QMessageBox
from PySide6.QtWidgets import QPushButton
from PySide6.QtWidgets import QSizePolicy
from PySide6.QtWidgets import QStackedWidget
from PySide6.QtWidgets import QSystemTrayIcon
from PySide6.QtWidgets import QVBoxLayout
from PySide6.QtWidgets import QWidget

from database import ALL_TABS
from database import DEFAULT_PROFILE
from database import DEFAULT_VALUE
from database import OPTIONS_DB
from database import SECTION_SEP
from database import WIDGET_SEP
from database import get_about_data
from database import get_option_default_value
from database import get_option_description
from database import get_option_label
from database import get_option_options
from database import resolve_option_value
from presets import process_preset_combo_items
from presets import get_preset_placeholder_label
from presets import is_valid_preset_name
from presets import process_preset_apply
from profiles import build_config_dir
from profiles import build_options_path
from profiles import call_all_profiles
from profiles import is_reserved_profile_name
from profiles import process_profile_delete
from profiles import process_profile_save
from profiles import process_profile_widget_load
from themes import STANDARD_BUTTON_HEIGHT
from themes import STANDARD_BUTTON_WIDTH
from themes import process_theme_application
from ui import create_slider_widget
from ui import create_scrollable_content_area
from ui import create_tab_content_widget
from ui import create_sidebar_container_widget
from ui import STYLE_DESCRIPTION
from ui import WINDOW_MIN_HEIGHT
from ui import WINDOW_MIN_WIDTH
from welcome import create_welcome_window_widget

SINGLETON_PORT: Final[int] = 47832
OPTIONS_SAVE_DEBOUNCE_MS: Final[int] = 500
NEW_PROFILE_LABEL: Final[str] = "New"
SUBMENU_TITLE: Final[str] = "Apply Profile   "
DELETE_PROFILE_LABEL: Final[str] = "Delete"
SELECTOR_MIN_WIDTH: Final[int] = 120
SELECTOR_STRETCH: Final[int] = 1
DEFAULT_PROFILE_LABEL: Final[str] = "Default"
SCALE_MIN: Final[float] = 0.8
SCALE_MAX: Final[float] = 2.0
DEFAULT_SCALE: Final[str] = "1.0"
GRAPHIC_FIRST: Final[int] = 33
GRAPHIC_LAST: Final[int] = 126
WINDOW_OPACITY: Final[float] = 0.95
WINDOW_OPAQUE: Final[float] = 1.0
WELCOME_DELAY_MS: Final[int] = 100
SHOW_DELAY_MS: Final[int] = 0
NOTICE_DELAY_MS: Final[int] = 200
TRAY_ICON_NAME: Final[str] = "ohm-gui"
NOTIFICATION_TITLE: Final[str] = "ohm-gui"
PROBE_BIN: Final[str] = "ohm-probe"
ROOT_BIN: Final[str] = "ohm"
PKEXEC_BIN: Final[str] = "pkexec"
RESTORE_WORD: Final[str] = "restore"
ORIGINALS_PATH: Final[str] = "/run/ohm/originals.toml"
REPORT_PREFIX: Final[str] = "[ohm] "
PROBE_EXIT_OK: Final[int] = 0
ROOT_EXIT_OK: Final[int] = 0
PKEXEC_DISMISSED: Final[int] = 126
PKEXEC_REFUSED: Final[int] = 127
ROOT_MISSING: Final[int] = -1
BUNDLE_ATTR: Final[str] = "_MEIPASS"
LIB_PATH_VAR: Final[str] = "LD_LIBRARY_PATH"
LIB_PATH_ORIG: Final[str] = "LD_LIBRARY_PATH_ORIG"
PRELOAD_VAR: Final[str] = "LD_PRELOAD"
PATH_VAR: Final[str] = "PATH"
PROBE_FAILED_ERROR: Final[str] = "ohm-probe failed to run.\n\nWithout it ohm-gui cannot read your kernel, so every card holds nothing but default.\n\nohm-probe installs next to ohm and ohm-gui. Check that their directory is on your PATH, then restart ohm-gui."
ROOT_MISSING_ERROR: Final[str] = "pkexec or ohm is not on your PATH, so nothing was written.\n\nohm installs next to ohm-gui, and pkexec comes with polkit."
APPLY_CANCELLED: Final[str] = "The password prompt was dismissed, nothing was written."
APPLY_REFUSED: Final[str] = "polkit refused to run ohm, nothing was written."
APPLY_FAILED: Final[str] = "ohm stopped before writing anything."


def build_profile_label(profile_name: str) -> str:
    match profile_name == DEFAULT_PROFILE:
        case True:
            return DEFAULT_PROFILE_LABEL
        case False:
            return profile_name


def resolve_profile_label(label: str) -> str:
    match label == DEFAULT_PROFILE_LABEL:
        case True:
            return DEFAULT_PROFILE
        case False:
            return label


def call_persisted_option_value(option_key: str) -> str:
    match build_options_path().exists():
        case False:
            return get_option_default_value(option_key)
        case True:
            parser_instance = configparser.ConfigParser(interpolation=None)
            parser_instance.read(build_options_path())
            saved = parser_instance.get("Options", option_key, fallback="").strip()
            match saved == "":
                case True:
                    return get_option_default_value(option_key)
                case False:
                    return saved


def is_scale_text(raw: str) -> bool:
    return raw.replace(".", "", 1).isdigit()


def resolve_scale_factor(raw: str) -> str:
    match is_scale_text(raw) and SCALE_MIN <= float(raw) <= SCALE_MAX:
        case True:
            return raw
        case False:
            return DEFAULT_SCALE


def call_persisted_option_resolved(option_key: str) -> str:
    return resolve_option_value(option_key, call_persisted_option_value(option_key))


def get_bundle_dir() -> str:
    return getattr(sys, BUNDLE_ATTR, "")


def _outside_bundle(bundle: str, entry: str) -> bool:
    return bundle not in entry


def _cleaned_path(value: str, bundle: str) -> str:
    return os.pathsep.join(
        filter(partial(_outside_bundle, bundle), value.split(os.pathsep)))


def call_restore_lib_path() -> None:
    match os.environ.pop(LIB_PATH_ORIG, ""):
        case "":
            os.environ.pop(LIB_PATH_VAR, None)
        case original:
            os.environ[LIB_PATH_VAR] = original
    return None


def call_drop_bundle_vars() -> None:
    call_restore_lib_path()
    os.environ.pop(PRELOAD_VAR, None)
    return None


def call_clean_path(bundle: str) -> None:
    os.environ[PATH_VAR] = _cleaned_path(os.environ.get(PATH_VAR, ""), bundle)
    return None


def call_unbundle_environment(bundle: str) -> None:
    call_drop_bundle_vars()
    call_clean_path(bundle)
    return None


def call_clean_environment() -> None:
    match get_bundle_dir():
        case "":
            return None
        case bundle:
            call_unbundle_environment(bundle)
            return None


def process_initial_scale() -> None:
    os.environ["QT_SCALE_FACTOR"] = resolve_scale_factor(
        call_persisted_option_resolved("interface_scale_factor"))
    return None


def build_platform_chain(platform: str) -> str:
    match platform:
        case "xcb":
            return "xcb;wayland"
        case "wayland":
            return "wayland;xcb"
        case other:
            return other


def process_initial_platform() -> None:
    match call_persisted_option_resolved("qt_platform"):
        case "":
            return None
        case platform:
            os.environ.setdefault("QT_QPA_PLATFORM", build_platform_chain(platform))
            return None


def get_widget_option_text(main_window: QMainWindow, option_key: str) -> str:
    match main_window.options_widgets.get(option_key):
        case None:
            return DEFAULT_VALUE
        case widget:
            return widget.currentText().strip()


def get_resolved_option_value(main_window: QMainWindow, option_key: str) -> str:
    return resolve_option_value(option_key, get_widget_option_text(main_window, option_key))


def is_option_enabled(main_window: QMainWindow, option_key: str) -> bool:
    return get_resolved_option_value(main_window, option_key) == "on"


def create_options_tab_widget() -> dict:
    widget = QWidget()
    options_widgets = {}
    main_layout = QVBoxLayout(widget)
    main_layout.setContentsMargins(0, 0, 0, 0)
    main_layout.setSpacing(0)
    container_widget = QWidget()
    container_widget.setProperty("scrollContainer", True)
    content_layout = QVBoxLayout(container_widget)
    content_layout.setSpacing(6)
    content_layout.setContentsMargins(12, 12, 8, 12)
    for option_key in OPTIONS_DB:
        card = QFrame()
        card.setProperty("settingCard", True)
        card.setFrameStyle(QFrame.Box)
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(14, 10, 14, 10)
        card_layout.setSpacing(4)
        title_label = QLabel(get_option_label(option_key))
        title_label.setStyleSheet("font-weight: 500; font-size: 11pt;")
        card_layout.addWidget(title_label)
        slider = create_slider_widget(get_option_options(option_key))
        card_layout.addWidget(slider)
        description_label = QLabel(get_option_description(option_key))
        description_label.setWordWrap(True)
        description_label.setStyleSheet(STYLE_DESCRIPTION)
        card_layout.addWidget(description_label)
        content_layout.addWidget(card)
        options_widgets[option_key] = slider
    main_layout.addWidget(create_scrollable_content_area(container_widget), 1)
    return {"tab": widget, "widgets": options_widgets}


def process_profile_list_update(main_window: QMainWindow) -> None:
    main_window.profile_selector.blockSignals(True)
    main_window.profile_selector.clear()
    for profile_name in call_all_profiles():
        main_window.profile_selector.addItem(build_profile_label(profile_name), profile_name)
    main_window.profile_selector.blockSignals(False)
    return None


def process_profile_selector_restore(main_window: QMainWindow) -> None:
    main_window.profile_selector.blockSignals(True)
    main_window.profile_selector.setCurrentText(build_profile_label(main_window.current_profile))
    main_window.profile_selector.blockSignals(False)
    return None


def process_profile_change(main_window: QMainWindow, profile_name: str) -> None:
    match getattr(main_window, "initial_setup_complete", False):
        case False:
            return None
        case True:
            process_profile_save(main_window.all_widgets, main_window.current_profile)
            main_window.current_profile = profile_name
            process_dropped_notice(
                main_window,
                process_profile_widget_load(main_window.all_widgets, profile_name))
            process_tray_menu_update(main_window)
            return None


def process_yes_no_dialog(parent_widget: QMainWindow, title: str, message: str) -> bool:
    dialog = QMessageBox(parent_widget)
    dialog.setWindowTitle(title)
    dialog.setText(message)
    dialog.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
    button_box = dialog.findChild(QDialogButtonBox)
    match button_box is None:
        case False:
            button_box.setCenterButtons(True)
        case True:
            pass
    return dialog.exec() == QMessageBox.Yes


def is_graphic_ascii(profile_name: str) -> bool:
    return all(GRAPHIC_FIRST <= ord(character) <= GRAPHIC_LAST for character in profile_name)


def call_new_profile_name_valid(profile_name: str) -> bool:
    match (
        profile_name.strip() == "",
        is_reserved_profile_name(profile_name),
        profile_name.strip() in call_all_profiles(),
        "/" in profile_name or "\\" in profile_name or ".." in profile_name,
        "\0" in profile_name,
        is_graphic_ascii(profile_name),
    ):
        case (False, False, False, False, False, True):
            return True
        case _:
            return False


def process_new_profile_save(main_window: QMainWindow) -> None:
    profile_name, accepted = QInputDialog.getText(main_window, "New Profile", "Profile name:")
    match (accepted, profile_name is not None and call_new_profile_name_valid(profile_name)):
        case (True, True):
            process_profile_save(main_window.all_widgets, main_window.current_profile)
            main_window.current_profile = profile_name.strip()
            process_profile_save(main_window.all_widgets, profile_name.strip())
            process_profile_list_update(main_window)
            process_profile_selector_restore(main_window)
            process_tray_menu_update(main_window)
            process_notification_display(main_window, "Profile '" + profile_name.strip() + "' created.")
            return None
        case (True, False):
            process_notification_display(main_window, "Profile name invalid or already exists.")
            return None
        case _:
            return None


def process_current_profile_delete(main_window: QMainWindow) -> None:
    match main_window.current_profile == DEFAULT_PROFILE:
        case True:
            process_notification_display(main_window, "Cannot delete default profile.")
            return None
        case False:
            match process_yes_no_dialog(main_window, "Delete Profile", "Delete profile '" + main_window.current_profile + "'?"):
                case False:
                    return None
                case True:
                    process_profile_delete(main_window.current_profile)
                    main_window.current_profile = DEFAULT_PROFILE
                    process_profile_list_update(main_window)
                    process_profile_selector_restore(main_window)
                    process_dropped_notice(
                        main_window,
                        process_profile_widget_load(main_window.all_widgets, DEFAULT_PROFILE))
                    process_tray_menu_update(main_window)
                    process_notification_display(main_window, "Profile deleted.")
                    return None


def process_preset_combo_change(main_window: QMainWindow, selected_text: str) -> None:
    match (selected_text == get_preset_placeholder_label(), is_valid_preset_name(selected_text)):
        case (True, _):
            return None
        case (False, False):
            process_preset_combo_items(main_window.preset_selector)
            return None
        case (False, True):
            match process_yes_no_dialog(main_window, "Apply Preset", "Apply '" + selected_text + "' to '" + main_window.current_profile + "'? All values will be replaced."):
                case True:
                    dropped = process_preset_apply(main_window.all_widgets, selected_text)
                    process_profile_save(main_window.all_widgets, main_window.current_profile)
                    process_notification_display(main_window, "Preset '" + selected_text + "' applied to profile '" + main_window.current_profile + "'.")
                    process_dropped_notice(main_window, dropped)
                case False:
                    pass
            process_preset_combo_items(main_window.preset_selector)
            return None


def create_system_tray_widget(main_window: QMainWindow) -> None:
    match QSystemTrayIcon.isSystemTrayAvailable():
        case False:
            return None
        case True:
            main_window.tray_icon = QSystemTrayIcon(main_window)
            main_window.tray_icon.setIcon(QIcon.fromTheme(TRAY_ICON_NAME))
            menu = QMenu()
            menu.addAction(QAction("Show", main_window, triggered=lambda: process_window_show(main_window)))
            main_window.profile_submenu = QMenu(SUBMENU_TITLE, menu)
            process_tray_menu_update(main_window)
            menu.addMenu(main_window.profile_submenu)
            menu.addSeparator()
            menu.addAction(QAction("Quit", main_window, triggered=lambda: process_application_quit(main_window)))
            main_window.tray_icon.setContextMenu(menu)
            main_window.tray_icon.show()
            main_window.tray_icon.activated.connect(lambda activation_reason: process_tray_activation(main_window, activation_reason))
            return None


def process_tray_menu_update(main_window: QMainWindow) -> None:
    match hasattr(main_window, "profile_submenu"):
        case False:
            return None
        case True:
            main_window.profile_submenu.clear()
            for profile_name in call_all_profiles():
                action = QAction("Apply " + build_profile_label(profile_name), main_window)
                action.triggered.connect(lambda checked, bound_profile_name=profile_name: process_profile_apply_from_tray(main_window, bound_profile_name))
                main_window.profile_submenu.addAction(action)
            return None


def process_tray_activation(main_window: QMainWindow, activation_reason: QSystemTrayIcon.ActivationReason) -> None:
    match activation_reason in (QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick):
        case False:
            return None
        case True:
            match main_window.isVisible():
                case True:
                    main_window.hide()
                case False:
                    process_window_show(main_window)
            return None


def process_window_show(main_window: QMainWindow) -> None:
    match main_window.start_maximized:
        case True:
            main_window.showMaximized()
        case False:
            main_window.show()
    main_window.activateWindow()
    main_window.raise_()
    return None


def process_profile_apply_from_tray(main_window: QMainWindow, profile_name: str) -> None:
    match profile_name != main_window.current_profile:
        case True:
            process_profile_save(main_window.all_widgets, main_window.current_profile)
            main_window.current_profile = profile_name
            process_profile_selector_restore(main_window)
            process_dropped_notice(
                main_window,
                process_profile_widget_load(main_window.all_widgets, profile_name))
        case False:
            pass
    process_all_settings_apply(main_window)
    return None


def process_notification_display(main_window: QMainWindow, notification_message: str, details: str = "") -> None:
    dialog = QMessageBox(main_window)
    dialog.setWindowTitle(NOTIFICATION_TITLE)
    dialog.setText(notification_message)
    dialog.setIcon(QMessageBox.NoIcon)
    dialog.setStandardButtons(QMessageBox.Ok)
    match details == "":
        case True:
            pass
        case False:
            dialog.setDetailedText(details)
    dialog.exec()
    return None


def process_tray_option_update(main_window: QMainWindow, tray_enabled: bool) -> None:
    match (main_window.use_system_tray == tray_enabled, tray_enabled, hasattr(main_window, "tray_icon")):
        case (True, _, _):
            main_window.use_system_tray = tray_enabled
        case (False, True, False):
            main_window.use_system_tray = tray_enabled
            create_system_tray_widget(main_window)
        case (False, False, True):
            main_window.use_system_tray = tray_enabled
            main_window.tray_icon.hide()
            main_window.tray_icon.deleteLater()
            delattr(main_window, "tray_icon")
            match main_window.isVisible():
                case False:
                    process_window_show(main_window)
                case True:
                    pass
        case _:
            main_window.use_system_tray = tray_enabled
    match QApplication.instance() is None:
        case False:
            QApplication.instance().setQuitOnLastWindowClosed(not main_window.use_system_tray)
        case True:
            pass
    return None


def process_options_application(main_window: QMainWindow) -> None:
    process_theme_application(QApplication.instance(), get_resolved_option_value(main_window, "application_theme"))
    match (is_option_enabled(main_window, "window_transparency"),
           QApplication.instance().platformName()):
        case (True, "xcb"):
            main_window.setWindowOpacity(WINDOW_OPACITY)
        case _:
            main_window.setWindowOpacity(WINDOW_OPAQUE)
    process_tray_option_update(main_window, is_option_enabled(main_window, "system_tray_behavior"))
    main_window.start_minimized = is_option_enabled(main_window, "start_window_minimized")
    main_window.start_maximized = is_option_enabled(main_window, "start_window_maximized")
    main_window.show_welcome = is_option_enabled(main_window, "welcome_message_display")
    return None


def process_options_save_timer_trigger(main_window: QMainWindow) -> None:
    match getattr(main_window, "options_save_timer", None):
        case None:
            main_window.options_save_timer = QTimer(main_window)
            main_window.options_save_timer.setSingleShot(True)
            main_window.options_save_timer.timeout.connect(lambda: process_application_options_save(main_window))
        case _:
            pass
    main_window.options_save_timer.start(OPTIONS_SAVE_DEBOUNCE_MS)
    return None


def process_option_change(main_window: QMainWindow) -> None:
    match getattr(main_window, "initial_setup_complete", False):
        case True:
            process_options_save_timer_trigger(main_window)
        case False:
            pass
    return None


def _option_present(main_window: QMainWindow, option_key: str) -> bool:
    return option_key in main_window.options_widgets


def process_application_options_save(main_window: QMainWindow) -> None:
    parser_instance = configparser.ConfigParser(interpolation=None)
    parser_instance["Options"] = {
        option_key: main_window.options_widgets[option_key].currentText().strip()
        for option_key in filter(partial(_option_present, main_window), OPTIONS_DB)}
    parser_instance["Profile"] = {"last_active_profile": main_window.current_profile}
    os.makedirs(build_config_dir(), exist_ok=True)
    with open(build_options_path(), "w") as file_handle:
        parser_instance.write(file_handle)
    return None


def process_application_options_load(main_window: QMainWindow) -> None:
    parser_instance = configparser.ConfigParser(interpolation=None)
    parser_instance.read(build_options_path())
    for option_key in OPTIONS_DB:
        match option_key in main_window.options_widgets:
            case False:
                continue
            case True:
                saved = parser_instance.get("Options", option_key, fallback=get_option_default_value(option_key))
                main_window.options_widgets[option_key].setCurrentText(saved)
    last_profile = parser_instance.get("Profile", "last_active_profile", fallback=DEFAULT_PROFILE)
    match main_window.profile_selector.findText(build_profile_label(last_profile)) >= 0:
        case True:
            main_window.profile_selector.blockSignals(True)
            main_window.profile_selector.setCurrentText(build_profile_label(last_profile))
            main_window.profile_selector.blockSignals(False)
            main_window.current_profile = last_profile
        case False:
            pass
    process_options_application(main_window)
    return None


def call_run_probe() -> bool:
    match shutil.which(PROBE_BIN):
        case None:
            return False
        case path:
            return subprocess.run([path], capture_output=True).returncode == PROBE_EXIT_OK


def call_root_run(argument: str) -> tuple:
    match (shutil.which(PKEXEC_BIN), shutil.which(ROOT_BIN)):
        case (None, _) | (_, None):
            return (ROOT_MISSING, "")
        case (pkexec, root):
            result = subprocess.run([pkexec, root, argument], capture_output=True, text=True)
            return (result.returncode, result.stdout)


def build_report_text(output: str) -> str:
    return "\n".join(
        line.removeprefix(REPORT_PREFIX) for line in output.splitlines() if line.strip() != "")


def process_root_notice(main_window: QMainWindow, result: tuple, done_text: str) -> None:
    match result:
        case (code, _) if code == ROOT_MISSING:
            process_notification_display(main_window, ROOT_MISSING_ERROR)
        case (code, _) if code == PKEXEC_DISMISSED:
            process_notification_display(main_window, APPLY_CANCELLED)
        case (code, _) if code == PKEXEC_REFUSED:
            process_notification_display(main_window, APPLY_REFUSED)
        case (code, output) if code == ROOT_EXIT_OK:
            process_notification_display(main_window, done_text, build_report_text(output))
        case (_, output):
            process_notification_display(main_window, APPLY_FAILED, build_report_text(output))
    return None


def process_dropped_notice(main_window: QMainWindow, dropped: tuple) -> None:
    match len(dropped):
        case 0:
            return None
        case _:
            process_notification_display(
                main_window,
                "This machine cannot provide "
                + ", ".join(key.replace(WIDGET_SEP, SECTION_SEP) for key in dropped)
                + ", reset to default.")
            return None


def process_all_settings_apply(main_window: QMainWindow) -> None:
    process_application_options_save(main_window)
    process_profile_save(main_window.all_widgets, main_window.current_profile)
    process_root_notice(
        main_window,
        call_root_run(main_window.current_profile),
        "Profile '" + main_window.current_profile + "' applied.")
    return None


def process_originals_restore() -> None:
    match os.path.exists(ORIGINALS_PATH):
        case True:
            call_root_run(RESTORE_WORD)
        case False:
            pass
    return None


def process_window_close(main_window: QMainWindow, singleton_socket: Optional[socket.socket], close_event: QCloseEvent) -> None:
    match (main_window.use_system_tray, hasattr(main_window, "tray_icon")):
        case (True, True):
            main_window.hide()
            close_event.ignore()
            return None
        case _:
            process_cleanup(main_window, singleton_socket)
            QApplication.quit()
            close_event.accept()
            return None


def process_cleanup(main_window: QMainWindow, singleton_socket: Optional[socket.socket]) -> None:
    match getattr(main_window, "options_save_timer", None):
        case None:
            pass
        case timer:
            timer.stop()
    process_profile_save(main_window.all_widgets, main_window.current_profile)
    process_application_options_save(main_window)
    process_originals_restore()
    match singleton_socket is None:
        case False:
            singleton_socket.close()
        case True:
            pass
    match main_window.welcome_window is None:
        case False:
            main_window.welcome_window.close()
            main_window.welcome_window = None
        case True:
            pass
    return None


def process_application_quit(main_window: QMainWindow) -> None:
    process_cleanup(main_window, main_window.singleton_socket)
    QApplication.quit()
    return None


def process_welcome_show(main_window: QMainWindow) -> None:
    match main_window.welcome_window is None:
        case True:
            main_window.welcome_window = create_welcome_window_widget()
        case False:
            pass
    main_window.welcome_window.show()
    main_window.welcome_window.activateWindow()
    main_window.welcome_window.raise_()
    return None


def call_claim_singleton(singleton_port: int) -> dict:
    lock_socket = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    lock_name = "\0ohm-gui-singleton-" + str(singleton_port)
    match lock_socket.connect_ex(lock_name) != 0:
        case True:
            lock_socket.close()
            lock_socket = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
            lock_socket.bind(lock_name)
            return {"socket": lock_socket, "running": False}
        case False:
            lock_socket.close()
            return {"socket": None, "running": True}


def process_signal_handler(main_window: QMainWindow, signal_number: int) -> None:
    print("\nReceived signal " + str(signal_number) + ", closing...")
    process_cleanup(main_window, main_window.singleton_socket)
    QApplication.quit()
    sys.exit(0)


def process_signal_handlers_setup(main_window: QMainWindow) -> None:
    signal.signal(signal.SIGINT, lambda signal_number, frame: process_signal_handler(main_window, signal_number))
    signal.signal(signal.SIGTERM, lambda signal_number, frame: process_signal_handler(main_window, signal_number))
    return None


def process_create_tab(stacked_widget: QStackedWidget, all_widgets: dict, options_widgets: dict, tab_name: str) -> None:
    match tab_name:
        case "Options":
            tab_result = create_options_tab_widget()
            options_widgets.update(tab_result["widgets"])
            stacked_widget.addWidget(tab_result["tab"])
        case "About":
            stacked_widget.addWidget(create_tab_content_widget(tab_name, get_about_data())["tab"])
        case _:
            tab_result_settings = create_tab_content_widget(tab_name, None)
            all_widgets.update(tab_result_settings["widgets"])
            stacked_widget.addWidget(tab_result_settings["tab"])
    return None


def create_main_window_widget(singleton_socket: Optional[socket.socket], probe_ok: bool) -> QMainWindow:
    window = QMainWindow()
    window.singleton_socket = singleton_socket
    window.start_maximized = False
    window.start_minimized = False
    window.show_welcome = True
    window.use_system_tray = False
    window.current_profile = DEFAULT_PROFILE
    window.welcome_window = None
    window.setWindowTitle("ohm-gui")
    window.setMinimumSize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
    window.setAttribute(Qt.WA_DontShowOnScreen, True)
    process_theme_application(QApplication.instance(), call_persisted_option_resolved("application_theme"))
    central_widget = QWidget()
    main_layout = QVBoxLayout(central_widget)
    main_layout.setContentsMargins(8, 8, 8, 8)
    main_layout.setSpacing(8)
    content_layout = QHBoxLayout()
    content_layout.setContentsMargins(0, 0, 0, 0)
    content_layout.setSpacing(0)
    stacked_widget = QStackedWidget()
    all_widgets = {}
    options_widgets = {}
    for tab_name in ALL_TABS:
        process_create_tab(stacked_widget, all_widgets, options_widgets, tab_name)
    sidebar_container, tab_list = create_sidebar_container_widget(ALL_TABS, stacked_widget)
    window.sidebar_tab_list = tab_list
    content_layout.addWidget(sidebar_container)
    content_layout.addWidget(stacked_widget, 1)
    main_layout.addLayout(content_layout, 1)
    bottom_bar_widget = QWidget()
    bottom_bar_widget.setProperty("buttonContainer", True)
    bottom_bar_layout = QHBoxLayout(bottom_bar_widget)
    bottom_bar_layout.setContentsMargins(8, 8, 8, 8)
    bottom_bar_layout.setSpacing(8)
    bottom_bar_layout.setAlignment(Qt.AlignBottom)
    preset_slider = create_slider_widget(())
    preset_slider.setMinimumWidth(SELECTOR_MIN_WIDTH)
    preset_slider.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
    window.preset_selector = preset_slider
    process_preset_combo_items(preset_slider)
    profile_slider = create_slider_widget(())
    profile_slider.setMinimumWidth(SELECTOR_MIN_WIDTH)
    profile_slider.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
    window.profile_selector = profile_slider
    apply_button = QPushButton("Apply")
    apply_button.setFixedSize(STANDARD_BUTTON_WIDTH, STANDARD_BUTTON_HEIGHT)
    apply_button.clicked.connect(lambda: process_all_settings_apply(window))
    new_button = QPushButton(NEW_PROFILE_LABEL)
    new_button.setFixedSize(STANDARD_BUTTON_WIDTH, STANDARD_BUTTON_HEIGHT)
    new_button.clicked.connect(lambda: process_new_profile_save(window))
    delete_button = QPushButton(DELETE_PROFILE_LABEL)
    delete_button.setFixedSize(STANDARD_BUTTON_WIDTH, STANDARD_BUTTON_HEIGHT)
    delete_button.clicked.connect(lambda: process_current_profile_delete(window))
    bottom_bar_layout.addWidget(preset_slider, SELECTOR_STRETCH, Qt.AlignVCenter)
    bottom_bar_layout.addWidget(profile_slider, SELECTOR_STRETCH, Qt.AlignVCenter)
    bottom_bar_layout.addWidget(delete_button, 0, Qt.AlignVCenter)
    bottom_bar_layout.addWidget(new_button, 0, Qt.AlignVCenter)
    bottom_bar_layout.addWidget(apply_button, 0, Qt.AlignVCenter)
    main_layout.addWidget(bottom_bar_widget)
    window.setCentralWidget(central_widget)
    window.all_widgets = all_widgets
    window.options_widgets = options_widgets
    process_profile_list_update(window)
    process_profile_selector_restore(window)
    window.profile_selector.currentTextChanged.connect(lambda text: process_profile_change(window, resolve_profile_label(text)))
    window.preset_selector.currentTextChanged.connect(lambda text: process_preset_combo_change(window, text))
    for option_key in options_widgets:
        options_widgets[option_key].currentTextChanged.connect(lambda text, bound_window=window: process_option_change(bound_window))
    process_application_options_load(window)
    process_dropped_notice(
        window,
        process_profile_widget_load(window.all_widgets, window.current_profile))
    window.initial_setup_complete = True
    window.setAttribute(Qt.WA_DontShowOnScreen, False)
    match QApplication.instance() is None:
        case False:
            QApplication.instance().setQuitOnLastWindowClosed(not window.use_system_tray)
        case True:
            pass
    match window.show_welcome:
        case True:
            QTimer.singleShot(WELCOME_DELAY_MS, lambda: process_welcome_show(window))
        case False:
            pass
    match window.start_minimized and window.use_system_tray:
        case False:
            QTimer.singleShot(SHOW_DELAY_MS, lambda: process_window_show(window))
        case True:
            pass
    match probe_ok:
        case False:
            QTimer.singleShot(NOTICE_DELAY_MS, lambda: process_notification_display(window, PROBE_FAILED_ERROR))
        case True:
            pass
    window.closeEvent = lambda close_event: process_window_close(window, singleton_socket, close_event)
    return window


def main() -> None:
    match os.environ.get("SUDO_USER") is not None:
        case True:
            print("Error: Do not run with sudo.\nRun as regular user.")
            sys.exit(1)
        case False:
            pass
    singleton_result = call_claim_singleton(SINGLETON_PORT)
    match singleton_result["running"]:
        case True:
            print("ohm-gui is already running.")
            sys.exit(0)
        case False:
            pass
    os.environ.setdefault("QT_LOGGING_RULES", "qt.qpa.theme.gnome=false")
    call_clean_environment()
    process_initial_platform()
    process_initial_scale()
    probe_ok = call_run_probe()
    application = QApplication(sys.argv)
    application.setStyle("Fusion")
    application.setQuitOnLastWindowClosed(False)
    window = create_main_window_widget(singleton_result["socket"], probe_ok)
    process_signal_handlers_setup(window)
    sys.exit(application.exec())


match __name__:
    case "__main__":
        main()
