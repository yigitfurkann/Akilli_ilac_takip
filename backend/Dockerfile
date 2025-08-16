FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc libjpeg62-turbo-dev zlib1g-dev \
 && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_HOME=/app \
    PORT=8000

WORKDIR $APP_HOME

# requirements.txt UTF-16 olabilir; güvenli decode
COPY backend/requirements.txt /tmp/requirements.txt
RUN python - <<'PY'\nimport sys\np='/tmp/requirements.txt'\nraw=open(p,'rb').read()\nfor enc in ('utf-8','utf-16','utf-16le','utf-16be'):\n  try:\n    txt=raw.decode(enc); break\n  except UnicodeDecodeError: pass\nopen('/tmp/req.txt','w',encoding='utf-8').write(txt)\nprint('requirements decoded')\nPY
RUN pip install --no-cache-dir -r /tmp/req.txt \
 && pip install --no-cache-dir whitenoise gunicorn

COPY backend/ /app/

RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# collectstatic + migrate + gunicorn
CMD sh -c "python manage.py collectstatic --noinput && python manage.py migrate && gunicorn akilli_ilac_backend.wsgi:application --bind 0.0.0.0:${PORT} --workers 3 --timeout 120"
EXPOSE 8000
