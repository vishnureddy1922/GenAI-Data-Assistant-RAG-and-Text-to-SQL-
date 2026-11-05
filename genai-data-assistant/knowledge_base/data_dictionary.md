# Data dictionary: analytics schema

The `analytics` schema in the warehouse holds cleaned, business-ready tables. It is rebuilt every night by the dbt project owned by the Data Engineering team.

## analytics.customers

One row per customer account.

- `customer_id`: surrogate key
- `country`: ISO 3166 two letter country code taken from the billing address
- `signup_date`: date the account was created
- `tier`: loyalty tier. Bronze is the default. Silver after 3 orders in 12 months, gold after 10, platinum is invitation only.
- `email`: personal data. Classified as PII (see data policies).

## analytics.products

The product catalog. `unit_price` is the current list price and changes over time, so never use it to calculate historical revenue. Categories are Electronics, Home, Books, Beauty, Sports and Toys.

## analytics.orders

One row per order header. `status` is one of `completed`, `cancelled` or `refunded`. `channel` is where the order was placed: `web`, `mobile` (the iOS and Android apps) or `store` (point of sale in retail locations).

## analytics.order_items

One row per product in an order. The primary key is (`order_id`, `product_id`). `unit_price` here is the price actually charged on that order, after discounts.
