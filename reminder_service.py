"""Field-service deadline reminders, with typed input and a runnable workflow."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from infrai_client import InfraiClient, namespace


@dataclass(frozen=True)
class WorkOrder:
    work_order_id: str
    deadline: datetime
    dispatch_status: str
    photo_urls: tuple[str, ...]
    technician_id: str


@dataclass(frozen=True)
class ReminderRequest:
    work_order_id: str
    technician_id: str
    deadline: str
    photo_count: int
    action: str


def reminder_for(order: WorkOrder, now: datetime) -> ReminderRequest | None:
    """Remind only dispatched work orders due within the next day."""
    remaining = order.deadline - now
    if order.dispatch_status != "dispatched" or remaining < timedelta(0) or remaining > timedelta(days=1):
        return None
    return ReminderRequest(
        work_order_id=order.work_order_id,
        technician_id=order.technician_id,
        deadline=order.deadline.isoformat(),
        photo_count=len(order.photo_urls),
        action="confirm completion and attach final photos",
    )


def publish_reminder(client: InfraiClient, queue: str, request: ReminderRequest) -> dict[str, Any]:
    """Publish a stable event identity so a retried publish represents one reminder."""
    payload = {"event_id": f"deadline-reminder:{request.work_order_id}:{request.deadline}", **request.__dict__}
    return client.queue_publish(queue, payload)


def configure(client: InfraiClient, task_url: str) -> str:
    """Create the queue pair and schedule the worker callback."""
    client.queue_create("field-service-reminders-dlq", "field-service-reminders-dlq", 3)
    client.queue_create("field-service-reminders", "field-service-reminders-dlq", 3)
    infrai = namespace(client)
    job = infrai.cron.create("0 * * * *", task_url)
    return str(job["job_id"])


def example_order() -> WorkOrder:
    return WorkOrder(
        work_order_id="WO-1042",
        deadline=datetime.now(timezone.utc) + timedelta(hours=6),
        dispatch_status="dispatched",
        photo_urls=("https://photos.example/WO-1042-before.jpg",),
        technician_id="tech-17",
    )


if __name__ == "__main__":
    client = InfraiClient()
    order = example_order()
    reminder = reminder_for(order, datetime.now(timezone.utc))
    if reminder:
        print(publish_reminder(client, "field-service-reminders", reminder))
