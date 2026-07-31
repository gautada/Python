# Building the missing middle layer: a `gautada/python` base image

I've got a `debian` base image and I've got `hermes`, an actual application
running on top of it. What I don't have is anything in between — and it turns
out "anything in between" is exactly the thing I keep needing.

## The gap

Every time I containerize a Python thing, I end up doing the same handful of
steps: install `python3`, install `python-is-python3` so `python` actually
resolves, pull in `uv` because I'm not writing another `requirements.txt` by
hand in 2026, set the usual `PYTHONUNBUFFERED` and `PYTHONDONTWRITEBYTECODE`
env vars, and then get on with whatever the actual project needed. `hermes`
does all of this today, directly on top of `debian`. It works, but it means
the "how do I get Python working in this fleet" answer is copy-pasted into
every repo that needs it, instead of living in exactly one place.

So: a `python` base image. Small, boring, and shared.

## What it actually needs to do

I landed on three jobs, and I wrote them down in that order deliberately
because they're in increasing order of how much they constrain the design:

1. **Something I can `kubectl exec` into.** `kubectl exec -n code
   deploy/python -it -- python` should just work and drop me into a REPL.
   That's it. That's the whole bar for job one.
2. **A `FROM` for staged builds.** Sometimes I've got a build that's more
   involved than "pip install and go" — clone a repo, compile something,
   assemble a dependency set — and I want to do that heavy lifting in one
   stage and then hand off a slim artifact to a second stage. Both stages
   should be able to start from this same image.
3. **A `FROM` for real apps**, the same way `hermes` sits on `debian` right
   now. Eventually `hermes` itself should sit on `python` instead, and get
   its Python setup for free.

None of these are exotic. What made me actually sit down and spec this out
carefully is that they pull in slightly different directions, and I didn't
want to find that out halfway through writing a Containerfile.

## The constraint that mattered most: don't let it grow

The temptation with a base image is to keep adding "just one more thing" —
git, because you'll probably clone something; build-essential, because
you'll probably compile something; maybe pip too, just in case someone
doesn't want `uv`. I looked at how `hermes` builds today and it already adds
`build-essential`, `cmake`, `git`, and a pile of other things directly on top
of `debian`, on the fly, for exactly the one build it needs.

That's actually the right instinct, and I don't want to take it away from
downstream images by pre-baking their choices into the shared layer. So the
rule I landed on is: this image gets `python3`, `python-is-python3`, and
`uv`. Nothing that compiles things, nothing that clones things. If a
downstream Containerfile needs `build-essential` and `git`, it adds them
itself, in its own layer, the same way `hermes` already does — just starting
one layer higher up the stack.

`uv` earns its spot here specifically because it's a single static binary
(I'm copying it in from Astral's official image, the same trick `hermes`
already uses for both `uv` and Node) — it costs almost nothing in image size
and it means I never have to think about pip's version-check chatter or venv
bootstrapping ceremony again. It's opinionated, but it's opinionated in a way
that stays small.

## The part that surprised me: `container-version`

`debian` ships a `/usr/bin/container-version` script whose entire job is to
print a version number, and its own comment says, plainly, that downstream
images are supposed to override it. `hermes` does exactly that today —
its version of the script reports the Hermes app version instead of the raw
Debian version. That's a clean little contract, and it means the `python`
image needs to participate in it too: override `container-version` once more
to report the interpreter version, so the chain reads sensibly at every
layer — Debian version at the base, Python version in the middle, app version
at the top. Small detail, but it's exactly the kind of thing that's easy to
skip and annoying to retrofit later.

## Where the two build-stage jobs actually diverge

Job one (the `kubectl exec` target) wants the image to just sit there,
running, with nothing overridden — inherit `debian`'s `s6-svscan` entrypoint
unchanged, keep the same user, keep the same volumes. Boring on purpose.

Job two and three (the build-stage jobs) don't run the image at all — they
build on top of it, `COPY --from=` the result, and throw the rest away.
For those, the image needs to document a pattern more than it needs to *be*
anything special: here's how you add `build-essential` and `git` in a first
stage, `git clone` and `uv sync` your project, and then `COPY --from=build`
the resulting `.venv` into a clean second stage that never saw a compiler.

The nice part is that "boring and unchanged" for job one and "documented
recipe" for job two don't conflict — they're both just consequences of
keeping the base image itself minimal and putting the opinions in the
README instead of the Containerfile.

## What's actually going out for review

I didn't want to just start writing a Containerfile from vibes, especially
since this thing is going to sit underneath everything else I build in
Python going forward — mistakes here get inherited by every downstream repo.
So the concrete next step is a spec, not code: [`build-prompt.md`](build-prompt.md)
in this repo lays out the exact packages, the exact `Containerfile` sections
in `debian`'s own comment-block style, the two new health checks
(`pythonversion-check`, `uv-check`), the `.args` defaults, the README
sections including a real staged-build example, and the CI/CD wiring —
copied verbatim from `hermes`'s working `container.yaml` against
`gautada/cicd@main`, since there's no reason to reinvent that part.

It also ends with four open questions I genuinely don't have strong opinions
on yet — mostly around version pinning for `uv` and whether `python`'s
version should show up somewhere more formal than just what `container-version`
reports. Those are worth deciding before the first line of Containerfile
gets written, not after.

Once that spec gets a look and a nod, the actual build is small: it's
deliberately a thin, almost trivial layer. That's the point.
