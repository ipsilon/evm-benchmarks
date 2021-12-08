# EVM Benchmarks project
# Copyright 2021 The EVM Benchmarks Authors.
# SPDX-License-Identifier: Apache-2.0

# Directory for tools
BIN_DIR := bin

# Directory with benchmark source files
SRC_DIR := src

# Directory for benchmark output files (JSON State Tests)
OUT_DIR := benchmarks

# Place for intermediary files
TMP_DIR := tmp

# Directory for temporary retesteth config.
RETESTETH_CONFIG_DIR := ${TMP_DIR}/config

# Geth evm tool for t8n processing, can be downloaded with `make bin/evm`.
EVM := ${BIN_DIR}/evm

# retesteth tool, can be downloaded with `make bin/retesteth`.
RETESTETH := ${BIN_DIR}/retesteth


sources := $(wildcard src/*/*.yml)
outputs := $(sources:${SRC_DIR}/%.yml=${OUT_DIR}/%.json)

# Do not remove any intermediate files.
# Make considers %Filler.yml intermediate files, but we want to keep them for inspection.
.SECONDARY:

all: ${outputs}

# Create and patch the retesteth configuration.
${RETESTETH_CONFIG_DIR}:
	@echo Generating retesteth config dir at $@
	${RETESTETH} -- --datadir $@ 2>/dev/null >/dev/null || true
	@echo Patching t8ntool config with '${EVM}'
	sed -i 's|/bin/evm|$(abspath ${EVM})|g' $@/t8ntool/start.sh

# Generate the State Test fillers out of benchmark source files.
${TMP_DIR}/%Filler.yml: ${SRC_DIR}/%.yml
	mkdir -p $(dir $@)
	./evmbench.py build-source $< -o $@

# Generate the State Tests for benchmarks using previously generated fillers.
${OUT_DIR}/%.json: ${TMP_DIR}/%Filler.yml ${RETESTETH_CONFIG_DIR}
	${RETESTETH} -t GeneralStateTests -- --datadir ${RETESTETH_CONFIG_DIR} --testpath . --filltests --forceupdate --clients t8ntool --testfile $< --outfile $@

clean:
	rm -rf ${TMP_DIR}
	find ${OUT_DIR} -name '*.json' -delete

# Download the retesteth tool.
${RETESTETH}:
	mkdir -p $(dir $@)
	curl http://retesteth.ethdevops.io/release/0.2.1-difficulty/ubuntu-18.04.3/retesteth-0.2.1-difficulty-ubuntu-18.04.3 > $@
	chmod +x $@

# Download and extract geth evm tool.
${EVM}:
	mkdir -p ${TMP_DIR}
	curl https://gethstore.blob.core.windows.net/builds/geth-alltools-linux-amd64-1.10.13-7a0c19f8.tar.gz > ${TMP_DIR}/geth-alltools.tar.gz
	tar -xz -f ${TMP_DIR}/geth-alltools.tar.gz -C ${TMP_DIR}
	mkdir -p $(dir $@)
	mv ${TMP_DIR}/geth-alltools-*/evm $@
