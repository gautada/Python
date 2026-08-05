# Directive: Consolidate the `python` repos into one image lineage

Status: **ready to execute.** This supersedes the CI/CD and version-pinning
guidance in [`build-prompt.md`](build-prompt.md) where they conflict (see
below) — `build-prompt.md` stays as historical research, this file is the
current instruction set.

## Why this exists

Three things currently answer to "the python repo":

1. **`gautada/Python`** (GitHub, default branch `main`, commit `0897dad`) —
   historically a grab-bag of standalone scripts (`public/*.py`) dispatched
   through `bin/run-python.sh`, which expects a
   `~/Workspace/Python/{public,private}` layout on the machine running it.
2. **This local checkout** (`~/Workspace/Containers/python/dev`, `origin` →
   `gautada/Python`) — `dev` is two commits ahead of `origin/main`
   (`550e700`, `58b7fa2`), not yet pushed. Those commits pivot this repo into
   `gautada/python`: a small Debian-based image (`FROM gautada/debian`,
   `uv`/`uvx`, no `pip`/`git`/`build-essential`). The legacy `public/`
   scripts and `bin/run-python.sh` were left in place, untouched.
3. **`gautada/python2`** — a separate, actively maintained Alpine-based
   pip/JupyterLab "fast drafting" dev container, plus a pile of dead cruft
   (Bazel/TensorFlow `Containerfile`, `drone.yml`, `wetty`/`sshd` sudoers
   snippets, a stray `client.py`).

This directive collapses that into one repo: `gautada/python`, as small as
possible, nothing else.

## Decisions (final — do not re-litigate)

- **No notebook/fast-drafting image in this pass.** `python2`'s Jupyter
  capability is not being rebuilt anywhere right now. That's explicitly
  deferred to a future, separate piece of work.
- **`python2` gets harvested, then deleted** (not archived — delete the
  GitHub repo outright once nothing more is needed from it). See step 5.
- **The legacy scripts survive**, consolidated under `./scripts/*.py` in
  `gautada/python`, `COPY`'d into the image at `~/scripts/*.py`. Clean up
  their names and add a short purpose/usage header to each. `bin/run-python.sh`
  does not survive — its whole job was locating scripts via a
  `~/Workspace/Python` path convention on the host machine, which stops
  applying once the scripts just live inside the image at a fixed path.
- **`.github/workflows/container.yaml` comes from `gautada/cicd`, verbatim.**
  `gautada/cicd`'s own `.github/workflows/container.yaml` is the current
  master template — a thin harness that calls the single reusable
  `gautada/cicd/.github/workflows/cicd-container.yaml@dev` workflow. This is
  a newer, simpler pattern than the multi-job wiring `build-prompt.md`
  copied from `hermes` (separate `check`/`build-arm64`/`build-amd64`/
  `publish`/`clean`/`test`/`release` jobs) — **use the `cicd` version, not
  the `hermes`-derived one from `build-prompt.md`.**
- **No version pinning.** `DEBIAN_IMAGE` and `UV_IMAGE` default to `:latest`,
  not a pinned tag. This will very likely trip hadolint's "pin your base
  image" rule (`DL3007`) in CI — that's accepted, not a bug to fix.
- **`requirements.txt` and `requirements.txt~` are deleted**, not moved.
  Nothing in this repo needs them right now; add a fresh one later once this
  image is actually used to build something that needs pinned Python deps.
- **Downstream stays out of scope**, with one exception: a single example
  Containerfile (step 4) showing the build-stage/run-stage split, purely as
  documentation — it is not a repo, not published, not wired to CI.
- **`hermes` is untouched.** Ignore it entirely this pass.

## What to actually do, in order

### 1. Finish `gautada/python`'s `Containerfile` / `README.md` (`dev` branch)

- [ ] Change `ARG DEBIAN_IMAGE` and `ARG UV_IMAGE` defaults to `:latest`
      (e.g. `docker.io/gautada/debian:latest`, `ghcr.io/astral-sh/uv:latest`)
      and update `.args` and the README's build-arg example to match. Note
      in the README that these are intentionally unpinned.
- [ ] Replace the CI/CD section: copy `gautada/cicd`'s
      `.github/workflows/container.yaml` into
      `gautada/python/.github/workflows/container.yaml` verbatim (it's the
      thin harness calling `cicd-container.yaml@dev` — don't reconstruct the
      older per-job version from `build-prompt.md`).
- [ ] Delete `requirements.txt` and `requirements.txt~`.
- [ ] Delete `bin/run-python.sh` (and the now-empty `bin/` dir if nothing
      else lands there — `bin/install-build-deps` from step 3 will likely
      repopulate it).
- [ ] Run the `build-prompt.md` "Definition of done" checks (`podman build`,
      REPL check, `container-version`, `container-test`, `uv`/`uvx` check) —
      still valid, just re-run them against the `:latest`-based build.

### 2. Consolidate the legacy scripts under `./scripts/`

Move and rename for clarity (kebab-case, purpose-first names):

| From | To | Notes |
| --- | --- | --- |
| `public/flask-hello-world.py` | `scripts/flask-hello-world.py` | Name's already clear, keep it. |
| `public/namespace.py` | `scripts/deployment-namespace.py` | "namespace" alone doesn't say what it does — it looks up a deployment's k8s namespace by name. |
| `public/psql-test-client.py` | `scripts/psql-client.py` | Drop "test" — it's a real connectivity/version-check client, not a test harness. |
| `public/run-public-test.py` | *(delete)* | It's a one-line placeholder (`print("Run test for [PUBLIC] python script.")`) with no real behavior — nothing to carry forward. |

