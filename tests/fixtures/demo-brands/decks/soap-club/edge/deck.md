---
spec_version: 1
brand: soap-club
title: Soap Club edge cases
author: Soap Club
date: 2026-10-01
kicker: Edge cases
footer: Soap Club | Crème & piñón edition
---

## Soap Club edge cases: crème, müesli & piñón
layout: title
subtitle: Bars < $10, margins > 50%, and "small batch" means 100% cut by hand

## Ingredients
layout: content

- Olive oil from Jaén, cold pressed, is 62% of the oils
- **`SC-LAV-OAT`** marks every Oat & Lavender batch
- Lye is handled under the *[safety sheet](https://example.com/sds)* only
- Shea & cocoa butter < 20%, castor oil > 5% for "lather"
- Crème de lavande and müesli oats, ground in house for $0.04 a bar

Notes:
Edge cases: a one-word title; the body at its five-bullet budget; bold around code; an italic link; accents, ampersands, angle brackets, quotes, percent and dollar signs.

## Four scents, four buyers and one order day
layout: cards-4
kicker: Range
label1: Oat & Lavender
footer1: 41% of units
label2: Cedar Smoke
footer2: 24% of units
label3: Salt Scrub
label4: Fig & Pepper

### body1
- **Gentle** for daily use
- Unscented on request

### body2
- **Dark** and woody
- Sells out in December

### body3
- Sea salt & **olive oil**
- For working hands

### body4
- **Spicy**, for winter
- Grew 41% this year

Notes:
Edge cases: the title is exactly at its 42-character budget; two cards have the optional footer and two don't; bold keywords in every card.

## -$12,345.67
layout: big-number
caption: Lost on the refill pouch trial in FY2026, the single product line we will not make or stock again

Notes:
Edge cases: the number is exactly at its 11-character budget and negative; the caption is exactly at its 97-character budget.
Source: refill pouch cost and sales ledger, FY2026.

## Three batches lost money in September
layout: table
kicker: Batches
takeaway: Batch SC-LAV-OAT-2026-0042 lost the most; one reprice fixes them all

| Batch | Scent | Bars | Margin | Change |
|---|---|---|---|---|
| SC-LAV-OAT-2026-0042 | Oat & Lavender | 480 | -$140 | -12% |
| SC-CED-SMK-2026-0017 | Cedar Smoke | 360 | -$85 | -7% |
| SC-SLT-SCR-2026-0031 | Salt Scrub | 300 | -$20 | -2% |
| SC-FIG-PEP-2026-0008 | Fig & Black Pepper | 240 | $310 | +9% |

Notes:
Edge cases: a long unbreakable batch code in the first column, negative amounts and percentages, and a takeaway exactly at its 68-character budget.
Source: batch costing sheet, September 2026.

## Eight scents, eight colors, no repeats
layout: chart
kicker: Range
subtitle: Units sold by scent and quarter, FY2026
takeaway: Oat & Lavender led every quarter; Crème Brûlée and Piñón trail

```chart
type: line
number_format: '#,##0'
labels: false
legend: true
colors: [primary, accent, muted, "B07A4F", "6B8A99", "7D8F6A", "5A4A6E", "9C4A32"]
categories: [Q1, Q2, Q3, Q4]
series:
  - name: Oat & Lavender
    values: [5200, 4100, 4300, 4600]
  - name: Cedar Smoke
    values: [4400, 1900, 2000, 2600]
  - name: Salt Scrub
    values: [2100, 2000, 2200, 2300]
  - name: Fig & Pepper
    values: [1900, 1200, 1400, 1600]
  - name: Rose Clay
    values: [1200, 1000, 1100, 1000]
  - name: Charcoal & Mint
    values: [800, 700, 700, 700]
  - name: Crème Brûlée
    values: [600, 300, 200, 400]
  - name: Piñón
    values: [500, 200, 150, 350]
```

Notes:
Edge case: exactly eight series, the most a chart takes before SERIES_MANY, each with its own color.
Source: Soap Club production log, FY2026.

## A logo and a photo share one row
layout: logos
caption1: Transparent logo, fitted
caption2: Opaque photo, fitted too

### logo1
![Soap Club logo](assets/soap-club-logo.png)

### logo2
![Two Soap Club bars on a wooden stand](assets/soap-club-hero.png)

Notes:
Edge cases: two logos, the minimum; an opaque photo in a logo slot must be fitted whole, not cropped.

## Six slots, three partners, each twice
layout: logos
subtitle: The row at its six-logo maximum
caption1: Paper wrap
caption2: Office washrooms
caption3: Bars and scent card
caption4: Gift box sleeve
caption5: Monthly order
caption6: Winter gift box
takeaway: Repeat logos are allowed, and every slot is filled

### logo1
![Dumbder Nifftlin Paper Co. logo](assets/dumbder-nifftlin-logo.png)

### logo2
![Cubicle 9 Enterprises logo](assets/cubicle-nine-logo.png)

### logo3
![Soap Club logo](assets/soap-club-logo.png)

### logo4
![Dumbder Nifftlin Paper Co. logo](assets/dumbder-nifftlin-logo.png)

### logo5
![Cubicle 9 Enterprises logo](assets/cubicle-nine-logo.png)

### logo6
![Soap Club logo](assets/soap-club-logo.png)

## The logo fits its box without a crop
layout: image-right
subtitle: A transparent PNG is fitted, never cut

- The drop and the wordmark both show
- Clear space stays around the logo
- No stretch, no squash

### image
![Soap Club logo](assets/soap-club-logo.png)

## How a batch moves from log to report
layout: process-6
kicker: Batches
icon1: brand:icon/database
step1: Log
text1: A code when the oils are weighed.
icon2: brand:icon/layers
step2: Layer
text2: Molds poured and stacked to set.
icon3: brand:icon/gear
step3: Cut
text3: Cut by hand after two days.
icon4: brand:icon/shield
step4: Cure
text4: Six weeks on open racks.
icon5: brand:icon/check
step5: Check
text5: Weighed and checked for cracks.
icon6: brand:icon/chart
step6: Report
text6: Yield and cost go to the report.

Notes:
Edge case: six steps, all with starter icons the kit doesn't ship (database, layers, gear, shield, check, chart).

## Four steps to a new stockist
layout: process-4
kicker: Stockists
icon1: brand:icon/people
step1: Meet
text1: A buyer smells the range at a market or a trade fair.
icon2: brand:icon/document
step2: Sign
text2: Sale-or-return terms on one page, signed the same week.
icon3: brand:icon/box
step3: Ship
text3: The first cases ship with a crate fixture and staff notes.
icon4: brand:icon/growth
step4: Grow
text4: Reorders by email; we add a scent after the second one.

## Three risks for the coming year
layout: bands-3
kicker: ""
label1: Olive oil prices
label2: Summer heat in the cure room
label3: One soap maker

### text1
- Oil rose **11%** this year
- A 12-month price caps it

### text2
- Rose Clay **cracked** above 28 °C
- A fan and a cooler shelf, under $400

### text3
- Every bar depends on **one person**
- A second maker by March

Notes:
Edge case: the deck-wide kicker is overridden to empty on this slide, so no section label shows.

## Merci, gracias, danke & "thanks" for reading
layout: closing
subtitle: Questions to edge@example.com; 100% answered within 48 hours
