from datetime import datetime, timedelta, timezone

from reminder_service import WorkOrder, reminder_for


def test_dispatched_order_due_tomorrow_gets_a_photo_follow_up():
    now = datetime(2026, 1, 10, 8, tzinfo=timezone.utc)
    order = WorkOrder(
        work_order_id="WO-7",
        deadline=now + timedelta(hours=8),
        dispatch_status="dispatched",
        photo_urls=("before.jpg", "meter.jpg"),
        technician_id="tech-2",
    )

    reminder = reminder_for(order, now)

    assert reminder is not None
    assert reminder.photo_count == 2
    assert reminder.action == "confirm completion and attach final photos"


def test_undispatched_order_is_not_published():
    now = datetime(2026, 1, 10, 8, tzinfo=timezone.utc)
    order = WorkOrder("WO-8", now + timedelta(hours=8), "assigned", (), "tech-2")

    assert reminder_for(order, now) is None
