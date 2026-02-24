# Task Plan: Daily Reservation Behavior Dashboard

## Goal

Enhance the dashboard to visualize "Daily Behavior" - specifically tracking how many hotels are being reserved and where the demand is highest using the `pickup_trends` data.

## Current Phase

Phase 3: Verification

## Phases

### Phase 1: Research & Design

- [x] Analyze `pickup_trends` table schema
- [x] Identify key metrics: Total Pickups, Hot Properties, Hourly/Daily velocity
- **Status:** complete

### Phase 2: Implementation (Dashboard Update)

- [x] Add a new "Market Demand" tab to `dashboard.py`
- [x] Create a "Demand Velocity" chart (Line chart for hourly rooms reserved)
- [x] Create a "Top Performing Properties" table (League table for booking velocity)
- [x] Enhance database to support fine-grained `detected_at` timestamps
- **Status:** complete

### Phase 3: Verification

- [ ] Run the dashboard and verify charts populate with data (Waiting for first monitor cycle)
- **Status:** in_progress

## Key Questions

1. How soon will data appear? (Answer: After the `hotel_monitor.py` completes its second cycle - approx 30 mins - as it needs two snapshots to calculate a difference).

## Decisions Made

| Decision                    | Rationale                                                                                              |
| --------------------------- | ------------------------------------------------------------------------------------------------------ |
| Use `Line Chart` for demand | Better visualize "velocity" peaks throughout the day                                                   |
| Add `detected_at` to DB     | Required to track _when_ our system spotted the reservation, even if it happened between daily scrapes |
