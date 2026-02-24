# Pahang Hotel Revenue Intelligence & Compliance Suite

A modular, automated auditing system built with **Python**, **Playwright**, and **Dash** to monitor hotel inventory and identify tax leakage by comparing OTA data (Agoda, Booking.com) against official government declarations.

## 🚀 Key Features

- **Multi-Platform Scraping**: Robust extraction of prices, inventory, and property types from Agoda and Booking.com.
- **Revenue Audit Dashboard**: Real-time visualization of compliance rates, tax leakage, and market supply.
- **Fuzzy Data Linking**: Intelligent name matching to connect scraped OTA records with official state registration files.
- **Enforcement Prioritization**: Automatically flags "Critical" and "High Risk" properties with significant reporting gaps.
- **Platform Analytics**: Detailed distribution of market segments (Airbnb, Villa, Hotel) and platform presence.

---

## 🛠 Project Structure

```text
hotel/
├── main.py              # The "Brain": Orchestrates all scrapers
├── dashboard.py         # The "UI": Dash application for data visualization
├── up.sh                # Main Entry Point: Starts dashboard and tunnels
├── scrapers/            # The "Workers": Site-specific scraping logic
├── scripts/             # The "Utilities": Conversion, cleanup, and secondary scripts
├── bin/                 # The "Tools": Binaries like cloudflared
├── docs/                # The "Library": Presentation guides and documentation
├── utils/               # The "Core": Shared database and helper functions
├── data/                # The "Vault": SQLite database and official CSVs
└── venv/                # The "Environment": Current virtual environment
```

---

## 📥 Setup & Installation

Ensure you have Python 3.10+ installed.

```bash
# 1. Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# 2. Install required packages
pip install playwright pandas dash dash-bootstrap-components plotly

# 3. Install Playwright browser engines
playwright install chromium
```

---

## 🖥 Usage

### 1. Execute Scrapers

To capture real-time market data across all configured areas:

```bash
# Basic run (1 day ahead)
./venv/bin/python3 main.py --mode daily --days 1

# Full week pickup sequence (7 days with dynamic stay duration)
./venv/bin/python3 main.py --week
```

### 3. Remote Access & Automation (Cloudflare)

To start the Dashboard, SSH access, and public tunnels with a **single command**:

```bash
chmod +x up.sh
./up.sh
```

This script will:

1.  Clean up any existing dashboard/tunnel processes.
2.  Launch the **Dashboard** on port 8050.
3.  Establish an **SSH Tunnel** (for remote server management).
4.  Establish a **Web Tunnel** (for public dashboard access).
5.  Generate and display your public access URLs.

---

## 📊 Dashboard Modules

### 1. Revenue Audit Matrix

A detailed table linking OTA supply to state reports.

- **Scraped Room-Nights**: Total Observed Inventory (Supply).
- **Submitted Nights**: Nights officially declared by the hotel.
- **Tax Loss (RM)**: Estimated leakage calculated as `(Scraped - Submitted) * Tax Rate`.

### 2. Enforcement Priority

A risk-ranked list focusing on "Critical" properties:

- **Critical**: Unregistered properties with high occupancy detected.
- **High Risk**: Registered properties with reporting gaps > 100 nights.

### 3. Platform Distribution Overview

Located in the **Analytics & Trends** tab, this provides a breakdown of unique properties and market capacity for **Airbnb**, **Booking.com**, **Agoda**, and **Traveloka**.

---

## � Data Linking Logic

The system uses **Fuzzy Substring Matching** to connect scraped OTA names to official records.

- **Example**: If "Garden Home at Midhills" is scraped, the engine automatically matches it to "Midhills" in your registration CSV.
- **Normalization**: All names are stripped of whitespace and lowercased before comparison to prevent duplication.

---

## 📋 Database Schema & Metrics

| Table             | Purpose                                                                     |
| :---------------- | :-------------------------------------------------------------------------- |
| **snapshots**     | Stores every unique listing, price, and "Rooms Left" found during scraping. |
| **pickup_trends** | Tracks inventory drops between T and T-1 to estimate sold nights.           |

**Important Definitions:**

- **Estimated Room-Nights**: Total detected supply for sale on platforms.
- **Compliance Rate**: Percentage of expected tax actually collected based on verified state records.

---

## 🛡 Anti-Detection & Proxy Support

Use the `--proxy` flag to enable stealth browsing. The system randomized Viewports, User-Agents, and Interaction Patterns to bypass advanced bot protection on major platforms.

```

```
