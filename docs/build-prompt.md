# Build Prompt: `gautada/python` base container

Status: **superseded, kept for historical context.** The `Containerfile` now
exists and was built from this spec, but [`consolidation-directive.md`](consolidation-directive.md)
overrides this document's guidance on two points: version pinning (this doc
pins `DEBIAN_IMAGE`/`UV_IMAGE`; the directive drops pinning in favor of
`:latest`) and the CI/CD workflow source (this doc copies the older
per-job wiring from `hermes`; the directive copies the newer, simpler
harness from `gautada/cicd`'s own `.github/workflows/container.yaml`
directly). Read the directive for what actually shipped.

## Mission

Produce a small, opinionated Python base image, `docker.io/gautada/python`, that
sits directly on top of [`gautada/debian`](https://github.com/gautada/debian) in
the container fleet. It has exactly three jobs:

1. **A deployable Python environment.** Running as a long-lived pod so that
   `kubectl exec -n code deploy/python -it -- python` drops straight into a
   working interactive interpreter.
2. **The `FROM` for staged builds.** Downstream projects with a non-trivial
   build (clone a repo, compile native deps, install a big dependency set) use
   this image as an early stage, then `COPY --from=` the built artifact into a
   final stage — which is also based on this image, but without the build/test
   tooling.
3. **The `FROM` for real applications**, the way
   [`gautada/hermes`](https://github.com/gautada/hermes/tree/dev) does today —
   except `hermes` should eventually build `FROM gautada/python` instead of
   `FROM gautada/debian` directly, inheriting Python for free.

## Non-goals

Keep it small and opinionated. Specifically do **not**:

- Bake in `build-essential`, `git`, compilers, or any app-specific system
  packages. Those belong in the downstream Containerfile that needs them
  (exactly as `hermes` already does on top of `debian`).
- Add a second language runtime (no Node, no Rust toolchain) — that's a
  `hermes`-level concern, not a `python`-level one.
- Pin or vendor a specific Python version outside of whatever Debian trixie's
  `python3` package provides. No deadsnakes PPA, no compiling from source.
- Reinvent anything `debian` already provides (s6 supervision, cron, health
  framework, sudoers, users, volumes, signature scripts). Inherit, don't
  duplicate.

## Upstream references (read these, then mirror their conventions exactly)

- [`gautada/debian`](https://github.com/gautada/debian) — the base this image
  extends. Study `Containerfile`, `README.md`, `.args`, and
  `usr/bin/container-*` for the exact comment-block style, ARG names, and
  helper-script contract.
- [`gautada/cicd`](https://github.com/gautada/cicd) — the reusable
  GitHub Actions workflows. Study `README.md` for the promotion model
  (`:dev` → `:candidate` → `:latest`, human-reviewed promotion PR).
- [`gautada/hermes`](https://github.com/gautada/hermes/tree/dev) — the most
  advanced downstream consumer today. Study its `Containerfile` (multi-stage
  `COPY --from=` pattern for `uv` and `node`, `container-version` override,
  added `s6` service) and its `.github/workflows/container.yaml` (the actual
  wiring against `cicd@main`). This is the template for the CI/CD file below,
  and for the "staged build" recipe this image needs to document.

## Repo layout

Mirror `debian`'s flat layout:

```
.
├── .args
├── .gitignore
├── Containerfile
├── README.md
├── etc
│   └── health.d
│       ├── pythonversion-check
│       └── uv-check
├── usr
│   └── bin
│       └── container-version        # overridden from debian's default
└── .github
    └── workflows
        └── container.yaml
```

No `etc/services.d`, no `etc/sudoers.d`, no new user — all inherited unchanged
from `debian`.

## Containerfile requirements

1. **Base and pinning**, same shape as `debian`'s own `ARG IMAGE_VERSION`:
   ```dockerfile
   ARG DEBIAN_IMAGE=docker.io/gautada/debian:13.6
   ARG UV_IMAGE=ghcr.io/astral-sh/uv:0.11.6

   FROM ${UV_IMAGE} AS uv
   FROM ${DEBIAN_IMAGE}
   ```
   Both ARGs get defaults recorded in `.args`, same as `debian`'s pattern.

2. **OCI labels** — same four/five `LABEL org.opencontainers.image.*` lines
   `debian`'s Containerfile uses, updated for this image (`title="python"`,
   `source="https://github.com/gautada/python"`, etc).

3. **Packages** — apt-installed, no recommends, cleaned up in the same RUN
   layer (mirror `debian`'s exact `apt-get update && apt-get install --yes
   --no-install-recommends ... && apt-get clean && rm -rf
   /var/lib/apt/lists/*` idiom):
   - `python3`
   - `python3-venv`
   - `python-is-python3` — this is what makes plain `python` resolve on
     `PATH`, which is required for the `kubectl exec ... -- python` use case.

   Deliberately **not** installing `python3-pip`. `uv` is the one dependency
   manager this image is opinionated about; document `uv pip` as the pip-
   compatible escape hatch for anyone who wants pip syntax.

4. **`uv` / `uvx`** — copied in from the pinned `uv` image stage, same
   mechanism `hermes` already uses:
   ```dockerfile
   COPY --from=uv /uv /uvx /usr/local/bin/
   ```

5. **Environment** — set the standard Python container hygiene vars:
   ```dockerfile
   ENV PYTHONUNBUFFERED=1 \
       PYTHONDONTWRITEBYTECODE=1 \
       UV_LINK_MODE=copy
   ```

6. **`container-version` override** — replace the inherited
   `/usr/bin/container-version` (which just `cat`s `/etc/debian_version`) with
   one that prints `python3 --version` output. Follow `debian`'s own comment in
   that script verbatim: this file exists precisely so downstream images
   override it again for their own app version. Keep the same "print ONLY the
   version, nothing else" contract.

7. **Health checks** — add to `/etc/health.d/`, following the existing
   drop-in contract in `debian`'s `container-health` (executable script,
   receives the check type as `$1`, exit 0/non-zero, same colored-output
   style as `osversion-check`/`packages-check`):
   - `pythonversion-check` — confirms `python3` and `python` both resolve and
     run.
   - `uv-check` — confirms `uv --version` and `uvx --version` both succeed.

   Do **not** touch `/usr/bin/container-health` itself or the
   liveness/readiness/startup/test symlinks — those are inherited unchanged.

8. **No `ENTRYPOINT`, no `CMD`, no `WORKDIR` override.** Inherit `debian`'s
   `s6-svscan` entrypoint and root `WORKDIR` as-is. This is what keeps the pod
   alive for `kubectl exec` and keeps the image usable as a build stage
   without surprising a downstream `WORKDIR`.

9. **No `USER`/`UID`/`GID`/volume changes.** Inherit `debian`'s `debian`
   user (1001:1001) and the four `/mnt/volumes/*` mounts unchanged. A generic
   Python base has no opinion on what app-specific data lives where — that's
   for the downstream image.

## `.args` file

```
DEBIAN_IMAGE=docker.io/gautada/debian:13.6
UV_IMAGE=ghcr.io/astral-sh/uv:0.11.6
GITHUB_SIGNATURE=
```

## README requirements

Structure it exactly like `debian`'s `README.md` (same section order and
headings: base image and build args, what this image configures, runtime
helpers, health check behavior, downstream usage notes, project structure,
license), plus two sections `debian`'s README doesn't need:

- **Interactive use** — the literal `kubectl exec -n code deploy/python -it
  -- python` example, and a `podman run --rm -it gautada/python python`
  equivalent for local use.
- **Using this image as a build stage** — a concrete two-stage example
  Containerfile for a downstream project, e.g.:
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
  This is the pattern `hermes` should migrate to once this image exists —
  call that out explicitly as a follow-on, not part of this repo's scope.

## CI/CD (`gautada/cicd`)

Add `.github/workflows/container.yaml` copied from `hermes`'s working file
verbatim, with no logic changes — just let it resolve to this repo:

```yaml
name: "Continuous Integration: Build and Publish Multi-Architecture Container Images"

'on':
  workflow_dispatch: {}
  push:
    branches:
      - dev
  pull_request:
    branches:
      - main

permissions:
  contents: read
  checks: write
  statuses: write
  security-events: write
jobs:
  check:
    uses: gautada/cicd/.github/workflows/ci-linter.yaml@main
  deep-scan:
    needs: check
    uses: gautada/cicd/.github/workflows/ci-deep-scan.yaml@main
  build-arm64:
    needs: check
    uses: gautada/cicd/.github/workflows/ci-podman-build.yaml@main
    with:
      architecture: "arm64"
    secrets:
      REGISTRY_USERNAME: ${{ secrets.DOCKERIO_REGISTRY }}
      REGISTRY_TOKEN: ${{ secrets.DOCKERIO_TOKEN }}
  build-amd64:
    needs: check
    uses: gautada/cicd/.github/workflows/ci-podman-build.yaml@main
    with:
      architecture: "amd64"
    secrets:
      REGISTRY_USERNAME: ${{ secrets.DOCKERIO_REGISTRY }}
      REGISTRY_TOKEN: ${{ secrets.DOCKERIO_TOKEN }}
  publish:
    needs: [build-arm64, build-amd64]
    uses: gautada/cicd/.github/workflows/ci-podman-publish.yaml@main
    with:
      architectures: '["arm64", "amd64"]'
    secrets:
      REGISTRY_USERNAME: ${{ secrets.DOCKERIO_REGISTRY }}
      REGISTRY_TOKEN: ${{ secrets.DOCKERIO_TOKEN }}
  clean:
    needs: [publish]
    uses: gautada/cicd/.github/workflows/ci-registry-clean.yaml@main
    secrets:
      REGISTRY_USERNAME: ${{ secrets.DOCKERIO_REGISTRY }}
      REGISTRY_TOKEN: ${{ secrets.DOCKERIO_TOKEN }}
  test:
    needs: [clean]
    uses: gautada/cicd/.github/workflows/ci-container-test.yaml@main
    secrets:
      REGISTRY_USERNAME: ${{ secrets.DOCKERIO_REGISTRY }}
      REGISTRY_TOKEN: ${{ secrets.DOCKERIO_TOKEN }}
  release:
    needs: [test]
    uses: gautada/cicd/.github/workflows/cd-tag-latest.yaml@main
    secrets:
      REGISTRY_USERNAME: ${{ secrets.DOCKERIO_REGISTRY }}
      REGISTRY_TOKEN: ${{ secrets.DOCKERIO_TOKEN }}
```

Repo-side prerequisites (do these in the GitHub repo settings, not in code):

- `DOCKERIO_REGISTRY` and `DOCKERIO_TOKEN` configured as environment secrets,
  scoped per `cicd`'s security model (never exposed to PR-triggered runs).
- Branch protection on `main` requiring the promotion PR to be reviewed and
  merged by a human — `cicd` explicitly never auto-merges that PR.
- Confirm `/usr/bin/container-test` (symlinked from `container-health`) and
  `/usr/bin/container-version` (overridden per above) both exist in the image
  before the first CI run, since `ci-container-test.yaml` depends on them.

## Definition of done

- [ ] `Containerfile` builds locally with `podman build -t python .` using the
      defaults in `.args`.
- [ ] `podman run --rm -it python python` opens an interactive REPL.
- [ ] `podman run --rm python container-version` prints a clean Python
      version string, nothing else.
- [ ] `podman exec <container> container-test` passes, including the two new
      `pythonversion-check` / `uv-check` health drop-ins.
- [ ] `podman run --rm python uv --version` and `uvx --version` both succeed.
- [ ] Image size is meaningfully smaller than `hermes` (sanity check that
      nothing build-only leaked into this layer).
- [ ] README reviewed against `debian`'s for section-by-section parity, plus
      the two Python-specific sections above.
- [ ] `.github/workflows/container.yaml` present and a `dev` push produces a
      `:dev` tagged image in the registry.

## Open questions for you to decide before implementation starts

1. **`uv` version pin** — `0.11.6` above is copied from `hermes`'s current
   pin as a placeholder. Do you want this image to track `uv` latest, or pin
   and bump deliberately like `DEBIAN_IMAGE`?
2. **`python-is-python3`** — confirmed necessary for the `kubectl exec ...
   python` requirement. Any objection to that package specifically, or
   preference for a manual `ln -s` instead of the apt package?
3. **Default registry tag scheme** — should this repo's `:latest` track
   Debian trixie's default `python3` (currently 3.13), or do you want an
   explicit `PYTHON_VERSION` label surfaced somewhere (e.g. in the OCI
   labels) so downstream Containerfiles can assert a minimum version at
   build time?
4. **`hermes` migration** — confirmed out of scope for this repo, but worth
   a follow-up ticket once this image ships, so `hermes`'s `Containerfile`
   drops its direct `uv`/`build-essential`/`python3` setup in favor of `FROM
   gautada/python`.
