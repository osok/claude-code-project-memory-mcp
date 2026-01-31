"""Base repository classes with common CRUD operations."""

from abc import ABC, abstractmethod
from typing import Generic, Optional, TypeVar, Callable
from uuid import UUID

T = TypeVar("T")


class BaseRepository(ABC, Generic[T]):
    """
    Abstract base repository defining the interface for data access.

    All concrete repositories must implement these methods to provide
    consistent CRUD operations across different storage backends.

    Type Parameters:
        T: The entity type this repository manages.
    """

    @abstractmethod
    def get(self, id: UUID) -> Optional[T]:
        """
        Get an entity by its ID.

        Args:
            id: The unique identifier of the entity.

        Returns:
            The entity if found, None otherwise.
        """
        pass

    @abstractmethod
    def get_all(self) -> list[T]:
        """
        Get all entities.

        Returns:
            List of all entities.
        """
        pass

    @abstractmethod
    def create(self, entity: T) -> T:
        """
        Create a new entity.

        Args:
            entity: The entity to create.

        Returns:
            The created entity.
        """
        pass

    @abstractmethod
    def update(self, entity: T) -> Optional[T]:
        """
        Update an existing entity.

        Args:
            entity: The entity with updated values.

        Returns:
            The updated entity if found, None otherwise.
        """
        pass

    @abstractmethod
    def delete(self, id: UUID) -> bool:
        """
        Delete an entity by its ID.

        Args:
            id: The unique identifier of the entity to delete.

        Returns:
            True if deleted, False if not found.
        """
        pass

    @abstractmethod
    def exists(self, id: UUID) -> bool:
        """
        Check if an entity exists.

        Args:
            id: The unique identifier to check.

        Returns:
            True if exists, False otherwise.
        """
        pass

    @abstractmethod
    def count(self) -> int:
        """
        Get the total count of entities.

        Returns:
            The number of entities.
        """
        pass


class InMemoryRepository(BaseRepository[T]):
    """
    In-memory implementation of the base repository.

    Stores entities in a dictionary for fast access.
    Useful for testing and development.

    Attributes:
        _storage: Dictionary mapping IDs to entities.
        _id_getter: Function to extract ID from an entity.
    """

    def __init__(self, id_getter: Callable[[T], UUID]) -> None:
        """
        Initialize the repository.

        Args:
            id_getter: Function that extracts the ID from an entity.
        """
        self._storage: dict[UUID, T] = {}
        self._id_getter = id_getter

    def get(self, id: UUID) -> Optional[T]:
        """Get an entity by its ID."""
        return self._storage.get(id)

    def get_all(self) -> list[T]:
        """Get all entities."""
        return list(self._storage.values())

    def create(self, entity: T) -> T:
        """Create a new entity."""
        entity_id = self._id_getter(entity)
        if entity_id in self._storage:
            raise ValueError(f"Entity with ID {entity_id} already exists")
        self._storage[entity_id] = entity
        return entity

    def update(self, entity: T) -> Optional[T]:
        """Update an existing entity."""
        entity_id = self._id_getter(entity)
        if entity_id not in self._storage:
            return None
        self._storage[entity_id] = entity
        return entity

    def delete(self, id: UUID) -> bool:
        """Delete an entity by its ID."""
        if id in self._storage:
            del self._storage[id]
            return True
        return False

    def exists(self, id: UUID) -> bool:
        """Check if an entity exists."""
        return id in self._storage

    def count(self) -> int:
        """Get the total count of entities."""
        return len(self._storage)

    def find_by(self, predicate: Callable[[T], bool]) -> list[T]:
        """
        Find entities matching a predicate.

        Args:
            predicate: Function that returns True for matching entities.

        Returns:
            List of matching entities.
        """
        return [entity for entity in self._storage.values() if predicate(entity)]

    def find_one(self, predicate: Callable[[T], bool]) -> Optional[T]:
        """
        Find the first entity matching a predicate.

        Args:
            predicate: Function that returns True for matching entities.

        Returns:
            First matching entity or None.
        """
        for entity in self._storage.values():
            if predicate(entity):
                return entity
        return None

    def clear(self) -> None:
        """Remove all entities from the repository."""
        self._storage.clear()

    def bulk_create(self, entities: list[T]) -> list[T]:
        """
        Create multiple entities at once.

        Args:
            entities: List of entities to create.

        Returns:
            List of created entities.

        Raises:
            ValueError: If any entity already exists.
        """
        created = []
        for entity in entities:
            created.append(self.create(entity))
        return created

    def __len__(self) -> int:
        """Return the number of entities."""
        return self.count()

    def __contains__(self, id: UUID) -> bool:
        """Check if an entity exists using 'in' operator."""
        return self.exists(id)

    def __iter__(self):
        """Iterate over all entities."""
        return iter(self._storage.values())
