-- Deterministic synthetic data (setseed makes random() repeatable).
SELECT setseed(0.42);

INSERT INTO analytics.customers (customer_id, full_name, email, country, signup_date, tier)
SELECT
    g,
    (ARRAY['Ava','Liam','Noah','Emma','Mia','Ethan','Priya','Arjun','Wei','Sofia','Lucas','Zara'])[1 + floor(random() * 12)::int]
      || ' ' ||
    (ARRAY['Smith','Reddy','Garcia','Chen','Patel','Brown','Kim','Lopez','Nguyen','Khan'])[1 + floor(random() * 10)::int],
    'customer' || g || '@example.com',
    (ARRAY['US','US','US','CA','GB','DE','IN','AU'])[1 + floor(random() * 8)::int],
    DATE '2024-01-01' + floor(random() * 640)::int,
    (ARRAY['bronze','bronze','bronze','silver','silver','gold','platinum'])[1 + floor(random() * 7)::int]
FROM generate_series(1, 1500) AS g;

INSERT INTO analytics.products (product_id, product_name, category, unit_price)
SELECT
    g,
    c.category || ' item ' || g,
    c.category,
    round((c.base + random() * c.base * 2)::numeric, 2)
FROM generate_series(1, 120) AS g
CROSS JOIN LATERAL (
    SELECT (ARRAY['Electronics','Home','Books','Beauty','Sports','Toys'])[1 + (g % 6)] AS category,
           (ARRAY[120, 45, 15, 25, 60, 30])[1 + (g % 6)] AS base
) c;

INSERT INTO analytics.orders (order_id, customer_id, order_date, status, channel)
SELECT
    g,
    1 + floor(random() * 1500)::int,
    DATE '2025-01-01' + floor(random() * 640)::int,
    (ARRAY['completed','completed','completed','completed','completed','completed','completed','completed','cancelled','refunded'])[1 + floor(random() * 10)::int],
    (ARRAY['web','web','mobile','mobile','store'])[1 + floor(random() * 5)::int]
FROM generate_series(1, 20000) AS g;

-- 1 to 3 distinct products per order, charged near list price
INSERT INTO analytics.order_items (order_id, product_id, quantity, unit_price)
SELECT DISTINCT ON (o.order_id, p.product_id)
    o.order_id,
    p.product_id,
    1 + floor(random() * 3)::int,
    round(p.unit_price * (0.85 + random() * 0.15)::numeric, 2)
FROM analytics.orders o
CROSS JOIN LATERAL generate_series(1, 1 + (o.order_id % 3)) AS line
JOIN analytics.products p ON p.product_id = 1 + ((o.order_id * 7 + line * 13) % 120);

ANALYZE;
