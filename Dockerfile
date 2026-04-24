FROM cgr.dev/chainguard/python:latest-dev AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    VENV_PATH=/home/nonroot/venv \
    PATH="/home/nonroot/venv/bin:${PATH}"

WORKDIR /home/nonroot/app

COPY --chown=nonroot:nonroot --chmod=0444 requirements.txt ./

RUN python -m venv "${VENV_PATH}" \
    && python -m pip install --upgrade pip \
    && python -m pip install -r requirements.txt

COPY --chown=nonroot:nonroot --chmod=0444 database.py ./
COPY --chown=nonroot:nonroot --chmod=0444 extractor.py ./
COPY --chown=nonroot:nonroot --chmod=0444 init_db.py ./
COPY --chown=nonroot:nonroot --chmod=0444 main.py ./
COPY --chown=nonroot:nonroot --chmod=0444 models.py ./
COPY --chown=nonroot:nonroot --chmod=0444 schemas.py ./
COPY --chown=nonroot:nonroot --chmod=0444 security.py ./

RUN chmod -R a=rX /home/nonroot/app /home/nonroot/venv

FROM cgr.dev/chainguard/python:latest AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    VENV_PATH=/home/nonroot/venv \
    PATH="/home/nonroot/venv/bin:${PATH}"

WORKDIR /home/nonroot/app

COPY --from=builder --chown=nonroot:nonroot --chmod=0555 /home/nonroot/venv /home/nonroot/venv
COPY --from=builder --chown=nonroot:nonroot --chmod=0555 /home/nonroot/app /home/nonroot/app

USER nonroot

EXPOSE 8002

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8002/api/v1/expenses/health', timeout=3)"]

ENTRYPOINT ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8002"]
