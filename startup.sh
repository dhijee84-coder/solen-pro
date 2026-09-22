#!/bin/sh
# Start SuryaSetu (FastAPI) on 0.0.0.0:8080 for the live preview.
set -e
cd /workspace/suryasetu

if ! python3 -c "import fastapi, uvicorn, sqlalchemy, jose, passlib, jinja2, dotenv, pydantic_settings, multipart" 2>/dev/null; then
  pip3 install --quiet -r requirements.txt
fi

if [ ! -f /workspace/suryasetu/suryasetu.db ]; then
  python3 scripts/seed.py
fi

if curl -sf http://127.0.0.1:8080/api/health >/dev/null 2>&1; then
  exit 0
fi

python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload > /tmp/suryasetu.log 2>&1 &
sleep 2
exit 0
