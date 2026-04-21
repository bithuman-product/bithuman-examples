# Maintainers

Who is responsible for this repo, and which identities you'll see on
commits, comments, and review.

## Humans

Real people. These are the folks who merge changes and make final
calls. Reach them on the emails below or via the org on GitHub. If you
see a commit, review, or approval from one of these accounts, a human
did it.

| Name     | GitHub             | Email              | Role                      |
| -------- | ------------------ | ------------------ | ------------------------- |
| Steve Gu | [@sgu-bithuman][1] | sgu@bithuman.ai    | Lead maintainer           |

[1]: https://github.com/sgu-bithuman

<!--
  Add new human maintainers here. This section is reserved for real
  people — no bots, no shared service accounts, and no AI assistants.
  Automation identities belong in the section below.
-->

## Automation

GitHub Apps owned by the `bithuman-product` org. Every action below is
performed by one of these bot identities — never by a human account
pretending to be automation, and never by an AI assistant using a
human's name.

| Identity             | What it does                                                                    | Scope                    |
| -------------------- | ------------------------------------------------------------------------------- | ------------------------ |
| `bithuman-ci[bot]`   | Validates docker-compose + YAML configs, lints Python snippets, posts checks.   | This repo, read + write. |
| `bithuman-deps[bot]` | Runs Renovate on schedule; opens dependency-update PRs.                         | This repo, read + write. |

Source of truth for each bot:

- App manifests: [`.github/app-manifests/`](.github/app-manifests/)
- Avatars (logo-variant glyphs, no faces): [`.github/bot-avatars/`](.github/bot-avatars/)
- Workflows that mint app tokens: [`.github/workflows/bithuman-ci.yml`](.github/workflows/bithuman-ci.yml), [`.github/workflows/bithuman-deps.yml`](.github/workflows/bithuman-deps.yml)
- Installation + secrets guide: [`.github/SETUP-BOTS.md`](.github/SETUP-BOTS.md)

If you see a commit or PR from an identity **not** in either table,
treat it as unauthorized and flag it to a human maintainer.
