> [!NOTE]
> Bug reports and pull requests are welcome, but please understand that development happens in my free time and progress may be slow at times. The project is still maintained even if the last commit was made a while ago.
>
> Also English isn't my first language. I mainly speak Spanish (and some Portuguese), so I usually write the docs in Spanish, run them through a translator, and then edit the result. Some parts may sound a bit stiff or unnatural because of that. If anything is unclear, feel free to open an issue and I'll fix it.

# ohm-gui

Control panel for kernel settings on Linux. Settings are applied by **ohm**, a small root helper written in Rust and started through pkexec, when you press Apply, and put back when ohm-gui closes.

Kernel files only. ohm writes nothing a kernel subsystem doesn't describe itself, and nothing at boot.

ohm-gui's settings originally lived inside volt-gui. To keep both projects easier to ship and maintain, and each with one objective, they were split: ohm stays a kernel settings control panel, and the Vulkan side lives in [volt-gui](https://github.com/pythonlover02/volt-gui).

![](/images/1.png)
![](/images/2.png)
![](/images/3.png)

## Quick Start

```
git clone https://github.com/pythonlover02/ohm-gui.git
cd ohm-gui
make
make install-user

ohm-gui          # set what you want, press Apply
```

For a system-wide install use `sudo make install` instead. Pick one, never both.

## Table of Contents

