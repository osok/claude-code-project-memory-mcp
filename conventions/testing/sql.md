# SQL Testing Conventions

## Test Structure

```
database/
├── migrations/
├── tests/
│   ├── unit/
│   │   ├── functions/
│   │   │   └── test_calculate_total.sql
│   │   └── triggers/
│   │       └── test_update_timestamp.sql
│   ├── integration/
│   │   └── test_order_flow.sql
│   ├── fixtures/
│   │   ├── users.sql
│   │   └── orders.sql
│   └── helpers/
│       └── test_helpers.sql
└── pgtest.yaml
```

## Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| Test file | `test_{function}.sql` | `test_calculate_total.sql` |
| Test function | `test_{scenario}` | `test_returns_correct_total` |
| Fixture | `{table}.sql` | `users.sql` |

## Test Framework

| Purpose | Tool | Notes |
|---------|------|-------|
| PostgreSQL | pgTAP | TAP-compliant |
| General | SQLite + Python | Simple testing |
| Schema | SchemaSpy | Documentation |
| Migration | Flyway/Liquibase | Version testing |

## Test Commands

| Action | Command |
|--------|---------|
| Run pgTAP | `pg_prove -d testdb tests/` |
| Single file | `pg_prove -d testdb tests/unit/test_func.sql` |
| Verbose | `pg_prove -v -d testdb tests/` |

## pgTAP Unit Tests

```sql
-- tests/unit/functions/test_calculate_total.sql
BEGIN;
SELECT plan(4);

-- Setup test data
INSERT INTO orders (id, user_id, status) VALUES (1, 1, 'pending');
INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES
    (1, 101, 2, 10.00),
    (1, 102, 1, 25.00);

-- Test 1: Calculate correct total
SELECT is(
    calculate_order_total(1),
    45.00::NUMERIC(10,2),
    'Should calculate correct total for order with items'
);

-- Test 2: Empty order returns zero
INSERT INTO orders (id, user_id, status) VALUES (2, 1, 'pending');
SELECT is(
    calculate_order_total(2),
    0.00::NUMERIC(10,2),
    'Should return zero for order with no items'
);

-- Test 3: Non-existent order returns zero
SELECT is(
    calculate_order_total(9999),
    0.00::NUMERIC(10,2),
    'Should return zero for non-existent order'
);

-- Test 4: Handles decimal quantities
INSERT INTO orders (id, user_id, status) VALUES (3, 1, 'pending');
INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES
    (3, 103, 1.5, 10.00);
SELECT is(
    calculate_order_total(3),
    15.00::NUMERIC(10,2),
    'Should handle decimal quantities'
);

SELECT * FROM finish();
ROLLBACK;
```

## Trigger Tests

```sql
-- tests/unit/triggers/test_update_timestamp.sql
BEGIN;
SELECT plan(2);

-- Setup
INSERT INTO users (id, email, name, password_hash)
VALUES (1, 'test@example.com', 'Test User', 'hash');

-- Capture original timestamps
SELECT created_at, updated_at INTO STRICT _orig
FROM users WHERE id = 1;

-- Wait a moment to ensure timestamp changes
SELECT pg_sleep(0.1);

-- Update the user
UPDATE users SET name = 'Updated Name' WHERE id = 1;

-- Test 1: created_at unchanged
SELECT is(
    (SELECT created_at FROM users WHERE id = 1),
    _orig.created_at,
    'created_at should not change on update'
);

-- Test 2: updated_at changed
SELECT isnt(
    (SELECT updated_at FROM users WHERE id = 1),
    _orig.updated_at,
    'updated_at should change on update'
);

SELECT * FROM finish();
ROLLBACK;
```

## View Tests

