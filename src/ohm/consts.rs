pub(crate) const CATEGORY_CPU: &str = "cpu";
pub(crate) const CATEGORY_MEMORY: &str = "memory";
pub(crate) const CATEGORY_DISK: &str = "disk";
pub(crate) const CATEGORY_PCIE: &str = "pcie";
pub(crate) const CATEGORY_NETWORK: &str = "network";

pub(crate) const ROOT_POLICY: &str = "/sys/devices/system/cpu/cpufreq/policy*";
pub(crate) const ROOT_CPUIDLE: &str = "/sys/devices/system/cpu/cpuidle";
pub(crate) const ROOT_THP: &str = "/sys/kernel/mm/transparent_hugepage";
pub(crate) const ROOT_THP_SIZE: &str = "/sys/kernel/mm/transparent_hugepage/hugepages-*";
pub(crate) const ROOT_KSM: &str = "/sys/kernel/mm/ksm";
pub(crate) const ROOT_BLOCK: &str = "/sys/block/*/queue";
pub(crate) const ROOT_ASPM: &str = "/sys/module/pcie_aspm/parameters";
pub(crate) const ROOT_TCP: &str = "/proc/sys/net/ipv4";
pub(crate) const ROOT_MPTCP: &str = "/proc/sys/net/mptcp";

pub(crate) const KEY_SCALING_GOVERNOR: &str = "scaling_governor";
pub(crate) const KEY_SCALING_AVAILABLE_GOVERNORS: &str = "scaling_available_governors";
pub(crate) const KEY_SCALING_MIN_FREQ: &str = "scaling_min_freq";
pub(crate) const KEY_SCALING_MAX_FREQ: &str = "scaling_max_freq";
pub(crate) const KEY_CPUINFO_MIN_FREQ: &str = "cpuinfo_min_freq";
pub(crate) const KEY_CPUINFO_MAX_FREQ: &str = "cpuinfo_max_freq";
pub(crate) const KEY_CURRENT_GOVERNOR: &str = "current_governor";
pub(crate) const KEY_AVAILABLE_GOVERNORS: &str = "available_governors";
pub(crate) const KEY_ENABLED: &str = "enabled";
pub(crate) const KEY_DEFRAG: &str = "defrag";
pub(crate) const KEY_SHMEM_ENABLED: &str = "shmem_enabled";
pub(crate) const KEY_ADVISOR_MODE: &str = "advisor_mode";
pub(crate) const KEY_SCHEDULER: &str = "scheduler";
pub(crate) const KEY_POLICY: &str = "policy";
pub(crate) const KEY_TCP_CONGESTION_CONTROL: &str = "tcp_congestion_control";
pub(crate) const KEY_TCP_AVAILABLE_CONGESTION_CONTROL: &str = "tcp_available_congestion_control";
pub(crate) const KEY_PATH_MANAGER: &str = "path_manager";
pub(crate) const KEY_AVAILABLE_PATH_MANAGERS: &str = "available_path_managers";

pub(crate) const PATH_SEP: &str = "/";
pub(crate) const GLOB: char = '*';
pub(crate) const SECTION_DOT: &str = ".";
pub(crate) const DEFAULT_VALUE: &str = "default";
pub(crate) const RESERVED_PROFILES: [&str; 2] = ["probe", "options"];
pub(crate) const NAME_SLASH: char = '/';
pub(crate) const NAME_BACKSLASH: char = '\\';
pub(crate) const NAME_CLIMB: &str = "..";
pub(crate) const NAME_NUL: char = '\0';
pub(crate) const CONFIG_REL: &str = ".config";
pub(crate) const APP_DIR: &str = "ohm-gui";
pub(crate) const PROFILE_SUFFIX: &str = ".toml";

pub(crate) const RUN_DIR: &str = "/run/ohm";
pub(crate) const ORIGINALS_FILE: &str = "originals.toml";
pub(crate) const ORIGINALS_TEMP: &str = "originals.toml.new";
pub(crate) const RUN_DIR_MODE: u32 = 0o755;
pub(crate) const ORIGINALS_MODE: u32 = 0o600;
pub(crate) const ROOT_UID: u32 = 0;
pub(crate) const ENV_PKEXEC_UID: &str = "PKEXEC_UID";
pub(crate) const RESTORE_WORD: &str = "restore";

pub(crate) const CHOICES_SUFFIX: &str = ".choices";
pub(crate) const BOUNDS_SUFFIX: &str = ".bounds";
pub(crate) const LIST_SEP: &str = ";";
pub(crate) const SECTION_OPEN: &str = "[";
pub(crate) const SECTION_CLOSE: &str = "]";
pub(crate) const PAIR_SEP: &str = "=";
pub(crate) const PAIR_OPEN: &str = " = \"";
pub(crate) const PAIR_CLOSE: &str = "\"\n";
pub(crate) const COMMENT: &str = "#";
pub(crate) const QUOTE: char = '"';
pub(crate) const MARK_OPEN: char = '[';
pub(crate) const MARK_CLOSE: char = ']';
pub(crate) const LINE_END: &str = "\n";

pub(crate) const LINE_PREFIX: &str = "[ohm] ";
pub(crate) const REPORT_MARK: &str = ": ";
pub(crate) const REPORT_WAS: &str = "was ";
pub(crate) const REPORT_APPLIED: &str = ", applied ";

pub(crate) const RANK_UPPER_FIRST: u8 = 0;
pub(crate) const RANK_LOWER: u8 = 1;
pub(crate) const RANK_UPPER_AFTER: u8 = 2;
pub(crate) const RANK_REST: u8 = 3;

pub(crate) const EXIT_OK: i32 = 0;
pub(crate) const EXIT_FAIL: i32 = 1;

