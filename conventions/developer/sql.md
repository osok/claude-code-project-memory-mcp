# SQL Conventions

## Project Structure

```
database/
├── migrations/
│   ├── 001_create_users.sql
│   ├── 002_create_orders.sql
│   └── 003_add_user_email_index.sql
├── seeds/
│   ├── dev/
│   │   └── users.sql
│   └── test/
│       └── users.sql
├── functions/
│   └── calculate_total.sql
├── views/
│   └── order_summary.sql
├── triggers/
│   └── update_timestamp.sql
└── queries/
    └── reports/
        └── monthly_sales.sql
```

## Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| Table | snake_case, plural | `users`, `order_items` |
| Column | snake_case | `first_name`, `created_at` |
| Primary key | `id` | `id` |
| Foreign key | `{table}_id` | `user_id`, `order_id` |
| Index | `idx_{table}_{columns}` | `idx_users_email` |
| Unique | `uq_{table}_{columns}` | `uq_users_email` |
| Check | `chk_{table}_{column}` | `chk_orders_total_positive` |
| Function | snake_case, verb | `calculate_total` |
| View | snake_case | `order_summary` |
| Trigger | `trg_{table}_{action}` | `trg_users_updated_at` |

## Standard Columns

```sql
-- Every table should have these columns
CREATE TABLE users (
    id          BIGSERIAL PRIMARY KEY,
    -- ... other columns ...
    created_at  TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- For soft deletes
deleted_at  TIMESTAMP WITH TIME ZONE
```

## Migration File Format

```sql
-- migrations/001_create_users.sql
-- Description: Create users table
-- Author: developer@example.com
-- Date: 2024-01-15

-- Up
CREATE TABLE users (
    id              BIGSERIAL PRIMARY KEY,
    email           VARCHAR(255) NOT NULL,
    name            VARCHAR(255) NOT NULL,
    password_hash   VARCHAR(255) NOT NULL,
    status          VARCHAR(50) NOT NULL DEFAULT 'active',
    created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_users_email UNIQUE (email),
    CONSTRAINT chk_users_status CHECK (status IN ('active', 'inactive', 'suspended'))
);

CREATE INDEX idx_users_email ON users (email);
CREATE INDEX idx_users_status ON users (status);

-- Down
DROP TABLE IF EXISTS users;
```

## Query Formatting

```sql
-- SELECT statements
SELECT
    u.id,
    u.name,
    u.email,
    COUNT(o.id) AS order_count,
    SUM(o.total) AS total_spent
FROM users u
LEFT JOIN orders o ON o.user_id = u.id
WHERE u.status = 'active'
    AND u.created_at >= '2024-01-01'
GROUP BY u.id, u.name, u.email
HAVING COUNT(o.id) > 0
ORDER BY total_spent DESC
LIMIT 100;

-- INSERT statements
INSERT INTO users (
    email,
    name,
    password_hash,
    status
) VALUES (
    'user@example.com',
    'John Doe',
    '$2b$10$...',
    'active'
)
RETURNING id, created_at;

-- UPDATE statements
UPDATE users
SET
    name = 'Jane Doe',
    updated_at = NOW()
WHERE id = 123
    AND status = 'active';

-- DELETE statements (prefer soft delete)
UPDATE users
SET
    deleted_at = NOW(),
    updated_at = NOW()
WHERE id = 123;
```

## Functions

```sql
-- functions/calculate_order_total.sql
CREATE OR REPLACE FUNCTION calculate_order_total(p_order_id BIGINT)
RETURNS NUMERIC(10, 2)
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    v_total NUMERIC(10, 2);
BEGIN
    SELECT COALESCE(SUM(quantity * unit_price), 0)
    INTO v_total
    FROM order_items
    WHERE order_id = p_order_id;

    RETURN v_total;
END;
$$;

COMMENT ON FUNCTION calculate_order_total IS 'Calculate total for an order';
```

## Views

```sql
-- views/order_summary.sql
CREATE OR REPLACE VIEW order_summary AS
SELECT
    o.id AS order_id,
    o.created_at AS order_date,
    u.id AS user_id,
    u.name AS user_name,
    u.email AS user_email,
    COUNT(oi.id) AS item_count,
    SUM(oi.quantity * oi.unit_price) AS total_amount
FROM orders o
INNER JOIN users u ON u.id = o.user_id
LEFT JOIN order_items oi ON oi.order_id = o.id
WHERE o.deleted_at IS NULL
GROUP BY o.id, o.created_at, u.id, u.name, u.email;

COMMENT ON VIEW order_summary IS 'Aggregated order information with user details';
```

## Triggers

```sql
-- triggers/update_timestamp.sql
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

-- Apply to tables
CREATE TRIGGER trg_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();
```

## Code Style

- Use uppercase for SQL keywords
- Use lowercase for identifiers
- Align keywords vertically
- One column per line in SELECT
- Indent JOIN conditions
- Use table aliases consistently
- Comment complex queries
- Use parameterized queries (never concatenate)
- Always specify columns in INSERT
- Use transactions for multiple statements
