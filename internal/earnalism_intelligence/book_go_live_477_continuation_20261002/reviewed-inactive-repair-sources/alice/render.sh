#!/usr/bin/env bash
set -euo pipefail

source_image="$1"
output_dir="$2"
font_file="/tmp/earnalism-post509-ledger/frontend/public/assets/fonts/eb-garamond-400.ttf"
stored_description="A curious girl tumbles down a rabbit hole into a fantastical world of illogical creatures and absurd rules."

mkdir -p "$output_dir"

convert "$source_image" \
  -crop 360x180+105+1132 +repage \
  -statistic Median 31x31 \
  "$output_dir/parchment-clean.png"

convert -background none -fill '#6f5126' \
  -font "$font_file" -pointsize 25 -gravity center \
  -size 320x144 "caption:$stored_description" \
  "$output_dir/verified-description.png"

convert "$source_image" \
  "$output_dir/parchment-clean.png" -geometry +105+1132 -composite \
  "$output_dir/verified-description.png" -geometry +125+1150 -composite \
  -strip -define png:exclude-chunks=date,time \
  "$output_dir/alices-adventures-in-wonderland-back-corrected.png"
