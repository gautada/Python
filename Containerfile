ARG DEBIAN_IMAGE=docker.io/gautada/debian:latest
ARG UV_IMAGE=ghcr.io/astral-sh/uv:latest

FROM ${UV_IMAGE} AS uv
FROM ${DEBIAN_IMAGE} AS python

# ╭――――――――――――――――――╮
# │ METADATA           │
# ╰――――――――――――――――――╯
LABEL org.opencontainers.image.title="python"
LABEL org.opencontainers.image.description="A small, opinionated Python base container."
LABEL org.opencontainers.image.url="https://hub.docker.com/r/gautada/python"
LABEL org.opencontainers.image.source="https://github.com/gautada/python"
LABEL org.opencontainers.image.license="Debian Free Software Guidelines (DFSG)"

# ╭――――――――――――――――――╮
# │ PACKAGES           │
# ╰――――――――――――――――――╯
# This is deliberately the minimum needed to run Python and resolve `python`
# on PATH. No compilers, no git, no pip. Downstream images add whatever their
# own build needs (see README: "Using this image as a build stage").
#
# python3 - the interpreter
# python3-venv - venv module, needed by some tooling built on top of uv
# python-is-python3 - makes `python` resolve, not just `python3`
RUN apt-get update \
 && apt-get install --yes --no-install-recommends \
            python3 python3-venv python-is-python3 \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

# ╭――――――――――――――――――╮
# │ UV                 │
# ╰――――――――――――――――――╯
# uv is the one dependency manager this image is opinionated about. It ships
# as a single static binary, so pulling it in costs almost nothing in image
# size and needs no compiler toolchain.
COPY --from=uv /uv /uvx /usr/local/bin/

# ╭――――――――――――――――――╮
# │ ENVIRONMENT        │
# ╰――――――――――――――――――╯
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_LINK_MODE=copy

# ╭――――――――――――――――――╮
# │ VERSION            │
# ╰――――――――――――――――――╯
# Overrides the base image's Debian version reporter, per debian's own
# contract: container-version should print ONLY this layer's version.
COPY usr/bin/container-version /usr/bin/container-version
RUN chmod 0755 /usr/bin/container-version

# ╭――――――――――――――――――╮
# │ HEALTH             │
# ╰――――――――――――――――――╯
# Adds two drop-ins to the base image's health.d mechanism. Both run
# standalone (no network, no runtime config), so they're valid for
# liveness, readiness, startup, and test alike.
COPY etc/health.d/pythonversion-check /etc/health.d/pythonversion-check
COPY etc/health.d/uv-check /etc/health.d/uv-check
RUN chmod 0755 /etc/health.d/pythonversion-check /etc/health.d/uv-check

# ╭――――――――――――――――――╮
# │ BUILD DEPENDENCIES │
# ╰――――――――――――――――――╯
# Not installed here - just placed on PATH so a downstream build stage can
# `RUN install-build-deps` without a COPY step of its own. Never invoked in
# this image itself; see README: "Using this image as a build stage".
COPY bin/install-build-deps /usr/local/bin/install-build-deps
RUN chmod 0755 /usr/local/bin/install-build-deps

# ╭――――――――――――――――――╮
# │ SCRIPTS            │
# ╰――――――――――――――――――╯
# A small set of ready-to-run reference scripts, owned by the inherited
# `debian` user. Some need a dependency this image doesn't ship (see each
# script's own header comment for the `uv run --with ...` workaround) -
# that's deliberate, not an oversight; see README: "Scripts".
COPY --chown=debian:debian scripts/*.py /home/debian/scripts/

# ╭――――――――――――――――――╮
# │ CONTAINER          │
# ╰――――――――――――――――――╯
# ENTRYPOINT, WORKDIR, USER, and VOLUMEs are all inherited unchanged from
# gautada/debian. That's what keeps `kubectl exec ... -- python` working
# (the pod stays alive under s6) and keeps this image predictable as a
# FROM target for staged builds.
