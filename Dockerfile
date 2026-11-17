FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN pip install --no-cache-dir . && useradd --system --no-create-home --uid 10101 serverwatch && mkdir /data && chown serverwatch:serverwatch /data
USER serverwatch
EXPOSE 8787
HEALTHCHECK --interval=30s --timeout=3s --start-period=20s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8787/healthz',timeout=2)"
CMD ["serverwatch", "dashboard"]
