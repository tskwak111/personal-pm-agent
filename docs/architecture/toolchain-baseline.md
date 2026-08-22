# Toolchain Baseline and Version Policy

- **Verified on:** 2026-08-23 (Asia/Seoul)
- **Purpose:** lock a reproducible major-version baseline without pretending that a future patch version is known in advance.

## Baseline

| Component | Baseline | Policy |
|---|---:|---|
| Python | 3.13.x | Pin the latest compatible security/maintenance patch in `.python-version` and CI image during P0-T01. |
| Node.js | 24.x LTS | Pin an LTS patch in `.node-version`; do not use Current-only Node for production. |
| pnpm | 10.x | Keep the plan's vetted major; pin an exact patch in `packageManager` and the lockfile. Upgrade major only through ADR. |
| FastAPI | 0.141.x | Pin an exact patch compatible with the selected Pydantic/Starlette versions. |
| PostgreSQL | 18.x | Pin an exact container patch/digest and exercise backup/restore before release. |
| Redis | 8.x | Pin an exact security-patched image digest; Redis is not the official Planning Core store. |
| Next.js | 16.x | Select the latest security-patched 16.x available on implementation day; never pin a known vulnerable patch. |
| React | 19.2.x | Pin the latest compatible security-patched 19.2.x release. |

## Official verification sources

These URLs are recorded for engineers and dependency-update automation:

- Python releases: `https://www.python.org/downloads/`
- Node.js release status: `https://nodejs.org/en/about/previous-releases`
- PostgreSQL current documentation: `https://www.postgresql.org/docs/current/`
- Redis release documentation: `https://redis.io/docs/latest/develop/whats-new/`
- FastAPI release notes: `https://fastapi.tiangolo.com/release-notes/`
- Next.js releases: `https://nextjs.org/blog`
- React releases: `https://react.dev/blog`
- pnpm releases: `https://pnpm.io/blog/releases`

## Patch-selection gate

P0-T01 must record the exact resolved versions in `docs/status/DECISION_LOG.md` and satisfy all of the following:

1. The version is published by the official project.
2. The version is not end-of-life.
3. No unresolved critical advisory applies to the selected patch and enabled feature set.
4. All direct dependencies resolve from lockfiles with integrity metadata.
5. Container images use immutable digests in staging and production.
6. Renovate or Dependabot opens update PRs; updates do not bypass tests or release gates.

The major-version baseline is architectural. Exact patch versions are implementation evidence and may move through reviewed dependency-update commits.
