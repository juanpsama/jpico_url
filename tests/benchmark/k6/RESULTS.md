# Results from stress test with concurrent API calls

**Test config:** 1500 iterations shared among 200 VUs, hitting a single short URL repeatedly.

## Cache route (`/6hmG`)

| Metric | Value |
|---|---|
| Error rate | 0.00% (0 / 1500) |
| Requests | 1500 @ 339 req/s |
| Avg duration | 47.7 ms |
| Median duration | 36.64 ms |
| p(90) | 89.86 ms |
| p(95) | 168.39 ms |
| Max | 261.2 ms |

## No-cache route (`/no-cache/6hmG`)

| Metric | Value |
|---|---|
| Error rate | 0.00% (0 / 1500) |
| Requests | 1500 @ 322 req/s |
| Avg duration | 78.27 ms |
| Median duration | 49.82 ms |
| p(90) | 150.86 ms |
| p(95) | 320.95 ms |
| Max | 469.7 ms |

## Conclusion

At 200 concurrent VUs the cache delivers roughly **1.6x lower latency** than the no-cache path (avg 47.7 ms vs 78.27 ms). The gap widens sharply at the tail: p(95) is nearly **2x** and p(90) is **1.7x** higher when bypassing the cache. Both routes maintained a 0% error rate, meaning the DB pool and Redis held up under the load. The cache route also achieved slightly higher throughput (339 vs 322 req/s).

---

# Results from ramp-up stress test (up to 5000 VUs)

**Test config:** 5-stage ramp from 5 → 5000 VUs over 60s, hitting random short URLs across 500k seeded rows.

**System:** 16 GB RAM, Intel i5-12450H

## Cache-aside route

| Metric | Value |
|---|---|
| Error rate | **0.00%** (0 / 24832) |
| Throughput | **909 req/s** |
| Avg | **1.35 s** |
| Median | 1.09 s |
| p(90) | **3.26 s** |
| p(95) | **3.37 s** |
| Max | **3.8 s** |


### No-cache route (original, for reference)

| Metric | Value |
|---|---|
| Error rate | 0.05% (13 / 21750) |
| Throughput | 274.54 req/s |
| Avg | 5.74 s |
| Median | 3.25 s |
| p(90) | 19.16 s |
| p(95) | 24.21 s |
| Max | 27.84 s |
| Interrupted | 13 |

## Conclusion

At 5000 concurrent VUs, the cache layer is the difference between a functional service and a degraded one:

- **Error rate:** 0.00% (cache) vs 0.05% (no-cache) — zero failures vs 13.
- **Throughput:** 909 req/s (cache) vs 274.54 req/s (no-cache) — **3.3x** more work done.
- **Avg latency:** 1.35 s (cache) vs 5.74 s (no-cache) — **4.3x** faster.
- **p(95) tail:** 3.37 s (cache) vs 24.21 s (no-cache) — **7.2x** better.
- **Max latency:** 3.8 s (cache) vs 27.84 s (no-cache) — **7.3x** tighter ceiling.
- **Interrupted iterations:** 0 (cache) vs 13 (no-cache) — all requests completed under cache.

The no-cache route is bound by the DB connection pool (pool_size=20, max_overflow=100). Under heavy load, most requests queue waiting for a connection, causing cascading latency and eventually dropped requests. Redis absorbs the read traffic on the cache path, keeping the DB pool free for writes and cache fills.

---

# Results from random-URL stress test (up to 1000 VUs)

**Test config:** 4-stage ramp from 9 → 1000 VUs over 50s, hitting random short URLs across 500k seeded rows.

**System:** 16 GB RAM, Intel i5-12450H

## Cache route (random URLs)

| Metric | Value |
|---|---|
| Error rate | 0.00% (0 / 9016) |
| Throughput | 179 req/s |
| Avg | 2.67 s |
| Median | 2.87 s |
| p(90) | 5.04 s |
| p(95) | 5.22 s |
| Max | 5.35 s |

## No-cache route (random URLs)

| Metric | Value |
|---|---|
| Error rate | 0.00% (0 / 7668) |
| Throughput | 146 req/s |
| Avg | 3.43 s |
| Median | 3.03 s |
| p(90) | 5.72 s |
| p(95) | 10.71 s |
| Max | 13.14 s |

## Conclusion

At 1000 VUs with random URLs, the cache still holds a clear advantage, but the gap narrows compared to the 5000 VU single-URL test — random requests cause more cache misses, so more work falls through to the DB:

- **Throughput:** 179 req/s (cache) vs 146 req/s (no-cache) — **23%** more.
- **Avg latency:** 2.67 s (cache) vs 3.43 s (no-cache) — **28%** faster.
- **p(90):** 5.04 s (cache) vs 5.72 s (no-cache) — close, **13%** better.
- **p(95):** 5.22 s (cache) vs 10.71 s (no-cache) — **2.1x** better at the tail.
- **Max:** 5.35 s (cache) vs 13.14 s (no-cache) — **2.5x** tighter ceiling.

Both paths maintained 0% errors. The no-cache p(95) nearly doubles between p(90) and p(95) (5.72 s → 10.71 s), while the cache p(95) stays flat (5.04 s → 5.22 s) — Redis absorbs the burst and keeps tail latency predictable. The DB path shows growing variance under contention.
