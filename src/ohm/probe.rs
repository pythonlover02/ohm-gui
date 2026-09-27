use crate::consts::BOUNDS_SUFFIX;
use crate::consts::CHOICES_SUFFIX;
use crate::consts::LINE_END;
use crate::consts::LIST_SEP;
use crate::profile::pair_line;
use crate::profile::render_section;
use crate::shapes::reading;
use crate::shapes::Offer;
use crate::shapes::Reading;
use crate::walk::grouped;
use crate::walk::targets;
use crate::walk::Target;

fn offer_line(key: &str, offer: &Offer) -> String {
    match offer {
        Offer::Choices(all) => pair_line(&[key, CHOICES_SUFFIX].concat(), &all.join(LIST_SEP)),
        Offer::Bounds(low, high) => pair_line(
            &[key, BOUNDS_SUFFIX].concat(),
            &[low.to_string(), high.to_string()].join(LIST_SEP),
        ),
    }
}

pub(crate) fn reading_lines(key: &str, found: &Reading) -> Vec<String> {
    std::iter::once(pair_line(key, &found.current))
        .chain(found.offer.iter().map(|offer| offer_line(key, offer)))
        .collect()
}

fn target_lines(target: &Target) -> Vec<String> {
    reading(&target.dir, target.setting)
        .map(|found| reading_lines(target.setting.key, &found))
        .unwrap_or_default()
}

pub fn probe_text() -> String {
    grouped(targets(), |target| target.section.clone())
        .iter()
        .map(|(name, group)| {
            render_section(
                name,
                &group.iter().flat_map(target_lines).collect::<Vec<String>>(),
            )
        })
        .collect::<Vec<String>>()
        .join(LINE_END)
}
