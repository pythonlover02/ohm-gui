fn main() {
    std::process::exit(ohm::call_run_root(std::env::args().skip(1).collect()));
}
