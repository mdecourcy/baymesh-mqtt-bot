# Daily Broadcast Feature

## Overview

The bot can automatically send daily statistics summaries to a specified Meshtastic channel at a scheduled time (default: 9 PM / 21:00 UTC).

## Configuration

Add these environment variables to your `.env` file:

```bash
# Enable daily broadcast
DAILY_BROADCAST_ENABLED=true

# Time to send broadcast (24-hour format, UTC)
DAILY_BROADCAST_HOUR=21        # 9 PM UTC (default)
DAILY_BROADCAST_MINUTE=0       # Top of the hour (default)

# Channel to send to (0-7)
DAILY_BROADCAST_CHANNEL=0      # Primary channel (default)
```

## Channel Selection

Meshtastic devices support up to 8 channels (0-7):
- **Channel 0**: Primary channel (default, usually "LongFast")
- **Channel 1-7**: Secondary channels

To broadcast to a different channel, set `DAILY_BROADCAST_CHANNEL` to the desired channel index.

## Message Format

The daily broadcast message includes:
```
📊 Daily Stats
Messages: 4,050
Avg GW: 14.2
Peak GW: 79
Min GW: 1
🌐 meshtastic-stats.local
```

## Example Configuration

### Send to Primary Channel at 9 PM
```bash
DAILY_BROADCAST_ENABLED=true
DAILY_BROADCAST_HOUR=21
DAILY_BROADCAST_MINUTE=0
DAILY_BROADCAST_CHANNEL=0
```

### Send to Secondary Channel at Noon
```bash
DAILY_BROADCAST_ENABLED=true
DAILY_BROADCAST_HOUR=12
DAILY_BROADCAST_MINUTE=0
DAILY_BROADCAST_CHANNEL=1
```

### Send at 6 AM to "MediumSlow" Channel
If your MediumSlow channel is configured as channel index 2:
```bash
DAILY_BROADCAST_ENABLED=true
DAILY_BROADCAST_HOUR=6
DAILY_BROADCAST_MINUTE=0
DAILY_BROADCAST_CHANNEL=2
```

## Time Zone Considerations

All times are in **UTC**. To convert from your local time zone:

- **Pacific Time (PST/PDT)**: Add 8 hours (7 during DST)
  - 9 PM PST = 5 AM UTC next day
- **Eastern Time (EST/EDT)**: Add 5 hours (4 during DST)
  - 9 PM EST = 2 AM UTC next day
- **Central European Time (CET/CEST)**: Subtract 1 hour (2 during DST)
  - 9 PM CET = 8 PM UTC

Example for 9 PM Pacific Time:
```bash
DAILY_BROADCAST_HOUR=5   # 9 PM PST = 5 AM UTC next day
```

## Disabling the Feature

To disable daily broadcasts:
```bash
DAILY_BROADCAST_ENABLED=false
```

Or simply remove/comment out the `DAILY_BROADCAST_ENABLED` variable.

## Testing

### Test the Broadcast Manually

You can trigger a test broadcast using the scheduler's method directly (useful for testing):

```python
# In Python shell or script
from src.config import get_settings
from src.tasks.scheduler import SchedulerManager
from src.services.meshtastic_service import MeshtasticService
from src.services.stats_service import StatsService
# ... initialize services ...

scheduler = SchedulerManager(...)
scheduler.send_daily_broadcast()
```

### Verify Configuration

Check your logs for confirmation:
```bash
tail -f logs/meshtastic_stats.log | grep -i broadcast
```

You should see:
```
INFO | SchedulerManager | Daily broadcast job set for 21:00 UTC to channel 0
```

## Troubleshooting

### Broadcast Not Sending

1. **Check if enabled**: Verify `DAILY_BROADCAST_ENABLED=true` in your `.env` file
2. **Check logs**: Look for errors in `logs/meshtastic_stats.log`
3. **Verify channel**: Ensure the channel index exists on your device (0-7)
4. **Check Meshtastic CLI**: Verify the CLI is working:
   ```bash
   meshtastic --info
   ```

### Message Not Appearing on Mesh

1. **Verify channel configuration**: Ensure the channel index matches your device's setup
2. **Check device connection**: Ensure your Meshtastic device is connected
3. **Review logs**: Check for "Daily broadcast sent successfully" message

### Wrong Time

Remember: All times are **UTC**. Convert from your local time zone.

## Advanced Usage

### Custom Message Format

To customize the broadcast message format, edit `src/tasks/scheduler.py`:

```python
def _format_broadcast_message(self, stats: dict) -> str:
    """Format daily stats into a broadcast message."""
    # Customize this method to change the message format
    return f"Your custom message format"
```

### Multiple Daily Broadcasts

To send broadcasts at multiple times per day, you can add additional cron jobs in `scheduler.py`:

```python
# In start() method
broadcast_trigger_morning = CronTrigger(hour=9, minute=0)
self._scheduler.add_job(
    self.send_daily_broadcast, 
    broadcast_trigger_morning, 
    name="morning_broadcast"
)

broadcast_trigger_evening = CronTrigger(hour=21, minute=0)
self._scheduler.add_job(
    self.send_daily_broadcast, 
    broadcast_trigger_evening, 
    name="evening_broadcast"
)
```

## Statistics Included

The broadcast includes:
- **Message Count**: Total messages processed today
- **Average Gateways**: Average number of gateways that received each message
- **Peak Gateways**: Highest gateway count for any single message
- **Minimum Gateways**: Lowest gateway count for any single message

## Notes

- The broadcast runs automatically every day at the configured time
- If stats computation fails, the broadcast is skipped and an error is logged
- The feature uses the same Meshtastic service as individual DM subscriptions
- Broadcasts are sent to **all nodes** on the specified channel (not DMs)



