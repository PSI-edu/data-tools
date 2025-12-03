#!/usr/bin/env bash

INFILE=$1
BAKFILE="${INFILE}.bak"

mv "$INFILE" "$BAKFILE"
xxd "$BAKFILE" | sed -e 's/7fc0 0000/0000 0000/g' | xxd -r > "$INFILE"
