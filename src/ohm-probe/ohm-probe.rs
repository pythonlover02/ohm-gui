use std::env;
use std::fs;
use std::path::Path;
use std::path::PathBuf;
use std::process::exit;

const ENV_HOME: &str = "HOME";
const CONFIG_REL: &str = ".config";
const APP_DIR: &str = "ohm-gui";
const PROBE_FILE: &str = "probe.toml";
const PROBE_TEMP: &str = "probe.toml.new";
const EXIT_OK: i32 = 0;
const EXIT_FAIL: i32 = 1;

fn config_dir(home: PathBuf) -> PathBuf {
    home.join(CONFIG_REL).join(APP_DIR)
}

fn call_write_probe(dir: &Path) -> i32 {
    let temp = dir.join(PROBE_TEMP);
    match fs::create_dir_all(dir)
        .and_then(|()| fs::write(&temp, ohm::probe_text()))
        .and_then(|()| fs::rename(&temp, dir.join(PROBE_FILE)))
    {
        Ok(()) => EXIT_OK,
        Err(_) => EXIT_FAIL,
    }
}

fn call_status() -> i32 {
    match env::var_os(ENV_HOME) {
        Some(home) => call_write_probe(&config_dir(PathBuf::from(home))),
        None => EXIT_FAIL,
    }
}

fn main() {
    exit(call_status());
}
