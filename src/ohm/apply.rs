use std::fs;
use std::fs::DirBuilder;
use std::fs::OpenOptions;
use std::io::Write;
use std::os::unix::fs::DirBuilderExt;
use std::os::unix::fs::OpenOptionsExt;
use std::path::Path;
use std::path::PathBuf;

use crate::consts::ORIGINALS_FILE;
use crate::consts::ORIGINALS_MODE;
use crate::consts::ORIGINALS_TEMP;
use crate::consts::RANK_LOWER;
use crate::consts::RANK_REST;
use crate::consts::RANK_UPPER_AFTER;
use crate::consts::RANK_UPPER_FIRST;
use crate::consts::REASON_ABSENT;
use crate::consts::REASON_CROSSED;
use crate::consts::REASON_NOT_OFFERED;
use crate::consts::REASON_NO_OFFER;
use crate::consts::REASON_REFUSED;
use crate::consts::REASON_UNREAD_BACK;
use crate::consts::REPORT_APPLIED;
use crate::consts::REPORT_MARK;
use crate::consts::REPORT_WAS;
use crate::consts::ROOT_UID;
use crate::consts::RUN_DIR;
use crate::consts::RUN_DIR_MODE;
use crate::consts::SAVE_FAILED;
use crate::consts::SETTINGS;
use crate::consts::Setting;
use crate::files::owned_text;
use crate::profile::parse_profile;
use crate::profile::render_entries;
use crate::profile::Entry;
use crate::shapes::bound;
use crate::shapes::offered;
use crate::shapes::reading;
use crate::shapes::Reading;
use crate::walk::grouped;
use crate::walk::target_name;
use crate::walk::Target;

struct Checked {
    target: Target,
    reading: Reading,
    value: String,
}

#[derive(Clone, Copy, Debug, PartialEq)]
pub(crate) struct TiePlan {
    pub(crate) lower: Option<u64>,
    pub(crate) upper: Option<u64>,
    pub(crate) upper_first: bool,
}

pub(crate) fn tie_plan(
    lower: Option<u64>,
    upper: Option<u64>,
    lower_now: u64,
    upper_now: u64,
) -> TiePlan {
    let lower_landed = lower.filter(|value| *value <= upper.unwrap_or(upper_now));
    let upper_landed = upper.filter(|value| *value >= lower_landed.unwrap_or(lower_now));
    TiePlan {
        lower: lower_landed,
        upper: upper_landed,
        upper_first: upper_landed.is_some_and(|value| value >= lower_now),
    }
}

pub(crate) fn names(entry: &Entry, target: &Target) -> bool {
    entry.section == target.section && entry.key == target.setting.key
}

pub(crate) fn entry_for(entries: &[Entry], target: &Target) -> Option<Entry> {
    entries.iter().find(|entry| names(entry, target)).cloned()
}

fn reason_line(target: &Target, reason: &str) -> String {
    [target_name(target).as_str(), REPORT_MARK, reason].concat()
}

fn checked_offer(target: Target, found: Reading, value: String) -> Result<Checked, String> {
    match found.offer.as_ref().map(|offer| offered(offer, &value)) {
        None => Err(reason_line(&target, REASON_NO_OFFER)),
        Some(false) => Err(reason_line(&target, REASON_NOT_OFFERED)),
        Some(true) => Ok(Checked {
            target,
            reading: found,
            value,
        }),
    }
}

fn checked_one(target: Target, value: String) -> Result<Checked, String> {
    match reading(&target.dir, target.setting) {
        None => Err(reason_line(&target, REASON_ABSENT)),
        Some(found) => checked_offer(target, found, value),
    }
}

fn checked_all(wanted: Vec<(Target, String)>) -> (Vec<Checked>, Vec<String>) {
    wanted
        .into_iter()
        .map(|(target, value)| checked_one(target, value))
        .fold((Vec::new(), Vec::new()), |(mut kept, mut lines), result| {
            match result {
                Ok(item) => kept.push(item),
                Err(line) => lines.push(line),
            };
            (kept, lines)
        })
}

fn upper_of(lower: &Setting, key: &str) -> Option<&'static Setting> {
    SETTINGS
        .iter()
        .find(|one| one.root == lower.root && one.key == key)
}

fn tie_of(setting: &Setting) -> Option<(&'static Setting, &'static Setting)> {
    SETTINGS.iter().find_map(|lower| match lower.tie {
        Some(upper_key)
            if lower.root == setting.root
                && (lower.key == setting.key || upper_key == setting.key) =>
        {
            upper_of(lower, upper_key).map(|upper| (lower, upper))
        }
        _ => None,
    })
}

fn current_number(dir: &Path, setting: &Setting) -> Option<u64> {
    reading(dir, setting).and_then(|found| bound(&found.current))
}

fn wanted_number(items: &[Checked], key: &str) -> Option<u64> {
    items
        .iter()
        .find(|item| item.target.setting.key == key)
        .and_then(|item| bound(&item.value))
}

fn kept_by_plan(item: &Checked, lower: &Setting, upper: &Setting, plan: &TiePlan) -> bool {
    match (
        item.target.setting.key == lower.key,
        item.target.setting.key == upper.key,
    ) {
        (true, _) => plan.lower.is_some(),
        (_, true) => plan.upper.is_some(),
        (false, false) => true,
    }
}

