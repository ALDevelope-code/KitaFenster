FROM python:3.11-slim
ARG APP_VERSION=0.2.2
ARG SOURCE_URL=https://github.com/ALDevelope-code/KitaFenster
ARG REVISION=local
LABEL org.opencontainers.image.title="KitaFenster" \
      org.opencontainers.image.licenses="AGPL-3.0-only" \
      org.opencontainers.image.version=$APP_VERSION \
      org.opencontainers.image.source=$SOURCE_URL \
      org.opencontainers.image.revision=$REVISION
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 DATA_DIR=/data NAS_ROOT=/nas
WORKDIR /app
RUN groupadd --gid 10001 kita && useradd --uid 10001 --gid kita --no-create-home kita
COPY requirements-server.txt ./
RUN pip install --no-cache-dir -r requirements-server.txt
COPY pyproject.toml README.md CONTRIBUTING.md SECURITY.md LICENSE NOTICE Dockerfile compose.yaml compose.build.yaml .env.example .dockerignore .gitignore .gitattributes ./
COPY .github ./.github
COPY server ./server
COPY shared ./shared
COPY player ./player
COPY deploy ./deploy
COPY docs ./docs
COPY tools ./tools
COPY tests ./tests
RUN pip install --no-cache-dir --no-deps . && mkdir /data && chown kita:kita /data
USER kita
EXPOSE 8088
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8088/api/health',timeout=3)"
CMD ["uvicorn", "server.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8088", "--workers", "1", "--no-access-log"]
