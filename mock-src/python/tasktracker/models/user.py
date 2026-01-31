"""User model with role-based access."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from ..utils.validators import validate_email, validate_username


class UserRole(Enum):
    """User roles for access control."""

    VIEWER = "viewer"
    MEMBER = "member"
    ADMIN = "admin"
    OWNER = "owner"


@dataclass
class User:
    """
    Represents a user in the system.

    Users can be assigned to tasks and projects. They have roles
    that determine their access level.

    Attributes:
        id: Unique identifier for the user.
        username: Unique username for login.
        email: User's email address.
        display_name: Name shown in the UI.
        role: User's access level.
        is_active: Whether the user account is active.
        created_at: When the user was created.
        last_login: When the user last logged in.
    """

    username: str
    email: str
    id: UUID = field(default_factory=uuid4)
    display_name: str = ""
    role: UserRole = UserRole.MEMBER
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None

    def __post_init__(self) -> None:
        """Validate user data after initialization."""
        if not validate_username(self.username):
            raise ValueError(f"Invalid username: {self.username}")
        if not validate_email(self.email):
            raise ValueError(f"Invalid email: {self.email}")
        if not self.display_name:
            self.display_name = self.username

    def has_permission(self, permission: str) -> bool:
        """
        Check if user has a specific permission.

        Args:
            permission: The permission to check.

        Returns:
            True if user has the permission.
        """
        permissions_map = {
            UserRole.VIEWER: {"read"},
            UserRole.MEMBER: {"read", "write", "comment"},
            UserRole.ADMIN: {"read", "write", "comment", "manage"},
            UserRole.OWNER: {"read", "write", "comment", "manage", "delete"},
        }
        return permission in permissions_map.get(self.role, set())

    def promote_to(self, new_role: UserRole) -> bool:
        """
        Promote user to a higher role.

        Args:
            new_role: The new role to assign.

        Returns:
            True if promotion was successful.
        """
        role_hierarchy = [UserRole.VIEWER, UserRole.MEMBER, UserRole.ADMIN, UserRole.OWNER]
        current_index = role_hierarchy.index(self.role)
        new_index = role_hierarchy.index(new_role)

        if new_index > current_index:
            self.role = new_role
            return True
        return False

    def deactivate(self) -> None:
        """Deactivate the user account."""
        self.is_active = False

    def record_login(self) -> None:
        """Record a login event."""
        self.last_login = datetime.utcnow()

    @property
    def is_admin(self) -> bool:
        """Check if user is an admin or owner."""
        return self.role in (UserRole.ADMIN, UserRole.OWNER)

    @staticmethod
    def create_guest(display_name: str = "Guest") -> "User":
        """
        Create a guest user with limited access.

        Args:
            display_name: Name to display for the guest.

        Returns:
            A new guest user instance.
        """
        return User(
            username=f"guest_{uuid4().hex[:8]}",
            email=f"guest_{uuid4().hex[:8]}@example.com",
            display_name=display_name,
            role=UserRole.VIEWER,
        )

    @classmethod
    def from_dict(cls, data: dict) -> "User":
        """
        Create a User from a dictionary.

        Args:
            data: Dictionary containing user data.

        Returns:
            A new User instance.
        """
        return cls(
            id=UUID(data["id"]) if "id" in data else uuid4(),
            username=data["username"],
            email=data["email"],
            display_name=data.get("display_name", ""),
            role=UserRole(data.get("role", "member")),
            is_active=data.get("is_active", True),
        )

    def to_dict(self) -> dict:
        """
        Convert user to a dictionary.

        Returns:
            Dictionary representation of the user.
        """
        return {
            "id": str(self.id),
            "username": self.username,
            "email": self.email,
            "display_name": self.display_name,
            "role": self.role.value,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
            "last_login": self.last_login.isoformat() if self.last_login else None,
        }
