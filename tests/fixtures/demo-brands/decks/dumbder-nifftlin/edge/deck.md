---
spec_version: 1
brand: dumbder-nifftlin
title: "Edge cases: Dumbder Nifftlin & friends"
author: Fixture <tests>
date: 2026-10-02
kicker: Edge cases
footer: "R&D <draft> 100% \"internal\""
---

## Señor Muñoz's café & crème: "50% off" <today> for $5
layout: title
subtitle: 'Accents and symbols: déjà vu, über, niño, “curly” and ‘single’ quotes, 10% < 20% > 5% & $1,200'

Notes:
Every character on this slide must survive the build: é, ü, ñ, &, <, >, straight and curly quotes, % and $.

## Inventory
layout: content
kicker: ""

- **`PX-4401`** is the item code for recycled A4
- See *[the 2027 catalog](https://example.com/catalog)* for prices
- `code`, **bold** and *italic* in one line
- Stock: 1,200 reams & 40 pallets
- Reorder when stock < 25% or > 90 days old

Notes:
A one-word title, a slide that clears the deck-wide kicker with an empty kicker, and a list at its five-bullet budget, which check warns about as BULLETS_MANY on purpose.

## Recycled A4 paper now ships from each site
layout: content
subtitle: Twelve sites, one price list and the same three-day lead time to all
takeaway: All twelve sites stock recycled A4 at one price and deliver in three days.

- One price list for all twelve sites
- Three-day lead time everywhere

Notes:
The title, subtitle and takeaway each sit exactly at their character budgets.

## Price changes for 2027 by item
layout: table
takeaway: Recycled lines get cheaper in 2027 & A3 stock is on back order

| Item code | Description | Price | Change | Stock |
|---|---|---|---|---|
| PX-4401-RECYCLED-A4-500 | Recycled A4, 500 sheets | $5.40 | -0.35 | 1,240 |
| PX-4402-RECYCLED-A3-250 | Recycled A3 & card | $7.90 | −1.10 | -40 |
| CS-118 | Card stock <heavy> | $12.00 | +0.80 | 310 |
| EN-DL-1000 | Envelopes "DL" | $18.25 | -2.05 | 0 |

Notes:
The item codes are long tokens with no spaces; Change and Stock hold negative numbers, one with a Unicode minus sign.
Source: the 2027 draft price list.

## Eight sites ordered recycled paper in 2026
layout: chart
takeaway: Exactly eight series, the most a chart takes before check warns

```chart
type: column
number_format: '#,##0'
labels: false
colors: [primary, accent, muted, ink, "8FA89B", "E2C9A6", "4F6F66", "A67C45"]
categories: [Q1, Q2, Q3]
series:
  - name: North
    values: [420, 460, 510]
  - name: South
    values: [380, 395, 410]
  - name: East
    values: [300, 340, 365]
  - name: West
    values: [280, 290, 305]
  - name: Riverside
    values: [210, 240, 260]
  - name: Harbor
    values: [190, 185, 200]
  - name: Hillcrest
    values: [150, 170, 175]
  - name: Online
    values: [120, 160, 220]
```

Notes:
Source: warehouse shipment ledger, recycled reams by site, first three quarters of 2026.

## Two logos sit as evenly as six
layout: logos
caption1: Office systems
caption2: Soap maker

### logo1
![Cubicle 9 Enterprises logo](assets/cubicle-nine-logo.png)

### logo2
![Soap Club logo](assets/soap-club-logo.png)

## Six logo slots, one photo among them
layout: logos
caption1: Paper supplier
caption2: Office systems
caption3: Soap maker
caption4: Warehouse photo
caption5: Repeat of slot one
caption6: Repeat of slot two
takeaway: The photo in slot four is fitted inside its slot, not cropped

### logo1
![Dumbder Nifftlin Paper Co. logo](assets/dumbder-nifftlin-logo.png)

### logo2
![Cubicle 9 Enterprises logo](assets/cubicle-nine-logo.png)

### logo3
![Soap Club logo](assets/soap-club-logo.png)

### logo4
![Dumbder Nifftlin warehouse](assets/hero.png)

### logo5
![Dumbder Nifftlin Paper Co. logo](assets/dumbder-nifftlin-logo.png)

### logo6
![Cubicle 9 Enterprises logo](assets/cubicle-nine-logo.png)

## A photo in a logo slot is fitted, not cut
layout: comparison
left-heading: Opaque photo
right-heading: Kit logo by reference

### left
- The warehouse photo is opaque
- It must fit inside the slot

### right
- The kit's primary logo, by brand reference
- It keeps its clear space

### left-logo
![Dumbder Nifftlin warehouse](assets/hero.png)

### right-logo
![Dumbder Nifftlin Paper Co. logo](brand:logo/primary)

## Soap Club signed for weekly delivery
layout: image-right
subtitle: A transparent logo is fitted in the image box

- Weekly delivery to the Harbor plant
- Recycled wrap for 12 soap lines
- Monthly invoice from January

### image
![Soap Club logo](assets/soap-club-logo.png)

## Two starter icons fill gaps in the kit
layout: icon-row
icon1: brand:icon/gear
text1: Gear is a starter icon this kit doesn't have
icon2: brand:icon/shield
text2: Shield is a starter icon too, in the kit's icon color
icon3: brand:icon/box
text3: Box comes from the kit's own icon set

## Two cards
layout: cards-2
label1: Now
label2: Next

### body1
- **Ream**

### body2
- **Case**

## Three steps
layout: process-3
step1: Order
text1: Online.
step2: Pick
text2: Same day.
step3: Ship
text3: Next route.

## Two bands
layout: bands-2
label1: Risk
label2: Fix

### text1
- **Freight**

### text2
- **Reprice**

## Merci, gracias & danke: questions welcome
layout: closing
subtitle: "Write to <edge-cases@example.com> with “quotes”, 100% & $0 fees"
