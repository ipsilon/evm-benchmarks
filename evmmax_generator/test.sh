#! /usr/bin/env bash

~/projects/go-ethereum-evmmax-no-eof/build/bin/evm --nomemory=false --code $(python3 generate.py) --json run
