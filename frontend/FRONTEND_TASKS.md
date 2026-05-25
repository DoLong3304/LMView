# Frontend Task Progress

This file tracks frontend-only work completed from the bug-fix and improvement list.
Update it when a frontend task is completed.

## Completed

- 2026-05-24: Added light and dark theme support through shared CSS tokens, persisted the selected mode in local storage, and refreshed chart colors when the mode changes.
- 2026-05-24: Hid developer-facing UI indicators from the header, including the data source badge and system health card, behind a disabled developer-tools flag.
- 2026-05-24: Improved the app shell responsiveness by making the drawing toolbar and overview panel collapsible, defaulting secondary panels closed on compact screens, and keeping the chart area as the primary view.
- 2026-05-24: Repositioned Order Book and Recent Trades into the right Overview panel beside Watchlist, using horizontal tabs for all three views.
- 2026-05-24: Removed the old chart content tab strip so the chart remains the default view, with timeframe and chart-type controls handled from the header.
- 2026-05-24: Reworked the header around LMView branding, chart/markets navigation, theme/settings/user controls, and chart-only controls.
- 2026-05-24: Top-aligned the drawing toolbar to the chart canvas so chart controls above the canvas can use the full width.
- 2026-05-24: Improved Markets & News with 10-item pagination, list/grid view toggle, better scroll containment, and full-card external article links.
- 2026-05-24: Reworked symbol metadata to always expose symbol, name, and icon fields, with a bundled default icon when exchange or CoinGecko metadata is missing.
- 2026-05-24: Added frontend client caching for stable symbols, chart history, market overview, movers, news, and short-lived live market snapshots.
- 2026-05-24: Expanded mock ticker coverage so mock-mode watchlist, order book, trades, and chart candles line up with the bundled mock data generator.
- 2026-05-24: Built and launched a frontend-only Vite preview from a mock-mode production bundle.
- 2026-05-24: Wired the chart type selector to candlestick, bar, line, and area renderers while keeping all chart modes synchronized for replay and drawing coordinates.
- 2026-05-24: Improved chart autoscale reset so it restores the intended initial candle window and price scaling instead of dumping the full loaded history into view.
- 2026-05-24: Rebuilt chart export to include chart canvases, visible price/time axes, latest OHLCV metadata, selected chart type, and SVG user drawings.
- 2026-05-24: Fixed drawing selection and delete-selected by letting cursor mode hit-test drawings and by recording toolbar deletes in the drawing command history.
- 2026-05-24: Filled in visible rendering and hit-testing for text, rectangle, circle, triangle, ruler, horizontal line, and trendline drawing tools using data-space anchors.
- 2026-05-24: Fixed replay mode startup so it begins from the selected candle, hides future candles, blocks live refresh races, and uses correct playback speed values.
- 2026-05-24: Rebuilt and relaunched the frontend-only mock preview after the chart, export, drawing, and replay fixes.
- 2026-05-25: Fixed chart time navigation while drawing/replay overlays are active by forwarding wheel zoom/scroll and adding overlay-level pan handling for captured pointer states.

## Pending

- None for the scoped frontend tasks completed in this pass.
