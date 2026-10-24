#!/usr/bin/env bash
# Deja listo el motor de reels de Clickly en una sesión nueva (idempotente).
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
if [ ! -x /opt/espeak/bin/espeak-ng ]; then tar xzf "$HERE/deps/espeak_opt.tgz" -C /opt; fi
if [ ! -f /opt/kokoro-multi-lang-v1_0/model.onnx ]; then
  curl -sSL -o /tmp/kokoro.tar.bz2 https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/kokoro-multi-lang-v1_0.tar.bz2
  tar xjf /tmp/kokoro.tar.bz2 -C /opt && rm -f /tmp/kokoro.tar.bz2
fi
python3 -c "import onnxruntime, numpy" 2>/dev/null || pip install --break-system-packages onnxruntime numpy
command -v ffmpeg >/dev/null || (apt-get update -qq && apt-get install -y -qq ffmpeg)
node -e "try{require('playwright')}catch(e){require('/opt/npm-tools/node_modules/playwright')}" 2>/dev/null || npm i -g playwright
/opt/espeak/bin/espeak-ng --path=/opt/espeak/share -q --ipa -v es-419 "hola" >/dev/null
echo "motor listo"
