---
spec_version: 1
brand: "{{brand}}"
title: "{{company}} Q3 review"
footer: "{{company}} | Q3 review"
---

## {{company}} Q3 review
layout: title
subtitle: Shipments, margins and the plan for Q4

## Agenda
layout: agenda

- Volume and the accounts behind it
- Margins by product line
- Warehouse and delivery
- Q4 plan

## Volume grew in every month of Q3
layout: section
kicker: Part 1

## The {{product}} line drove the growth
layout: content

- Volume on the {{product}} line rose 18% over Q2
- Two regional school districts signed annual contracts
- Returns stayed under 1% of shipments

Notes:
A short list: the layout centers it in the body area instead of leaving it at the top.

## What the field team heard this quarter
layout: content

- Buyers want one invoice per month instead of one per delivery
- Districts plan budgets in March, so renewal offers should land in February
- Same-day delivery matters more than unit price for facilities buyers
- Two accounts asked for recycled-content reporting on every order
- Larger buyers are consolidating suppliers and expect volume pricing
- The online order form drops line items when a session times out

## 12%
layout: big-number
caption: Total volume growth, Q2 to Q3

## {{unit}} shipped by month
layout: chart
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

## Margins by product line
layout: table

| Line | Q2 margin | Q3 margin | Change |
|---|---|---|---|
| Core | 21% | 23% | +2 pts |
| Specialty | 34% | 31% | -3 pts |
| Services | 28% | 29% | +1 pt |

## Accounts up for renewal in Q4
layout: table
takeaway: Three of six renewals need attention before December

| Account | Segment | Annual {{unit}} | Renewal | Owner | Status |
|---|---|---|---|---|---|
| Northfield School District | Education | 6,400 | October | Field team north | Green |
| Harbor County Facilities | Government | 4,900 | November | Field team east | Amber |
| Linden Medical Group | Healthcare | 3,750 | November | Key accounts | Green |
| Westmark Office Parks | Commercial | 2,980 | December | Field team west | Red |
| Riverside Community College | Education | 2,600 | December | Field team north | Green |
| Cedar Logistics | Commercial | 1,850 | December | Inside sales | Amber |

## Two ways to cover the north
layout: two-col

### left
- One shift, six days a week
- Next-day delivery for orders after noon
- No new hires

### right
- Two shifts, five days a week
- Same-day delivery until 3 pm
- Four new hires by November

## Before and after the scanner rollout
layout: comparison
left-heading: Before
right-heading: After

### left
- Manual counts at the dock
- Two-day lag on inventory
- Mis-picks found at delivery

### right
- Scanned at receiving
- Same-day inventory
- Mis-picks caught at packing

## The new north warehouse
layout: image

### image
![The new north warehouse](assets/{{brand}}-hero.png)

### caption
Opened in August. Eight bays, and same-day delivery for the northern accounts.

## Where the second shift goes
layout: image-right

- Receiving and putaway from 2 pm
- Picks for the next morning's routes
- Weekly cycle counts moved off the day shift

### image
![The new north warehouse](assets/{{brand}}-hero.png)

## What changes in Q4
layout: icon-row
icon1: brand:icon/growth
text1: Price the specialty line to the new supplier cost
icon2: brand:icon/people
text2: Add a second shift at the north warehouse
icon3: brand:icon/delivery
text3: Renew both school district contracts early

## "Same-day delivery is why we switched."
layout: quote
attribution: Facilities buyer, regional school district

## Thank you
layout: closing
subtitle: Questions to operations@example.com
