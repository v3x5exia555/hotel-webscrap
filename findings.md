# Findings: Reservation Behavior Analytics

## New Intelligence Layer

- **Demand Velocity**: The system now tracks how many rooms are sold per hour.
- **Top Performers**: We have a "League Table" of hotels with the highest booking velocity.
- **Timestamping**: I added a `detected_at` column to the database to track the exact moment our monitor spotted a room reservation.

## Dashboard Updates

- **New Tab**: "Market Demand" added to the main dashboard.
- **Charts**:
  - **Total Rooms Reserved**: A real-time line chart showing demand spikes.
  - **Top Performing Properties**: Highlights hotels that are currently "trending" or being booked heavily.

## Data Timing

Because the system detects "Pickups" by comparing two points in time, you will see the behavior data populate **30 minutes after the monitor starts** (on its second scan).
