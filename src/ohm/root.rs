use std::env;
use std::ffi::CStr;
use std::ffi::OsStr;
use std::os::unix::ffi::OsStrExt;
use std::path::Path;
use std::path::PathBuf;

use crate::apply::call_remove_originals;
use crate::apply::call_writes;
use crate::apply::entry_for;
use crate::apply::names;
use crate::apply::originals;
use crate::consts::APP_DIR;
use crate::consts::BAD_NAME;
use crate::consts::CONFIG_REL;
use crate::consts::DEFAULT_VALUE;
use crate::consts::ENV_PKEXEC_UID;
use crate::consts::EXIT_FAIL;
use crate::consts::EXIT_OK;
use crate::consts::LINE_PREFIX;
use crate::consts::NOTHING_SAVED;
use crate::consts::NOT_ROOT;
use crate::consts::NO_UID;
use crate::consts::PROFILE_SUFFIX;
use crate::consts::RESTORE_WORD;
use crate::consts::ROOT_UID;
use crate::consts::UNKNOWN_CLOSE;
use crate::consts::UNREAD_PROFILE;
use crate::consts::USAGE;
use crate::files::owned_text;
use crate::profile::name_is_valid;
use crate::profile::parse_profile;
use crate::profile::Entry;
use crate::walk::targets;
use crate::walk::Target;

fn call_print(line: &str) {
    println!("{}{}", LINE_PREFIX, line);
}

fn call_print_all(lines: &[String]) {
    lines.iter().for_each(|line| call_print(line));
}

fn call_failed(message: &str) -> i32 {
    call_print(message);
    EXIT_FAIL
}

fn call_usage() -> i32 {
    print!("{}", USAGE);
    EXIT_FAIL
}

fn pkexec_uid() -> Option<u32> {
    env::var(ENV_PKEXEC_UID)
        .ok()
        .and_then(|text| text.parse::<u32>().ok())
}

fn home_of(uid: u32) -> Option<PathBuf> {
    let entry = unsafe { libc::getpwuid(uid) };
    match entry.is_null() {
        true => None,
        false => Some(PathBuf::from(OsStr::from_bytes(
            unsafe { CStr::from_ptr((*entry).pw_dir) }.to_bytes(),
        ))),
    }
}

fn profile_path(home: &Path, name: &str) -> PathBuf {
    home.join(CONFIG_REL)
        .join(APP_DIR)
        .join([name, PROFILE_SUFFIX].concat())
}

fn set_value(profile: &[Entry], target: &Target) -> Option<String> {
    profile
        .iter()
        .find(|entry| names(entry, target) && entry.value != DEFAULT_VALUE)
        .map(|entry| entry.value.clone())
}

fn unknown_count(profile: &[Entry], all: &[Target]) -> usize {
    profile
        .iter()
        .filter(|entry| {
            entry.value != DEFAULT_VALUE && !all.iter().any(|target| names(entry, target))
        })
        .count()
}

fn call_unknown_line(count: usize) {
    match count > 0 {
        true => call_print(&[count.to_string().as_str(), UNKNOWN_CLOSE].concat()),
        false => (),
    }
}

fn call_apply_profile(profile: &[Entry]) -> i32 {
    let all = targets();
    let unknown = unknown_count(profile, &all);
    let wanted: Vec<(Target, String)> = all
        .into_iter()
        .filter_map(|target| set_value(profile, &target).map(|value| (target, value)))
        .collect();
    call_print_all(&call_writes(wanted, true));
    call_unknown_line(unknown);
    EXIT_OK
}

fn call_apply_home(uid: u32, home: Option<PathBuf>, name: &str) -> i32 {
    match home.and_then(|dir| owned_text(&profile_path(&dir, name), uid)) {
        None => call_failed(UNREAD_PROFILE),
        Some(text) => call_apply_profile(&parse_profile(&text)),
    }
}

fn call_apply_named(name: &str) -> i32 {
    match (pkexec_uid(), name_is_valid(name)) {
        (None, _) => call_failed(NO_UID),
        (Some(_), false) => call_failed(BAD_NAME),
        (Some(uid), true) => call_apply_home(uid, home_of(uid), name),
    }
}

fn call_restore_saved(saved: &[Entry]) {
    let wanted: Vec<(Target, String)> = targets()
        .into_iter()
        .rev()
        .filter_map(|target| entry_for(saved, &target).map(|entry| (target, entry.value)))
        .collect();
    call_print_all(&call_writes(wanted, false));
    call_remove_originals();
}

fn call_restore() -> i32 {
    match originals().as_slice() {
        [] => call_print(NOTHING_SAVED),
        saved => call_restore_saved(saved),
    };
    EXIT_OK
}

pub fn call_run_root(args: Vec<String>) -> i32 {
    match (unsafe { libc::geteuid() } == ROOT_UID, args.as_slice()) {
        (false, _) => call_failed(NOT_ROOT),
        (true, [word]) if word.as_str() == RESTORE_WORD => call_restore(),
        (true, [name]) => call_apply_named(name),
        (true, _) => call_usage(),
    }
}
