use crate::apply::tie_plan;
use crate::apply::TiePlan;
use crate::probe::reading_lines;
use crate::profile::name_is_valid;
use crate::profile::parse_profile;
use crate::profile::render_entries;
use crate::profile::Entry;
use crate::shapes::bounds_offer;
use crate::shapes::bracketed;
use crate::shapes::choices_offer;
use crate::shapes::offered;
use crate::shapes::Offer;
use crate::shapes::Reading;
use crate::walk::natural_key;
use crate::walk::segment_matches;
use crate::walk::split_root;

const THP_TEXT: &str = "always [madvise] never\n";
const THP_CURRENT: &str = "madvise";
const THP_CHOICES: [&str; 3] = ["always", "madvise", "never"];
const UNMARKED_TEXT: &str = "none\n";
const TWO_MARKED_TEXT: &str = "[always] [never]\n";
const BLANK_TEXT: &str = " \n";
const GOVERNORS_TEXT: &str = "schedutil performance powersave\n";
const GOVERNOR_ORDER: [&str; 3] = ["schedutil", "performance", "powersave"];
const LOW_TEXT: &str = "400000\n";
const HIGH_TEXT: &str = "5000000\n";
const LOW: u64 = 400000;
const HIGH: u64 = 5000000;
const LOW_VALUE: &str = "400000";
const HIGH_VALUE: &str = "5000000";
const INSIDE: &str = "3600000";
const OUTSIDE: &str = "6000000";
const NOT_NUMBER: &str = "fast";
const POLICY_PATTERN: &str = "policy*";
const POLICY_NAME: &str = "policy12";
const OTHER_NAME: &str = "cpu0";
const SIZE_PATTERN: &str = "hugepages-*";
const SIZE_NAME: &str = "hugepages-2048kB";
const BLOCK_ROOT: &str = "/sys/block/*/queue";
const BLOCK_PREFIX: &str = "/sys/block";
const BLOCK_PATTERN: &str = "*";
const BLOCK_SUFFIX: &str = "queue";
const PLAIN_ROOT: &str = "/sys/kernel/mm/transparent_hugepage";
const UNSORTED: [&str; 3] = ["policy10", "policy2", "policy1"];
const SORTED: [&str; 3] = ["policy1", "policy2", "policy10"];
const PROFILE_TEXT: &str = "# a comment\n[cpu.policy0]\nscaling_governor = \"performance\"\n\n[memory]\nenabled = \"default\"\n";
const POLICY_SECTION: &str = "cpu.policy0";
const GOVERNOR_KEY: &str = "scaling_governor";
const PERFORMANCE: &str = "performance";
const MEMORY_SECTION: &str = "memory";
const ENABLED_KEY: &str = "enabled";
const DEFAULT_WORD: &str = "default";
const RESERVED_NAME: &str = "Options";
const PROBE_NAME: &str = "probe";
const CLIMBING_NAME: &str = "../up";
const SPACED_NAME: &str = "two words";
const EMPTY_NAME: &str = "";
const ENABLED_LINE: &str = "enabled = \"madvise\"\n";
const CHOICES_LINE: &str = "enabled.choices = \"always;madvise;never\"\n";
const RISE_LOWER: u64 = 3000;
const RISE_UPPER: u64 = 5000;
const NOW_LOWER: u64 = 1000;
const NOW_UPPER: u64 = 2000;
const FALL_LOWER: u64 = 800;
const FALL_UPPER: u64 = 1000;
const HIGH_NOW_LOWER: u64 = 2000;
const HIGH_NOW_UPPER: u64 = 4000;
const CROSS_LOWER: u64 = 5000;
const CROSS_UPPER: u64 = 4000;
const SUNK_UPPER: u64 = 500;

fn texts(words: &[&str]) -> Vec<String> {
    words.iter().map(|word| word.to_string()).collect()
}

fn profile_entries() -> Vec<Entry> {
    vec![
        Entry {
            section: POLICY_SECTION.into(),
            key: GOVERNOR_KEY.into(),
            value: PERFORMANCE.into(),
        },
        Entry {
            section: MEMORY_SECTION.into(),
            key: ENABLED_KEY.into(),
            value: DEFAULT_WORD.into(),
        },
    ]
}

#[test]
fn reads_the_marked_word_of_a_bracketed_file_as_the_current_value() {
    assert_eq!(
        bracketed(THP_TEXT),
        Some(Reading {
            current: THP_CURRENT.into(),
            offer: Some(Offer::Choices(texts(&THP_CHOICES))),
        })
    );
}

#[test]
fn a_bracketed_file_marking_no_word_or_two_states_nothing() {
    assert_eq!(bracketed(UNMARKED_TEXT), None);
    assert_eq!(bracketed(TWO_MARKED_TEXT), None);
}

#[test]
fn keeps_a_list_in_the_order_the_kernel_wrote_it() {
    assert_eq!(
        choices_offer(Some(GOVERNORS_TEXT.into())),
        Some(Offer::Choices(texts(&GOVERNOR_ORDER)))
    );
}

