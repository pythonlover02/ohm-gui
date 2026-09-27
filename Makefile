PREFIX  ?= /usr
DESTDIR ?=
bindir  ?= $(PREFIX)/bin
datadir ?= $(PREFIX)/share

OUT      ?= build
RELEASES ?= releases

CARGO   ?= cargo
PYTHON3 ?= python3
TAR     ?= tar

ifeq ($(filter grouped-target,$(.FEATURES)),)
$(error GNU make 4.3+ required)
endif

POLICY_DIR    := $(datadir)/polkit-1/actions
DESKTOP_DIR   := $(datadir)/applications
ICON_DIR      := $(datadir)/icons/hicolor/256x256/apps
POLICY_FILE   := io.github.pythonlover02.ohm.policy
POLICY_SOURCE := polkit/$(POLICY_FILE).in
DESKTOP_FILE  := ohm-gui.desktop
ICON_FILE     := ohm-gui.png
ICON_SOURCE   := images/icon.png
ORIGINALS     := /run/ohm/originals.toml
SYSTEM_OHMS   := /usr/bin/ohm /usr/local/bin/ohm

VERSION := $(shell sed -n 's/^version = "\(.*\)"/\1/p' Cargo.toml | head -n1)

TARGET_DIR := $(OUT)/target
BIN_DIR    := $(OUT)/bin
SHARE_DIR  := $(OUT)/share
VENV       := $(OUT)/py_env

DIST_DIR   := $(OUT)/dist
DIST_NAME  := ohm-gui-$(VERSION)
DIST       := $(DIST_DIR)/$(DIST_NAME)
DIST_STAMP := $(OUT)/.dist

CARGO_TARGET_DIR := $(abspath $(TARGET_DIR))
export CARGO_TARGET_DIR

ROOT_BIN  := $(TARGET_DIR)/release/ohm
PROBE_BIN := $(TARGET_DIR)/release/ohm-probe
GUI_BIN   := $(BIN_DIR)/ohm-gui
DESKTOP   := $(SHARE_DIR)/$(DESKTOP_FILE)

