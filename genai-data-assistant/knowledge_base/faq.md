# Analytics FAQ

## Why doesn't my revenue match the finance report?

Finance reports revenue after refunds are processed and includes shipping fees. The analytics definition excludes shipping and drops refunded orders on their original order date. Small timing differences are normal. Differences above 0.5% should be raised with Data Engineering.

## Why is today's data missing?

The warehouse refreshes nightly, so data for today appears tomorrow morning after 05:00 UTC.

## Which channel is "store"?

`store` means in person purchases at retail locations, recorded by the point of sale system. Online orders are `web` or `mobile`.

## Can I use product list price for historical analysis?

No. `analytics.products.unit_price` is today's list price. Use `analytics.order_items.unit_price`, which is the price charged at the time of the order.

## How do I request a new metric?

Open a ticket in the Analytics board with the business question, the proposed definition and an example of how it will be used. The Analytics team reviews new metric requests weekly.
