# Ruby Conventions

## Project Structure

```
project/
├── app/
│   ├── controllers/
│   ├── models/
│   ├── services/           # Service objects
│   ├── jobs/               # Background jobs
│   └── views/
├── config/
│   ├── initializers/
│   └── routes.rb
├── db/
│   ├── migrate/
│   └── schema.rb
├── lib/
│   └── tasks/              # Rake tasks
├── spec/                   # RSpec tests
├── Gemfile
└── Rakefile
```

## Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| Class | PascalCase | `UserService` |
| Module | PascalCase | `Authentication` |
| Method | snake_case | `create_user` |
| Variable | snake_case | `user_name` |
| Constant | SCREAMING_SNAKE_CASE | `MAX_RETRIES` |
| File | snake_case | `user_service.rb` |
| Predicate method | ends with ? | `valid?` |
| Dangerous method | ends with ! | `save!` |
| Setter | ends with = | `name=` |

## Approved Libraries

| Purpose | Library | Notes |
|---------|---------|-------|
| Web framework | Rails or Sinatra | Rails for full apps |
| ORM | ActiveRecord | Built into Rails |
| Background jobs | Sidekiq | Redis-backed |
| HTTP client | Faraday | Flexible HTTP client |
| Authentication | Devise | User auth |
| Authorization | Pundit | Policy-based |
| Serialization | Alba or Blueprinter | JSON serialization |
| Testing | RSpec | BDD testing |
| Linting | RuboCop | Style enforcement |

## Build Commands

| Action | Command |
|--------|---------|
| Run server | `rails server` or `bundle exec rails s` |
| Console | `rails console` |
| Test | `bundle exec rspec` |
| Lint | `bundle exec rubocop` |
| Lint fix | `bundle exec rubocop -A` |
| Migrate | `rails db:migrate` |
| Routes | `rails routes` |
| Install deps | `bundle install` |

## Error Handling

```ruby
# Custom error classes
module Errors
  class NotFoundError < StandardError
    attr_reader :resource, :id

    def initialize(resource, id)
      @resource = resource
      @id = id
      super("#{resource} with id #{id} not found")
    end
  end
end

# Service object pattern
class CreateUser
  def initialize(params)
    @params = params
  end

  def call
    validate!
    user = User.create!(@params)
    Result.success(user)
  rescue ActiveRecord::RecordInvalid => e
    Result.failure(e.message)
  end

  private

  def validate!
    raise ArgumentError, "Email required" if @params[:email].blank?
  end
end
```

## Code Style

- Two spaces for indentation
- Use `frozen_string_literal: true` pragma
- Prefer `&&` and `||` over `and` and `or`
- Use guard clauses for early returns
- Keep methods under 10 lines
- Use service objects for complex business logic
- Prefer composition over inheritance
- Use keyword arguments for methods with 3+ parameters
