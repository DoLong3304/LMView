# Frontend — React 19 SPA

React 19 + TypeScript + Vite + TailwindCSS + lightweight-charts trading dashboard.

## Tech Stack

- **React 19** with functional components + hooks
- **TypeScript** strict mode
- **Vite** for build/dev server
- **TailwindCSS** for styling
- **lightweight-charts** for candlestick charts
- **react-router-dom** for routing
- **i18next** for internationalization (en/vi)
- **shadcn/ui** components (Lucide icons)

## Directory Structure

```
frontend/src/
├── App.tsx                    Root: routing, providers, global state
├── main.tsx                   Entry point
├── @types/                    Global TS declarations
├── types/index.ts             Shared types (Symbol, Ticker, Candle, etc.)
├── constants/                 Env, timeframe, market constants
│   ├── env.ts
│   ├── timeframes.ts
│   └── markets.ts
├── services/                  API client functions
│   ├── apiClient.ts           Base HTTP client (fetch wrapper)
│   ├── marketDataService.ts   Klines, tickers, trades
│   ├── authService.ts         Login, register, session
│   ├── aiService.ts           AI chat, actions, sessions
│   ├── settingsService.ts     User preferences
│   ├── symbolService.ts       Symbol metadata
│   └── newsService.ts         News articles
├── hooks/                     Custom React hooks
│   ├── useApiCall.ts          Fetch with retry/toast/error states
│   ├── useSymbolMeta.ts       Symbol logo/name lookup
│   └── useI18n.ts             i18n hook wrapper
├── features/                  Feature modules
│   ├── chart/
│   │   ├── CandlestickChart.tsx   Main chart component
│   │   ├── indicators/            Indicator overlays
│   │   └── transforms/           Heikin Ashi, Renko, etc.
│   ├── ai/
│   │   ├── AiAssistantPanel.tsx   AI chat panel
│   │   └── components/            AI UI components
│   ├── auth/
│   │   ├── AuthModal.tsx          Login/Register modal
│   │   └── AuthContext.tsx        Auth state context
│   ├── drawing/                   Drawing tools (trendline, fib, etc.)
│   ├── market/                    Market overview components
│   ├── watchlist/                 Symbol watchlist
│   ├── settings/                  Settings modal
│   ├── replay/                    Historical replay
│   └── admin/                     Admin panel
├── components/                Shared components
│   ├── layout/                    Shell (header, sidebar, footer)
│   └── ui/                        shadcn/ui components
├── pages/                     Route-level screens
│   ├── Dashboard.tsx
│   ├── MarketOverview.tsx
│   └── ...
└── data/                      Static/mock data and adapters
    └── mock/                      API-shaped mock adapters
```

## Key Components

### CandlestickChart.tsx
- Core chart using lightweight-charts
- Multiple timeframes (1s, 1m, 5m, 15m, 1h, 4h, 1d, 1w)
- Chart types: Candlestick, Heikin Ashi, Renko, Line Break, Kagi
- Drawing tools: trendline, horizontal ray, vertical line, fibonacci, rectangle, circle, arrow, text
- Indicators: SMA, EMA, RSI, MACD, Bollinger, Stoch, ATR, Volume, OBV, VWAP
- Multi-chart layout system (standalone, ready for integration)

### AiAssistantPanel.tsx
- AI chat interface
- Ask mode: market questions, analysis
- Interact mode (scaffolded): chart actions
- Markdown rendering
- Session management

### AuthModal.tsx
- Login/Register tabs
- Form validation
- Session management
- Vietnamese i18n support

### SettingsModal.tsx
- User preferences
- Customization (timeframe, chart type, theme)
- AI Helper settings
- Account management

## Data Flow

```
Component → Service (useApiCall) → apiClient.ts → FastAPI REST → State update
Component ← WebSocket ← /api/stream/all ← Redis poll (50ms)
```

- `VITE_DATA_SOURCE=mock` → uses `src/data/mock/` adapters
- Default: API mode (connects to FastAPI)
- Backend ms → lightweight-charts seconds at service boundary

## Known Issues

- No frontend test script (hook specs exist but untested)
- Old single-candle frontend helper stale (backend uses all-timeframe WebSocket)
- Vite dev server proxies `/api` and `/ws` to FastAPI
- i18n implemented with `useI18n()` hook, 2 locales (en/vi)