pub(crate) const REASON_ABSENT: &str = "the file is not there, left alone";
pub(crate) const REASON_NO_OFFER: &str = "the kernel states no options or bounds for it, left alone";
pub(crate) const REASON_NOT_OFFERED: &str = "the kernel does not offer that value, the file keeps what it holds";
pub(crate) const REASON_CROSSED: &str = "the value would cross the other bound, dropped";
pub(crate) const REASON_REFUSED: &str = "the kernel refused the write, the file keeps what it holds";
pub(crate) const REASON_UNREAD_BACK: &str = "written, but the file could not be read back";
pub(crate) const NOT_ROOT: &str = "ohm runs as root: start it through pkexec";
pub(crate) const NO_UID: &str = "PKEXEC_UID is not set: start ohm through pkexec";
pub(crate) const BAD_NAME: &str = "the profile name is not one ohm reads";
pub(crate) const UNREAD_PROFILE: &str = "the profile is missing, not a regular file, or not yours: nothing written";
pub(crate) const SAVE_FAILED: &str = "the originals could not be saved, nothing written";
pub(crate) const NOTHING_SAVED: &str = "nothing to restore";
pub(crate) const UNKNOWN_CLOSE: &str = " profile setting(s) name nothing on this machine, left alone";
pub(crate) const USAGE: &str = "usage: ohm PROFILE\n       ohm restore\n\nohm applies ~/.config/ohm-gui/PROFILE.toml as root, through pkexec, and saves\nwhat each file held first. ohm restore puts those values back.\n";

#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub(crate) enum Instance {
    Global,
    Each,
}

#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub(crate) enum Shape {
    Bracketed,
    List(&'static str),
    Bounds(&'static str, &'static str),
}

pub(crate) struct Setting {
    pub(crate) category: &'static str,
    pub(crate) instance: Instance,
    pub(crate) root: &'static str,
    pub(crate) key: &'static str,
    pub(crate) shape: Shape,
    pub(crate) tie: Option<&'static str>,
}

pub(crate) static SETTINGS: [Setting; 14] = [
    Setting {
        category: CATEGORY_CPU,
        instance: Instance::Each,
        root: ROOT_POLICY,
        key: KEY_SCALING_GOVERNOR,
        shape: Shape::List(KEY_SCALING_AVAILABLE_GOVERNORS),
        tie: None,
    },
    Setting {
        category: CATEGORY_CPU,
        instance: Instance::Each,
        root: ROOT_POLICY,
        key: KEY_SCALING_MIN_FREQ,
        shape: Shape::Bounds(KEY_CPUINFO_MIN_FREQ, KEY_CPUINFO_MAX_FREQ),
        tie: Some(KEY_SCALING_MAX_FREQ),
    },
    Setting {
        category: CATEGORY_CPU,
        instance: Instance::Each,
        root: ROOT_POLICY,
        key: KEY_SCALING_MAX_FREQ,
        shape: Shape::Bounds(KEY_CPUINFO_MIN_FREQ, KEY_CPUINFO_MAX_FREQ),
        tie: None,
    },
    Setting {
        category: CATEGORY_CPU,
        instance: Instance::Global,
        root: ROOT_CPUIDLE,
        key: KEY_CURRENT_GOVERNOR,
        shape: Shape::List(KEY_AVAILABLE_GOVERNORS),
        tie: None,
    },
    Setting {
        category: CATEGORY_MEMORY,
        instance: Instance::Global,
        root: ROOT_THP,
        key: KEY_ENABLED,
        shape: Shape::Bracketed,
        tie: None,
    },
    Setting {
        category: CATEGORY_MEMORY,
        instance: Instance::Global,
        root: ROOT_THP,
        key: KEY_DEFRAG,
        shape: Shape::Bracketed,
        tie: None,
    },
    Setting {
        category: CATEGORY_MEMORY,
        instance: Instance::Global,
        root: ROOT_THP,
        key: KEY_SHMEM_ENABLED,
        shape: Shape::Bracketed,
        tie: None,
    },
    Setting {
        category: CATEGORY_MEMORY,
        instance: Instance::Each,
        root: ROOT_THP_SIZE,
        key: KEY_ENABLED,
        shape: Shape::Bracketed,
        tie: None,
    },
    Setting {
        category: CATEGORY_MEMORY,
        instance: Instance::Each,
        root: ROOT_THP_SIZE,
        key: KEY_SHMEM_ENABLED,
        shape: Shape::Bracketed,
        tie: None,
    },
    Setting {
        category: CATEGORY_MEMORY,
        instance: Instance::Global,
        root: ROOT_KSM,
        key: KEY_ADVISOR_MODE,
        shape: Shape::Bracketed,
        tie: None,
    },
    Setting {
        category: CATEGORY_DISK,
        instance: Instance::Each,
        root: ROOT_BLOCK,
        key: KEY_SCHEDULER,
        shape: Shape::Bracketed,
        tie: None,
    },
    Setting {
        category: CATEGORY_PCIE,
        instance: Instance::Global,
        root: ROOT_ASPM,
        key: KEY_POLICY,
        shape: Shape::Bracketed,
        tie: None,
    },
    Setting {
        category: CATEGORY_NETWORK,
        instance: Instance::Global,
        root: ROOT_TCP,
        key: KEY_TCP_CONGESTION_CONTROL,
        shape: Shape::List(KEY_TCP_AVAILABLE_CONGESTION_CONTROL),
        tie: None,
    },
    Setting {
        category: CATEGORY_NETWORK,
        instance: Instance::Global,
        root: ROOT_MPTCP,
        key: KEY_PATH_MANAGER,
        shape: Shape::List(KEY_AVAILABLE_PATH_MANAGERS),
        tie: None,
    },
];
