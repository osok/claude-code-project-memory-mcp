# Elixir Conventions

## Project Structure

```
my_app/
├── lib/
│   ├── my_app/
│   │   ├── accounts/           # Context module
│   │   │   ├── user.ex         # Schema
│   │   │   └── accounts.ex     # Context functions
│   │   ├── orders/
│   │   ├── application.ex      # Application supervision tree
│   │   └── repo.ex             # Ecto Repo
│   ├── my_app_web/
│   │   ├── controllers/
│   │   ├── live/               # LiveView modules
│   │   ├── components/
│   │   ├── router.ex
│   │   └── endpoint.ex
│   └── my_app.ex
├── test/
│   ├── my_app/
│   ├── my_app_web/
│   └── support/
├── priv/
│   └── repo/migrations/
├── config/
│   ├── config.exs
│   ├── dev.exs
│   ├── test.exs
│   └── runtime.exs
└── mix.exs
```

## Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| Module | PascalCase | `MyApp.Accounts.User` |
| Function | snake_case | `create_user` |
| Variable | snake_case | `user_name` |
| Atom | snake_case | `:user_created` |
| File | snake_case | `user_controller.ex` |
| Private function | prefix with _ | `_validate_email` |
| Guard clause | is_ prefix | `is_admin` |

## Approved Libraries

| Purpose | Library | Notes |
|---------|---------|-------|
| Web framework | Phoenix | Standard |
| Database | Ecto | ORM |
| Real-time | Phoenix LiveView | Interactive UI |
| HTTP client | Req | Modern HTTP |
| JSON | Jason | Fast JSON |
| Authentication | phx_gen_auth | Built-in generator |
| Testing | ExUnit | Built-in |
| Mocking | Mox | Behaviour mocking |

## Build Commands

| Action | Command |
|--------|---------|
| Deps | `mix deps.get` |
| Compile | `mix compile` |
| Server | `mix phx.server` |
| Test | `mix test` |
| Format | `mix format` |
| Lint | `mix credo` |
| Routes | `mix phx.routes` |
| Migrate | `mix ecto.migrate` |

## Context Module Pattern

```elixir
# lib/my_app/accounts/accounts.ex
defmodule MyApp.Accounts do
  @moduledoc """
  The Accounts context.
  """

  import Ecto.Query, warn: false
  alias MyApp.Repo
  alias MyApp.Accounts.User

  @doc """
  Returns the list of users.
  """
  def list_users do
    Repo.all(User)
  end

  @doc """
  Gets a single user.

  Raises `Ecto.NoResultsError` if the User does not exist.
  """
  def get_user!(id), do: Repo.get!(User, id)

  @doc """
  Gets a single user by email.
  """
  def get_user_by_email(email) when is_binary(email) do
    Repo.get_by(User, email: email)
  end

  @doc """
  Creates a user.
  """
  def create_user(attrs \\ %{}) do
    %User{}
    |> User.changeset(attrs)
    |> Repo.insert()
  end

  @doc """
  Updates a user.
  """
  def update_user(%User{} = user, attrs) do
    user
    |> User.changeset(attrs)
    |> Repo.update()
  end

  @doc """
  Deletes a user.
  """
  def delete_user(%User{} = user) do
    Repo.delete(user)
  end
end
```

## Schema Module

```elixir
# lib/my_app/accounts/user.ex
defmodule MyApp.Accounts.User do
  use Ecto.Schema
  import Ecto.Changeset

  @primary_key {:id, :binary_id, autogenerate: true}
  @foreign_key_type :binary_id

  schema "users" do
    field :email, :string
    field :name, :string
    field :password, :string, virtual: true, redact: true
    field :hashed_password, :string, redact: true
    field :status, Ecto.Enum, values: [:active, :inactive], default: :active

    has_many :orders, MyApp.Orders.Order

    timestamps(type: :utc_datetime)
  end

  @doc false
  def changeset(user, attrs) do
    user
    |> cast(attrs, [:email, :name, :password, :status])
    |> validate_required([:email, :name])
    |> validate_email()
    |> validate_password()
  end

  defp validate_email(changeset) do
    changeset
    |> validate_format(:email, ~r/^[^\s]+@[^\s]+$/, message: "must have @ sign and no spaces")
    |> validate_length(:email, max: 160)
    |> unsafe_validate_unique(:email, MyApp.Repo)
    |> unique_constraint(:email)
  end

  defp validate_password(changeset) do
    changeset
    |> validate_length(:password, min: 8, max: 72)
    |> maybe_hash_password()
  end

  defp maybe_hash_password(changeset) do
    password = get_change(changeset, :password)

    if password && changeset.valid? do
      changeset
      |> put_change(:hashed_password, Bcrypt.hash_pwd_salt(password))
      |> delete_change(:password)
    else
      changeset
    end
  end
end
```

## LiveView Module

```elixir
# lib/my_app_web/live/user_live/index.ex
defmodule MyAppWeb.UserLive.Index do
  use MyAppWeb, :live_view

  alias MyApp.Accounts
  alias MyApp.Accounts.User

  @impl true
  def mount(_params, _session, socket) do
    {:ok, stream(socket, :users, Accounts.list_users())}
  end

  @impl true
  def handle_params(params, _url, socket) do
    {:noreply, apply_action(socket, socket.assigns.live_action, params)}
  end

  defp apply_action(socket, :index, _params) do
    socket
    |> assign(:page_title, "Users")
    |> assign(:user, nil)
  end

  defp apply_action(socket, :new, _params) do
    socket
    |> assign(:page_title, "New User")
    |> assign(:user, %User{})
  end

  @impl true
  def handle_event("delete", %{"id" => id}, socket) do
    user = Accounts.get_user!(id)
    {:ok, _} = Accounts.delete_user(user)

    {:noreply, stream_delete(socket, :users, user)}
  end
end
```

## Code Style

- Use pipe operator `|>` for data transformations
- Pattern match in function heads
- Use `with` for complex conditional logic
- Keep functions small (< 10 lines)
- Use behaviours for polymorphism
- Define typespecs for public functions
- Use contexts to organize business logic
- Prefer immutability
- Handle errors with `{:ok, value}` / `{:error, reason}`
