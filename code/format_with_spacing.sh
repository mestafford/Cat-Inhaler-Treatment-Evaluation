#!/bin/bash

# This script processes a file and formats its output by separating lines based on date changes.
# Usage: ./spaces.sh <input_file>
# Dates are expected to be in the format YYYY-MM-DD.

input_file="$1"

gawk '
{
    match($0, /[0-9]{4}-[0-9]{2}-[0-9]{2}/, date)
    if (NR == 1) {
        prev_date = date[0]
    } else if (date[0] != prev_date) {
        print ""
        prev_date = date[0]
    }
    print
}' "$input_file"