- [Settings](#settings)
- [How It Works](#how-it-works)
- [Requirements](#requirements)
- [Installation](#installation)
- [Install paths](#install-paths)
- [Uninstalling](#uninstalling)
- [Immutable Systems](#immutable-systems)
- [Building Releases](#building-releases)
- [Usage](#usage)
- [Environment Variables](#environment-variables)
- [Files](#files)
- [Profiles, Presets & Options](#profiles-presets--options)
- [What ohm will never do](#what-ohm-will-never-do)
- [Contributing](#contributing)

## Settings

12 settings across 5 tabs. Every one defaults to `default`, which leaves the file alone. A profile with everything on default writes nothing.

Each setting is a single value in a single file. Several instances of one file are several cards: one per policy, one per page size, one per drive. A card for one instance names it in its title, like `Governor (policy0)`.

| Tab | Section | Count | Covers |
|-----|---------|------:|--------|
| CPU | `[cpu]`, `[cpu.policyN]` | 4 | idle governor, governor, clock range |
| Memory | `[memory]`, `[memory.hugepages-SIZE]` | 5 | huge pages, defrag, shared memory, per page size |
| Disk | `[disk.DEVICE]` | 1 | I/O scheduler, per drive |
| PCIe | `[pcie]` | 1 | link power policy |
| Network | `[network]` | 1 | TCP congestion control |

Every list is read from your kernel, not from a table in ohm-gui. Governors, schedulers, huge page modes, frequencies, PCIe policies and congestion controls all come from the files themselves or the siblings that list their choices. A file your kernel lacks holds only `default`.

Values are shown and stored exactly as the kernel writes them: kHz stays kHz. A profile written on another machine can name a policy, a drive or a value this one lacks. That setting resets to default and ohm-gui says which.

Settings are written when you press Apply and put back when ohm-gui closes.

### The probe

ohm-gui runs `ohm-probe` once each time it opens. It runs as you and never writes a kernel file: it lists each root's directory one level deep, never recursively, reads only the files a root names, and writes `~/.config/ohm-gui/probe.toml` with one section per instance. Every card is built from that file.

```
ohm-probe
```

It exits 0 on success and 1 where it couldn't write `probe.toml`.

A file that isn't there is a card holding only `default`. So is a file whose list or bounds are missing.

### CPU

**Governor** how the policy picks its clock. `performance` holds the top, `powersave` the bottom, the rest follow the load. `schedutil` reads the scheduler's own figure and reacts fastest. Which governors exist is the cpufreq driver's answer: intel_pstate in active mode offers two.

**Minimum / Maximum Frequency** the clock range in kHz, between the hardware's floor and ceiling in 1000 kHz steps. Both endpoints are always stops. The two never cross on the way: the maximum rises before the minimum rises, the minimum falls before the maximum falls, and a bound that would cross the other is dropped with a line. The kernel snaps a written value to one it supports.

**Idle Governor** who decides how deep an idle core sleeps. `teo` guesses from a longer history than `menu`, `ladder` steps down one state at a time.

### Memory

**Huge Pages** back memory with large pages. `always` everywhere, `madvise` only where a program asked, `never` off. Fewer address lookups, at the cost of stalling while the kernel finds a free large page.

**Huge Page Defrag** what happens when no large page is free. `always` waits while the kernel makes one, which is where huge pages cost you a stutter. `defer` hands out small pages now and compacts in the background.

**Huge Pages For Shared Memory** the same for shared memory and tmpfs, where shader caches and `/dev/shm` live.

Per page size, `inherit` follows the setting above it. Most sizes should stay there: your CPU only has hardware for one or two.

### Disk

**I/O Scheduler** how requests are ordered before they reach the drive. `none` suits an SSD that reorders on its own, `mq-deadline` stops a request waiting forever, `bfq` shares bandwidth between processes so a background copy can't starve a game. The list is what this kernel has modules for.

### PCIe

**PCIe Power Policy** how eagerly PCIe links sleep between transfers. `performance` keeps them awake, trimming latency on the GPU and NVMe links for a little power. `powersave` and `powersupersave` sleep them sooner. The kernel's own `default` isn't offered, since ohm's default already leaves the file on what your firmware chose. Some firmware keeps this for itself and refuses the write.

### Network

**TCP Congestion Control** how a TCP connection backs off when the network gets busy. `cubic` is the long-standing choice, `bbr` keeps queues short and helps downloads on a loaded link. Games mostly talk UDP, so this moves launchers and downloads rather than the game. The list is what this kernel has loaded.

## How It Works

ohm is a small root helper started through pkexec under the polkit action `io.github.pythonlover02.ohm.apply`. It runs as root only for the moment it writes, then exits.

ohm reads `~/.config/ohm-gui/<profile>.toml` when you press Apply and writes these files:

| Tab | Where ohm writes |
|-----|------------------|
| CPU | `/sys/devices/system/cpu/cpuidle/current_governor`, `/sys/devices/system/cpu/cpufreq/policyN/{scaling_governor,scaling_min_freq,scaling_max_freq}` |
| Memory | `/sys/kernel/mm/transparent_hugepage/{enabled,defrag,shmem_enabled}`, `.../hugepages-SIZE/{enabled,shmem_enabled}` |
| Disk | `/sys/block/DEVICE/queue/scheduler` |
| PCIe | `/sys/module/pcie_aspm/parameters/policy` |
| Network | `/proc/sys/net/ipv4/tcp_congestion_control` |

A profile never names a path. It names a section and a kernel file name, and ohm maps them to a path through its own table and a live walk of the roots.

The profile is checked first. pkexec runs ohm with root's environment, so ohm finds your home from `PKEXEC_UID`, the user who started it, never from `HOME`. The file is opened without following a symlink and must be a regular file you own.

Every value is checked against the kernel at the moment of writing, and every write is read back. A value outside the options or bounds the file states isn't written.

Before writing, ohm saves what each file holds to `/run/ohm/originals.toml`, root-only. A later apply adds the files it touches for the first time and never overwrites a value already saved. Restore writes them back in reverse order and deletes the file.

Nothing applies at boot: no unit, no sysctl file, no udev rule. `/run` is gone at reboot, and so is anything ohm saved there.

ohm-gui is the PySide6 front end. Apply saves the profile and runs ohm through pkexec, and closing runs `ohm restore`. Nothing else runs as root, no scripts.

## Requirements

| Component | Requirement |
|-----------|-------------|
| Root helper | Linux, `pkexec` from polkit |
| Build | Rust 1.85.1+ with cargo, GNU make 4.3+ |
| GUI | Python 3.10+, PySide6 |
| Container release | `podman` or `docker` |

No architecture-specific code. Anything the kernel, Rust and PySide6 run on builds natively.

## Installation

### From source

Every build target is a file, so make only rebuilds what changed. Everything lands under `build/`.

| Command | What it does |
|---------|--------------|
| `make` | ohm, ohm-probe, GUI, desktop entry |
| `make ohm` | ohm and ohm-probe |
| `make gui` | `build/bin/ohm-gui` |
| `make dist` | sources with `build/` populated |
| `make release` | archive in `releases/`, host toolchain |
| `make release-container` | same, inside the build image |
| `sudo make install` | system-wide |
| `make install-user` | into `~/.local`, no root |
| `sudo make uninstall` | everything |
| `make uninstall-user` | the rootless install |
| `make clean` | `rm -rf build releases` |
| `make help` | this list |

Actions artifacts are `make dist` trees. Unpack one and `sudo make install` installs without compiling.

Building with `sudo` is refused, so you never end up with a root-owned `build/`. Install targets only copy what's already built and name what's missing if you skipped a step. ohm-gui also refuses to start under `sudo`.

Packagers can stage without root:

```
make
make install DESTDIR="$PWD/pkg" PREFIX=/usr
```

With `DESTDIR` set the install skips the desktop database, the icon cache, and the competing-install check.

## Install paths

| File | System | User |
|------|--------|------|
| Root helper | `/usr/bin/ohm` | `~/.local/bin/ohm` |
| Probe | `/usr/bin/ohm-probe` | `~/.local/bin/ohm-probe` |
| GUI | `/usr/bin/ohm-gui` | `~/.local/bin/ohm-gui` |
| polkit action | `/usr/share/polkit-1/actions/io.github.pythonlover02.ohm.policy` | none |
| Desktop entry | `/usr/share/applications/ohm-gui.desktop` | `~/.local/share/applications/ohm-gui.desktop` |
| Icon | `/usr/share/icons/hicolor/256x256/apps/ohm-gui.png` | `~/.local/share/icons/hicolor/256x256/apps/ohm-gui.png` |

polkit only reads actions from `/usr/share/polkit-1/actions`. Without the action, pkexec asks for the admin password on every Apply and every close.

> [!WARNING]
> Don't change `PREFIX` away from `/usr`. The polkit action names the path ohm is installed to, and anywhere else it lands where polkit never reads it.

## Uninstalling

```
sudo make uninstall     # system
make uninstall-user     # ~/.local
```

Both put back anything ohm applied, then remove the binaries, the desktop entry, the icon and `~/.config/ohm-gui`, plus the polkit action for the system install. Run directly as root there's no `SUDO_USER` to work from, so your config is left alone.

`make clean` removes `build/` and `releases/`.

## Immutable Systems

On SteamOS, Bazzite, Silverblue and anything with a read-only `/usr`, skip the system install:

```
make
make install-user
```

`~/.local/bin` has to be on your `PATH`, because ohm-gui runs `ohm-probe` and `ohm`.

Pick one install, not both. Both install targets refuse to run while the other owns `ohm`, so there's never a second copy deciding which one pkexec runs.

The GUI is one self-contained binary, so unpacking a release and double-clicking `build/bin/ohm-gui` opens the editor with nothing installed. Enough to write and copy profiles, not enough to use them: without ohm-probe on your `PATH` every card holds only `default`, and without ohm nothing is written.

## Building Releases

Both targets produce `releases/ohm-gui-<version>.tar.gz`, a ready-to-install tree. Unpack and `sudo make install` or `make install-user` without compiling.

`make release` uses your toolchain and inherits your glibc floor.

`make release-container` builds inside `rust:1.85.1-bookworm` (glibc 2.36, Python 3.11), so the floor is fixed. Builds into `build/container/` and runs as your uid.

```
make release-container CONTAINER=docker
```

## Usage

```
pkexec ohm PROFILE      # apply ~/.config/ohm-gui/PROFILE.toml
pkexec ohm restore      # put back what ohm saved
```

ohm-gui runs both for you: the first on Apply, the second when it closes.

Profile names must be non-empty graphic ASCII with no space, no path separator, no `..` and no null byte.

Every line is prefixed `[ohm]` and goes to stdout.

Each setting the profile sets gets one line, naming what the file held and what it holds now.

```
[ohm] cpu.policy0.scaling_governor: was powersave, applied performance
[ohm] cpu.policy0.scaling_max_freq: was 4800000, applied 4200000
[ohm] disk.sda.scheduler: the kernel does not offer that value, the file keeps what it holds
```

Every setting line names the setting first, then either `was A, applied B` or the reason the setting did not land. Both values are read from the kernel, so a value the kernel snapped shows what landed rather than what the profile says.

A line names the setting and the reason, never text from the profile, so root's output can't be turned into a way to read a file you can't. After Apply, ohm-gui shows these lines under Show Details.

## Environment Variables

ohm reads no variable of its own. `PKEXEC_UID` is set by pkexec and is the only way ohm learns whose profile to read. `HOME` decides where ohm-gui and ohm-probe keep their files, and ohm itself never reads it.

There's no environment override for the settings themselves. A profile file is the only way to set them.

## Files

| Path | What it is |
|------|------------|
| `~/.config/ohm-gui/default.toml` | default profile |
| `~/.config/ohm-gui/<name>.toml` | named profiles |
| `~/.config/ohm-gui/probe.toml` | what the probe read, one section per instance |
| `~/.config/ohm-gui/options.toml` | ohm-gui preferences and last active profile |
| `/run/ohm/originals.toml` | what the files held before ohm, root-only, gone at reboot |

Profiles are plain TOML, one section per instance and one string per file, so you can edit them by hand. Keys are the kernel's own file names:

```
[cpu]
current_governor = "default"

[cpu.policy0]
scaling_governor = "performance"
scaling_min_freq = "default"
scaling_max_freq = "4200000"

[memory]
enabled = "madvise"

[disk.nvme0n1]
scheduler = "none"
```

## Profiles, Presets & Options

**Profiles** are TOML files in `~/.config/ohm-gui/`, one per configuration. Create and switch from the GUI or the tray. Switching writes nothing to the kernel: press Apply.

**Presets** fill the active profile with curated values, from Power Saving (every policy on `powersave`) up to Performance Throughput (every policy on `performance`, huge pages `always`, defrag `defer`). A preset writes every value, so anything it doesn't set goes back to default. No preset touches the clock range, the idle governor, the I/O scheduler, the PCIe policy or TCP congestion control, since those depend on your hardware and your network. A preset naming something your kernel doesn't offer resets that one to default and says which.

**Options** holds ohm-gui's own preferences: theme, transparency, display backend, scale, start maximised or in tray, tray icon, welcome window. They save as you change them and take effect on restart. With the tray icon on, closing the window keeps your settings applied until you quit from the tray. One instance at a time.

## What ohm will never do

- **Overclocking, undervolting, fan curves, power caps.** Use LACT, or CoreCtrl if you want CPU controls too.
- **A driver's own interface.** A power cap under hwmon exists on one vendor's cards. ohm ships the interface a kernel subsystem owns and leaves the rest to the tools that own it.
- **Watchdogs, lockdown levels, suspend modes, debug knobs, the clocksource.** Each is a driver's, a security boundary, or a lever whose result you can't see.
- **Apply at boot.** No sysctl.d file, no unit, no udev rule.
- **Write a file the kernel doesn't describe.** A bare number with no bounds, options that only live in documentation, a file that acts when written.
- **Write several files from one card.**
- **Rename, sort or convert a value.**

## Contributing

Contributions welcome. ohm and ohm-probe are plain Rust with no build scripts, the GUI is PySide6 only. A new setting is decided in `settings.auto` first, in its own words, and the code follows.
