-- Read-only role used to execute LLM generated SQL.
-- Even if a guardrail were bypassed, this role cannot write, and long queries are cut off.
CREATE ROLE assistant_ro LOGIN PASSWORD 'assistant_ro';

GRANT CONNECT ON DATABASE assistant TO assistant_ro;
GRANT USAGE ON SCHEMA analytics TO assistant_ro;
GRANT SELECT ON ALL TABLES IN SCHEMA analytics TO assistant_ro;
ALTER DEFAULT PRIVILEGES IN SCHEMA analytics GRANT SELECT ON TABLES TO assistant_ro;

REVOKE ALL ON SCHEMA public FROM assistant_ro;
ALTER ROLE assistant_ro SET default_transaction_read_only = on;
ALTER ROLE assistant_ro SET statement_timeout = '5s';
ALTER ROLE assistant_ro SET search_path = analytics;
