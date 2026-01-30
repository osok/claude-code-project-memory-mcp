# Zig Conventions

## Project Structure

```
project/
├── src/
│   ├── main.zig              # Entry point
│   ├── lib.zig               # Library root
│   ├── core/
│   │   ├── allocator.zig
│   │   └── types.zig
│   └── utils/
│       └── string.zig
├── build.zig                  # Build configuration
├── build.zig.zon              # Package manifest
└── tests/
    └── integration/
```

## Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| File | snake_case | `user_service.zig` |
| Function | camelCase | `createUser` |
| Type | PascalCase | `UserService` |
| Constant | SCREAMING_SNAKE | `MAX_SIZE` |
| Variable | snake_case | `user_count` |
| Namespace | snake_case | `std.mem` |

## Approved Libraries

| Purpose | Library | Notes |
|---------|---------|-------|
| Standard | std | Built-in |
| HTTP | std.http | Standard library |
| JSON | std.json | Built-in parser |
| Async | std.event | Event loop |
| Memory | std.mem | Allocators |
| Testing | std.testing | Built-in |

## Build Commands

| Action | Command |
|--------|---------|
| Build | `zig build` |
| Run | `zig build run` |
| Test | `zig build test` |
| Release | `zig build -Doptimize=ReleaseFast` |
| Format | `zig fmt src/` |

## Main Entry Point

```zig
// src/main.zig
const std = @import("std");
const Allocator = std.mem.Allocator;

const UserService = @import("core/user_service.zig").UserService;

pub fn main() !void {
    // Get allocator
    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    // Initialize service
    var service = try UserService.init(allocator);
    defer service.deinit();

    // Run application
    try service.run();
}
```

## Struct Definition

```zig
// src/core/user.zig
const std = @import("std");
const Allocator = std.mem.Allocator;

pub const User = struct {
    id: u64,
    name: []const u8,
    email: []const u8,
    status: Status,

    allocator: Allocator,

    pub const Status = enum {
        active,
        inactive,
        suspended,
    };

    const Self = @This();

    pub fn init(allocator: Allocator, id: u64, name: []const u8, email: []const u8) !Self {
        const name_copy = try allocator.dupe(u8, name);
        errdefer allocator.free(name_copy);

        const email_copy = try allocator.dupe(u8, email);
        errdefer allocator.free(email_copy);

        return Self{
            .id = id,
            .name = name_copy,
            .email = email_copy,
            .status = .active,
            .allocator = allocator,
        };
    }

    pub fn deinit(self: *Self) void {
        self.allocator.free(self.name);
        self.allocator.free(self.email);
    }

    pub fn isActive(self: Self) bool {
        return self.status == .active;
    }

    pub fn format(
        self: Self,
        comptime fmt: []const u8,
        options: std.fmt.FormatOptions,
        writer: anytype,
    ) !void {
        _ = fmt;
        _ = options;
        try writer.print("User{{ id: {d}, name: {s}, email: {s} }}", .{
            self.id,
            self.name,
            self.email,
        });
    }
};
```

## Error Handling

```zig
// src/core/errors.zig
pub const UserError = error{
    NotFound,
    InvalidEmail,
    DuplicateEmail,
    DatabaseError,
};

pub const AppError = UserError || std.mem.Allocator.Error;

// Usage
pub fn getUser(id: u64) AppError!User {
    const user = database.find(id) orelse return error.NotFound;
    return user;
}

// Error handling patterns
pub fn processUser(id: u64) !void {
    const user = getUser(id) catch |err| switch (err) {
        error.NotFound => {
            std.log.warn("User {d} not found", .{id});
            return;
        },
        error.DatabaseError => return err,
        else => return err,
    };

    try user.validate();
}
```

## Generic Functions

```zig
// src/utils/collections.zig
const std = @import("std");
const Allocator = std.mem.Allocator;

pub fn ArrayList(comptime T: type) type {
    return struct {
        items: []T,
        capacity: usize,
        allocator: Allocator,

        const Self = @This();

        pub fn init(allocator: Allocator) Self {
            return Self{
                .items = &[_]T{},
                .capacity = 0,
                .allocator = allocator,
            };
        }

        pub fn deinit(self: *Self) void {
            self.allocator.free(self.items.ptr[0..self.capacity]);
        }

        pub fn append(self: *Self, item: T) !void {
            if (self.items.len >= self.capacity) {
                try self.ensureCapacity(self.capacity * 2 + 1);
            }
            self.items.ptr[self.items.len] = item;
            self.items.len += 1;
        }

        fn ensureCapacity(self: *Self, new_capacity: usize) !void {
            const new_items = try self.allocator.realloc(
                self.items.ptr[0..self.capacity],
                new_capacity,
            );
            self.items.ptr = new_items.ptr;
            self.capacity = new_capacity;
        }
    };
}
```

## Build Configuration

```zig
// build.zig
const std = @import("std");

pub fn build(b: *std.Build) void {
    const target = b.standardTargetOptions(.{});
    const optimize = b.standardOptimizeOption(.{});

    // Executable
    const exe = b.addExecutable(.{
        .name = "myapp",
        .root_source_file = b.path("src/main.zig"),
        .target = target,
        .optimize = optimize,
    });
    b.installArtifact(exe);

    // Run step
    const run_cmd = b.addRunArtifact(exe);
    run_cmd.step.dependOn(b.getInstallStep());
    const run_step = b.step("run", "Run the application");
    run_step.dependOn(&run_cmd.step);

    // Tests
    const unit_tests = b.addTest(.{
        .root_source_file = b.path("src/main.zig"),
        .target = target,
        .optimize = optimize,
    });
    const run_unit_tests = b.addRunArtifact(unit_tests);
    const test_step = b.step("test", "Run unit tests");
    test_step.dependOn(&run_unit_tests.step);
}
```

## Code Style

- Use explicit allocators
- Handle all errors explicitly
- Use `defer` for cleanup
- Prefer comptime where possible
- Use `errdefer` for error cleanup
- Keep functions pure when possible
- Use `const` by default
- Document public functions
- Use meaningful error sets
