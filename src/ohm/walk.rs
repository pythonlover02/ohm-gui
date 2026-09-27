use std::fs;
use std::path::PathBuf;

use crate::consts::Instance;
use crate::consts::Setting;
use crate::consts::GLOB;
use crate::consts::PATH_SEP;
use crate::consts::SECTION_DOT;
use crate::consts::SETTINGS;

pub(crate) struct Target {
    pub(crate) setting: &'static Setting,
    pub(crate) section: String,
    pub(crate) dir: PathBuf,
}

pub(crate) fn segment_matches(pattern: &str, name: &str) -> bool {
    match pattern.split_once(GLOB) {
        None => pattern == name,
        Some((head, tail)) => {
            name.len() >= head.len() + tail.len() && name.starts_with(head) && name.ends_with(tail)
        }
    }
}

pub(crate) fn natural_key(name: &str) -> (String, u64, String) {
    let head: String = name.chars().take_while(|one| !one.is_ascii_digit()).collect();
    let rest = &name[head.len()..];
    let digits: String = rest.chars().take_while(|one| one.is_ascii_digit()).collect();
    (
        head,
        digits.parse::<u64>().unwrap_or_default(),
        rest[digits.len()..].to_string(),
    )
}

pub(crate) fn split_root(root: &str) -> Option<(String, String, String)> {
    let parts: Vec<&str> = root.split(PATH_SEP).collect();
    let at = parts.iter().position(|part| part.contains(GLOB))?;
    Some((
        parts[..at].join(PATH_SEP),
        parts[at].to_string(),
        parts[at + 1..].join(PATH_SEP),
    ))
}

fn section_name(category: &str, instance: &str) -> String {
    [category, SECTION_DOT, instance].concat()
}

fn instance_names(prefix: &str, pattern: &str) -> Vec<String> {
    let mut names: Vec<String> = fs::read_dir(prefix)
        .map(|entries| {
            entries
                .filter_map(|entry| entry.ok())
                .filter_map(|entry| entry.file_name().into_string().ok())
                .filter(|name| segment_matches(pattern, name))
                .collect()
        })
        .unwrap_or_default();
    names.sort_by_key(|name| natural_key(name));
    names
}

fn each_targets(setting: &'static Setting) -> Vec<Target> {
    match split_root(setting.root) {
        None => Vec::new(),
        Some((prefix, pattern, suffix)) => instance_names(&prefix, &pattern)
            .into_iter()
            .map(|name| Target {
                setting,
                dir: PathBuf::from(&prefix).join(&name).join(&suffix),
                section: section_name(setting.category, &name),
            })
            .collect(),
    }
}

fn global_targets(setting: &'static Setting) -> Vec<Target> {
    vec![Target {
        setting,
        section: setting.category.to_string(),
        dir: PathBuf::from(setting.root),
    }]
}

fn setting_targets(setting: &'static Setting) -> Vec<Target> {
    match setting.instance {
        Instance::Global => global_targets(setting),
        Instance::Each => each_targets(setting),
    }
}

pub(crate) fn targets() -> Vec<Target> {
    SETTINGS.iter().flat_map(setting_targets).collect()
}

pub(crate) fn target_name(target: &Target) -> String {
    [target.section.as_str(), SECTION_DOT, target.setting.key].concat()
}

pub(crate) fn grouped<T, F>(items: Vec<T>, section_of: F) -> Vec<(String, Vec<T>)>
where
    F: Fn(&T) -> String,
{
    items
        .into_iter()
        .fold(Vec::new(), |mut groups: Vec<(String, Vec<T>)>, item| {
            let name = section_of(&item);
            match groups.iter().position(|group| group.0 == name) {
                Some(at) => groups[at].1.push(item),
                None => groups.push((name, vec![item])),
            };
            groups
        })
}