For each script that survives, add a short header comment/docstring (purpose,
how to run it, and any external dependency it needs — see below) rather than
leaving them undocumented.

Update the `Containerfile` to `COPY scripts/*.py` into the image at
`~/scripts/` for whatever user `gautada/debian` runs as (confirm the exact
home directory from `gautada/debian`'s own README/Containerfile — it's the
`debian` user, UID/GID `1001:1001`, so this is almost certainly
`/home/debian/scripts/`). Set ownership to that user, not root.

**Dependency gap to document, not silently paper over**: `flask-hello-world.py`
needs `flask`, `psql-client.py` needs `psycopg2`. Neither ships in this
image (no `pip`, nothing installed beyond `python3`/`uv`) and shouldn't —
baking app dependencies into the shared base contradicts "smallest possible
image." Document the workaround in each script's header and in the README:
`uv run --with flask ~/scripts/flask-hello-world.py` (and similarly `--with
psycopg2-binary` for the psql client) runs them ad hoc without installing
anything into the image itself. `deployment-namespace.py` needs nothing
beyond the standard library plus a working `kubectl` on `PATH` — call that
out too, since `kubectl` isn't in this image either.

### 3. Add the build-stage dependency script

Add `bin/install-build-deps` to `gautada/python` — a script downstream
Containerfiles `COPY` in and `RUN` during their build stage, installing a
sane default "broad build dependencies" set: `build-essential`, `git`,
`pkg-config`, `curl`, `ca-certificates`, using the same `apt-get update &&
apt-get install --yes --no-install-recommends ... && apt-get clean && rm -rf
/var/lib/apt/lists/*` idiom used everywhere else in this image.

### 4. Add one example downstream Containerfile

Under `examples/downstream-build/Containerfile` (docs only — not built by CI,
not a real app): a full two-stage example showing

- **Build stage**: `FROM gautada/python:TAG AS build`, `COPY` + `RUN
  bin/install-build-deps`, then a representative `git clone` + `uv sync`
  for some placeholder project.
- **Run stage**: `FROM gautada/python:TAG` (clean), `COPY --from=build
  /opt/app/.venv /opt/app/.venv`, `ENV PATH=...`.
- Inline comments explicitly calling out what's *not* in the run stage and
  why: no `git`, no `build-essential`, no compiler toolchain, no source
  checkout — only the built `.venv`. This is the size-constraint argument
  made concrete, not just asserted in prose.

### 5. Harvest anything useful from `python2`, then delete it

Before deleting, do one deliberate pass over `python2` for anything worth
porting into `gautada/python` on its own merits (not as part of a notebook
image, which isn't happening this pass). Candidates already reviewed and
ruled out — don't re-import these:

- Its `pre-commit` script and `.shellcheckrc` are themselves just local
  copies of `gautada/cicd`'s canonical templates
  (`gautada/cicd/bin/pre-commit`, `gautada/cicd/templates/pre-commit/`) — if
  `gautada/python` wants pre-commit tooling, pull it from `gautada/cicd`
  directly, not from `python2`.
- Everything else in `python2` (Alpine base, `pip`, Jupyter, the
  Bazel/TensorFlow `Containerfile`, `drone.yml`, `wetty-wheel` /
  `wheel-ssh-keygen` / `wheel-sshd`, `client.py`, `html.txt`) is either
  superseded by what `gautada/python` already does differently, or dead
  weight tied to the deferred notebook use case.

If that pass turns up nothing else, delete the `gautada/python2` repository
on GitHub (Settings → General → Delete this repository) — not just archive
it. Its open issue (#1, "Interface should be Jupyter notebook") and merged
PRs are lost with the deletion; that's accepted since the capability isn't
being preserved anywhere else right now.

## Guardrails

There are almost none, deliberately — this `dev` branch is free to change in
any way needed to reach the smallest working image. The only two hard
constraints:

- **No `pip`, no `git`, no `build-essential`, no compilers, no app-specific
  packages baked into the shared image.** Anything beyond `python3`,
  `python3-venv`, `python-is-python3`, and `uv`/`uvx` needs a specific reason
  and should probably live in a downstream image instead, not here.
- **`kubectl exec -n code deploy/python -it -- python` must keep working** —
  a plain interactive REPL, no extra ceremony. That's the one behavior this
  whole image exists to guarantee.

Downstream projects (`hermes`, any future notebook image) are explicitly out
of scope for this pass beyond the one documentation-only example in step 4.

## Definition of done

- [ ] `Containerfile` builds locally with `podman build -t python .` on the
      `:latest`-pinned defaults.
- [ ] `podman run --rm -it python python` opens an interactive REPL.
- [ ] `podman run --rm python container-version` prints a clean Python
      version string.
- [ ] `podman exec <container> container-test` passes, including
      `pythonversion-check` / `uv-check`.
- [ ] `~/scripts/*.py` are present in the built image, owned by the `debian`
      user, each with a header comment describing purpose/usage/deps.
- [ ] `bin/install-build-deps` exists and is used by the example in
      `examples/downstream-build/Containerfile`.
- [ ] `.github/workflows/container.yaml` is the verbatim `gautada/cicd`
      harness, and a `dev` push produces a `:dev` tagged image.
- [ ] `requirements.txt`, `requirements.txt~`, and `bin/run-python.sh` are
      gone.
- [ ] `python2` has been reviewed for anything worth harvesting and then
      deleted from GitHub.