fn plan_rank(item: &Checked, lower: &Setting, upper: &Setting, plan: &TiePlan) -> u8 {
    match (
        item.target.setting.key == upper.key,
        plan.upper_first,
        item.target.setting.key == lower.key,
    ) {
        (true, true, _) => RANK_UPPER_FIRST,
        (_, _, true) => RANK_LOWER,
        (true, false, _) => RANK_UPPER_AFTER,
        (false, _, false) => RANK_REST,
    }
}

fn settled(
    items: Vec<Checked>,
    lower: &Setting,
    upper: &Setting,
    plan: TiePlan,
) -> (Vec<Checked>, Vec<String>) {
    let (mut kept, dropped): (Vec<Checked>, Vec<Checked>) = items
        .into_iter()
        .partition(|item| kept_by_plan(item, lower, upper, &plan));
    kept.sort_by_key(|item| plan_rank(item, lower, upper, &plan));
    (
        kept,
        dropped
            .iter()
            .map(|item| reason_line(&item.target, REASON_CROSSED))
            .collect(),
    )
}

fn planned(items: Vec<Checked>, lower: &Setting, upper: &Setting) -> (Vec<Checked>, Vec<String>) {
    let dir: PathBuf = items
        .first()
        .map(|item| item.target.dir.clone())
        .unwrap_or_default();
    let wanted = (
        wanted_number(&items, lower.key),
        wanted_number(&items, upper.key),
    );
    match (current_number(&dir, lower), current_number(&dir, upper)) {
        (Some(lower_now), Some(upper_now)) => settled(
            items,
            lower,
            upper,
            tie_plan(wanted.0, wanted.1, lower_now, upper_now),
        ),
        (_, _) => (items, Vec::new()),
    }
}

fn tied_section(items: Vec<Checked>) -> (Vec<Checked>, Vec<String>) {
    match items.iter().find_map(|item| tie_of(item.target.setting)) {
        None => (items, Vec::new()),
        Some((lower, upper)) => planned(items, lower, upper),
    }
}

fn ordered(items: Vec<Checked>) -> (Vec<Checked>, Vec<String>) {
    grouped(items, |item| item.target.section.clone())
        .into_iter()
        .map(|(_, section)| tied_section(section))
        .fold(
            (Vec::new(), Vec::new()),
            |(mut writes, mut lines), (more, reasons)| {
                writes.extend(more);
                lines.extend(reasons);
                (writes, lines)
            },
        )
}

fn originals_path() -> PathBuf {
    Path::new(RUN_DIR).join(ORIGINALS_FILE)
}

pub(crate) fn originals() -> Vec<Entry> {
    owned_text(&originals_path(), ROOT_UID)
        .map(|text| parse_profile(&text))
        .unwrap_or_default()
}

fn saved_entry(item: &Checked) -> Entry {
    Entry {
        section: item.target.section.clone(),
        key: item.target.setting.key.to_string(),
        value: item.reading.current.clone(),
    }
}

fn call_write_originals(entries: &[Entry]) -> bool {
    let dir = Path::new(RUN_DIR);
    let temp = dir.join(ORIGINALS_TEMP);
    DirBuilder::new()
        .recursive(true)
        .mode(RUN_DIR_MODE)
        .create(dir)
        .and_then(|()| {
            OpenOptions::new()
                .write(true)
                .create(true)
                .truncate(true)
                .mode(ORIGINALS_MODE)
                .custom_flags(libc::O_NOFOLLOW)
                .open(&temp)
        })
        .and_then(|mut file| file.write_all(render_entries(entries).as_bytes()))
        .and_then(|()| fs::rename(&temp, dir.join(ORIGINALS_FILE)))
        .is_ok()
}

fn call_saved(items: &[Checked]) -> bool {
    let existing = originals();
    let added: Vec<Entry> = items
        .iter()
        .filter(|item| entry_for(&existing, &item.target).is_none())
        .map(saved_entry)
        .collect();
    match added.is_empty() {
        true => true,
        false => call_write_originals(&[existing, added].concat()),
    }
}

pub(crate) fn call_remove_originals() {
    let _ = fs::remove_file(originals_path());
}

fn call_write_value(path: &Path, value: &str) -> bool {
    OpenOptions::new()
        .write(true)
        .custom_flags(libc::O_NOFOLLOW)
        .open(path)
        .and_then(|mut file| file.write_all(value.as_bytes()))
        .is_ok()
}

fn landed_line(item: &Checked) -> String {
    match reading(&item.target.dir, item.target.setting) {
        Some(after) => reason_line(
            &item.target,
            &[
                REPORT_WAS,
                item.reading.current.as_str(),
                REPORT_APPLIED,
                after.current.as_str(),
            ]
            .concat(),
        ),
        None => reason_line(&item.target, REASON_UNREAD_BACK),
    }
}

fn call_write_one(item: &Checked) -> String {
    match call_write_value(&item.target.dir.join(item.target.setting.key), &item.value) {
        true => landed_line(item),
        false => reason_line(&item.target, REASON_REFUSED),
    }
}

pub(crate) fn call_writes(wanted: Vec<(Target, String)>, save: bool) -> Vec<String> {
    let (checked, refused) = checked_all(wanted);
    let (writes, crossed) = ordered(checked);
    let head = [refused, crossed].concat();
    match save && !call_saved(&writes) {
        true => [head, vec![SAVE_FAILED.to_string()]].concat(),
        false => [
            head,
            writes.iter().map(call_write_one).collect::<Vec<String>>(),
        ]
        .concat(),
    }
}
