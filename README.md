# McCoy's Fleet Cost per Mile / Hour — YTD 2026

Interactive report (`index.html`) of fleet cost by location and month, January–October 2026.

The 2027 store pickup reallocation proposal lives in its own repo: Store-Pickup-Reallocation.

**Costs:** maintenance spend, WEX fuel card, onsite diesel (353/356/359), propane, straight-line depreciation
(trucks/LD/trailers 60 mo; TMFLs/forklifts/ancillary 84 mo), registration (0.05%/mo) and taxes (0.0667%/mo) on original cost.

**Measures:** all-in cost per mile, truck & LD cost per mile, forklift & TMFL cost per hour, trailer cost per asset-month, annualized run rate.

Open `index.html` in a browser, or enable GitHub Pages (Settings → Pages → Deploy from branch `main`, `/root`).

`scripts/` holds the build: `build_data.py` combines the monthly source files into `data.json`; `build_html.py` injects it and the logo into `template.html`. Source data files are not stored in this repo.
