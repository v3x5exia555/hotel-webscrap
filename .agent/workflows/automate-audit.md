---
description: Run the full weekly scraping, update the Word report, and restart the dashboard tunnels
---

This workflow automates the end-to-end hotel intelligence process. It captures new market data, generates a fresh business report, and ensures the remote dashboard is live.

// turbo-all

1. Run the Weekly Scraping Pipeline (7-day window)

```bash
./venv/bin/python3 main.py --week
```

2. Generate the Updated Business Presentation Guide (.docx)

```bash
./venv/bin/python3 scripts/convert_to_word.py docs/PRESENTATION_GUIDE_LITE.md docs/Hotel_Intelligence_Presentation_Lite.docx
```

3. Launch/Restart the Dashboard and Remote Access Tunnels

```bash
./up.sh
```
