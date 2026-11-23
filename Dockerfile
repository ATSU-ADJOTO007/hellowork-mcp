# Image du serveur Hellowork MCP en mode HTTP (connecteur ajouté par URL).
# Chromium n'est pas installé : en mode HTTP, les outils qui pilotent un navigateur sont désactivés.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HELLOWORK_MCP_DATA_DIR=/data \
    HELLOWORK_MCP_TRANSPORT=http \
    HELLOWORK_MCP_HOST=0.0.0.0 \
    PORT=8000

WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN pip install --no-cache-dir . && useradd --create-home --uid 10001 app && mkdir -p /data && chown app /data

USER app
VOLUME ["/data"]
EXPOSE 8000
CMD ["hellowork-mcp"]
