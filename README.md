# This repository has moved

The contents of `bithuman-product/bithuman-examples` have been folded into
[`bithuman-product/bithuman-sdk-public`](https://github.com/bithuman-product/bithuman-sdk-public)
under `Examples/ + docs/` as part of the 2026-05 GitHub org consolidation
(14 → 7 active repos).

The new repo holds: all bitHuman Cloud / self-hosted / Apple-local SDK examples plus the Mintlify-rendered docs site source.

## Pointers

| Want | Go here |
|---|---|
| Latest source | [`bithuman-sdk-public`](https://github.com/bithuman-product/bithuman-sdk-public) |
| Examples | [`bithuman-sdk-public/Examples/`](https://github.com/bithuman-product/bithuman-sdk-public/tree/main/Examples) |
| Mintlify docs source | [`bithuman-sdk-public/docs/`](https://github.com/bithuman-product/bithuman-sdk-public/tree/main/docs) |
| Public Python SDK metadata | [`bithuman-sdk-public/python/`](https://github.com/bithuman-product/bithuman-sdk-public/tree/main/python) |
| Hosted docs | [docs.bithuman.ai](https://docs.bithuman.ai) (unaffected) |
| File history | preserved — `git filter-repo --to-subdirectory-filter` was used |
| Pre-move snapshot | tag `pre-merge-archive-2026-05-05` on this repo |

## Existing clones

To migrate a local clone:

```bash
git remote set-url origin https://github.com/bithuman-product/bithuman-sdk-public.git
git fetch origin
git checkout main
```

Note that paths now live under `Examples/`, `docs/`, or `python/`.

This repo is kept read-only for at least one quarter (until ~2026-08)
so old links and external references continue to resolve. After that
it will be formally archived.
