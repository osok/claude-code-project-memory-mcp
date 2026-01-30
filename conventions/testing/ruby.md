# Ruby Testing Conventions

## Test Structure

```
spec/
├── controllers/
│   └── users_controller_spec.rb
├── models/
│   └── user_spec.rb
├── services/
│   └── create_user_spec.rb
├── requests/              # API integration tests
│   └── users_spec.rb
├── support/
│   ├── factory_bot.rb
│   └── shared_examples/
├── rails_helper.rb
└── spec_helper.rb
```

## Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| Spec file | `{class}_spec.rb` | `user_service_spec.rb` |
| Describe block | Class or method name | `describe UserService` |
| Context | Starts with "when" or "with" | `context "when user exists"` |
| It block | Describes behavior | `it "returns the user"` |
| Factory | snake_case | `create(:user)` |

## Test Framework

| Purpose | Tool | Notes |
|---------|------|-------|
| Framework | RSpec | BDD-style testing |
| Factories | FactoryBot | Test data generation |
| Mocking | RSpec Mocks | Built-in |
| HTTP mocking | WebMock | External API mocking |
| Time mocking | Timecop | Time travel |
| Coverage | SimpleCov | Code coverage |

## Test Commands

| Action | Command |
|--------|---------|
| Run all | `bundle exec rspec` |
| Run file | `bundle exec rspec spec/models/user_spec.rb` |
| Run line | `bundle exec rspec spec/models/user_spec.rb:42` |
| Run tag | `bundle exec rspec --tag focus` |
| Documentation | `bundle exec rspec --format documentation` |
| Coverage | `COVERAGE=true bundle exec rspec` |

## Unit Tests

```ruby
# spec/services/create_user_spec.rb
require 'rails_helper'

RSpec.describe CreateUser do
  describe '#call' do
    subject(:service) { described_class.new(params) }

    context 'when params are valid' do
      let(:params) { { name: 'Test', email: 'test@example.com' } }

      it 'creates a user' do
        expect { service.call }.to change(User, :count).by(1)
      end

      it 'returns success result' do
        result = service.call
        expect(result).to be_success
        expect(result.value.name).to eq('Test')
      end
    end

    context 'when email is missing' do
      let(:params) { { name: 'Test' } }

      it 'returns failure result' do
        result = service.call
        expect(result).to be_failure
        expect(result.error).to include('email')
      end
    end
  end
end
```

## Factories

```ruby
# spec/factories/users.rb
FactoryBot.define do
  factory :user do
    sequence(:email) { |n| "user#{n}@example.com" }
    name { 'Test User' }
    created_at { Time.current }

    trait :admin do
      role { 'admin' }
    end

    trait :with_posts do
      transient do
        posts_count { 3 }
      end

      after(:create) do |user, evaluator|
        create_list(:post, evaluator.posts_count, user: user)
      end
    end
  end
end

# Usage
create(:user)
create(:user, :admin)
create(:user, :with_posts, posts_count: 5)
build(:user)  # doesn't persist
```

## Request Specs (Integration)

```ruby
# spec/requests/users_spec.rb
require 'rails_helper'

RSpec.describe 'Users API', type: :request do
  describe 'GET /api/users' do
    let!(:users) { create_list(:user, 3) }

    it 'returns all users' do
      get '/api/users'

      expect(response).to have_http_status(:ok)
      expect(json_response.size).to eq(3)
    end
  end

  describe 'POST /api/users' do
    let(:valid_params) { { user: { name: 'Test', email: 'test@example.com' } } }

    it 'creates a user' do
      expect {
        post '/api/users', params: valid_params
      }.to change(User, :count).by(1)

      expect(response).to have_http_status(:created)
    end
  end

  private

  def json_response
    JSON.parse(response.body)
  end
end
```

## Shared Examples

```ruby
# spec/support/shared_examples/paginatable.rb
RSpec.shared_examples 'paginatable' do
  it 'returns paginated results' do
    get endpoint, params: { page: 1, per_page: 10 }

    expect(response).to have_http_status(:ok)
    expect(json_response['meta']).to include('total_pages', 'current_page')
  end
end

# Usage
RSpec.describe 'Users API' do
  it_behaves_like 'paginatable' do
    let(:endpoint) { '/api/users' }
  end
end
```

## Mocking

```ruby
# Stub method
allow(UserMailer).to receive(:welcome).and_return(double(deliver_later: true))

# Expect call
expect(UserMailer).to receive(:welcome).with(user).once

# Stub external API
stub_request(:get, 'https://api.example.com/users')
  .to_return(status: 200, body: { users: [] }.to_json)
```

## Coverage Target

- Minimum: 80% line coverage
- 100% coverage for service objects
- Use SimpleCov with minimum coverage enforcement
