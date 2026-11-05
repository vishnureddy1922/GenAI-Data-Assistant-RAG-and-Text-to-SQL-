-- Runs once when the Postgres container is first created.
CREATE EXTENSION IF NOT EXISTS vector;

CREATE SCHEMA IF NOT EXISTS analytics;

CREATE TABLE analytics.customers (
    customer_id   integer PRIMARY KEY,
    full_name     text        NOT NULL,
    email         text        NOT NULL,
    country       char(2)     NOT NULL,
    signup_date   date        NOT NULL,
    tier          text        NOT NULL CHECK (tier IN ('bronze', 'silver', 'gold', 'platinum'))
);
COMMENT ON TABLE analytics.customers IS 'One row per customer account';
COMMENT ON COLUMN analytics.customers.country IS 'ISO 3166 alpha-2 country code';
COMMENT ON COLUMN analytics.customers.tier IS 'Loyalty tier: bronze, silver, gold, platinum';

CREATE TABLE analytics.products (
    product_id    integer PRIMARY KEY,
    product_name  text          NOT NULL,
    category      text          NOT NULL,
    unit_price    numeric(10,2) NOT NULL
);
COMMENT ON TABLE analytics.products IS 'Product catalog with current list price';

CREATE TABLE analytics.orders (
    order_id      integer PRIMARY KEY,
    customer_id   integer NOT NULL REFERENCES analytics.customers(customer_id),
    order_date    date    NOT NULL,
    status        text    NOT NULL CHECK (status IN ('completed', 'cancelled', 'refunded')),
    channel       text    NOT NULL CHECK (channel IN ('web', 'mobile', 'store'))
);
COMMENT ON TABLE analytics.orders IS 'Order headers. Only status = completed counts toward revenue';
COMMENT ON COLUMN analytics.orders.channel IS 'Sales channel: web, mobile or store';

CREATE TABLE analytics.order_items (
    order_id      integer       NOT NULL REFERENCES analytics.orders(order_id),
    product_id    integer       NOT NULL REFERENCES analytics.products(product_id),
    quantity      integer       NOT NULL CHECK (quantity > 0),
    unit_price    numeric(10,2) NOT NULL,
    PRIMARY KEY (order_id, product_id)
);
COMMENT ON TABLE analytics.order_items IS 'Order lines. unit_price is the price actually charged at order time';

CREATE INDEX ON analytics.orders (order_date);
CREATE INDEX ON analytics.orders (customer_id);
CREATE INDEX ON analytics.order_items (product_id);
