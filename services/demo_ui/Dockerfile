FROM python:3.13-slim

ARG DECK_VERSION=1.52.0

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl tar \
    && rm -rf /var/lib/apt/lists/*

RUN arch="$(dpkg --print-architecture)" \
    && case "$arch" in \
      amd64) deck_arch="amd64" ;; \
      arm64) deck_arch="arm64" ;; \
      *) echo "Unsupported architecture: $arch" >&2; exit 1 ;; \
    esac \
    && curl -fsSL "https://github.com/Kong/deck/releases/download/v${DECK_VERSION}/deck_${DECK_VERSION}_linux_${deck_arch}.tar.gz" -o /tmp/deck.tgz \
    && tar -xzf /tmp/deck.tgz -C /tmp \
    && mv /tmp/deck /usr/local/bin/deck \
    && chmod +x /usr/local/bin/deck \
    && rm -f /tmp/deck.tgz

WORKDIR /app
