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

- Base image: `${DEBIAN_IMAGE}`
- `uv`/`uvx` binaries copied in from `${UV_IMAGE}` (Astral's official image)
- Default `DEBIAN_IMAGE`: `docker.io/gautada/debian:latest`
- Default `UV_IMAGE`: `ghcr.io/astral-sh/uv:latest`

Both are deliberately unpinned - this image tracks whatever `debian` and
`uv` currently publish as `latest`, rather than a version bumped by hand.
That will likely trip CI's "pin your base image" lint rule; that's accepted,
not a bug to fix.

Example build:

```bash
podman build -t python \
  --build-arg DEBIAN_IMAGE=docker.io/gautada/debian:latest \
  --build-arg UV_IMAGE=ghcr.io/astral-sh/uv:latest \
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
- Places `install-build-deps` on `PATH` for downstream build stages (see
  "Using this image as a build stage") and a handful of reference scripts
  under `~/scripts/` (see "Scripts") - neither is used by this image itself.

Everything else - user, UID/GID, shell, volumes, sudoers, cron, s6
entrypoint - is inherited unchanged from `gautada/debian`. See
[that image's README](https://github.com/gautada/debian) for the full list.
That inheritance already covers `ca-certificates`, `curl`, `tzdata`, and a
few other basics - this image doesn't repeat any of it.

## Non-goals

This image stays small and opinionated on purpose:

- No `git`, `build-essential`, or compilers. If a downstream build needs
  them, add them in that downstream Containerfile (see "Using this image as
  a build stage" below).
- No `pip`. `uv` is the one dependency manager this image ships with; `uv
  pip ...` is the pip-compatible escape hatch for anyone who wants that
  syntax.
- No pinned Python or Debian version. This image tracks whatever `python3`
  Debian's current release provides, and whatever `debian`/`uv` currently
  tag as `latest`.
- No additional runtime tooling beyond `python3`/`uv`. Anything a specific
  app needs (`ca-certificates` aside, already inherited) belongs in that
  app's own downstream image, not here.

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

## Scripts

A small set of reference scripts ship under `~/scripts/` (`/home/debian/scripts/`
in the container), each with a header comment describing its purpose and
usage:

- `flask-hello-world.py` - minimal Flask smoke test.
- `deployment-namespace.py` - looks up a k8s Deployment's namespace by name.
- `psql-client.py` - PostgreSQL connectivity/version/SSL check.

`deployment-namespace.py` needs only the standard library (plus `kubectl` on
`PATH`, which this image also doesn't ship). The other two need a package
this image doesn't install (`flask`, `psycopg2`) - run them without touching
the image at all via `uv`'s ephemeral dependency install:

```bash
uv run --with flask ~/scripts/flask-hello-world.py
uv run --with psycopg2-binary ~/scripts/psql-client.py --host db.example.com
```

## Using this image as a build stage

For a downstream project with a build heavier than "pip install and go" -
cloning a repository, resolving a large dependency set - build in a first
stage and copy only the result into a clean second stage. `install-build-deps`
(already on `PATH`, see "What this image configures") installs the usual
build-time set - `build-essential`, `git`, `pkg-config`, `curl`,
`ca-certificates` - for that first stage only:

```dockerfile
FROM docker.io/gautada/python:TAG AS build
RUN install-build-deps
WORKDIR /opt/app
RUN git clone --filter=blob:none "${APP_REPOSITORY}" . \
 && git checkout "${APP_REF}" \
 && uv sync --frozen --no-install-project

FROM docker.io/gautada/python:TAG
COPY --from=build /opt/app/.venv /opt/app/.venv
ENV PATH=/opt/app/.venv/bin:$PATH
```

A full, documentation-only version of this example lives at
[`examples/downstream-build/Containerfile`](examples/downstream-build/Containerfile),
with inline comments on exactly what does and doesn't survive into the run
stage and why.

`gautada/hermes` is the model for a full application built this way; it
currently builds directly on `gautada/debian`. Migrating it to
`gautada/python` is a separate, future piece of work, not part of this repo.

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
- Use `install-build-deps` in your build stage for the common
  `build-essential`/`git`/`pkg-config` set, or add your own packages
  directly - don't expect them baked into the run stage.
- Add service directories under `/etc/services.d/<service>/run` for any
  process that should run under the inherited `s6-svscan` supervisor.

## Project structure

```text
.
├── .args
├── .gitignore
├── Containerfile
├── README.md
├── bin
│   └── install-build-deps
├── docs
│   ├── build-prompt.md
│   ├── blog-python-base-container.md
│   └── consolidation-directive.md
├── etc
│   └── health.d
│       ├── pythonversion-check
│       └── uv-check
├── examples
│   └── downstream-build
│       └── Containerfile
├── scripts
│   ├── deployment-namespace.py
│   ├── flask-hello-world.py
│   └── psql-client.py
└── usr
    └── bin
        └── container-version
```

## License

[Debian Free Software Guidelines
(DFSG)](https://www.debian.org/social_contract#guidelines)
