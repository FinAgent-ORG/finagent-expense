FROM dhi.io/python:3.13-dev AS builder

WORKDIR /app

ENV PATH="/app/venv/bin:$PATH"

RUN python -m venv /app/venv

COPY requirements.txt .

RUN --mount=type=cache,target=/root/.cache/pip \
    /app/venv/bin/pip install -r requirements.txt


FROM dhi.io/python:3.13.13

WORKDIR /app

ENV PATH="/app/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

COPY --from=builder --chown=0:0 --chmod=0555 /app/venv /app/venv
COPY --chown=0:0 --chmod=0555 database.py ./
COPY --chown=0:0 --chmod=0555 extractor.py ./
COPY --chown=0:0 --chmod=0555 init_db.py ./
COPY --chown=0:0 --chmod=0555 main.py ./
COPY --chown=0:0 --chmod=0555 models.py ./
COPY --chown=0:0 --chmod=0555 schemas.py ./
COPY --chown=0:0 --chmod=0555 security.py ./

USER 10001

EXPOSE 8002

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8002/api/v1/expenses/health', timeout=3)"]

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8002"]
