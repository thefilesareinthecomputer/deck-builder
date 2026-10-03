---
spec_version: 1
brand: "{{brand}}"
title: "{{company}} data platform walkthrough"
footer: "{{company}} | Data platform"
kicker: Data platform
---

## How {{company}} turns orders into a forecast
layout: title
subtitle: The query, the job and the config behind the weekly {{product}} forecast

## The forecast reads twelve weeks of orders
layout: code
subtitle: Lines 4 and 5 are the change that fixed the holiday spike
takeaway: Capping each week at three times the median removed the false spike

```python {4-5} lines title="forecast.py"
def weekly_forecast(orders, weeks=12):
    history = orders.last(weeks).groupby("week").sum()
    median = history["units"].median()
    # one bulk order shouldn't read as a trend
    history["units"] = history["units"].clip(upper=3 * median)
    return history["units"].ewm(span=4).mean().iloc[-1]
```

## Orders come from one query
layout: code-right
subtitle: Open orders only, grouped by region and week

- Cancelled and test orders are left out
- Weeks start on Monday in every region
- The query runs in under two seconds

### code
```sql {7}
SELECT
  region,
  DATE_TRUNC('week', placed_at) AS week,
  SUM(units) AS units
FROM orders
WHERE status = 'open'
  AND is_test = FALSE
GROUP BY region, week
ORDER BY week;
```

## One job refreshes it every Monday
layout: code
subtitle: The schedule and the alert live in the same file

```yaml lines
forecast:
  schedule: "0 6 * * MON"     # 6 am, before the planning call
  source: warehouse.orders
  weeks: 12
  alert:
    channel: "#planning"
    when: forecast_change > 0.25
```

## Anyone can run it by hand
layout: code-right
subtitle: Three commands from a fresh clone

- Install once per machine
- Run for one region or all of them
- The report opens in the browser

### code
```bash
uv sync
uv run forecast --region north
open out/forecast-north.html
```

## The runbook shows the same commands
layout: code
subtitle: A markdown file can hold a fenced block of its own

````markdown {3-5}
## Rerun the forecast

```bash
uv run forecast --region all
```

Check the report before the planning call.
````

## Questions
layout: closing
subtitle: "Ask in #planning, or open an issue on the forecast repo"
