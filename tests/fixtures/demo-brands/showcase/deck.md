---
spec_version: 1
brand: "{{brand}}"
title: "{{company}} Q3 review"
author: Operations
date: 2026-10-01
kicker: Q3 review
---

## {{company}} Q3 review
layout: title
subtitle: Volume, delivery and the plan for Q4

## Agenda
layout: agenda

- Volume and what drove it
- Three bets for Q4
- Risks and margins
- Partners and next steps

## Three bets for Q4
layout: cards-3
kicker: The plan
label1: Monthly invoicing
footer1: "Target: 40 accounts"
label2: Same-day delivery
footer2: "Target: 95% same-day"
label3: Recycled reporting
footer3: "Target: 12 accounts"
takeaway: The three bets add about 9% to Q4 revenue

### body1
- One invoice a month
- Pilot with ten accounts
- All accounts by December

### body2
- North region in October
- Two new evening routes
- Every order tracked

### body3
- **Recycled** share on invoices
- A quarterly summary

Notes:
Targets from the Q4 operating plan. Invented figures for the demo fixtures.

## {{unit}} shipped by month
layout: chart
kicker: Volume
subtitle: The core line set a record in September
takeaway: The core line grew every month while specialty held flat

```chart
type: column
number_format: '#,##0'
labels: true
categories: [Jul, Aug, Sep]
series:
  - name: Core line
    values: [9800, 10400, 11250]
  - name: Specialty
    values: [3100, 3050, 3120]
```

Notes:
Source: the Q3 shipment ledger. Invented figures for the demo fixtures.

## 18%
layout: big-number
caption: Growth in {{product}} volume, Q2 to Q3

Notes:
Source: the Q3 shipment ledger. Invented figures for the demo fixtures.

## Three risks to watch in Q4
layout: bands-3
kicker: Risks
label1: Freight costs
label2: Supplier capacity
label3: Order errors

### text1
- Diesel surcharges rose **6%** in September
- Two carriers want to reprice in January

### text2
- Our main supplier runs at **94%** of capacity
- A second supplier is qualified as a backup

### text3
- The web form drops lines when a session times out
- A fix ships in the October release

## Margins held on two of three lines
layout: table
kicker: Margins
takeaway: Specialty slipped as supplier costs rose

| Line | Q2 margin | Q3 margin | Change |
|---|---|---|---|
| Core | 21% | 23% | +2 pts |
| Specialty | 34% | 31% | -3 pts |
| Services | 28% | 29% | +1 pt |

Notes:
Source: the Q3 margin report. Invented figures for the demo fixtures.

## The new north warehouse opened in August
layout: image-right
kicker: Delivery
subtitle: Same-day delivery for the northern accounts

- Two loading docks and a second shift
- Orders before noon ship the same day
- Inventory counted nightly by scanner

### image
![The new north warehouse](assets/{{brand}}-hero.png)

## Two partners share the north routes
layout: logos
kicker: Partners
caption1: "{{partner_a_name}}"
caption2: "{{partner_b_name}}"
takeaway: Shared routes cut each partner's delivery cost

### logo1
![{{partner_a_name}} logo](assets/{{partner_a}}-logo.png)

### logo2
![{{partner_b_name}} logo](assets/{{partner_b}}-logo.png)

## What changes in Q4
layout: icon-row
kicker: Next steps
icon1: brand:icon/growth
text1: Price the specialty line to the new supplier cost
icon2: brand:icon/delivery
text2: Add a second shift at the north warehouse
icon3: brand:icon/people
text3: Renew the three largest contracts early

## Thank you
layout: closing
subtitle: Questions to operations@example.com
