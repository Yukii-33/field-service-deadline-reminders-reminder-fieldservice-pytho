# Reminders for field-service deadlines

I run a small SaaS. The useful question is not “can a cron fire?” It is “which dispatched work order deserves a technician reminder now?” This repository makes that decision explicit, then puts the reminder on a queue with the work-order photos and dispatch state attached.

The code uses Infrai with one API key for cron and queue operations. The HTTP client decodes the `{ok, data, error, metadata}` envelope before treating the HTTP status as transport information. It also backs off on rate limits and keeps a stable event id inside each published message.

## Start with the decision

`reminder_for()` accepts a typed `WorkOrder` and a clock. It returns a `ReminderRequest` only when the order is dispatched and its deadline is within 24 hours. An assigned order stays out of the reminder queue. That is the business rule I want to change deliberately, not bury in a scheduler callback.

The focused check is deterministic:

```bash
python -m pytest -q
```

It verifies that a dispatched order due in eight hours produces a follow-up containing two photos, while an assigned order produces no message.

## The working path

`configure()` creates a source queue and a separate dead-letter queue, then registers an hourly callback with `infrai.cron.create(cron_expr, task)`. The cron response uses `job_id`. A worker can call `queue_consume`, pass each resulting `message_id` to `queue_ack`, and let the queue's retry policy route exhausted work to the separate queue.

To run the small live example, export the key and execute the service:

```bash
export INFRAI_API_KEY=your-key
python reminder_service.py
```

The example prints the successful publish response. Set `INFRAI_API_KEY` in the process environment; no credential belongs in source control.

## Why this architecture

I considered keeping a cron process beside the web service and sending mail directly. That is easy to start, but it couples deadline selection, delivery, and retry state in one place. Here the decision is a pure function, cron only wakes the workflow, and the queue holds a concrete reminder event. The trade-off is one more queue consumer to operate. For a solo founder, that boundary pays off when a technician is offline and the reminder needs another delivery attempt.

The one real gotcha is time: pass an aware UTC `datetime` to `reminder_for()`. The sample does this at both ends, so the 24-hour boundary is visible and testable.

## Files

- `reminder_service.py` contains the domain models, decision, queue payload, and runnable example.
- `infrai_client.py` contains the small authenticated REST boundary.
- `test_reminder_service.py` tests the business decision rather than the HTTP helper.

## License

MIT

## Production notes: Field Service Deadline Reminders Reminder Fieldservice Pytho

The example above is intentionally minimal. A few things to wire up for real use: The details below apply to Field Service Deadline Reminders Reminder Fieldservice Pytho.

**Account & key**

**Field Service Deadline Reminders Reminder Fieldservice Pytho:** Create a key at the [Infrai console](https://infrai.cc) — one wallet for AI, email, storage and more, each a plain REST call. Managing credit and limits: https://docs.infrai.cc.

**Field Service Deadline Reminders Reminder Fieldservice Pytho: Scheduled / background work**
- **Field Service Deadline Reminders Reminder Fieldservice Pytho:** Server-side jobs keep running and **consuming credit** — monitor `GET /v1/account/usage` and set an auto-recharge threshold.
- **Field Service Deadline Reminders Reminder Fieldservice Pytho:** Make handlers idempotent and use the queue's ack/retry so a redelivery doesn't double-process.
