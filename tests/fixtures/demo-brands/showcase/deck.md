---
spec_version: 1
brand: "{{brand}}"
title: "{{company}} Q3 review"
author: Operations
date: 2026-10-01
---

## {{company}} Q3 review
layout: title
subtitle: Volume, delivery and the plan for Q4

## Agenda
layout: agenda

- Volume and what drove it
- Delivery times
- Margins by line
- Q4 plan

## Volume grew in every month of Q3
layout: section
kicker: Part 1

## 18%
layout: big-number
caption: Growth in {{product}} volume, Q2 to Q3

Notes:
Source: the Q3 shipment ledger. Invented figures for the demo fixtures.

## {{unit}} shipped by month
layout: chart

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

## Margins by line
layout: table

| Line | Q2 margin | Q3 margin | Change |
|---|---|---|---|
| Core | 21% | 23% | +2 pts |
| Specialty | 34% | 31% | -3 pts |
| Services | 28% | 29% | +1 pt |

## The new north warehouse
layout: image
caption: Opened in August, with same-day delivery for the northern accounts.

![The new north warehouse](../brands/{{brand}}/assets/hero.png)

## What changes in Q4
layout: icon-row
icon1: brand:icon/growth
text1: Price the specialty line to the new supplier cost
icon2: brand:icon/delivery
text2: Add a second shift at the north warehouse
icon3: brand:icon/people
text3: Renew the three largest contracts early

## Thank you
layout: closing
subtitle: Questions to operations@example.com