RUST_SOURCES := Cargo.toml $(wildcard Cargo.lock) $(wildcard src/ohm/*.rs) $(wildcard src/ohm-probe/*.rs)
GUI_SOURCES  := $(wildcard src/ohm-gui/*.py)
VENV_STAMP   := $(OUT)/.venv

DESKTOP_NAME     := ohm-gui
DESKTOP_COMMENT  := My Linux Kernel Settings Modifier
DESKTOP_CATEGORY := Utility;System;
DESKTOP_KEYWORDS := kernel;cpu;governor;hugepages;scheduler;

RELEASE_FILES := $(RELEASES)/ohm-gui-$(VERSION).tar.gz

CONTAINER       ?= $(shell command -v podman 2>/dev/null || command -v docker 2>/dev/null || echo podman)
CONTAINER_BASE  ?= rust:1.85.1-bookworm
CONTAINER_IMAGE ?= ohm-gui-build
CONTAINER_OUT   ?= $(OUT)/container
CONTAINER_STAMP := $(OUT)/.container-image

NO_SUDO = @test -z "$$SUDO_USER" || { echo "error: do not build with sudo — run 'make' as your user, then 'sudo make install'"; exit 1; }

DIST_TREES = Cargo.toml $(wildcard Cargo.lock) src images polkit container .github

ifeq ($(DESTDIR),)
ROOT_GUARD := check-root
USER_GUARD := check-no-user-install
LIVE_SYSTEM := 1
else
ROOT_GUARD :=
USER_GUARD :=
LIVE_SYSTEM :=
endif

USER_OHM_HOME = $${SUDO_USER:+$$(getent passwd "$$SUDO_USER" | cut -d: -f6)}

INSTALL_FILES := \
  $(DESTDIR)$(bindir)/ohm \
  $(DESTDIR)$(bindir)/ohm-probe \
  $(DESTDIR)$(bindir)/ohm-gui \
  $(DESTDIR)$(POLICY_DIR)/$(POLICY_FILE) \
  $(DESTDIR)$(DESKTOP_DIR)/$(DESKTOP_FILE) \
  $(DESTDIR)$(ICON_DIR)/$(ICON_FILE)

USER_PREFIX   ?= $(HOME)/.local
USER_BIN      := $(USER_PREFIX)/bin
USER_DATA     := $(USER_PREFIX)/share
USER_DESK_DIR := $(USER_DATA)/applications
USER_ICON_DIR := $(USER_DATA)/icons/hicolor/256x256/apps

USER_FILES := \
  $(USER_BIN)/ohm \
  $(USER_BIN)/ohm-probe \
  $(USER_BIN)/ohm-gui \
  $(USER_DESK_DIR)/$(DESKTOP_FILE) \
  $(USER_ICON_DIR)/$(ICON_FILE)

BUILT_ARTIFACTS := $(ROOT_BIN) $(PROBE_BIN) $(GUI_BIN) $(DESKTOP)

.DELETE_ON_ERROR:

.PHONY: all ohm gui desktop dist release release-container container-image \
        install install-user uninstall uninstall-user clean help \
        check-root check-not-root check-built check-no-user-install check-no-system-install

all: $(BUILT_ARTIFACTS)

ohm:             $(ROOT_BIN) $(PROBE_BIN)
gui:             $(GUI_BIN)
desktop:         $(DESKTOP)
dist:            $(DIST_STAMP)
release:         $(RELEASE_FILES)
container-image: $(CONTAINER_STAMP)

$(OUT) $(BIN_DIR) $(SHARE_DIR) $(RELEASES) $(OUT)/pyinstaller:
	@mkdir -p $@

$(ROOT_BIN) $(PROBE_BIN) &: $(RUST_SOURCES)
	$(NO_SUDO)
	$(CARGO) build --release

$(VENV_STAMP): requirements.txt | $(OUT)
	$(NO_SUDO)
	$(PYTHON3) -m venv $(VENV)
	$(VENV)/bin/pip install --upgrade pip -q
	$(VENV)/bin/pip install --no-cache-dir -r requirements.txt -q
	@touch $@

$(GUI_BIN): $(GUI_SOURCES) $(VENV_STAMP) | $(BIN_DIR) $(OUT)/pyinstaller
	$(NO_SUDO)
	$(VENV)/bin/pyinstaller --onefile --name=$(@F) -y --log-level WARN \
	  --distpath $(BIN_DIR) --workpath $(OUT)/pyinstaller --specpath $(OUT)/pyinstaller \
	  src/ohm-gui/ohm-gui.py

$(DESKTOP): Makefile | $(SHARE_DIR)
	@printf '%s\n' \
	  '[Desktop Entry]' \
	  'Type=Application' \
	  'Version=1.0' \
	  'Name=$(DESKTOP_NAME)' \
	  'Comment=$(DESKTOP_COMMENT)' \
	  'Exec=ohm-gui' \
	  'Icon=ohm-gui' \
	  'Terminal=false' \
	  'Categories=$(DESKTOP_CATEGORY)' \
	  'Keywords=$(DESKTOP_KEYWORDS)' \
	  'StartupNotify=true' \
	  'StartupWMClass=ohm-gui' > $@

$(DIST_STAMP): $(GUI_BIN) $(ROOT_BIN) $(PROBE_BIN) $(DESKTOP) \
    Makefile Cargo.toml LICENSE README.md requirements.txt | $(OUT)
	rm -rf $(DIST)
	install -Dm755 $(GUI_BIN) $(DIST)/build/bin/ohm-gui
	install -Dm755 $(ROOT_BIN) $(DIST)/build/target/release/ohm
	install -Dm755 $(PROBE_BIN) $(DIST)/build/target/release/ohm-probe
	install -Dm644 $(DESKTOP) $(DIST)/build/share/$(DESKTOP_FILE)
	install -Dm644 Makefile $(DIST)/Makefile
	install -Dm644 LICENSE $(DIST)/LICENSE
	install -Dm644 README.md $(DIST)/README.md
	install -Dm644 requirements.txt $(DIST)/requirements.txt
	cp -r $(DIST_TREES) $(DIST)/
	touch $(DIST)/build/.venv
	touch $(DIST)/build/bin/* $(DIST)/build/share/* $(DIST)/build/target/release/*
	@touch $@

$(RELEASES)/ohm-gui-$(VERSION).tar.gz: $(DIST_STAMP) | $(RELEASES)
	$(TAR) -czf $@ -C $(DIST_DIR) $(DIST_NAME)

$(CONTAINER_STAMP): container/Containerfile | $(OUT)
	$(CONTAINER) build --build-arg BASE=$(CONTAINER_BASE) -t $(CONTAINER_IMAGE) -f $< container
	@touch $@

release-container: $(CONTAINER_STAMP)
	$(CONTAINER) run --rm -v "$(CURDIR):/src:z" -w /src \
	  --user "$$(id -u):$$(id -g)" \
	  -e HOME=/tmp \
	  -e CARGO_HOME=/src/$(CONTAINER_OUT)/cargo \
	  $(CONTAINER_IMAGE) make release OUT=$(CONTAINER_OUT)

install: | $(ROOT_GUARD) check-built $(USER_GUARD)
	install -Dm755 $(ROOT_BIN)    $(DESTDIR)$(bindir)/ohm
	install -Dm755 $(PROBE_BIN)   $(DESTDIR)$(bindir)/ohm-probe
	install -Dm755 $(GUI_BIN)     $(DESTDIR)$(bindir)/ohm-gui
	install -dm755 $(DESTDIR)$(POLICY_DIR)
	sed 's|@bindir@|$(bindir)|g' $(POLICY_SOURCE) > $(DESTDIR)$(POLICY_DIR)/$(POLICY_FILE)
	chmod 644 $(DESTDIR)$(POLICY_DIR)/$(POLICY_FILE)
	install -Dm644 $(DESKTOP)     $(DESTDIR)$(DESKTOP_DIR)/$(DESKTOP_FILE)
	install -Dm644 $(ICON_SOURCE) $(DESTDIR)$(ICON_DIR)/$(ICON_FILE)
	@test -z "$(LIVE_SYSTEM)" || update-desktop-database $(DESKTOP_DIR) 2>/dev/null || true
	@test -z "$(LIVE_SYSTEM)" || gtk-update-icon-cache -qtf $(datadir)/icons/hicolor 2>/dev/null || true
	@echo "install complete."
	@echo "  bin:       $(bindir)"
	@echo "  polkit:    $(POLICY_DIR)/$(POLICY_FILE)"
	@echo "  launcher:  $(DESKTOP_DIR)/$(DESKTOP_FILE)"
	@echo "  icon:      $(ICON_DIR)/$(ICON_FILE)"

install-user: | check-not-root check-built check-no-system-install
	install -Dm755 $(ROOT_BIN)    $(USER_BIN)/ohm
	install -Dm755 $(PROBE_BIN)   $(USER_BIN)/ohm-probe
	install -Dm755 $(GUI_BIN)     $(USER_BIN)/ohm-gui
	install -Dm644 $(DESKTOP)     $(USER_DESK_DIR)/$(DESKTOP_FILE)
	install -Dm644 $(ICON_SOURCE) $(USER_ICON_DIR)/$(ICON_FILE)
	@echo "user install complete, no root used."
	@echo "  bin:       $(USER_BIN)"
	@echo "$(USER_BIN) must be on PATH: ohm-gui runs ohm-probe and ohm."

uninstall: | $(ROOT_GUARD)
	@test -z "$(LIVE_SYSTEM)" -o ! -x "$(bindir)/ohm" || "$(bindir)/ohm" restore || true
	rm -f $(INSTALL_FILES)
	@test -z "$(LIVE_SYSTEM)" || update-desktop-database $(DESKTOP_DIR) 2>/dev/null || true
	@test -z "$(LIVE_SYSTEM)" || gtk-update-icon-cache -qtf $(datadir)/icons/hicolor 2>/dev/null || true
	@test -z "$(LIVE_SYSTEM)" -o -z "$$SUDO_USER" || \
	  su - "$$SUDO_USER" -c "rm -rf \"\$$HOME/.config/ohm-gui\"" || true
	@echo "uninstall complete."

uninstall-user: | check-not-root
	@test ! -e $(ORIGINALS) -o ! -x "$(USER_BIN)/ohm" || pkexec "$(USER_BIN)/ohm" restore || true
	rm -f $(USER_FILES)
	rm -rf "$(HOME)/.config/ohm-gui"
	@echo "user uninstall complete."

clean:
	rm -rf $(OUT) $(RELEASES)

check-root:
	@test "$$(id -u)" -eq 0 || { echo "error: needs root — run: sudo make $(MAKECMDGOALS)"; exit 1; }

check-not-root:
	@test "$$(id -u)" -ne 0 || { echo "error: this installs into \$$HOME — run as your user, no sudo"; exit 1; }

check-built:
	@missing=; for f in $(BUILT_ARTIFACTS); do \
	  test -e "$$f" || missing="$$missing $$f"; done; \
	test -z "$$missing" || { \
	  echo "error: build artifacts missing:"; \
	  for f in $$missing; do echo "  $$f"; done; \
	  echo "run 'make' as your user first, then re-run this target"; \
	  exit 1; }

check-no-user-install:
	@home="$(USER_OHM_HOME)"; \
	  test -z "$$home" -o ! -e "$$home/.local/bin/ohm" || { \
	  echo "error: a user install already owns ohm at"; \
	  echo "  $$home/.local/bin/ohm"; \
	  echo "two copies of ohm leave it undefined which one pkexec runs: run 'make uninstall-user' first"; \
	  exit 1; }

check-no-system-install:
	@for f in $(SYSTEM_OHMS); do test ! -e "$$f" || { \
	  echo "error: a system install already owns ohm at"; \
	  echo "  $$f"; \
	  echo "two copies of ohm leave it undefined which one pkexec runs: run 'sudo make uninstall' first"; \
	  exit 1; }; done

help:
	@echo "make                    ohm, ohm-probe, gui, desktop entry"
	@echo "make ohm                ohm and ohm-probe"
	@echo "make gui                gui binary via PyInstaller"
	@echo "make desktop            desktop entry only"
	@echo "make dist               source + build tree in $(DIST_DIR)/"
	@echo "make release            full release into $(RELEASES)/ (host toolchain)"
	@echo "make release-container  the same, built inside $(CONTAINER_BASE)"
	@echo "install targets never build: run 'make' as your user first"
	@echo "sudo make install"
	@echo "sudo make uninstall"
	@echo "make install-user       ohm, ohm-probe and gui into ~/.local"
	@echo "make uninstall-user"
	@echo "make clean"
