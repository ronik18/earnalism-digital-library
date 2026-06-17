#!/usr/bin/env bash
set -euo pipefail

input_path="${1:-}"
output_path="${2:-}"

if [[ -z "$input_path" || -z "$output_path" ]]; then
  echo "Usage: scripts/audio/tts/piperEnglishTts.sh <input.txt> <output.mp3>" >&2
  exit 64
fi

model_path="${PIPER_ENGLISH_MODEL:-}"
if [[ -z "$model_path" ]]; then
  echo "Missing PIPER_ENGLISH_MODEL. Example: models/piper/en/en_US-lessac-medium.onnx" >&2
  exit 64
fi
if [[ ! -f "$model_path" ]]; then
  echo "Piper English model not found: $model_path" >&2
  exit 66
fi
piper_bin="${PIPER_BINARY:-piper}"
if ! command -v "$piper_bin" >/dev/null 2>&1; then
  echo "piper CLI not found: $piper_bin. Install Piper and rerun, or use ENGLISH_TTS_PROVIDER=edge." >&2
  exit 69
fi
if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "ffmpeg is required to convert Piper WAV output to MP3." >&2
  exit 69
fi

mkdir -p "$(dirname "$output_path")"
tmp_dir="$(mktemp -d)"
trap 'rm -rf "$tmp_dir"' EXIT
wav_path="$tmp_dir/piper-output.wav"

piper_args=(--model "$model_path" --output_file "$wav_path")
config_path="${PIPER_ENGLISH_CONFIG:-${model_path}.json}"
if [[ -f "$config_path" ]]; then
  piper_args+=(--config "$config_path")
fi
if [[ -n "${PIPER_ENGLISH_SPEAKER:-}" ]]; then
  piper_args+=(--speaker "${PIPER_ENGLISH_SPEAKER}")
fi
if [[ -n "${PIPER_ENGLISH_LENGTH_SCALE:-}" ]]; then
  piper_args+=(--length_scale "${PIPER_ENGLISH_LENGTH_SCALE}")
fi
"$piper_bin" "${piper_args[@]}" < "$input_path" >/dev/null
ffmpeg -y -hide_banner -loglevel error -i "$wav_path" -c:a libmp3lame -b:a "${PIPER_ENGLISH_MP3_BITRATE:-64k}" -ac 1 "$output_path"

node -e 'const path=require("path"); const model=process.env.PIPER_ENGLISH_MODEL||""; console.log(JSON.stringify({provider:"piper",voice:process.env.ENGLISH_TTS_VOICE_ID||path.basename(model,path.extname(model)),model,outputPath:process.argv[1]}));' "$output_path"
