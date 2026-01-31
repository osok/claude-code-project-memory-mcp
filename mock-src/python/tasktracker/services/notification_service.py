"""Notification service for sending alerts and messages."""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Protocol, Callable
from uuid import UUID, uuid4

from .base import BaseService, log_call


class NotificationType(Enum):
    """Types of notifications."""

    TASK_ASSIGNED = "task_assigned"
    TASK_COMPLETED = "task_completed"
    TASK_OVERDUE = "task_overdue"
    PROJECT_INVITE = "project_invite"
    MENTION = "mention"
    SYSTEM = "system"


class NotificationChannel(Enum):
    """Channels for delivering notifications."""

    EMAIL = "email"
    IN_APP = "in_app"
    PUSH = "push"
    SLACK = "slack"


@dataclass
class Notification:
    """
    A notification to be sent to a user.

    Attributes:
        id: Unique identifier.
        user_id: Recipient user ID.
        type: Type of notification.
        title: Notification title.
        message: Notification body.
        channels: Channels to deliver through.
        created_at: When the notification was created.
        read_at: When the notification was read.
        data: Additional metadata.
    """

    user_id: UUID
    type: NotificationType
    title: str
    message: str
    id: UUID = field(default_factory=uuid4)
    channels: list[NotificationChannel] = field(
        default_factory=lambda: [NotificationChannel.IN_APP]
    )
    created_at: datetime = field(default_factory=datetime.utcnow)
    read_at: Optional[datetime] = None
    data: dict = field(default_factory=dict)

    @property
    def is_read(self) -> bool:
        """Check if notification has been read."""
        return self.read_at is not None

    def mark_read(self) -> None:
        """Mark notification as read."""
        if not self.read_at:
            self.read_at = datetime.utcnow()


class NotificationSender(Protocol):
    """Protocol for notification senders."""

    def send(
        self,
        notification: Notification,
        channel: NotificationChannel,
    ) -> bool:
        """Send a notification through a specific channel."""
        ...


class EmailSender:
    """Sends notifications via email."""

    def send(
        self,
        notification: Notification,
        channel: NotificationChannel,
    ) -> bool:
        """
        Send notification via email.

        Args:
            notification: The notification to send.
            channel: The channel (should be EMAIL).

        Returns:
            True if sent successfully.
        """
        if channel != NotificationChannel.EMAIL:
            return False
        # Simulate email sending
        return True


class InAppSender:
    """Stores notifications for in-app display."""

    def __init__(self) -> None:
        """Initialize the in-app sender."""
        self._notifications: dict[UUID, list[Notification]] = {}

    def send(
        self,
        notification: Notification,
        channel: NotificationChannel,
    ) -> bool:
        """
        Store notification for in-app display.

        Args:
            notification: The notification to store.
            channel: The channel (should be IN_APP).

        Returns:
            True if stored successfully.
        """
        if channel != NotificationChannel.IN_APP:
            return False

        if notification.user_id not in self._notifications:
            self._notifications[notification.user_id] = []
        self._notifications[notification.user_id].append(notification)
        return True

    def get_user_notifications(
        self,
        user_id: UUID,
        unread_only: bool = False,
    ) -> list[Notification]:
        """Get notifications for a user."""
        notifications = self._notifications.get(user_id, [])
        if unread_only:
            return [n for n in notifications if not n.is_read]
        return notifications


