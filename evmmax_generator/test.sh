#! /usr/bin/env bash

~/projects/go-ethereum-evmmax-no-eof/build/bin/evm --code $(python3 generate.py) run
