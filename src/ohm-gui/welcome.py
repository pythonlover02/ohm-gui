from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout
from PySide6.QtWidgets import QMainWindow
from PySide6.QtWidgets import QPushButton
from PySide6.QtWidgets import QStackedWidget
from PySide6.QtWidgets import QVBoxLayout
from PySide6.QtWidgets import QWidget

from themes import STANDARD_BUTTON_HEIGHT
from themes import STANDARD_BUTTON_WIDTH
from ui import create_simple_sidebar_widget
from ui import create_tab_content_widget
from ui import WINDOW_MIN_HEIGHT
from ui import WINDOW_MIN_WIDTH


def get_welcome_settings() -> dict:
    return {
        "Welcome": {
            "Welcome to ohm gui": (
                ("text", "ohm-gui is my Linux Kernel Settings Modifier.\n\nIt sets the CPU governor and clock range, the idle governor, huge pages, the KSM scan advisor, the I/O scheduler of each drive, the PCIe link power policy and TCP congestion control."),
                ("text", "Settings are written by ohm, a small root helper started through pkexec when you press Apply. Close ohm-gui and every file goes back to what it held."),
            )
        },
        "How it Works": {
            "Apply and Restore": (
                ("text", "Pressing Apply saves the profile and runs ohm through pkexec, which asks for your password. ohm first saves what every file it is about to write holds to /run/ohm/originals.toml, then writes the profile."),
                ("text", "Closing ohm-gui runs ohm restore, which writes those values back and deletes the file. With the tray icon on, closing the window keeps ohm-gui running and your settings applied until you quit from the tray."),
                ("text", "Nothing applies at boot. There is no unit, no sysctl file and no udev rule, and /run is gone at reboot along with anything ohm saved there. A machine that never runs ohm is a machine ohm has never touched."),
            ),
            "What it Will Not Do": (
                ("text", "Overclocking, undervolting, fan curves and power caps stay out. Use LACT, or CoreCtrl if you also want CPU controls. So do watchdogs, lockdown levels, suspend modes, debug knobs and the clocksource: each is either one driver's, a security boundary, or a lever whose result you cannot see."),
                ("text", "A file only ships where the kernel describes it: a list marking the current choice, a sibling file naming the choices, or siblings naming the minimum and maximum. A file whose options only live in documentation, a bare number the kernel does not bound, and a file that acts when written are not settings."),
            )
        },
        "Settings": {
            "One Value Per Card": (
                ("text", "Every card is one file on one instance: the value ohm writes, or default, which means ohm does not touch the file."),
                ("text", "Cores that share a clock share a policy, so the CPU tab has one set of cards per policy. Memory has one set for huge pages as a whole and one per page size, and Disk has one card per drive. A card for one instance names it in its title."),
            ),
            "Where the Lists Come From": (
                ("text", "Every list is read from your kernel when ohm-gui opens. Governors come from the cpufreq driver, schedulers from the modules this kernel has, and frequencies from what the hardware reports. Nothing is sorted, renamed or converted: kHz stays kHz."),
                ("text", "ohm reads the same files again at the moment it writes. A value the kernel does not offer then is not written, and ohm says so."),
                ("text", "A profile written on another machine can name a policy, a drive or a value this one lacks. That setting resets to default and ohm-gui tells you which ones."),
            ),
            "Minimum and Maximum Frequency": (
                ("text", "The two never cross on the way. When both rise the maximum goes first, when both fall the minimum goes first. A minimum above the maximum, or a maximum below the minimum, is dropped with a line in the report."),
                ("text", "The slider runs in 1000 kHz steps between the hardware's floor and ceiling, and both of those are always stops. The kernel snaps a written value to one it supports, and the report shows what landed."),
            ),
        },
        "Usage": {
            "The Report": (
                ("text", "After Apply, the notice lists every file ohm wrote as was A, applied B, both read from the kernel. A setting that did not land says why instead. The report never repeats text from the profile."),
            ),
            "The Probe": (
                ("text", "ohm-probe runs as you when ohm-gui opens and never writes a kernel file. It lists each root's directory one level deep, reads only the files a root names, and writes ~/.config/ohm-gui/probe.toml. Every card is built from that file."),
                ("text", "A file that is not there is a card holding only default. So is a file whose list or bounds are missing."),
            ),
        },
        "Profiles": {
            "Profiles": (
                ("text", "Create profiles to switch between configurations.\n\n1. Press New in the bottom bar.\n2. Configure and Apply settings.\n3. Switch profiles from the bottom bar or the System Tray."),
            )
        },
        "Presets": {
            "Presets": (
                ("text", "Presets fill the profile you have open with a starting point, arranged as a ladder from least power to most throughput:\n\n- Power Saving: every policy on powersave.\n- Balanced: every policy on schedutil, huge pages where a program asks for them, compaction only where asked.\n- Performance: every policy on performance, huge pages where a program asks for them, and background compaction for everything else.\n- Performance Throughput: the same, with huge pages everywhere and every compaction in the background, trading memory for fewer address lookups.\n\nNo preset touches the clock range, the idle governor, the I/O scheduler, the KSM scan advisor, the PCIe policy or TCP congestion control: those depend on your hardware and your network, so they go back to default and the choice stays yours."),
                ("text", "Applying a preset replaces every value in the profile after a confirmation, so anything the preset does not set goes back to default."),
                ("text", "A preset can name a value your kernel does not offer, schedutil under intel_pstate in active mode for instance. That setting resets to default and ohm-gui says which ones, so the rest of the preset still lands."),
            )
        },
        "Options": {
            "Options": (
                ("text", "Changes to Options are saved automatically but only take effect after restarting ohm-gui. This includes the theme, scaling, tray behavior, and all other preferences."),
            )
        },
    }


def create_welcome_window_widget() -> QMainWindow:
    window = QMainWindow()
    window.setWindowTitle("ohm-gui Welcome")
    window.setMinimumSize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
    central_widget = QWidget()
    main_layout = QVBoxLayout(central_widget)
    main_layout.setContentsMargins(8, 8, 8, 8)
    main_layout.setSpacing(8)
    content_layout = QHBoxLayout()
    content_layout.setContentsMargins(0, 0, 0, 0)
    content_layout.setSpacing(0)
    welcome_settings = get_welcome_settings()
    stacked_widget = QStackedWidget()
    for section_data in welcome_settings.values():
        stacked_widget.addWidget(create_tab_content_widget("", section_data)["tab"])
    content_layout.addWidget(create_simple_sidebar_widget(tuple(welcome_settings.keys()), stacked_widget))
    content_layout.addWidget(stacked_widget, 1)
    main_layout.addLayout(content_layout, 1)
    button_container = QWidget()
    button_container.setProperty("buttonContainer", True)
    button_layout = QHBoxLayout(button_container)
    button_layout.setContentsMargins(8, 8, 8, 8)
    button_layout.setSpacing(8)
    button_layout.setAlignment(Qt.AlignVCenter)
    close_button = QPushButton("Close")
    close_button.setFixedSize(STANDARD_BUTTON_WIDTH, STANDARD_BUTTON_HEIGHT)
    close_button.clicked.connect(window.close)
    button_layout.addStretch(1)
    button_layout.addWidget(close_button, 0, Qt.AlignVCenter)
    button_layout.addStretch(1)
    main_layout.addWidget(button_container)
    window.setCentralWidget(central_widget)
    return window
