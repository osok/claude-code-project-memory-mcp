# Elixir Testing Conventions

## Test Structure

```
test/
├── my_app/
│   ├── accounts_test.exs       # Context tests
│   └── accounts/
│       └── user_test.exs       # Schema tests
├── my_app_web/
│   ├── controllers/
│   │   └── user_controller_test.exs
│   └── live/
│       └── user_live_test.exs
├── support/
│   ├── conn_case.ex            # Controller test case
│   ├── data_case.ex            # Data test case
│   ├── fixtures/
│   │   └── accounts_fixtures.ex
│   └── mocks.ex
└── test_helper.exs
```

## Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| Test file | `{module}_test.exs` | `accounts_test.exs` |
| Test module | `{Module}Test` | `MyApp.AccountsTest` |
| Test function | `test "description"` | `test "creates user"` |
| Fixture | `{context}_fixtures.ex` | `accounts_fixtures.ex` |

## Test Framework

| Purpose | Tool | Notes |
|---------|------|-------|
| Framework | ExUnit | Built-in |
| Mocking | Mox | Behaviour-based |
| Factory | ExMachina | Test data |
| Coverage | excoveralls | Code coverage |

## Test Commands

| Action | Command |
|--------|---------|
| Run all | `mix test` |
| Run file | `mix test test/my_app/accounts_test.exs` |
| Run line | `mix test test/my_app/accounts_test.exs:42` |
| Watch | `mix test.watch` |
| Coverage | `mix coveralls` |
| Stale | `mix test --stale` |

## Context Tests

```elixir
# test/my_app/accounts_test.exs
defmodule MyApp.AccountsTest do
  use MyApp.DataCase, async: true

  alias MyApp.Accounts
  alias MyApp.Accounts.User

  import MyApp.AccountsFixtures

  describe "list_users/0" do
    test "returns all users" do
      user = user_fixture()
      assert Accounts.list_users() == [user]
    end

    test "returns empty list when no users" do
      assert Accounts.list_users() == []
    end
  end

  describe "get_user!/1" do
    test "returns the user with given id" do
      user = user_fixture()
      assert Accounts.get_user!(user.id) == user
    end

    test "raises when user does not exist" do
      assert_raise Ecto.NoResultsError, fn ->
        Accounts.get_user!(Ecto.UUID.generate())
      end
    end
  end

  describe "create_user/1" do
    test "creates user with valid data" do
      valid_attrs = %{
        email: "user@example.com",
        name: "Test User",
        password: "password123"
      }

      assert {:ok, %User{} = user} = Accounts.create_user(valid_attrs)
      assert user.email == "user@example.com"
      assert user.name == "Test User"
      assert user.hashed_password != nil
    end

    test "returns error changeset with invalid data" do
      invalid_attrs = %{email: nil, name: nil}

      assert {:error, %Ecto.Changeset{}} = Accounts.create_user(invalid_attrs)
    end

    test "returns error for duplicate email" do
      user = user_fixture()
      attrs = %{email: user.email, name: "Another", password: "password123"}

      assert {:error, changeset} = Accounts.create_user(attrs)
      assert "has already been taken" in errors_on(changeset).email
    end
  end

  describe "update_user/2" do
    test "updates user with valid data" do
      user = user_fixture()
      update_attrs = %{name: "Updated Name"}

      assert {:ok, %User{} = updated} = Accounts.update_user(user, update_attrs)
      assert updated.name == "Updated Name"
    end

    test "returns error changeset with invalid data" do
      user = user_fixture()
      invalid_attrs = %{email: "invalid"}

      assert {:error, %Ecto.Changeset{}} = Accounts.update_user(user, invalid_attrs)
      assert user == Accounts.get_user!(user.id)
    end
  end

  describe "delete_user/1" do
    test "deletes the user" do
      user = user_fixture()
      assert {:ok, %User{}} = Accounts.delete_user(user)
      assert_raise Ecto.NoResultsError, fn -> Accounts.get_user!(user.id) end
    end
  end
end
```

## Fixtures

