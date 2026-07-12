# Dev container image for hass-qwikswitch-api.
#
# This holds MACHINE-WIDE, slow-changing installs only: system packages and
# standalone global binaries (uv, actionlint, gitleaks, Claude Code). Everything
# user/project-specific — dependency sync, pre-commit hook install, shell aliases —
# lives in .devcontainer/scripts/setup, which re-runs on every container create.
#
# Pin versions here and mirror them in .pre-commit-config.yaml so the hooks that
# use the -system variants (actionlint-system, gitleaks-system) match these binaries.

FROM mcr.microsoft.com/devcontainers/python:3.13

# System packages required by Home Assistant / its dependencies.
RUN apt-get update \
    && export DEBIAN_FRONTEND=noninteractive \
    && apt-get install -y --no-install-recommends \
        ffmpeg \
        libturbojpeg0 \
        libpcap-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# uv — pinned, copied from the official image (fast, no network resolution at build).
COPY --from=ghcr.io/astral-sh/uv:0.9.26 /uv /uvx /usr/local/bin/

# actionlint + gitleaks — binaries for the actionlint-system / gitleaks-system
# pre-commit hooks. Versions are pinned to match .pre-commit-config.yaml. Arch is
# detected so the image builds on both amd64 and arm64 hosts.
ARG ACTIONLINT_VERSION=1.7.12
ARG GITLEAKS_VERSION=8.30.1
RUN arch="$(dpkg --print-architecture)" \
    && gitleaks_arch="$([ "$arch" = "amd64" ] && echo x64 || echo "$arch")" \
    && curl -fsSL "https://github.com/rhysd/actionlint/releases/download/v${ACTIONLINT_VERSION}/actionlint_${ACTIONLINT_VERSION}_linux_${arch}.tar.gz" \
        | tar -xz -C /usr/local/bin actionlint \
    && curl -fsSL "https://github.com/gitleaks/gitleaks/releases/download/v${GITLEAKS_VERSION}/gitleaks_${GITLEAKS_VERSION}_linux_${gitleaks_arch}.tar.gz" \
        | tar -xz -C /usr/local/bin gitleaks \
    && actionlint --version \
    && gitleaks version

# Claude Code — installed for the vscode user so it is baked into the image
# (avoids re-downloading on every container create).
USER vscode
RUN curl -fsSL https://claude.ai/install.sh | bash
USER root
