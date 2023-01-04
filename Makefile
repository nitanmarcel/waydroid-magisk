PREFIX := /usr
UPST := /etc/init

USE_SYSTEMD ?= 0
USE_UPSTART ?= 0

BIN_DIR := $(PREFIX)/bin
SYSD_DIR := $(PREFIX)/lib/systemd/system
UPST_DIR := $(UPST)

INSTALL_BIN_DIR := $(DESTDIR)$(BIN_DIR)
INSTALL_SYSD_DIR := $(DESTDIR)$(SYSD_DIR)
INSTALL_UPST_DIR := $(DESTDIR)$(UPST_DIR)

build:
	@echo "Nothing to build, run 'make install' to copy the files!"
install:
	install -m 755 waydroid_magisk.py $(BIN_DIR)/waydroid_magisk
	if [ $(USE_SYSTEMD) = 1 ]; then \
		install -d $(INSTALL_SYSD_DIR); \
		cp waydroid_magisk_daemon.service $(INSTALL_SYSD_DIR); \
	fi
	if [ $(USE_UPSTART) = 1 ]; then \
		install -d $(UPST_DIR); \
		cp waydroid_magisk_daemon.conf $(INSTALL_UPST_DIR); \
	fi