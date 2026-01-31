"""Repository for User entities."""

from typing import Optional
from uuid import UUID

from ..models.user import User, UserRole
from .base import InMemoryRepository


class UserRepository(InMemoryRepository[User]):
    """
    Repository for managing User entities.

    Provides specialized query methods for users beyond basic CRUD.
    """

    def __init__(self) -> None:
        """Initialize the user repository."""
        super().__init__(id_getter=lambda u: u.id)
        self._email_index: dict[str, UUID] = {}
        self._username_index: dict[str, UUID] = {}

    def create(self, entity: User) -> User:
        """Create a new user with index updates."""
        if entity.email.lower() in self._email_index:
            raise ValueError(f"Email {entity.email} already exists")
        if entity.username.lower() in self._username_index:
            raise ValueError(f"Username {entity.username} already exists")

        result = super().create(entity)
        self._email_index[entity.email.lower()] = entity.id
        self._username_index[entity.username.lower()] = entity.id
        return result

    def delete(self, id: UUID) -> bool:
        """Delete a user and update indexes."""
        user = self.get(id)
        if user:
            self._email_index.pop(user.email.lower(), None)
            self._username_index.pop(user.username.lower(), None)
        return super().delete(id)

    def clear(self) -> None:
        """Clear all users and indexes."""
        super().clear()
        self._email_index.clear()
        self._username_index.clear()

    def get_by_email(self, email: str) -> Optional[User]:
        """
        Get a user by email address.

        Args:
            email: The email to search for.

        Returns:
            The user if found, None otherwise.
        """
        user_id = self._email_index.get(email.lower())
        if user_id:
            return self.get(user_id)
        return None

    def get_by_username(self, username: str) -> Optional[User]:
        """
        Get a user by username.

        Args:
            username: The username to search for.

        Returns:
            The user if found, None otherwise.
        """
        user_id = self._username_index.get(username.lower())
        if user_id:
            return self.get(user_id)
        return None

    def get_by_role(self, role: UserRole) -> list[User]:
        """
        Get all users with a specific role.

        Args:
            role: The role to filter by.

        Returns:
            List of users with the role.
        """
        return self.find_by(lambda u: u.role == role)

    def get_active(self) -> list[User]:
        """
        Get all active users.

        Returns:
            List of active users.
        """
        return self.find_by(lambda u: u.is_active)

    def get_inactive(self) -> list[User]:
        """
        Get all inactive users.

        Returns:
            List of inactive users.
        """
        return self.find_by(lambda u: not u.is_active)

    def get_admins(self) -> list[User]:
        """
        Get all admin and owner users.

        Returns:
            List of admin/owner users.
        """
        return self.find_by(lambda u: u.is_admin)

    def search(self, query: str) -> list[User]:
        """
        Search users by username, email, or display name.

        Args:
            query: Text to search for.

        Returns:
            List of matching users.
        """
        query_lower = query.lower()
        return self.find_by(
            lambda u: (
                query_lower in u.username.lower()
                or query_lower in u.email.lower()
                or query_lower in u.display_name.lower()
            )
        )

    def email_exists(self, email: str) -> bool:
        """
        Check if an email is already registered.

        Args:
            email: The email to check.

        Returns:
            True if email exists.
        """
        return email.lower() in self._email_index

    def username_exists(self, username: str) -> bool:
        """
        Check if a username is already taken.

        Args:
            username: The username to check.

        Returns:
            True if username exists.
        """
        return username.lower() in self._username_index

    def count_by_role(self) -> dict[UserRole, int]:
        """
        Get count of users grouped by role.

        Returns:
            Dictionary mapping role to count.
        """
        counts = {role: 0 for role in UserRole}
        for user in self:
            counts[user.role] += 1
        return counts
