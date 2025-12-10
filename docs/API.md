# API Reference

All endpoints are prefixed relative to `API_HOST:API_PORT` (default `http://localhost:8000`).

## Statistics

### `GET /stats/last`
Returns the most recent message stats.
```json
{
  "id": 42,
  "message_id": "msg-042",
  "sender_name": "Node123",
  "gateway_count": 5,
  "timestamp": "2025-01-01T12:00:00Z"
}
```

### `GET /stats/last/{count}`
Returns the latest `count` messages (1–100).

### `GET /stats/today`
Aggregated stats for the current UTC day.

### `GET /stats/today/detailed`
Hourly breakdown for today.

### `GET /stats/{date}`
Stats for a specific date (`YYYY-MM-DD`).

### `GET /stats/user/{user_id}/last`
Most recent message for a user.

### `GET /stats/user/{user_id}/last/{count}`
Latest `count` messages for a user.

## Subscriptions

### `POST /subscribe/{user_id}/{subscription_type}`
Subscribe a user to `daily_low`, `daily_avg`, or `daily_high`.

### `DELETE /subscribe/{user_id}`
Unsubscribe user from all notifications.

### `GET /subscriptions[?subscription_type=...]`
List active subscriptions, optionally filtered by type.

## Mock/Test Utilities

### `POST /mock/user`
Create/update a user.
```json
{
  "user_id": 101,
  "username": "Test User",
  "mesh_id": "mesh101"
}
```

### `POST /mock/message`
Create a message entry.
```json
{
  "sender_id": 101,
  "sender_name": "Test User",
  "gateway_count": 4,
  "rssi": -95,
  "snr": 6.2,
  "payload": "Hello",
  "timestamp": "2025-01-01T12:00:00Z"
}
```

## Health

### `GET /health`
Returns overall status and dependency state.

## Error Codes
| Status | Meaning |
|--------|---------|
| 200 | Success |
| 201 | Created |
| 400 | Bad request (validation error) |
| 404 | Resource not found |
| 500 | Internal server error |

All error responses follow:
```json
{
  "error": "error_code",
  "detail": "Human-readable message",
  "status_code": 400
}
```




