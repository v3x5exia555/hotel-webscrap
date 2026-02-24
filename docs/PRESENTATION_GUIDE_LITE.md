# Pahang Hotel Intelligence Presentation (Concise)

## Executive Summary

This dashboard provides **weekly batch auditing** of the hotel industry by comparing historical online sales data (Agoda/Booking) against government tax reports. It identifies hidden revenue and unregistered "ghost" properties through scheduled manual runs.

---

## 🚀 Key Business Value

- **Detect Under-reporting**: Automatically flags hotels whose online activity exceeds their tax declarations.
- **Find "Ghost" Hotels**: Identifies properties selling rooms online that are not in the state's registration database.
- **Weekly Batch Analysis**: Process an entire week of data in one go to see occupancy trends and revenue shifts across the state.
- **Manual Control**: The system is run manually by staff to ensure data accuracy and control over the audit cycle.
- **Data Fusion**: Uses "Fuzzy Matching" to link messy online names to clean government records instantly.

---

## ⚖️ The Audit Logic (How it works)

We calculate **Tax Leakage** using a simple 3-way check:

1. **Batch Data**: Historical sales detected on platforms (The Collected Market Truth).
2. **Submitted Data**: What the hotel tells the State (The Claim).
3. **The Gap**: `(Scraped - Submitted) * Tax Rate = Estimated Leakage`.

---

## 🚩 Risk Matrix & Action Plan

| Priority        | Scenario                     | Action                                  |
| :-------------- | :--------------------------- | :-------------------------------------- |
| **🔴 CRITICAL** | Unregistered + Active Sales  | **Enforcement**: Mandatory Registration |
| **🟠 HIGH**     | Registered + Large Sales Gap | **Audit**: Review financial records     |
| **🟡 WARN**     | Minor reporting gaps         | **Monitor**: Send automated reminder    |
| **🟢 OK**       | Data matches reports         | **Compliance**: No action needed        |

---

## ⚠️ Known Limitations

- **Not Real-Time**: Data is processed in **Weekly Batches** rather than a live stream.
- **Manual Over-ride**: Requires manual triggers by staff to update findings.
- **Digital Proxy**: Captures online sales only; walk-ins are outside the digital scope.

## Outcome: Strategic Enforcement

Instead of random audits, this system gives your team a **Targeted Hit List** of the properties with the largest tax discrepancies, maximizing state revenue with minimal manual effort.
