---
description: Run the comprehensive monthly hotel scraping and Supabase synchronization
---

This workflow executes the full-scale monthly audit (30-day window). It can run platforms
**sequentially** (one after another) or **in parallel** (all 3 at the same time).

// turbo-all

---

## Option A — Parallel (Recommended: 3× faster)

Launches Booking, Agoda, and Traveloka simultaneously. Each gets its own process pool
with 3 workers. Supabase sync runs automatically at the end.

```bash
python3 scripts/run_parallel_platforms.py --monthly --workers 3
```

> Use `--no-sync` to skip the Supabase push.
> Use `--platforms booking agoda` to run only specific platforms.

---

## Option B — Sequential (Original single-platform flow)

This command handles data sync to Supabase and starts the 2-worker scraping pipeline
for the next 30 days, one platform at a time.

```bash
python3 scripts/process_job.py --monthly
```

---

### After either run:

### 2. Verify Supabase Sync

Check the logs to ensure the one-way sync to the `analysis_hotel` schema completed without errors.

### 3. Review Dashboard

Once complete, refresh your Supabase-connected dashboard to see the latest 30-day supply trends.