#[test]
fn an_empty_or_missing_list_offers_nothing() {
    assert_eq!(choices_offer(Some(BLANK_TEXT.into())), None);
    assert_eq!(choices_offer(None), None);
}

#[test]
fn reads_bounds_only_where_both_are_numbers_in_order() {
    assert_eq!(
        bounds_offer(Some(LOW_TEXT.into()), Some(HIGH_TEXT.into())),
        Some(Offer::Bounds(LOW, HIGH))
    );
    assert_eq!(bounds_offer(Some(HIGH_TEXT.into()), Some(LOW_TEXT.into())), None);
    assert_eq!(bounds_offer(Some(NOT_NUMBER.into()), Some(HIGH_TEXT.into())), None);
    assert_eq!(bounds_offer(None, Some(HIGH_TEXT.into())), None);
}

#[test]
fn offers_a_value_only_inside_what_the_kernel_states() {
    let bounds = Offer::Bounds(LOW, HIGH);
    assert!(offered(&bounds, INSIDE));
    assert!(offered(&bounds, LOW_VALUE));
    assert!(offered(&bounds, HIGH_VALUE));
    assert!(!offered(&bounds, OUTSIDE));
    assert!(!offered(&bounds, NOT_NUMBER));
    let choices = Offer::Choices(texts(&THP_CHOICES));
    assert!(offered(&choices, THP_CURRENT));
    assert!(!offered(&choices, NOT_NUMBER));
}

#[test]
fn matches_an_instance_against_its_glob_segment() {
    assert!(segment_matches(POLICY_PATTERN, POLICY_NAME));
    assert!(!segment_matches(POLICY_PATTERN, OTHER_NAME));
    assert!(segment_matches(SIZE_PATTERN, SIZE_NAME));
    assert!(segment_matches(BLOCK_PATTERN, OTHER_NAME));
}

#[test]
fn splits_a_root_at_its_glob_segment() {
    assert_eq!(
        split_root(BLOCK_ROOT),
        Some((
            BLOCK_PREFIX.to_string(),
            BLOCK_PATTERN.to_string(),
            BLOCK_SUFFIX.to_string()
        ))
    );
    assert_eq!(split_root(PLAIN_ROOT), None);
}

#[test]
fn sorts_instances_by_their_number() {
    let mut found: Vec<&str> = UNSORTED.to_vec();
    found.sort_by_key(|name| natural_key(name));
    assert_eq!(found, SORTED.to_vec());
}

#[test]
fn reads_sections_and_pairs_from_a_profile() {
    assert_eq!(parse_profile(PROFILE_TEXT), profile_entries());
}

#[test]
fn reads_back_the_profile_it_writes() {
    assert_eq!(parse_profile(&render_entries(&profile_entries())), profile_entries());
}

#[test]
fn accepts_only_a_plain_profile_name() {
    assert!(name_is_valid(DEFAULT_WORD));
    assert!(!name_is_valid(RESERVED_NAME));
    assert!(!name_is_valid(PROBE_NAME));
    assert!(!name_is_valid(CLIMBING_NAME));
    assert!(!name_is_valid(SPACED_NAME));
    assert!(!name_is_valid(EMPTY_NAME));
}

#[test]
fn the_maximum_rises_before_the_minimum() {
    assert_eq!(
        tie_plan(Some(RISE_LOWER), Some(RISE_UPPER), NOW_LOWER, NOW_UPPER),
        TiePlan {
            lower: Some(RISE_LOWER),
            upper: Some(RISE_UPPER),
            upper_first: true,
        }
    );
}

#[test]
fn the_minimum_falls_before_the_maximum() {
    assert_eq!(
        tie_plan(Some(FALL_LOWER), Some(FALL_UPPER), HIGH_NOW_LOWER, HIGH_NOW_UPPER),
        TiePlan {
            lower: Some(FALL_LOWER),
            upper: Some(FALL_UPPER),
            upper_first: false,
        }
    );
}

#[test]
fn drops_a_minimum_that_would_cross_the_maximum() {
    assert_eq!(
        tie_plan(Some(CROSS_LOWER), Some(CROSS_UPPER), NOW_LOWER, NOW_UPPER).lower,
        None
    );
    assert_eq!(tie_plan(Some(CROSS_LOWER), None, NOW_LOWER, NOW_UPPER).lower, None);
}

#[test]
fn drops_a_maximum_that_would_cross_the_current_minimum() {
    assert_eq!(
        tie_plan(None, Some(SUNK_UPPER), NOW_LOWER, HIGH_NOW_UPPER).upper,
        None
    );
}

#[test]
fn writes_a_setting_and_what_the_kernel_offers_for_it() {
    assert_eq!(
        reading_lines(
            ENABLED_KEY,
            &Reading {
                current: THP_CURRENT.into(),
                offer: Some(Offer::Choices(texts(&THP_CHOICES))),
            }
        ),
        vec![ENABLED_LINE.to_string(), CHOICES_LINE.to_string()]
    );
}
