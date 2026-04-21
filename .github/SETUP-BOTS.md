# Setting up `bithuman-ci[bot]` and `bithuman-deps[bot]`

Creating a GitHub App can't be done from the API — GitHub requires a
human to click "Create" in the web UI. This page gives the exact
click-through steps. One-time setup, ~10 minutes total.

## 1. Create the two apps

Open [`app-manifests/create.html`](app-manifests/create.html) in a
browser (double-click the file in Finder — `file://` works). Click each
button once:

1. **Create `bithuman-ci`** → GitHub shows a confirmation page with the
   permissions from [`bithuman-ci.json`](app-manifests/bithuman-ci.json)
   pre-filled. Click **Create GitHub App**.
2. **Create `bithuman-deps`** → same flow with
   [`bithuman-deps.json`](app-manifests/bithuman-deps.json).

After each creation GitHub lands you on the app's settings page. For
each app, do the following once:

- **Upload avatar:** scroll to "Display information" → upload
  [`bot-avatars/bithuman-ci.png`](bot-avatars/bithuman-ci.png) or
  [`bot-avatars/bithuman-deps.png`](bot-avatars/bithuman-deps.png).
  These are logo-variant glyphs (no human faces).
- **Note the App ID** shown at the top of the settings page. You'll
  need it for secrets below.
- **Generate a private key:** scroll to "Private keys" → click
  *Generate a private key*. A `.pem` file downloads. Keep it — you
  need its contents for secrets below.

## 2. Install each app on both repos

From each app's settings → "Install App" → click the `bithuman-product`
org → check *Only select repositories* → pick both:

- `bithuman-python-sdk`
- `bithuman-examples`

## 3. Add the secrets

The workflows read four repo secrets per repo. Set them on **both**
repos (SDK and examples). The fastest way is the `gh` CLI — run once
per repo from the repo root:

```bash
gh secret set BITHUMAN_CI_APP_ID       --body "<bithuman-ci App ID>"
gh secret set BITHUMAN_CI_PRIVATE_KEY  < path/to/bithuman-ci.<date>.private-key.pem
gh secret set BITHUMAN_DEPS_APP_ID     --body "<bithuman-deps App ID>"
gh secret set BITHUMAN_DEPS_PRIVATE_KEY < path/to/bithuman-deps.<date>.private-key.pem
```

Or via the web: Settings → Secrets and variables → Actions → *New
repository secret* × 4.

> **Tip:** set these as *organization* secrets scoped to both repos
> instead of per-repo, so rotation is one place. Org settings →
> Secrets and variables → Actions → *New organization secret*, scope
> *Selected repositories*.

## 4. Verify

After secrets are in place:

```bash
gh workflow run bithuman-ci    # exercises bithuman-ci[bot] check run
gh workflow run bithuman-deps --field dryRun=true   # exercises bithuman-deps[bot] without opening PRs
```

Within a minute each run should show a check or log line attributed to
the correct `[bot]` identity. If you see `github-actions[bot]` where
you expected `bithuman-ci[bot]`, the App ID / private-key secrets
aren't wired up.

## 5. Rotating the private keys

When a key is compromised or every 12 months, whichever comes first:

1. App settings → *Generate a private key* (keep the old one active
   while you roll).
2. `gh secret set BITHUMAN_*_PRIVATE_KEY < new-key.pem` on both repos
   (or update the org secret once).
3. App settings → *Delete* the old key.

## What the bots will and won't do

See [`../MAINTAINERS.md`](../MAINTAINERS.md#automation) for the
authoritative list. Any action you see from a `[bot]` identity not on
that list is unauthorised and should be flagged to a human maintainer.
