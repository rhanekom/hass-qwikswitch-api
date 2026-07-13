# Dev container image for hass-qwikswitch-api.
#
# This holds MACHINE-WIDE, slow-changing installs only: system packages and
# standalone global binaries (uv, actionlint, gitleaks, gh, Claude Code). Everything
# user/project-specific — dependency sync, pre-commit hook install, shell aliases —
# lives in .devcontainer/scripts/setup, which re-runs on every container create.
#
# Pin versions here and mirror them in .pre-commit-config.yaml so the hooks that
# use the -system variants (actionlint-system, gitleaks-system) match these binaries.

FROM mcr.microsoft.com/devcontainers/python:3.14

# System packages required by Home Assistant / its dependencies.
RUN apt-get update \
    && export DEBIAN_FRONTEND=noninteractive \
    && apt-get install -y --no-install-recommends \
        ffmpeg \
        libturbojpeg0 \
        libpcap-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# GitHub CLI — installed from GitHub's official apt repository.
RUN mkdir -p -m 755 /etc/apt/keyrings \
    && curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg \
        -o /etc/apt/keyrings/githubcli-archive-keyring.gpg \
    && chmod go+r /etc/apt/keyrings/githubcli-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
        > /etc/apt/sources.list.d/github-cli.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends gh \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && gh --version

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

# Tools installed for the vscode user so they are baked into the image.
USER vscode

# Homebrew (Linux) — package manager for user-scoped CLI tools; lazygit is
# installed from it in .devcontainer/scripts/setup. Homebrew refuses to run as
# root, so it lives under the vscode user at /home/linuxbrew/.linuxbrew.
RUN NONINTERACTIVE=1 /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Claude Code — baked in to avoid re-downloading on every container create.
RUN curl -fsSL https://claude.ai/install.sh | bash

USER root
