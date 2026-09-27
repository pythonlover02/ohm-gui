use std::path::Path;

use crate::consts::MARK_CLOSE;
use crate::consts::MARK_OPEN;
use crate::consts::Setting;
use crate::consts::Shape;
use crate::files::file_text;

#[derive(Clone, Debug, PartialEq)]
pub(crate) enum Offer {
    Choices(Vec<String>),
    Bounds(u64, u64),
}

#[derive(Clone, Debug, PartialEq)]
pub(crate) struct Reading {
    pub(crate) current: String,
    pub(crate) offer: Option<Offer>,
}

fn marked(word: &str) -> bool {
    word.starts_with(MARK_OPEN) && word.ends_with(MARK_CLOSE)
}

fn unmarked(word: &str) -> String {
    word.trim_start_matches(MARK_OPEN)
        .trim_end_matches(MARK_CLOSE)
        .to_string()
}

pub(crate) fn bracketed(text: &str) -> Option<Reading> {
    let words: Vec<&str> = text.split_whitespace().collect();
    let chosen: Vec<&str> = words.iter().copied().filter(|word| marked(word)).collect();
    match chosen.as_slice() {
        [one] => Some(Reading {
            current: unmarked(one),
            offer: Some(Offer::Choices(words.iter().map(|word| unmarked(word)).collect())),
        }),
        _ => None,
    }
}

pub(crate) fn listed(text: &str) -> Vec<String> {
    text.split_whitespace().map(str::to_string).collect()
}

pub(crate) fn bound(text: &str) -> Option<u64> {
    text.trim().parse::<u64>().ok()
}

pub(crate) fn choices_offer(text: Option<String>) -> Option<Offer> {
    text.map(|held| listed(&held))
        .filter(|all| !all.is_empty())
        .map(Offer::Choices)
}

pub(crate) fn bounds_offer(low: Option<String>, high: Option<String>) -> Option<Offer> {
    match (low.as_deref().and_then(bound), high.as_deref().and_then(bound)) {
        (Some(floor), Some(ceiling)) if floor <= ceiling => Some(Offer::Bounds(floor, ceiling)),
        (_, _) => None,
    }
}

pub(crate) fn offered(offer: &Offer, value: &str) -> bool {
    match offer {
        Offer::Choices(all) => all.iter().any(|one| one == value),
        Offer::Bounds(low, high) => bound(value).is_some_and(|held| *low <= held && held <= *high),
    }
}

fn unoffered(text: &str) -> Reading {
    Reading {
        current: text.trim().to_string(),
        offer: None,
    }
}

fn sibling_reading(text: &str, offer: Option<Offer>) -> Reading {
    Reading {
        current: text.trim().to_string(),
        offer,
    }
}

pub(crate) fn reading(dir: &Path, setting: &Setting) -> Option<Reading> {
    let text = file_text(&dir.join(setting.key))?;
    match setting.shape {
        Shape::Bracketed => Some(bracketed(&text).unwrap_or_else(|| unoffered(&text))),
        Shape::List(sibling) => Some(sibling_reading(
            &text,
            choices_offer(file_text(&dir.join(sibling))),
        )),
        Shape::Bounds(low, high) => Some(sibling_reading(
            &text,
            bounds_offer(file_text(&dir.join(low)), file_text(&dir.join(high))),
        )),
    }
}
