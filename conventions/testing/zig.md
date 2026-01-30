# Zig Testing Conventions

## Test Structure

```
project/
├── src/
│   ├── main.zig
│   ├── lib.zig
│   └── core/
│       ├── user.zig          # Contains inline tests
│       └── service.zig
├── tests/
│   └── integration/
│       └── full_flow_test.zig
└── build.zig
```

## Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| Test block | `test "description"` | `test "creates user"` |
| Test file | `*_test.zig` | `user_test.zig` |
| Helper | `testing_*` | `testing_allocator` |

## Test Framework

| Purpose | Tool | Notes |
|---------|------|-------|
| Framework | std.testing | Built-in |
| Allocator | std.testing.allocator | Leak detection |
| Assertions | std.testing.expect* | Built-in assertions |

## Test Commands

| Action | Command |
|--------|---------|
| Run all | `zig build test` |
| Run file | `zig test src/core/user.zig` |
| With output | `zig build test --summary all` |
| Filter | `zig test --test-filter "user"` |

## Inline Unit Tests

```zig
// src/core/user.zig
const std = @import("std");
const testing = std.testing;

pub const User = struct {
    id: u64,
    name: []const u8,
    email: []const u8,
    allocator: std.mem.Allocator,

    const Self = @This();

    pub fn init(allocator: std.mem.Allocator, id: u64, name: []const u8, email: []const u8) !Self {
        const name_copy = try allocator.dupe(u8, name);
        errdefer allocator.free(name_copy);

        const email_copy = try allocator.dupe(u8, email);

        return Self{
            .id = id,
            .name = name_copy,
            .email = email_copy,
            .allocator = allocator,
        };
    }

    pub fn deinit(self: *Self) void {
        self.allocator.free(self.name);
        self.allocator.free(self.email);
    }

    pub fn isValidEmail(self: Self) bool {
        return std.mem.indexOf(u8, self.email, "@") != null;
    }
};

// Tests
test "User.init creates user with correct data" {
    const allocator = testing.allocator;

    var user = try User.init(allocator, 1, "Test User", "test@example.com");
    defer user.deinit();

    try testing.expectEqual(@as(u64, 1), user.id);
    try testing.expectEqualStrings("Test User", user.name);
    try testing.expectEqualStrings("test@example.com", user.email);
}

test "User.init copies strings" {
    const allocator = testing.allocator;

    var name = "Original".*;
    var user = try User.init(allocator, 1, &name, "test@example.com");
    defer user.deinit();

    // Modify original
    name[0] = 'X';

    // User's copy should be unchanged
    try testing.expectEqualStrings("Original", user.name);
}

test "User.isValidEmail returns true for valid email" {
    const allocator = testing.allocator;

    var user = try User.init(allocator, 1, "Test", "test@example.com");
    defer user.deinit();

    try testing.expect(user.isValidEmail());
}

test "User.isValidEmail returns false for invalid email" {
    const allocator = testing.allocator;

    var user = try User.init(allocator, 1, "Test", "invalid-email");
    defer user.deinit();

    try testing.expect(!user.isValidEmail());
}
```

## Testing Error Handling

```zig
// src/core/service.zig
const std = @import("std");
const testing = std.testing;

pub const ServiceError = error{
    NotFound,
    InvalidInput,
    ConnectionFailed,
};

pub const Service = struct {
    pub fn getUser(id: u64) ServiceError!User {
        if (id == 0) return error.InvalidInput;
        if (id > 1000) return error.NotFound;
        return User{ .id = id };
    }

    pub fn connectToDatabase(url: []const u8) ServiceError!void {
        if (url.len == 0) return error.InvalidInput;
        if (std.mem.eql(u8, url, "invalid://")) return error.ConnectionFailed;
    }
};

test "Service.getUser returns error for id 0" {
    const result = Service.getUser(0);
    try testing.expectError(error.InvalidInput, result);
}

test "Service.getUser returns error for non-existent user" {
    const result = Service.getUser(9999);
    try testing.expectError(error.NotFound, result);
}

test "Service.getUser returns user for valid id" {
    const user = try Service.getUser(1);
    try testing.expectEqual(@as(u64, 1), user.id);
}

test "Service.connectToDatabase fails for empty url" {
    try testing.expectError(error.InvalidInput, Service.connectToDatabase(""));
}

test "Service.connectToDatabase fails for invalid url" {
    try testing.expectError(error.ConnectionFailed, Service.connectToDatabase("invalid://"));
}
```

## Testing with Allocators

```zig
// Memory leak detection
test "no memory leaks" {
    // testing.allocator detects leaks automatically
    const allocator = testing.allocator;

    var list = std.ArrayList(u8).init(allocator);
    defer list.deinit(); // Forgetting this causes test failure

    try list.append(42);
    try testing.expectEqual(@as(usize, 1), list.items.len);
}

// Testing allocation failures
test "handles allocation failure" {
    var failing_allocator = testing.failing_allocator;

    const result = User.init(failing_allocator, 1, "Test", "test@example.com");
    try testing.expectError(error.OutOfMemory, result);
}
```

## Testing Comptime

```zig
fn fibonacci(n: u64) u64 {
    if (n <= 1) return n;
    return fibonacci(n - 1) + fibonacci(n - 2);
}

test "fibonacci comptime" {
    // Computed at compile time
    const result = comptime fibonacci(10);
    try testing.expectEqual(@as(u64, 55), result);
}

test "fibonacci runtime" {
    // Computed at runtime
    var n: u64 = 10;
    const result = fibonacci(n);
    try testing.expectEqual(@as(u64, 55), result);
}
```

## Integration Tests

```zig
// tests/integration/full_flow_test.zig
const std = @import("std");
const testing = std.testing;
const User = @import("../../src/core/user.zig").User;
const Service = @import("../../src/core/service.zig").Service;

test "full user creation flow" {
    const allocator = testing.allocator;

    // Create service
    var service = Service.init(allocator);
    defer service.deinit();

    // Create user
    const user_id = try service.createUser("Test User", "test@example.com");
    try testing.expect(user_id > 0);

    // Retrieve user
    const user = try service.getUser(user_id);
    defer user.deinit();

    try testing.expectEqualStrings("Test User", user.name);

    // Update user
    try service.updateUser(user_id, .{ .name = "Updated Name" });

    // Verify update
    const updated = try service.getUser(user_id);
    defer updated.deinit();

    try testing.expectEqualStrings("Updated Name", updated.name);
}
```

## Test Helpers

```zig
// src/testing/helpers.zig
const std = @import("std");
const testing = std.testing;

pub fn createTestUser(allocator: std.mem.Allocator) !User {
    return User.init(allocator, 1, "Test User", "test@example.com");
}

pub fn expectUserEqual(expected: User, actual: User) !void {
    try testing.expectEqual(expected.id, actual.id);
    try testing.expectEqualStrings(expected.name, actual.name);
    try testing.expectEqualStrings(expected.email, actual.email);
}

// Usage
test "user equality" {
    const allocator = testing.allocator;

    var user1 = try createTestUser(allocator);
    defer user1.deinit();

    var user2 = try createTestUser(allocator);
    defer user2.deinit();

    try expectUserEqual(user1, user2);
}
```

## Coverage Target

- Test all public functions
- Test error paths
- Test memory management
- Use testing.allocator for leak detection
