# PHP Conventions

## Project Structure

```
project/
├── app/
│   ├── Http/
│   │   ├── Controllers/
│   │   ├── Middleware/
│   │   └── Requests/        # Form requests
│   ├── Models/
│   ├── Services/
│   └── Repositories/
├── config/
├── database/
│   ├── migrations/
│   └── seeders/
├── resources/
│   └── views/
├── routes/
│   ├── api.php
│   └── web.php
├── tests/
├── composer.json
└── phpunit.xml
```

## Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| Class | PascalCase | `UserService` |
| Interface | PascalCase + Interface | `UserRepositoryInterface` |
| Method | camelCase | `createUser` |
| Property | camelCase | `$userName` |
| Constant | SCREAMING_SNAKE_CASE | `MAX_RETRIES` |
| File | PascalCase | `UserService.php` |
| Route | kebab-case | `/api/user-profiles` |
| Table | snake_case, plural | `user_profiles` |

## Approved Libraries

| Purpose | Library | Notes |
|---------|---------|-------|
| Framework | Laravel | Full-stack framework |
| ORM | Eloquent | Built into Laravel |
| HTTP client | Guzzle | HTTP requests |
| Queue | Laravel Queues | Redis/database backed |
| Validation | Laravel Validation | Built-in |
| Testing | PHPUnit + Pest | Pest preferred for new projects |
| Linting | PHP-CS-Fixer | Code style |
| Static analysis | PHPStan or Larastan | Type checking |

## Build Commands

| Action | Command |
|--------|---------|
| Run server | `php artisan serve` |
| Console | `php artisan tinker` |
| Test | `php artisan test` or `./vendor/bin/pest` |
| Lint | `./vendor/bin/php-cs-fixer fix` |
| Static analysis | `./vendor/bin/phpstan analyse` |
| Migrate | `php artisan migrate` |
| Clear cache | `php artisan cache:clear` |
| Install deps | `composer install` |

## Error Handling

```php
<?php

namespace App\Exceptions;

use Exception;

class NotFoundException extends Exception
{
    public function __construct(
        public readonly string $resource,
        public readonly mixed $key
    ) {
        parent::__construct("{$resource} with key {$key} not found");
    }

    public function render(): JsonResponse
    {
        return response()->json([
            'error' => $this->getMessage()
        ], 404);
    }
}

// Service pattern with result
class CreateUserService
{
    public function execute(CreateUserRequest $request): Result
    {
        try {
            $user = User::create($request->validated());
            return Result::success($user);
        } catch (QueryException $e) {
            return Result::failure('Failed to create user');
        }
    }
}
```

## Code Style

- Follow PSR-12 coding standard
- Use PHP 8.2+ features (readonly, enums, named arguments)
- Use strict types: `declare(strict_types=1);`
- Use dependency injection via constructor
- Keep controllers thin, logic in services
- Use form requests for validation
- Use resources for API responses
- Type everything: parameters, returns, properties