class NotificationService(BaseService):
    """
    Service for managing and sending notifications.

    Supports multiple channels and async delivery.

    Attributes:
        _senders: Map of channels to sender implementations.
        _queue: Pending notifications to be sent.
        _hooks: Event hooks for notification events.
    """

    def __init__(self) -> None:
        """Initialize the notification service."""
        super().__init__()
        self._senders: dict[NotificationChannel, NotificationSender] = {}
        self._queue: list[Notification] = []
        self._hooks: dict[NotificationType, list[Callable]] = {}
        self._in_app_sender = InAppSender()

        # Register default senders
        self.register_sender(NotificationChannel.EMAIL, EmailSender())
        self.register_sender(NotificationChannel.IN_APP, self._in_app_sender)

    def register_sender(
        self,
        channel: NotificationChannel,
        sender: NotificationSender,
    ) -> None:
        """
        Register a sender for a channel.

        Args:
            channel: The channel to register for.
            sender: The sender implementation.
        """
        self._senders[channel] = sender

    def register_hook(
        self,
        notification_type: NotificationType,
        callback: Callable[[Notification], None],
    ) -> None:
        """
        Register a hook for notification events.

        Args:
            notification_type: Type to hook into.
            callback: Function to call when notification is sent.
        """
        if notification_type not in self._hooks:
            self._hooks[notification_type] = []
        self._hooks[notification_type].append(callback)

    @log_call
    def send(self, notification: Notification) -> dict[NotificationChannel, bool]:
        """
        Send a notification through all specified channels.

        Args:
            notification: The notification to send.

        Returns:
            Map of channel to success status.
        """
        results = {}

        for channel in notification.channels:
            sender = self._senders.get(channel)
            if sender:
                results[channel] = sender.send(notification, channel)
            else:
                results[channel] = False
                self._log_error("No sender registered for channel: %s", channel)

        # Trigger hooks
        for callback in self._hooks.get(notification.type, []):
            try:
                callback(notification)
            except Exception as e:
                self._log_error("Hook failed: %s", str(e))

        return results

    @log_call
    def notify_task_assigned(
        self,
        user_id: UUID,
        task_id: UUID,
        task_title: str,
        assigner_name: str,
    ) -> Notification:
        """
        Send a task assignment notification.

        Args:
            user_id: Recipient user ID.
            task_id: The assigned task's ID.
            task_title: The task's title.
            assigner_name: Name of who assigned the task.

        Returns:
            The sent notification.
        """
        notification = Notification(
            user_id=user_id,
            type=NotificationType.TASK_ASSIGNED,
            title="New Task Assigned",
            message=f"{assigner_name} assigned you to: {task_title}",
            channels=[NotificationChannel.IN_APP, NotificationChannel.EMAIL],
            data={"task_id": str(task_id)},
        )

        self.send(notification)
        return notification

    @log_call
    def notify_task_completed(
        self,
        user_id: UUID,
        task_id: UUID,
        task_title: str,
        completer_name: str,
    ) -> Notification:
        """
        Send a task completion notification.

        Args:
            user_id: Recipient user ID.
            task_id: The completed task's ID.
            task_title: The task's title.
            completer_name: Name of who completed the task.

        Returns:
            The sent notification.
        """
        notification = Notification(
            user_id=user_id,
            type=NotificationType.TASK_COMPLETED,
            title="Task Completed",
            message=f"{completer_name} completed: {task_title}",
            data={"task_id": str(task_id)},
        )

        self.send(notification)
        return notification

    @log_call
    def notify_overdue_tasks(
        self,
        user_id: UUID,
        task_count: int,
    ) -> Notification:
        """
        Send overdue tasks notification.

        Args:
            user_id: Recipient user ID.
            task_count: Number of overdue tasks.

        Returns:
            The sent notification.
        """
        notification = Notification(
            user_id=user_id,
            type=NotificationType.TASK_OVERDUE,
            title="Overdue Tasks",
            message=f"You have {task_count} overdue task(s)",
            channels=[NotificationChannel.IN_APP, NotificationChannel.EMAIL],
            data={"overdue_count": task_count},
        )

        self.send(notification)
        return notification

    async def send_async(
        self,
        notification: Notification,
    ) -> dict[NotificationChannel, bool]:
        """
        Send a notification asynchronously.

        Args:
            notification: The notification to send.

        Returns:
            Map of channel to success status.
        """
        await asyncio.sleep(0.01)  # Simulate async operation
        return self.send(notification)

    async def send_batch_async(
        self,
        notifications: list[Notification],
    ) -> list[dict[NotificationChannel, bool]]:
        """
        Send multiple notifications asynchronously.

        Args:
            notifications: List of notifications to send.

        Returns:
            List of result maps for each notification.
        """
        results = []
        for notification in notifications:
            result = await self.send_async(notification)
            results.append(result)
        return results

    def queue(self, notification: Notification) -> None:
        """
        Queue a notification for later delivery.

        Args:
            notification: The notification to queue.
        """
        self._queue.append(notification)

    async def flush_queue_async(self) -> int:
        """
        Send all queued notifications.

        Returns:
            Number of notifications sent.
        """
        count = len(self._queue)
        for notification in self._queue:
            await self.send_async(notification)
        self._queue.clear()
        return count

    def get_user_notifications(
        self,
        user_id: UUID,
        unread_only: bool = False,
    ) -> list[Notification]:
        """
        Get in-app notifications for a user.

        Args:
            user_id: The user's ID.
            unread_only: Only return unread notifications.

        Returns:
            List of notifications.
        """
        return self._in_app_sender.get_user_notifications(user_id, unread_only)

    def mark_read(self, notification_id: UUID, user_id: UUID) -> bool:
        """
        Mark a notification as read.

        Args:
            notification_id: The notification's ID.
            user_id: The user's ID.

        Returns:
            True if notification was found and marked.
        """
        notifications = self._in_app_sender.get_user_notifications(user_id)
        for notification in notifications:
            if notification.id == notification_id:
                notification.mark_read()
                return True
        return False

    @property
    def queue_size(self) -> int:
        """Get number of queued notifications."""
        return len(self._queue)
