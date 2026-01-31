"""User service for managing users."""

import asyncio
import hashlib
import secrets
from typing import Optional
from uuid import UUID

from ..models.user import User, UserRole
from ..repositories.user_repository import UserRepository
from ..utils.validators import validate_email, validate_username, validate_password
from .base import (
    BaseService,
    NotFoundError,
    ValidationError,
    AuthorizationError,
    log_call,
)


class UserService(BaseService):
    """
    Service for user management operations.

    Handles user creation, authentication, and authorization.

    Attributes:
        repository: The user repository for data access.
    """

    def __init__(self, repository: Optional[UserRepository] = None) -> None:
        """
        Initialize the user service.

        Args:
            repository: Optional repository instance.
        """
        super().__init__()
        self.repository = repository or UserRepository()
        self._password_hashes: dict[UUID, str] = {}
        self._session_tokens: dict[str, UUID] = {}

    @log_call
    def create_user(
        self,
        username: str,
        email: str,
        password: str,
        display_name: str = "",
        role: UserRole = UserRole.MEMBER,
    ) -> User:
        """
        Create a new user account.

        Args:
            username: Unique username for login.
            email: User's email address.
            password: Account password.
            display_name: Name to display in UI.
            role: User's access level.

        Returns:
            The created user.

        Raises:
            ValidationError: If any field is invalid.
        """
        # Validate inputs
        if not validate_username(username):
            raise ValidationError("username", "Invalid username format")

        if not validate_email(email):
            raise ValidationError("email", "Invalid email format")

        is_valid, errors = validate_password(password)
        if not is_valid:
            raise ValidationError("password", "; ".join(errors))

        # Check uniqueness
        if self.repository.email_exists(email):
            raise ValidationError("email", "Email already registered")

        if self.repository.username_exists(username):
            raise ValidationError("username", "Username already taken")

        # Create user
        user = User(
            username=username,
            email=email,
            display_name=display_name or username,
            role=role,
        )

        created = self.repository.create(user)

        # Store password hash
        self._password_hashes[created.id] = self._hash_password(password)

        self._log_info("Created user: %s", created.username)
        return created

    @log_call
    def get_user(self, user_id: UUID) -> User:
        """
        Get a user by ID.

        Args:
            user_id: The user's unique identifier.

        Returns:
            The user.

        Raises:
            NotFoundError: If user doesn't exist.
        """
        user = self.repository.get(user_id)
        if not user:
            raise NotFoundError("User", str(user_id))
        return user

    def get_user_by_email(self, email: str) -> User:
        """
        Get a user by email address.

        Args:
            email: The email to look up.

        Returns:
            The user.

        Raises:
            NotFoundError: If user doesn't exist.
        """
        user = self.repository.get_by_email(email)
        if not user:
            raise NotFoundError("User", email)
        return user

    def get_user_by_username(self, username: str) -> User:
        """
        Get a user by username.

        Args:
            username: The username to look up.

        Returns:
            The user.

        Raises:
            NotFoundError: If user doesn't exist.
        """
        user = self.repository.get_by_username(username)
        if not user:
            raise NotFoundError("User", username)
        return user

    @log_call
    def update_user(
        self,
        user_id: UUID,
        display_name: Optional[str] = None,
        email: Optional[str] = None,
    ) -> User:
        """
        Update a user's profile.

        Args:
            user_id: The user to update.
            display_name: New display name.
            email: New email address.

        Returns:
            The updated user.
        """
        user = self.get_user(user_id)

        if display_name is not None:
            user.display_name = display_name

        if email is not None:
            if not validate_email(email):
                raise ValidationError("email", "Invalid email format")
            # Note: In real impl, would update email index
            user.email = email

        self.repository.update(user)
        return user

    @log_call
    def deactivate_user(self, user_id: UUID, actor_id: UUID) -> User:
        """
        Deactivate a user account.

        Args:
            user_id: The user to deactivate.
            actor_id: The user performing the action.

        Returns:
            The deactivated user.

        Raises:
            AuthorizationError: If actor lacks permission.
        """
        actor = self.get_user(actor_id)
        if not actor.is_admin:
            raise AuthorizationError("deactivate", "user accounts")

        user = self.get_user(user_id)
        user.deactivate()
        self.repository.update(user)
        return user

    def authenticate(self, username: str, password: str) -> Optional[str]:
        """
        Authenticate a user and return a session token.

        Args:
            username: The username to authenticate.
            password: The password to verify.

        Returns:
            Session token if successful, None if failed.
        """
        try:
            user = self.get_user_by_username(username)
        except NotFoundError:
            return None

        if not user.is_active:
            return None

        stored_hash = self._password_hashes.get(user.id)
        if not stored_hash:
            return None

        if self._hash_password(password) != stored_hash:
            return None

        # Create session token
        token = self._generate_token()
        self._session_tokens[token] = user.id

        # Record login
        user.record_login()
        self.repository.update(user)

        return token

    async def authenticate_async(
        self,
        username: str,
        password: str,
    ) -> Optional[str]:
        """
        Authenticate a user asynchronously.

        Args:
            username: The username to authenticate.
            password: The password to verify.

        Returns:
            Session token if successful, None if failed.
        """
        await asyncio.sleep(0.01)  # Simulate async verification
        return self.authenticate(username, password)

    def validate_token(self, token: str) -> Optional[User]:
        """
        Validate a session token and return the user.

        Args:
            token: The session token to validate.

        Returns:
            The user if valid, None otherwise.
        """
        user_id = self._session_tokens.get(token)
        if not user_id:
            return None

        try:
            user = self.get_user(user_id)
            return user if user.is_active else None
        except NotFoundError:
            return None

    def logout(self, token: str) -> bool:
        """
        Invalidate a session token.

        Args:
            token: The token to invalidate.

        Returns:
            True if token was valid and invalidated.
        """
        if token in self._session_tokens:
            del self._session_tokens[token]
            return True
        return False

    def change_password(
        self,
        user_id: UUID,
        old_password: str,
        new_password: str,
    ) -> bool:
        """
        Change a user's password.

        Args:
            user_id: The user's ID.
            old_password: Current password for verification.
            new_password: New password to set.

        Returns:
            True if password was changed.

        Raises:
            ValidationError: If new password is invalid.
            AuthorizationError: If old password is wrong.
        """
        user = self.get_user(user_id)

        stored_hash = self._password_hashes.get(user.id)
        if self._hash_password(old_password) != stored_hash:
            raise AuthorizationError("change", "password")

        is_valid, errors = validate_password(new_password)
        if not is_valid:
            raise ValidationError("password", "; ".join(errors))

        self._password_hashes[user.id] = self._hash_password(new_password)
        return True

    def promote_user(
        self,
        user_id: UUID,
        new_role: UserRole,
        actor_id: UUID,
    ) -> User:
        """
        Promote a user to a higher role.

        Args:
            user_id: The user to promote.
            new_role: The new role to assign.
            actor_id: The user performing the promotion.

        Returns:
            The updated user.

        Raises:
            AuthorizationError: If actor lacks permission.
        """
        actor = self.get_user(actor_id)
        if not actor.is_admin:
            raise AuthorizationError("promote", "users")

        user = self.get_user(user_id)
        user.promote_to(new_role)
        self.repository.update(user)
        return user

    def get_admins(self) -> list[User]:
        """Get all admin users."""
        return self.repository.get_admins()

    def search_users(self, query: str) -> list[User]:
        """
        Search users by name, email, or username.

        Args:
            query: Search text.

        Returns:
            Matching users.
        """
        return self.repository.search(query)

    @staticmethod
    def _hash_password(password: str) -> str:
        """Hash a password using SHA-256."""
        return hashlib.sha256(password.encode()).hexdigest()

    @staticmethod
    def _generate_token() -> str:
        """Generate a secure session token."""
        return secrets.token_urlsafe(32)

    @property
    def active_user_count(self) -> int:
        """Get count of active users."""
        return len(self.repository.get_active())
