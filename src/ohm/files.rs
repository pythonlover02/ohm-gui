use std::fs::File;
use std::fs::OpenOptions;
use std::io::Read;
use std::os::unix::fs::MetadataExt;
use std::os::unix::fs::OpenOptionsExt;
use std::path::Path;

fn text_of(mut file: File) -> Option<String> {
    let mut text = String::new();
    file.read_to_string(&mut text).ok().map(|_| text)
}

fn opened(path: &Path, flags: i32) -> Option<File> {
    OpenOptions::new()
        .read(true)
        .custom_flags(flags)
        .open(path)
        .ok()
}

pub(crate) fn file_text(path: &Path) -> Option<String> {
    opened(path, libc::O_NOFOLLOW).and_then(text_of)
}

fn owned_by(file: File, uid: u32) -> Option<String> {
    match file.metadata().map(|meta| meta.is_file() && meta.uid() == uid) {
        Ok(true) => text_of(file),
        Ok(false) | Err(_) => None,
    }
}

pub(crate) fn owned_text(path: &Path, uid: u32) -> Option<String> {
    opened(path, libc::O_NOFOLLOW | libc::O_NONBLOCK).and_then(|file| owned_by(file, uid))
}
