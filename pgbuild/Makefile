SHELL := /bin/bash
INSTALL_PREFIX := $(shell pwd)/../src/pgserver/pginstall/
BUILD := $(shell pwd)/pgbuild/
JOBS ?= 4

.PHONY: all
all: pgvector postgres

### postgres
POSTGRES_VERSION ?= 18.6
POSTGRES_SHA256 ?= 983ee554ec53dbeb9b70797bef9fcf4e67e117e7e48ca1463cc80b3ff8e8ff3f
POSTGRES_URL := https://ftp.postgresql.org/pub/source/v$(POSTGRES_VERSION)/postgresql-$(POSTGRES_VERSION).tar.gz
POSTGRES_SRC := postgresql-$(POSTGRES_VERSION)
POSTGRES_BLD := $(POSTGRES_SRC)

$(POSTGRES_SRC).tar.gz:
	curl -fL -o $@ $(POSTGRES_URL)

## extract
$(POSTGRES_SRC)/configure: $(POSTGRES_SRC).tar.gz
	python3 ../scripts/verify-sha256.py $(POSTGRES_SRC).tar.gz $(POSTGRES_SHA256)
	tar xzf $(POSTGRES_SRC).tar.gz
	mkdir -p ../src/pgserver/licenses
	cp $(POSTGRES_SRC)/COPYRIGHT ../src/pgserver/licenses/PostgreSQL.txt
	touch $(POSTGRES_SRC)/configure

## configure
$(POSTGRES_BLD)/config.status: $(POSTGRES_SRC)/configure
	mkdir -p $(POSTGRES_BLD)
	cd $(POSTGRES_BLD) && ../$(POSTGRES_SRC)/configure --prefix=$(INSTALL_PREFIX) --without-readline --without-icu

## build
# https://stackoverflow.com/questions/68379786/
# for explanation of unsetting make env variables prior to calling postgres' own make
$(POSTGRES_BLD)/src/bin/initdb/initdb: $(POSTGRES_BLD)/config.status
	unset MAKELEVEL && unset MAKEFLAGS && unset MFLAGS && $(MAKE) -C $(POSTGRES_BLD) -j$(JOBS)

## install to INSTALL_PREFIX
$(INSTALL_PREFIX)/bin/postgres: $(POSTGRES_BLD)/src/bin/initdb/initdb
	mkdir -p $(INSTALL_PREFIX)
	unset MAKELEVEL && unset MAKEFLAGS && unset MFLAGS && $(MAKE) -C $(POSTGRES_BLD) install

.PHONY: postgres
postgres: $(INSTALL_PREFIX)/bin/postgres

### pgvector
PGVECTOR_TAG ?= v0.8.6
PGVECTOR_SHA256 ?= 10bf9938906e5d643bbc4a7eea104b6f57ba4898e5b76b20e60484ea1d5a7f8f
PGVECTOR_URL := https://github.com/pgvector/pgvector/archive/refs/tags/$(PGVECTOR_TAG).tar.gz
PGVECTOR_DIR := pgvector-$(PGVECTOR_TAG)

$(PGVECTOR_DIR).tar.gz:
	curl -fL -o $@ $(PGVECTOR_URL)

$(PGVECTOR_DIR)/Makefile: $(PGVECTOR_DIR).tar.gz
	python3 ../scripts/verify-sha256.py $(PGVECTOR_DIR).tar.gz $(PGVECTOR_SHA256)
	# tar extract into pgvector-$(PGVECTOR_TAG)
	mkdir -p $(PGVECTOR_DIR)
	tar xzf $(PGVECTOR_DIR).tar.gz -C $(PGVECTOR_DIR) --strip-components=1
	touch $(PGVECTOR_DIR)/Makefile
	mkdir -p ../src/pgserver/licenses
	cp $(PGVECTOR_DIR)/LICENSE ../src/pgserver/licenses/pgvector.txt

$(INSTALL_PREFIX)/lib/vector.so: $(PGVECTOR_DIR)/Makefile $(INSTALL_PREFIX)/bin/postgres
	unset MAKELEVEL && unset MAKEFLAGS && unset MFLAGS \
		&& export PG_CONFIG=$(INSTALL_PREFIX)/bin/pg_config \
		&& $(MAKE) -C $(PGVECTOR_DIR) -j$(JOBS) OPTFLAGS="" \
		&& $(MAKE) -C $(PGVECTOR_DIR) install

.PHONY: pgvector
pgvector: postgres $(INSTALL_PREFIX)/lib/vector.so

### other
.PHONY: clean clean-all
clean:
	rm -rf $(INSTALL_PREFIX)
	rm -rf $(POSTGRES_SRC)
	rm -rf $(POSTGRES_BLD)
	rm -rf $(PGVECTOR_DIR)

clean-all: clean
	rm -rf *.tar.gz