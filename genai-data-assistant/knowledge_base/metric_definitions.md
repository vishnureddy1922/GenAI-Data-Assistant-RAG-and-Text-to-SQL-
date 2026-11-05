# Metric definitions

These are the approved definitions used in every dashboard and report. If a number disagrees with these rules, the number is wrong.

## Revenue

Revenue is the sum of `quantity * unit_price` from `analytics.order_items`, for orders whose status is `completed`. Cancelled and refunded orders are excluded. `unit_price` on the order line is the price actually charged, which can be lower than the catalog price in `analytics.products` because of discounts. Revenue is reported in USD, before tax and shipping.

## Orders

An order counts toward order volume only when its status is `completed`. Cancelled orders are tracked separately as the cancellation rate.

## Average order value (AOV)

AOV = revenue divided by the number of completed orders in the same period. Always compute AOV from totals for the period, never by averaging daily AOV values.

## Active customer

A customer is active in a month if they placed at least one completed order in that calendar month.

## Cancellation rate

Cancellation rate = cancelled orders divided by all orders (completed, cancelled and refunded) in the period.

## Refund rate

Refund rate = refunded orders divided by completed plus refunded orders. Refunds are recorded on the original order date, not the date the refund was processed.

## New customers

New customers in a period are customers whose `signup_date` falls inside the period, whether or not they ordered.