```elixir
# test/support/fixtures/accounts_fixtures.ex
defmodule MyApp.AccountsFixtures do
  @moduledoc """
  Test fixtures for Accounts context.
  """

  def unique_user_email, do: "user#{System.unique_integer()}@example.com"

  def valid_user_attributes(attrs \\ %{}) do
    Enum.into(attrs, %{
      email: unique_user_email(),
      name: "Test User",
      password: "password123456"
    })
  end

  def user_fixture(attrs \\ %{}) do
    {:ok, user} =
      attrs
      |> valid_user_attributes()
      |> MyApp.Accounts.create_user()

    user
  end
end
```

## Controller Tests

```elixir
# test/my_app_web/controllers/user_controller_test.exs
defmodule MyAppWeb.UserControllerTest do
  use MyAppWeb.ConnCase, async: true

  import MyApp.AccountsFixtures

  @create_attrs %{email: "new@example.com", name: "New User", password: "password123"}
  @invalid_attrs %{email: nil, name: nil}

  describe "index" do
    test "lists all users", %{conn: conn} do
      conn = get(conn, ~p"/api/users")
      assert json_response(conn, 200)["data"] == []
    end
  end

  describe "create user" do
    test "renders user when data is valid", %{conn: conn} do
      conn = post(conn, ~p"/api/users", user: @create_attrs)
      assert %{"id" => id} = json_response(conn, 201)["data"]

      conn = get(conn, ~p"/api/users/#{id}")
      assert %{"id" => ^id, "email" => "new@example.com"} = json_response(conn, 200)["data"]
    end

    test "renders errors when data is invalid", %{conn: conn} do
      conn = post(conn, ~p"/api/users", user: @invalid_attrs)
      assert json_response(conn, 422)["errors"] != %{}
    end
  end

  describe "show user" do
    setup [:create_user]

    test "renders user", %{conn: conn, user: user} do
      conn = get(conn, ~p"/api/users/#{user}")
      assert json_response(conn, 200)["data"]["id"] == user.id
    end
  end

  defp create_user(_) do
    user = user_fixture()
    %{user: user}
  end
end
```

## LiveView Tests

```elixir
# test/my_app_web/live/user_live_test.exs
defmodule MyAppWeb.UserLiveTest do
  use MyAppWeb.ConnCase, async: true

  import Phoenix.LiveViewTest
  import MyApp.AccountsFixtures

  describe "Index" do
    test "lists all users", %{conn: conn} do
      user = user_fixture()
      {:ok, _view, html} = live(conn, ~p"/users")

      assert html =~ "Users"
      assert html =~ user.email
    end

    test "deletes user", %{conn: conn} do
      user = user_fixture()
      {:ok, view, _html} = live(conn, ~p"/users")

      assert view
             |> element("#users-#{user.id} a", "Delete")
             |> render_click() =~ "Users"

      refute has_element?(view, "#users-#{user.id}")
    end
  end

  describe "New" do
    test "creates new user", %{conn: conn} do
      {:ok, view, _html} = live(conn, ~p"/users/new")

      assert view
             |> form("#user-form", user: %{email: "new@example.com", name: "New", password: "password123"})
             |> render_submit()

      assert_redirect(view, ~p"/users")
    end

    test "shows validation errors", %{conn: conn} do
      {:ok, view, _html} = live(conn, ~p"/users/new")

      assert view
             |> form("#user-form", user: %{email: "", name: ""})
             |> render_change() =~ "can&#39;t be blank"
    end
  end
end
```

## Mocking with Mox

```elixir
# Define behaviour
defmodule MyApp.ExternalService do
  @callback fetch_data(String.t()) :: {:ok, map()} | {:error, term()}
end

# In test/support/mocks.ex
Mox.defmock(MyApp.MockExternalService, for: MyApp.ExternalService)

# In test
defmodule MyApp.SomeModuleTest do
  use MyApp.DataCase, async: true

  import Mox

  setup :verify_on_exit!

  test "uses external service" do
    expect(MyApp.MockExternalService, :fetch_data, fn "123" ->
      {:ok, %{data: "test"}}
    end)

    assert {:ok, result} = MyApp.SomeModule.process("123")
    assert result.data == "test"
  end
end
```

## Coverage Target

- Minimum: 80% line coverage
- Focus on context modules and schemas
- Test LiveView interactions
- Mock external services
