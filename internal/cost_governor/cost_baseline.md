# Earnalism Cost and Performance Baseline

Captured at `2026-08-07T06:26:24Z` from clean commit
`335234cc7e4a8a75401b6c3ef81e7f9d98912a76`.

## Confirmed cost truth

- Previous Railway billing period: **$98.89 actual**.
- Previous memory cost: **$87.40**, the dominant cost center.
- Current Railway period projection: **$2.50** before this cleanup batch.
- Current plan recorded by the active deployment: **Pro**.
- Workspace guardrail: **$5 soft alert / $10 hard limit**.
- Exact incremental saving from this batch is not claimed until post-change billing data exists.

## Railway topology and utilization

| Service | Replicas | 7-day CPU | 7-day RAM | 7-day public egress | Status |
| --- | ---: | ---: | ---: | ---: | --- |
| API | 2 | 0.00314 vCPU | 310.98 MB | 1.30 MB | one replica justified |
| Redis | 1 | 0.00079 vCPU | 13.84 MB | 0 MB | non-authoritative keyspace; removal canary required |

Redis has ten keys: cache (1), public cache (1), reader-content cache (1), and
reader RUM aggregates (7). No values were read. No auth, payment, rights,
publication, manuscript, approval, or media key namespace was found.

## Deployment truth

- `origin/main`: `335234cc7e4a8a75401b6c3ef81e7f9d98912a76`
- active Railway backend: `be601e2eeb82a034b0e3136ece17c05ad06448f5`
- backend production is stale relative to `origin/main`.
- Railway Git source and GitHub Actions both trigger deployments.
- the GitHub Actions scope check used only `HEAD^..HEAD`.
- frontend production SHA is not yet proven and remains `BLOCKED_UNKNOWN`.

## CI baseline

The latest 100 runs span 90.04 hours and consumed 251.88 elapsed runner
minutes: 98.45 for the GO LIVE gate, 88.13 for the overlapping regression
suite, and 65.30 for production monitoring.

## Repository baseline

- 8,269 tracked files.
- 659,787,871 tracked blob bytes.
- 664,244 KiB clean worktree.
- 73 numbered-copy files.
- 870.95 MiB local Git pack data with orphan/corrupt pack metadata warnings.

No history rewrite or evidence deletion is authorized by this baseline.

## Rollback commands

```bash
railway service scale --service 5af42e7e-f518-4f6a-b602-d9950866501f --environment production sfo=2
railway usage limit remove --yes --json
git revert <cleanup-batch-commit>
```

Redis is not deleted in this batch. Its rollback remains a normal service
restart/redeploy until the no-Redis canary and rollback window close.
