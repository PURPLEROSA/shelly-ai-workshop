#!/usr/bin/env bash
# הסטודיו שלי: הפעלה במק ובלינוקס. בפעם הראשונה מותקן הכל אוטומטית.
set -e
cd "$(dirname "$0")"
export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"

if ! command -v uv >/dev/null 2>&1; then
  echo
  echo "  Installing uv (a small tool that sets up Python for the studio)..."
  echo
  if command -v curl >/dev/null 2>&1; then
    curl -LsSf https://astral.sh/uv/install.sh | sh
  else
    wget -qO- https://astral.sh/uv/install.sh | sh
  fi
  export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
fi

if ! command -v uv >/dev/null 2>&1; then
  echo "  Could not install uv automatically. Install it from https://docs.astral.sh/uv/ and run this again."
  exit 1
fi

echo
echo "  Getting the studio ready (the first run downloads its parts, a few minutes)..."
uv sync --no-dev
exec uv run --no-dev --no-sync python -m app "$@"
