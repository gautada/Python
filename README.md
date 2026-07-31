# python

A small, opinionated Python base container image for the gautada container
fleet, built on top of [`gautada/debian`](https://github.com/gautada/debian).

It has exactly three jobs:

1. A deployable Python environment - `kubectl exec ... -- python` should
   just work.
2. The `FROM` for staged builds - build in one stage, `COPY --from=` the
   result into a clean second stage.
3. The `FROM` for real Python applications, the way
   [`gautada/hermes`](https://github.com/gautada/hermes) does today on top
   of `debian` directly.

This image deliberately does not include `git`, `build-essential`, or `pip`.
See "Non-goals" below.

## Base image and build args

- Base image: `docker.io/gautada/debian:${DEBIAN_IMAGE}`
- `uv`/`uvx` binaries copied in from `${UV_IMAGE}` (Astral's official image)
- Default `DEBIAN_IMAGE`: `docker.io/gautada/debian:13.6`
- Default `UV_IMAGE`: `ghcr.io/astral-sh/uv:0.11.6`

Example build:

```bash
podman build -t python \
  --build-arg DEBIAN_IMAGE=docker.io/gautada/debian:13.6 \
  --build-arg UV_IMAGE=ghcr.io/astral-sh/uv:0.11.6 \
  .
```

## What this image configures

- Installs: `python3`, `python3-venv`, `python-is-python3`
- Copies in `uv` and `uvx` as single static binaries
- Sets:
  - `PYTHONUNBUFFERED=1`
  - `PYTHONDONTWRITEBYTECODE=1`
  - `UV_LINK_MODE=copy`
- Overrides `/usr/bin/container-version` to report the Python interpreter
  version instead of the base image's Debian version.
- Adds two health check drop-ins (see below).

Everything else - user, UID/GID, shell, volumes, sudoers, cron, s6
entrypoint - is inherited unchanged from `gautada/debian`. See
[that image's README](https://github.com/gautada/debian) for the full list.

## Non-goals

This image stays small and opinionated on purpose:

- No `git`, `build-essential`, or compilers. If a downstream build needs
  them, add them in that downstream Containerfile (see "Using this image as
  a build stage" below).
- No `pip`. `uv` is the one dependency manager this image ships with; `uv
  pip ...` is the pip-compatible escape hatch for anyone who wants that
  syntax.
- No pinned or third-party Python version. This image tracks whatever
  `python3` Debian's own repository provides for the base image's release.

## Interactive use

```bash
kubectl exec -n code deploy/python -it -- python
```

or locally:

```bash
podman run --rm -it gautada/python python
```

Both work because the container stays alive under the inherited
`s6-svscan` entrypoint, and `python-is-python3` puts `python` on `PATH`.

## Using this image as a build stage

For a downstream project with a build heavier than "pip install and go" -
cloning a repository, resolving a large dependency set - build in a first
stage and copy only the result into a clean second stage. Neither stage
needs anything beyond what this image and the app's own dependencies
require:

```dockerfile
FROM docker.io/gautada/python:TAG AS build
RUN apt-get update \
 && apt-get install --yes --no-install-recommends build-essential git \
 && apt-get clean && rm -rf /var/lib/apt/lists/*
WORKDIR /opt/app
RUN git clone --filter=blob:none "${APP_REPOSITORY}" . \
 && git checkout "${APP_REF}" \
 && uv sync --frozen --no-install-project

FROM docker.io/gautada/python:TAG
COPY --from=build /opt/app/.venv /opt/app/.venv
ENV PATH=/opt/app/.venv/bin:$PATH
```

`gautada/hermes` is the model for a full application built this way; it
currently builds directly on `gautada/debian` and is expected to migrate to
`gautada/python` as its base once this image is available.

## Runtime helpers

Inherited from `gautada/debian`, unchanged except where noted:

- `/usr/bin/container-version` - **overridden**: prints the `python3`
  interpreter version.
- `/usr/bin/container-backup`, `/usr/bin/container-signature`,
  `/usr/bin/container-basesignature`, `/usr/bin/container-signaturecheck` -
  inherited as-is.
- `/usr/bin/container-health` and its symlinks (`container-liveness`,
  `container-readiness`, `container-startup`, `container-test`) - inherited
  as-is.

## Health check behavior

Two drop-ins are added to `/etc/health.d/`, on top of the base image's own
(`osversion-check`, `packages-check`, `appversion-check`):

- `/etc/health.d/pythonversion-check` - confirms `python3` and `python`
  both resolve and run.
- `/etc/health.d/uv-check` - confirms `uv` and `uvx` both resolve and run.

Neither needs network access or runtime configuration, so both are valid
for liveness, readiness, startup, and test checks alike.

## Downstream usage notes

- Override `/usr/bin/container-version` again to report your application's
  version, not the interpreter's.
- Add app-specific health checks under `/etc/health.d/`.
- Add `git`, `build-essential`, or any other build-time package in your own
  Containerfile - don't expect them here.
- Add service directories under `/etc/services.d/<service>/run` for any
  process that should run under the inherited `s6-svscan` supervisor.

## Project structure

```text
.
├── .args
├── .gitignore
├── Containerfile
├── README.md
├── etc
│   └── health.d
│       ├── pythonversion-check
│       └── uv-check
└── usr
    └── bin
        └── container-version
```

## License

[Debian Free Software Guidelines
(DFSG)](https://www.debian.org/social_contract#guidelines)