```sql
-- tests/unit/views/test_order_summary.sql
BEGIN;
SELECT plan(3);

-- Setup test data
INSERT INTO users (id, email, name, password_hash)
VALUES (1, 'test@example.com', 'Test User', 'hash');

INSERT INTO orders (id, user_id, status)
VALUES (1, 1, 'completed');

INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES
    (1, 101, 2, 10.00),
    (1, 102, 3, 5.00);

-- Test view returns correct data
SELECT is(
    (SELECT item_count FROM order_summary WHERE order_id = 1),
    2::BIGINT,
    'Should count items correctly'
);

SELECT is(
    (SELECT total_amount FROM order_summary WHERE order_id = 1),
    35.00::NUMERIC,
    'Should calculate total correctly'
);

-- Test soft-deleted orders excluded
UPDATE orders SET deleted_at = NOW() WHERE id = 1;
SELECT is(
    (SELECT COUNT(*) FROM order_summary WHERE order_id = 1),
    0::BIGINT,
    'Should exclude soft-deleted orders'
);

SELECT * FROM finish();
ROLLBACK;
```

## Integration Tests

```sql
-- tests/integration/test_order_flow.sql
BEGIN;
SELECT plan(5);

-- Test complete order flow
-- 1. Create user
INSERT INTO users (email, name, password_hash)
VALUES ('customer@example.com', 'Customer', 'hash')
RETURNING id INTO _user_id;

SELECT ok(_user_id IS NOT NULL, 'User created');

-- 2. Create order
INSERT INTO orders (user_id, status)
VALUES (_user_id, 'pending')
RETURNING id INTO _order_id;

SELECT ok(_order_id IS NOT NULL, 'Order created');

-- 3. Add items
INSERT INTO order_items (order_id, product_id, quantity, unit_price)
VALUES
    (_order_id, 1, 2, 29.99),
    (_order_id, 2, 1, 49.99);

SELECT is(
    (SELECT COUNT(*) FROM order_items WHERE order_id = _order_id),
    2::BIGINT,
    'Items added to order'
);

-- 4. Complete order
UPDATE orders SET status = 'completed' WHERE id = _order_id;

SELECT is(
    (SELECT status FROM orders WHERE id = _order_id),
    'completed',
    'Order completed'
);

-- 5. Verify summary
SELECT is(
    (SELECT total_amount FROM order_summary WHERE order_id = _order_id),
    109.97::NUMERIC,
    'Order summary shows correct total'
);

SELECT * FROM finish();
ROLLBACK;
```

## Test Fixtures

```sql
-- tests/fixtures/users.sql
-- Idempotent fixture loading
INSERT INTO users (id, email, name, password_hash, status) VALUES
    (1, 'admin@example.com', 'Admin User', 'hash1', 'active'),
    (2, 'user@example.com', 'Regular User', 'hash2', 'active'),
    (3, 'inactive@example.com', 'Inactive User', 'hash3', 'inactive')
ON CONFLICT (id) DO UPDATE SET
    email = EXCLUDED.email,
    name = EXCLUDED.name;

-- Reset sequence
SELECT setval('users_id_seq', (SELECT MAX(id) FROM users));
```

## Test Helpers

```sql
-- tests/helpers/test_helpers.sql
CREATE OR REPLACE FUNCTION test_truncate_tables()
RETURNS VOID
LANGUAGE plpgsql
AS $$
BEGIN
    TRUNCATE TABLE order_items, orders, users CASCADE;
END;
$$;

CREATE OR REPLACE FUNCTION test_seed_user(
    p_email VARCHAR DEFAULT 'test@example.com',
    p_name VARCHAR DEFAULT 'Test User'
)
RETURNS BIGINT
LANGUAGE plpgsql
AS $$
DECLARE
    v_id BIGINT;
BEGIN
    INSERT INTO users (email, name, password_hash)
    VALUES (p_email, p_name, 'test_hash')
    RETURNING id INTO v_id;

    RETURN v_id;
END;
$$;
```

## Coverage Target

- Test all functions and procedures
- Test all triggers
- Test view correctness
- Test constraint violations
- Integration test critical flows
