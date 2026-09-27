use crate::consts::COMMENT;
use crate::consts::LINE_END;
use crate::consts::NAME_BACKSLASH;
use crate::consts::NAME_CLIMB;
use crate::consts::NAME_NUL;
use crate::consts::NAME_SLASH;
use crate::consts::PAIR_CLOSE;
use crate::consts::PAIR_OPEN;
use crate::consts::PAIR_SEP;
use crate::consts::QUOTE;
use crate::consts::RESERVED_PROFILES;
use crate::consts::SECTION_CLOSE;
use crate::consts::SECTION_OPEN;
use crate::walk::grouped;

#[derive(Clone, Debug, PartialEq)]
pub(crate) struct Entry {
    pub(crate) section: String,
    pub(crate) key: String,
    pub(crate) value: String,
}

enum Line {
    Section(String),
    Pair(String, String),
    Skip,
}

struct Folded {
    section: String,
    entries: Vec<Entry>,
}

fn section_name(line: &str) -> Option<&str> {
    line.strip_prefix(SECTION_OPEN)
        .and_then(|rest| rest.strip_suffix(SECTION_CLOSE))
}

fn classify(line: &str) -> Line {
    match (
        line.is_empty() || line.starts_with(COMMENT),
        section_name(line),
        line.split_once(PAIR_SEP),
    ) {
        (true, _, _) => Line::Skip,
        (false, Some(name), _) => Line::Section(name.trim().to_string()),
        (false, None, Some((key, value))) => Line::Pair(
            key.trim().to_string(),
            value.trim().trim_matches(QUOTE).to_string(),
        ),
        (false, None, None) => Line::Skip,
    }
}

fn folded(state: Folded, line: &str) -> Folded {
    match classify(line.trim()) {
        Line::Section(name) => Folded {
            section: name,
            entries: state.entries,
        },
        Line::Pair(key, value) => {
            let mut entries = state.entries;
            entries.push(Entry {
                section: state.section.clone(),
                key,
                value,
            });
            Folded {
                section: state.section,
                entries,
            }
        }
        Line::Skip => state,
    }
}

pub(crate) fn parse_profile(text: &str) -> Vec<Entry> {
    text.lines()
        .fold(
            Folded {
                section: String::new(),
                entries: Vec::new(),
            },
            folded,
        )
        .entries
}

pub(crate) fn pair_line(key: &str, value: &str) -> String {
    [key, PAIR_OPEN, value, PAIR_CLOSE].concat()
}

fn section_head(name: &str) -> String {
    [SECTION_OPEN, name, SECTION_CLOSE, LINE_END].concat()
}

pub(crate) fn render_section(name: &str, pairs: &[String]) -> String {
    [section_head(name), pairs.concat()].concat()
}

pub(crate) fn render_entries(entries: &[Entry]) -> String {
    grouped(entries.to_vec(), |entry| entry.section.clone())
        .iter()
        .map(|(name, group)| {
            render_section(
                name,
                &group
                    .iter()
                    .map(|entry| pair_line(&entry.key, &entry.value))
                    .collect::<Vec<String>>(),
            )
        })
        .collect::<Vec<String>>()
        .join(LINE_END)
}

fn reserved_name(raw: &str) -> bool {
    RESERVED_PROFILES
        .iter()
        .any(|name| raw.eq_ignore_ascii_case(name))
}

pub(crate) fn name_is_valid(raw: &str) -> bool {
    !raw.is_empty()
        && !raw.contains(NAME_SLASH)
        && !raw.contains(NAME_BACKSLASH)
        && !raw.contains(NAME_CLIMB)
        && !raw.contains(NAME_NUL)
        && !reserved_name(raw)
        && raw.chars().all(|one| one.is_ascii_graphic())
}
