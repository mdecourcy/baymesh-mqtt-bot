# Dashboard Features

## Overview
Enhanced Meshtastic MQTT Bot dashboard with comprehensive statistics and real-time network monitoring.

## New Components

### 1. **Network Health** (`NetworkHealth.tsx`)
- Real-time health score (0-100) based on recent activity
- Shows last 10 minutes of activity
- Displays:
  - Total messages in window
  - Active nodes
  - Average gateway count
  - Total messages today
- Color-coded health status (Excellent/Good/Fair/Poor)

### 2. **Top Senders** (`TopSenders.tsx`)
- Leaderboard of most active mesh nodes
- Shows top 10 senders by message count
- Displays:
  - Sender name and Meshtastic ID
  - Total message count
  - Average gateway count
  - Maximum gateway count achieved

### 3. **Gateway Distribution** (`GatewayDistribution.tsx`)
- Histogram showing distribution of gateway counts
- Buckets: 0-5, 6-10, 11-20, 21-40, 41-60, 60+
- Percentage and count for each bucket
- Visual bar chart with gradient colors

### 4. **Active Gateways** (`ActiveGateways.tsx`)
- Network coverage overview
- Shows peak gateway count
- Displays average coverage across all messages
- Network density explanation

### 5. **Enhanced Recent Messages** (`RecentMessages.tsx`)
- Improved color-coded gateway counts:
  - 50+ gateways: Emerald (excellent)
  - 20-49: Green (very good)
  - 10-19: Yellow (good)
  - 5-9: Orange (fair)
  - <5: Red (poor)
- Added SNR column
- Better formatting with mesh IDs
- Empty state message

### 6. **Enhanced Stats Overview** (`StatsOverview.tsx`)
- Shows sender mesh IDs in last message card
- Better formatting for gateway counts
- Improved readability

### 7. **Enhanced Message Chart** (`MessageChart.tsx`)
- Renamed to "Gateway Coverage Trend"
- Better color scheme:
  - Average: Blue (solid line)
  - Peak: Green (dashed)
  - Minimum: Orange (dotted)
- Improved tooltip styling
- Y-axis label
- Empty state handling

## Layout

The dashboard is organized into sections:

1. **Top Row**: 4 stat cards (Last Message, Today's Average, Peak, Total Messages)
2. **Second Row**: Network Health (1/4) + Gateway Coverage Trend Chart (3/4)
3. **Third Row**: Recent Messages (2/3) + Top Senders + Gateway Distribution (1/3)
4. **Bottom Row**: Hourly Breakdown + Message Distribution + Active Gateways

## Data Flow

- Fetches 100 recent messages (increased from 20 for better stats)
- Real-time updates via polling
- Memoized calculations for performance
- Responsive grid layout

## Color Scheme

The dashboard uses a modern, accessible color palette:
- Primary: Blue (#3B82F6)
- Success: Emerald (#10B981)
- Warning: Yellow (#F59E0B)
- Danger: Red (#EF4444)
- Info: Slate (#64748b)

All colors have dark mode variants for optimal readability.

## Technical Details

- Built with React + TypeScript
- Recharts for data visualization
- Tailwind CSS for styling
- Responsive design (mobile, tablet, desktop)
- No TypeScript errors
- Production-ready build

## Gateway Count Accuracy

The dashboard now displays accurate gateway counts thanks to:
1. Packet queueing mechanism (10-second window)
2. Deduplication of MQTT replays
3. Proper tracking of unique gateways per message
4. Text message filtering (only TEXT_MESSAGE_APP packets)

## Usage

```bash
cd dashboard
npm install
npm run dev    # Development server
npm run build  # Production build
```

The dashboard connects to the FastAPI backend at `http://localhost:8008` by default.


