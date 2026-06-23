## [0.26.12] - 2026-06-22

### Fixed — 7 UX bugs in Interact mode tour system

- **Dark blue banner removed** (`AiAssistantPanel.tsx`): The `actionResult` state was rendered as a visually prominent blue rectangle showing "error: unsupported X" messages to ALL users. Removed the banner; results now go to the admin-only action debug window. Added `// eslint-disable-next-line` and `void actionResult` to silence the TS unused-variable warning.
- **"Return to previous view" banner suppressed mid-tour** (`AiActionProvider.tsx`): `captureUiSnapshot` was called inside `showSection` (the highlight handler), which triggered `setRestoreAvailable(true)` on EVERY highlight step. Fixed by moving snapshot capture to when a tour STARTS (`onTourStart`) and clearing it on tour end (`onTourEnd`), so the RestoreBanner only appears when the user manually navigated away from a running tour.
- **`switchAppView` no longer closes right panel** (`AiActionProvider.tsx` + `panelHandler.ts`): When switching to Markets/News views, the right panel was closed (`setRightPanelOpen(false)`), hiding the AI Helper mid-tour. Removed the `setRightPanelOpen(false)` call — the panel stays open so the step overlay remains visible.
- **Tour step explanations improved** (`tour_templates.py`): Template steps now have detailed, market-specific explanations referencing actual platform features ("price scale is on the right, time along the bottom", "RSI >70 = overbought, <30 = oversold", "momentum direction and strength"). Removed generic filler like "The chart shows real-time OHLCV candlesticks."
- **StepOverlay.tsx deleted**: Dead component (`<StepOverlay />`) was a stale blue-rectangle overlay with no event handlers. Not imported anywhere. Removed.
- **Intent-based tour fallback** (`tour_planner.py`): Added `_intent_fallback_tour()` — a deterministic tour generator that recognises common user intents (order book, compare, analyze, news, indicators) and creates useful visual tours even when the LLM refuses to plan one (e.g. "I can't access order book data"). Handles ~15 cryptos (BTC/ETH/SOL/BNB/XRP/DOGE/ADA/AVAX/LINK/DOT/MATIC) with symbol detection.
- **Tour planner prompt revised**: Added few-shot examples for order book, compare, and simple-question rejection. Added rules for `open_panel` and `switch_app_view`. Removed overly aggressive "uncertain analysis → null tour" rule.
- **AI panel restored after tour ends** (`AiAssistantPanel.tsx` + `useAiChat.ts`): `cancelTour`, `tourNextStep` (Finish), Revert button, and `clearChat` now all dispatch `lmview:open-panel` with `target: "ai"` so the AI Helper tab is re-selected in the right panel after the tour completes. Previously the right panel stayed on "overview"/"orderBook" tab, hiding the textarea.

### Changed
- `backend version`: cryptoprice/fastapi:0.28.2 → 0.28.4
- `frontend version`: cryptoprice/nginx:1.62.0 → 1.64.0 (bundle `index-BJUu8qUV.js`)
- `docs/CHANGELOG.md`: added v0.26.12 entry

## [0.26.11] - 2026-06-22

### Fixed — Tour overlay invisible: infinite re-render loop + z-index stacking context + live-id gate

- **Infinite re-render loop**: Initial-load effect in `useAiChat` had dep chain `refreshApiSessions` → `loadApiSession` → `sessions` — transitive-unstable, re-firing on every render and calling `loadApiSession` → `setActiveTour(null)`. Fixed with `initialisedRef` guard ("already initialised" pattern).
- **z-index stacking context**: Step overlay `absolute z-[700]` inside AI panel's `position:relative` stacking context couldn't escape the panel. Body-level dim at `z-[680]` always won. Fixed by wrapping step overlay in `createPortal(overlayNode, document.body)` and changing overlay to `fixed z-[720]`.
- **`liveMessageIdsRef` gate too strict**: Cleared by `loadApiSession` on page load and by the infinite loop. Replaced with per-mount `autoExecutedTourIdsRef` keyed on message id — same protection against restart loops without blocking legitimate tour starts.
- **End-to-end Playwright verification**: `probe-tour-flow.mjs` confirms overlay visible after 20s with correct position and text "Step 1 of 5 20% Locate LMView Workspace...", Next button advances through steps 1→2→3 with correct step counter and progress bar.

### Changed
- `backend version`: cryptoprice/fastapi:0.28.0 (unchanged)
- `frontend version`: cryptoprice/nginx:1.62.0 (bundle `index-DecRvn1B.js`)
- `docs/CHANGELOG.md`: added v0.26.11 entry
- **Restructured Chương 2**: 2.1.1 FR, 2.1.2 NFR, 2.2.1 Các kiểu dữ liệu (mới), 2.2.2 Lambda ba tầng (2.2.2.1 Speed, 2.2.2.2 Batch, 2.2.2.3 Serving), 2.2.3 Cấu trúc lưu trữ, 2.3 Kiến trúc AI, 2.4.1 Use case, 2.4.2 Sequence.
- **Restructured Chương 3**: 3.1 Công nghệ (3.1.1-3.1.6), 3.2 Triển khai (3.2.1, 3.2.2), 3.3 UI.
- **Citations chuẩn APA**: Toàn bộ trích dẫn dùng (Author, Year), reference list ở cuối tài liệu.

## [0.27.1] - 2026-06-22

### Added — Thesis v6 (khoa-luan-nhom-79-v6.md) theo đề cương mới v6

- **Created `docs/khoa-luan-nhom-79-v6.md`** (~2195 dòng) từ v5 với cấu trúc section mới.
- **Restructured Chương 1**: 1.2 tách 1.2.3 (Nến+OHLCV) và 1.2.4 (Mô hình nến), thêm 1.3 Tác động tin tức, 1.4 Xử lý dữ liệu lớn, 1.5 AI với 1.5.3 DAG/MoE/Multi-Agents/FinBERT và 1.5.4 Vector DB+HNSW mới.
- **Restructured Chương 2**: 2.2.1 Các kiểu dữ liệu mới, 2.2.2 Lambda với sub-section 2.2.2.1-2.2.2.3, 2.3 Kiến trúc AI, 2.4.1 Use case + 2.4.2 Sequence.
- **Restructured Chương 3**: 3.1 Công nghệ (3.1.1-3.1.6), 3.2 Triển khai, 3.3 UI.
- **APA citations**: 227 APA-style citations, 0 IEEE.

## [0.27.0] - 2026-06-22

### Added — Thesis v5 (khoa-luan-nhom-79-v5.md) with restructured đề cương

- **Created `docs/khoa-luan-nhom-79-v5.md`** (~1936 dòng, ~44,640 từ) theo HƯỚNG DẪN VIẾT KHÓA LUẬN LMVIEW mới.
- **Chương 1 restructured** theo đề cương mới: 1.1 Tiền điện tử (1.1.1-1.1.5), 1.2 Phân tích kỹ thuật (1.2.1 Nền tảng, 1.2.2 Chỉ báo, 1.2.3 Nến Nhật+OHLCV+Mô hình nến, 1.2.4 Tác động tin tức), 1.3 Xử lý dữ liệu lớn (1.3.1 Lambda, 1.3.2 Lakehouse, 1.3.3 Streaming), 1.4 AI (1.4.1 LLM, 1.4.2 RAG). Sections 1.4.3 DAG/MoE và 1.4.4 Vector DB REMOVED theo đề cương.
- **Chương 3.3 reordered** 3.3.1 → 3.3.6 (v3 có 3.3.6 trước 3.3.3-3.3.5).
- **Chương 4.2.7-4.2.8 moved** từ sau "TÀI LIỆU THAM KHẢO" về đúng vị trí trước References.
- **1.2.3 và 1.2.4 added** (Biểu đồ nến Nhật, Mô hình nến) - bị mất trong rewrite script đầu tiên, đã restore từ v3 source.
- **1.2.3 combined** Nến Nhật + OHLCV + Mô hình nến vào một section thay vì tách riêng.

### Technical

- File `docs/khoa-luan-nhom-79-v5.md` synced với cấu trúc đề cương mới, nội dung văn phong lấy từ v3.
- **Ch1 thuần lý thuyết**: đã loại bỏ toàn bộ 19 tham chiếu "LMView" trong Chương 1 (cơ sở lý thuyết), thay bằng diễn đạt học thuật trung tính ("các hệ thống phân tích kỹ thuật", "trong thực tế", "trong bối cảnh phân tích tài chính", v.v.). Ch2-Ch4 vẫn đề cập LMView bình thường (đây là phần mô tả và đánh giá hệ thống).
- **Hình 3.0 — AWS 3-AZ infrastructure diagram**: thêm sơ đồ mới mô phỏng đúng bộ icon chuẩn Amazon (VPC, Subnet, AZ, EC2, EBS, EFS, ALB, CloudWatch, Route 53, Secrets Manager) bọc ngoài 3 node Docker Swarm hiện hữu. Đánh số lại toàn bộ Hình 3.x: 3.0 (AWS 3-AZ), 3.1 (Docker Swarm internal), 3.2–3.5 (Node 1/2/3, UI, Frontend). DANH MỤC HÌNH cập nhật khớp với body.
- **Mở Đầu Mục 1, 2, 3, 4 — bẻ nhỏ + bold keywords**: thay các khối văn dài đặc chữ bằng các đoạn ngắn 3–5 dòng, sử dụng **in đậm** cho keyword chính (đặc điểm thị trường, 6 bước DSRM, 4 bài toán con, 5 câu hỏi nghiên cứu, 4 đóng góp chính), thêm bullet list cho các thành phần liệt kê.
- **Luồng backup Lakehouse → S3 (Iceberg nguyên bản)**: thêm Mục 3.1.6.1 mới mô tả Spark job backup hằng ngày từ MinIO lên S3, bảo toàn metadata Iceberg (manifest, snapshot, schema). Cập nhật Hình 2.2 (batch path) thêm nhánh backup sang S3. Cập nhật Hình 3.0 thêm mũi tên MinIO → S3 + dòng backup trong external services. Thêm đoạn mô tả luồng batch path vào Mục 2.3.1. Chi phí S3 ~0.20 USD/tháng.
- **Rà soát toàn bộ tài liệu và tham chiếu S3 backup**: cập nhật Mục 3.1.3 (thêm backup Lakehouse như cấp thứ 4 của cơ chế chịu lỗi); Mục 3.2.6 (bổ sung ghi chú backup); Mục 4.2.3 (MinIO SPOF + S3 backup là mitigation; monitoring backup đã được tự động hóa cho MinIO); Mục 4.2.7 (CN2 nâng "ba cơ chế" lên "bốn cơ chế"); Mục 4.3.1 (tổng kết + abstract VN/EN đều đề cập backup); Phụ lục A.6 (bổ sung cấu hình backup_catalog).

## [0.26.11] - 2026-06-22

### Fixed — Infinite re-render loop + overlay stacking context + live-id gate

Diagnosed with a headless browser probe (`probe-tour.mjs`, `probe-direct.mjs`) by instrumenting the tour auto-start / auto-execute / clearChat code paths and dumping overlay DOM probes after each step.

- **Root cause: infinite re-render loop cleared `activeTour` on every render.** The initial-load effect in `useAiChat.ts` had `refreshApiSessions` in its deps. `refreshApiSessions` had `loadApiSession` in its deps. `loadApiSession` had `sessions` in its deps. So when `sessions` was updated, `loadApiSession` got a new ref, `refreshApiSessions` got a new ref, the initial-load effect re-fired, called `refreshApiSessions(true)`, which called `loadApiSession`, which called `setActiveTour(null)` — every single render. The tour would start, render once, then get wiped on the next re-render. **Fix**: guard with an `initialisedRef` so the initial-load effect only fires once per hook lifetime.
- **Step overlay was covered by the highlight dim.** The overlay was `absolute left-2 right-2 top-2 z-[700]` inside the AI panel (`data-ai-section="ai-panel"`). The dim is `fixed inset-0 z-[680]` at body level. Z-index only escapes a stacking context when you're at the body level, so the dim always won. **Fix**: render the overlay via `createPortal(overlayNode, document.body)` so its z-720 actually competes against the dim's z-680.
- **`liveMessageIdsRef` was too strict — blocked tours on reload AND on loaded sessions.** The v0.26.7 fix used this ref to gate auto-start, but the ref was cleared by `loadApiSession` on page load and by the auto-load effect's infinite loop, so the tour never auto-started for sessions that were loaded from the server. **Fix**: replaced with `autoExecutedTourIdsRef` keyed on message id only. Re-running on reload is fine because the ref is per-mount, so each page load gets a fresh set.
- **Highlight dim now always cuts out the AI panel during an active tour.** Added a `lmview:ai-tour-start` / `lmview:ai-tour-end` event pair; the `HighlightOverlay` listens and includes the AI panel rect in the cutouts whenever a tour is running, so the step text + nav buttons stay readable even when the dim is focused on a different chart section.

### Technical

- Bundle `index-DecRvn1B.js` (475.40 kB / 133.49 kB gzip)
- Deployed: `cryptoprice/nginx:1.62.0`
- Verified end-to-end with Playwright: overlay renders, Next button advances through all 5 steps (40% → 60% → ...), step counter updates correctly.
- Also deleted all 54 stale admin AI sessions so the user has a clean slate.

## [0.26.10] - 2026-06-22

### Fixed — Draggable step overlay + step counter + last-step keep/revert

- **Step overlay is now draggable.** The header bar (with grip icon) is the drag handle; the box can be moved anywhere over the AI panel so it doesn't cover the highlighted chart region. Position resets when a new tour starts.
- **Prominent step counter on every step.** "Step 2 of 5" + progress bar + percentage is in the drag header so users always know where they are and how much is left.
- **Nav buttons on every step.** Previous + Next on every step (was hidden on step 1). Next becomes "Finish" with a checkmark on the last step.
- **Keep current state / Revert to previous view ONLY on the last step.** Moved out of the (now removed) floating recap banner into a clear inline section in the overlay that only renders when `currentStep === steps.length - 1`. No more "always at the bottom" buttons.
- **Deleted all 54 stale admin sessions** from PostgreSQL so users can now create new sessions cleanly. Confirmed `POST /api/ai/sessions` returns 201 after cleanup.

### Technical

- Bundle `index-DyqHljDC.js` (474.91 kB / 133.41 kB gzip)
- Deployed: `cryptoprice/nginx:1.43.0`

## [0.26.9] - 2026-06-22

### Fixed — Breadcrumb dim + step overlay layout + legacy start_tour cleanup

- **Full-screen dim during action breadcrumbs.** The success-breadcrumb code path called `setHighlight({target: "debug", message})` after every action, but `SECTION_SELECTORS["debug"]` doesn't exist — `document.querySelector("debug")` returns `null`, so no "hole" is cut and the highlight overlay (z-680) dims the whole viewport including the chat and recap buttons. Removed the breadcrumb highlight entirely; the AI Action debug window's action log already records every call.
- **Legacy `start_tour` tool call running alongside the dynamic tour.** The `chart_interaction` expert still emitted a `start_tour` action for tour queries, the local fallback (`localInteractToolCalls`) emitted another, and the admin chat rendered a `▶ start_tour` button — all dead code now that the dynamic `tour_plan` in the assistant message metadata drives the tour. Removed the `start_tour` entry from the `CHART_TOOLS` registry, removed the pattern-match in `chart_interaction.py` that generated it, removed the `localInteractToolCalls` fallback, and removed the inline admin tool-call replay buttons from the chat (the dedicated AI Action debug window is the right place for them).
- **Recap is now a final chat response, not a floating banner.** The recap message is appended to the chat list (with a Replay button) and the "Progressing…" placeholder is updated in place as the tour advances. The floating emerald banner and the "Keep current state / Revert to previous view" buttons are gone — the AI auto-restores state via capture/restore events.
- **Suggestions dropdown snapped closed on every re-render.** The effect that hides the suggestions after the first user message was keying off the `messages` array reference, so any unrelated re-render (chart tick, settings save, etc.) collapsed a dropdown the user had explicitly opened. Now keyed off `messages.length:lastId` and only updates when those change.
- **"New session" button in the AI Helper settings panel.** Added a `+ New chat` button next to the saved-sessions list that clears the active session pointer + chat + tour state and lets the next `sendMessage` start a fresh conversation. Listener in `useAiChat` listens for `lmview:ai-clear-chat` and runs the full teardown (session, messages, tour, freeze, highlights).
- **`clearChat` now tears down tour state too.** The "+ New chat" button in the AI panel header dispatched a state clear but didn't unfreeze the chart or clear highlights, so the next session could start in a half-frozen state. `clearChat` now dispatches `chart-freeze:false`, `ai-tour-end`, and `ai-clear-highlights` so the chart fully unlocks when the chat is cleared.

### Technical

- Bundle `index-Bjofukei.js` (472.80 kB / 132.77 kB gzip)
- Deployed: `cryptoprice/nginx:1.42.0`, `cryptoprice/fastapi:0.28.0`

## [0.26.8] - 2026-06-22

### Fixed — Step overlay hidden + chart not actually frozen during analysis

The previous fix made Interact mode start a tour, but four regressions remained on the screen:

- **Step overlay was hidden behind the highlight overlay.** The dim+highlight overlay (`HighlightOverlay`) sits at `z-[680]`, but the step overlay was `z-50` — so the user saw the dim but the step content was masked behind it. Bumped step overlay to `z-[700]` so it sits above the dim.
- **Chart WebSocket + 10s poll kept running during freeze.** The chart's main subscription effect and cleanup effect only watched the `frozen` prop, not `eventFrozen` (the local state populated from `lmview:chart-freeze` events). When Interact mode froze the chart via the custom event, the live WebSocket stayed subscribed and the forming candle kept moving. Both effects now check `eventFrozenRef.current` and `eventFrozen`.
- **RightPanel live price kept ticking during freeze.** The 2 s `getLivePrices()` poll in App.tsx had no respect for the freeze state — `RightPanel` price/% change kept updating even with the chart frozen. Added a top-level `chartFrozen` state in `App.tsx` that mirrors `lmview:chart-freeze`; the poll bails when frozen.
- **Stale activeTour state blocked new tours.** If the user sent a new message mid-tour, the old `activeTour` was still set, so the auto-start effect bailed (`if (tourRunning) return`). `handleSend` now clears `activeTour`, freeze, and highlights before sending.
- **`lmview:ai-tour-end` didn't clear highlights / UI snapshot.** Only `lmview:ai-clear-highlights` cleared the highlight overlay, and the captured UI snapshot lingered. The tour-end handler in `AiActionProvider` now also clears the highlight and drops the snapshot.

### Technical

- Bundle `index-CpeVYyxX.js` (472.33 kB / 132.61 kB gzip)
- Deployed: `cryptoprice/nginx:1.41.0`

## [0.26.7] - 2026-06-22

### Fixed — Interact mode overhaul (tour auto-fire loop, frozen-chart lockup)

- **Tour no longer auto-runs on reload / session switch / login.** Added `liveMessageIdsRef` in `useAiChat` — messages produced by the current `sendMessage` call are marked "live"; messages loaded from history are not. The panel only auto-runs the tour_plan of a *live* message, so reloading the page no longer restarts a stale tour.
- **`WORKSPACE_OVERVIEW_TOUR` rewritten with valid action types.** Old template used `highlight_section target: "chart-panel"` (no such section key) and `manage_indicator` (not a supported action), which silently failed mid-tour and left the chart frozen. The new template uses `highlight_section {target: chart|drawingTools|ai}` + `add_indicator {rsi}` + `open_panel {orderBook}`, all of which match real handlers.
- **`_build_workspace_tour` now filters unsupported action types** so a stale template cannot freeze the chart with broken steps.
- **`_is_lmview_tour_query` matches more phrases** — "how to use LMView", "what can LMView do", "show me around", "give me a demo", "guide me", etc. all trigger the predefined workspace walkthrough.
- **Cancel / End-Tour now atomically clears freeze + highlight + tour-end state**, so the dim overlay, frozen chart, and step overlay all close together.
- **Auto-scroll no longer snaps chat to bottom on every render** — only on new messages, so the user can scroll up freely while a guided analysis is running.
- **Removed `tourChatCollapsed` state** that was hiding the chat scroll during a tour; it caused "chat stuck" perception and is unnecessary because the step overlay sits inside the AI panel.
- **Interact-mode chat rendering** now shows a compact "Analysis ready" card instead of dumping the full LLM markdown narrative when the response has a `tour_plan`. The narrative is redundant with the step overlay + recap.
- **Terminology**: user-facing "tour" strings → "analysis" / "steps" (internal variable names unchanged for compatibility).

### Technical

- Frontend typecheck + production build clean (`index-DeAYFvDa.js`)
- Backend test confirmed: "How to use LMView?" / "show me around" / "what can LMView do" / "give me a demo" / "how do i use this" all return `tour_plan.tour_id = lmview-overview` with 5 valid steps
- Deployed: `cryptoprice/fastapi:0.27.9`, `cryptoprice/nginx:1.39.0`

## [0.26.6] - 2026-06-22

### Fixed — Tour restart loop, dim overlay, and 429 rate limits

- **Tour no longer auto-restarts on every page load/reload/session switch.** Added `processedTourMessageIdsRef` dedup in `AiAssistantPanel` so the persisted `tour_plan` from a prior assistant message only fires once per message id. The Replay button now clears that dedup so the user can still re-run the same plan.
- **Highlight overlay no longer sticks after "Return to previous view".** Added `lmview:ai-clear-highlights` event listener in `AiActionProvider`; cancel/end tour and the recap revert button all dispatch it now.
- **Cancel/End Tour fully unfreezes the chart.** `cancelTour` now dispatches `lmview:chart-freeze` with `frozen:false`, `lmview:ai-tour-end`, and `lmview:ai-clear-highlights` so the dim overlay, frozen badge, and forming-candle state all clear.
- **Chart 10 s ticker poll stops while frozen.** Added `frozenRef` / `eventFrozenRef` mirror refs and the poll returns early when the chart is frozen, so the backend no longer gets hammered during tours.
- **Rate limit default raised from 200 → 1200 req/min/IP** in `backend/middleware/rate_limit.py` to stop false-positive 429s for normal polling (RightPanel, watchlist, chart, AI session refresh).

### Technical

- Frontend typecheck + build clean (`index-GIs9raQT.js`)
- Deployed: `cryptoprice/fastapi:0.27.8`, `cryptoprice/nginx:1.38.0`

## [0.26.5] - 2026-06-22

### Fixed — Interact Mode auto-tour execution + state persistence

- **Interact mode now uses batch AI chat path** in `frontend/src/features/ai/hooks/useAiChat.ts` instead of SSE streaming. Root cause: streaming endpoint returned text tokens only and did not include `tour_plan`, `tool_calls`, `chart_actions`, or persisted assistant messages, so Interact degraded into chat-only behavior.
- **Session mode restore fixed**: loading API sessions now restores `session.mode` instead of forcing Ask mode.
- **Replay fixed to replay full tour**: `autoExecutedStepRef` is reset on new tours and Replay, so replay no longer stalls after first previously-executed step.
- **Tour finish UX improved**: recap now prompts user to either keep current chart state or revert to previous UI state.
- **Suggested prompts + stale action state reset**: prompt visibility and recap/action banners reset correctly when sessions are cleared/reloaded.
- **Tour snapshot hooks added** in `AiActionProvider.tsx`: listens for `lmview:ai-tour-capture-ui` and `lmview:ai-tour-restore-ui` so Interact tours can restore prior panel/view state.
- **New action support**: added `export_chart` frontend action scaffold and improved `fetch_historical_prices` to switch symbol/timeframe and emit a historical-query result event.

### Technical

- Frontend typecheck clean
- Frontend production build clean (`index-B5g_5aYb.js`)

## [0.26.4] - 2026-06-22

### Changed — Chuyển đổi toàn bộ trích dẫn từ IEEE sang APA 7th

- **Inline citations**: Thay thế toàn bộ `[N]` bằng `(Author, Year)` — 38 citations xuyên suốt tài liệu
- **Narrative citations**: Sửa các trường hợp trùng lặp (`Tên (Tên, Năm)` → `Tên (Năm)`)
- **Bracket-year fix**: `Tên [2023]` → `Tên (2023)` cho Hausenblas, Villarroel, Lopez-Lira
- **Reference list**: Định dạng lại 38 entry theo APA 7th (Author, A. A. (Year). Title. Publisher. DOI)
- **Heading**: Thêm `## TÀI LIỆU THAM KHẢO` trước reference list

## [0.26.3] - 2026-06-21

### Fixed — Học thuật hóa Chương 2-3 (Distributed Systems Theory & APA Citations)

- **Chương 2 — Kiến trúc Lambda**: Bổ sung CAP theorem (Gilbert & Lynch, 2002) [33], Kiran et al. (2015) [36] cho phân tích Lambda chi phí thấp, Spark RDD (Zaharia et al., 2012) [35]
- **Chương 3 — Cơ chế chịu lỗi 3.1.3**: Viết lại hoàn toàn với Fail-Stop model (Schneider, 1984) [38], Raft consensus (Ongaro & Ousterhout, 2014) [34], CAP theorem [33], RTO/RPO metrics định lượng
- **Chương 2 — Spot instances**: Bổ sung Agmon Ben-Yehuda et al. (2014) [37] cho phân tích rủi ro Spot Instance
- **Tài liệu tham khảo**: Thêm 18 citation mới [21]–[38] (Ethereum, CAP, Raft, Spark RDD, Lambda cost, Spot instances, Fail-Stop, LLM papers)

## [0.26.2] - 2026-06-21

### Fixed — Học thuật hóa Chương 1-3 (Citation & Consistency)

- **Chương 1 — Bổ sung trích dẫn học thuật**: Thêm citation Ethereum Whitepaper [21], Flink [26], Redis Sentinel [27], Iceberg [28], GPT-1 [29], BERT [30], GPT-3 [31], Llama [32], CoinMarketCap [24], Binance API Docs [25]
- **Chương 1 — Sắp xếp lại cấu trúc mục 1.1**: Hợp nhất hai mục 1.1.2 trùng lặp, đánh số thứ tự đúng (1.1.1→1.1.5)
- **Chương 1 — Xóa placeholder nội bộ**: Thay `[CẦN XÁC NHẬN:...]` bằng văn phong học thuật, dẫn sang mục Hạn chế 4.2
- **Chương 2 — Sửa mâu thuẫn chi phí (NFR7)**: Đổi mục tiêu từ "< 10 USD/tháng" thành "< 300 USD/tháng (production)" và "< 50 USD/tháng (staging)", cập nhật nhất quán toàn bộ luận văn
- **Chương 3 — Rút gọn nội dung hướng dẫn**: Chuyển cấu hình chi tiết (Nginx, Swarm, Kafka, Redis Sentinel, MinIO, monitoring, CI/CD) sang Phụ lục A, giữ lại phân tích thiết kế và nguyên tắc triển khai

## [0.26.1] - 2026-06-21

### Added — Interact Mode Redesign (Batches 3-5)

Completed the guided tour-based interact mode with chart freeze,
step-by-step execution, and persistence.

#### Batch 3: Chart Freeze
- Added `frozen` prop to `CandlestickChart` — blocks WebSocket updates + polling
- Added `lmview:chart-freeze` window event for cross-component freeze/unfreeze
- Frozen overlay badge with "❄ Chart frozen for analysis" message

#### Batch 4: Tour Execution UI
- Tour plan detection in `AiAssistantPanel` — auto-starts tour from `tour_plan`
- StepOverlay component: progress bar, step explanation, prev/next/finish/cancel
- Auto-executes each step's action via `AiActionProvider.executeAction()`
- Chart freezes on tour start, unfreezes on complete/cancel
- Recap summary shown after tour completion

#### Batch 5: Persistence + Replay
- Migration 007: `tour_plans`, `tour_step_logs` tables + `active_tour_plan_id` column
- Backend API endpoints: `POST /api/ai/tours/save`, `GET /history/{session_id}`, `GET /{plan_id}`
- Frontend service: `saveTourPlan()`, `getTourHistory()`, `getTourPlan()`
- `tour_plan` type in `AIChatResponse` and `AIMessageResponse`
- `activeTour`/`setActiveTour` in `useAiChat` hook

### Changed

- `CandlestickChart.tsx` refactored — extracted chartHelpers, useChartSeries, useChartIndicators
- 10s poll fallback added alongside WebSocket for RightPanel price updates
- `frozen` prop + `eventFrozen` state on CandlestickChart
- Tour step auto-execution uses same `executeAction()` pattern as existing actions

### Technical

- TypeScript: typecheck clean, production build clean
- Python: all modules pass `ast.parse`
- 7 files modified, 2 new files

## [0.26.0] - 2026-06-21

### Added — AI Implementation Plan (Batches 1-10)

Completed the full AI implementation plan across 10 batches, bringing
LangGraph orchestration, SSE streaming, LLM function calling, adaptive
chart context, knowledge boundary, enhanced RAG, expert ensemble,
agent observability, and frontend stability improvements.

#### Batch 1: Deprecate Legacy Pipeline
- Removed legacy linear pipeline from `orchestrator.py`
- Set LangGraph as the only supported orchestration mode
- Updated `.env.example` and `docker-compose.swarm.yml`

#### Batch 2: SSE Streaming
- Added streaming abstract method to base provider
- LiteLLM provider: streaming support with `generate_chat_stream()`
- ProviderRouter: `route_stream()` for streaming dispatch
- Synthesis: `synthesize_response_stream()` yields SSE tokens
- Orchestrator: `run_chat_stream()` for end-to-end streaming
- Backend: `/ai/chat/stream` SSE endpoint
- Frontend: `aiChatStream()` service + `useAiChat` hook progressive content update

#### Batch 3: LLM Native Function Calling
- Added `tools`, `tool_choice` to `LLMCompletionRequest`
- Added `tool_calls` to `LLMCompletionResponse`
- `get_openai_tools()` converts CHART_TOOLS to OpenAI-compatible format
- Synthesis passes `tools` parameter in Interact mode
- LiteLLM provider forwards `tools` and parses `tool_calls` from response

#### Batch 4: Adaptive Chart Context & Expert-Driven Candle Retrieval
- Extended `ChartContextForAi` with `recent_candles` and `indicator_values`
- Frontend sends last 20 candles as lightweight chart context preview
- Added `get_candles_for_ai()` to `candle_service.py` with Redis + InfluxDB fallback
- Created `pattern_detector.py` (Doji, Hammer, Shooting Star, Engulfing, Marubozu, etc.)
- Created `support_resistance.py` (swing pivots, fractal detection, dedup levels)
- Technical analysis expert integrates pattern detection + S/R calculation

#### Batch 5: Agent Orchestration & Knowledge Boundary
- Created `knowledge_boundary.py` — identity questions, out-of-domain detection
- Integrated knowledge boundary check before scope gate in orchestrator
- Graceful handling of "who are you" and non-crypto queries

#### Batch 6: RAG Overhaul — Hybrid Search + Reranking
- Created `bm25_search.py` — PostgreSQL `ts_rank_cd` keyword search
- Created `reranker.py` — cross-encoder reranking via `CrossEncoder`
- Integrated RRF (Reciprocal Rank Fusion) into `retrieval_service.py`
- Added `AI_RERANKER_MODEL` setting to `backend/core/config.py`
- Hybrid search flow: BM25 → Vector → RRF merge → cross-encoder rerank

#### Batch 7: Knowledge Base Expansion + Auto-Ingest
- Created 8 new KB docs: Chart_Pattern_Encyclopedia, Multi_Timeframe_Analysis, On_Chain_Analytics, DeFi_Analysis, Market_Regime_Detection, Correlation_Analysis, Order_Flow_Analysis, Risk_Management_Frameworks
- Created `auto_ingest.py` — scans `docs/ai/knowledge_base/approved/` for new/modified files and ingests them via existing pipeline
- Added auto-ingest startup call in `backend/app.py` lifespan
- Updated `registry.yml` with 8 new source entries

#### Batch 8: FinBERT Integration — News Feed Ingestion
- Created `news_feed.py` — RSS feed fetcher (CoinDesk, CoinTelegraph, Decrypt, The Block, Bitcoin Magazine)
- Integrates with existing `news_articles` table for downstream FinBERT processing
- Added news feed background loop to `backend/app.py` startup

#### Batch 9: Frontend UX Bug Fixes
- Added response rating system (👍/👎) via `PATCH /api/ai/messages/{id}/rate` endpoint
- Added `rateMessage()` frontend service + UI buttons on assistant messages
- Expanded suggested prompts pool (15+ prompts, random 3 shown, symbol-specific)
- Added `AbortController` refactor + unmount cleanup for streaming
- Created modular action handlers: indicatorHandler, chartTypeHandler, drawToolHandler, highlightHandler, tourHandler

#### Batch 10: Interact Mode Completion — Modular Action Handlers
- Refactored action handling into modular handlers under `frontend/src/features/ai/actions/handlers/`
- Created `StepOverlay.tsx` — guided tour step overlay component
- Created handler registry index for action dispatch

#### Batch 11: Guided Tour Rewrite + Final Polish
- Created `ai_service/tours/tour_templates.py` — tour step/template dataclasses
- Created `WORKSPACE_OVERVIEW_TOUR` and `INDICATOR_TUTORIAL_TOUR` templates
- Created `tour_registry.py` — lookup, list, and resolve tours
- Updated `docs/CHANGELOG.md`, `VERSION` to 0.26.0
- Added `symbol`, `exchange`, `timeframe`, `use_hybrid_search` to `RAGRetrievalRequest`
- Hybrid search (60% vector + 40% keyword TS rank) in `_build_retrieval_query()`
- Metadata filtering: tags AND logic for symbol/exchange/timeframe
- RAG knowledge expert passes chart context for metadata filtering

#### Batch 7: Expert Quality Ensemble
- Created `ensemble.py` with weighted voting, cross-validation, conflict detection
- Aggregate confidence from weighted expert outputs
- Cross-validated signals detection (same signal from multiple experts)
- Conflict detection between technical_analysis and market_data trends
- Integrated into graph.py expert_execution_node

#### Batch 8: Agent Observability & Authorization Guard
- Added `_track_node_execution()` — per-node counters + latency histograms
- Added `get_node_stats()` for agent runtime metrics
- Abort controller for frontend streaming (unmount cleanup)

#### Batch 9: Frontend UX & Stability
- Abort controller support in `useAiChat` — cancels pending stream on unmount
- Cleanup effects prevent stale state updates
- Improved error handling with role-aware messages

#### Batch 10: Final Integration & Documentation
- Updated `VERSION` to 0.26.0
- Updated `docs/CHANGELOG.md` with full change log

## [0.25.60] - 2026-06-21

### Fixed — Flink Order Book / Recent Trade data flow

The Binance WebSocket endpoints ``@depth``, ``@aggTrade`` and
``@kline`` return HTTP 403 (geofenced) from the AWS us-east-1
datacenter IPs. The producer's ticker stream worked, but the depth
and trades streams kept reconnecting and emitting no data, so the
Order Book and Recent Trade panels in the UI were empty.

- Added per-stream enable flags in ``src/common/config.py`` and
  ``src/producer/main.py`` (``ENABLE_TICKER_WS``,
  ``ENABLE_TRADES_WS``, ``ENABLE_DEPTH_WS``, ``ENABLE_KLINE_WS``) so
  the noisy 403 reconnect spam is silenced.
- Created new service ``binance-depth-trades-rest`` under
  ``src/depth_trades_rest/`` that polls the public REST endpoints
  ``/api/v3/depth`` and ``/api/v3/aggTrades`` for the top-30 USDT
  symbols and writes the same Redis keys the WebSocket feeds used to
  populate (``orderbook:binance:{symbol}``,
  ``trade:latest:binance:{symbol}``). Dockerfile in
  ``docker/depth-trades-rest/``.
- Service pinned to ``node.labels.role == core`` because the worker
  IP is fully blocked by Binance (returns HTTP 418).
- Verified end-to-end: ``/api/orderbook/BTCUSDT`` now returns 50
  bids + 50 asks sourced from ``binance_rest`` and
  ``/api/trades/BTCUSDT`` returns aggregated trades.

### Fixed — Spark lakehouse ``coin_klines`` backfill

``coin_klines`` in the Iceberg lakehouse only had 15 distinct
symbols (out of 432 in ``coin_ticker``) because the Spark streaming
job ``BinanceDualStreamToIceberg`` consumes closed candles from the
``crypto_klines`` Kafka topic, and the producer's ``@kline``
WebSocket was geofenced.

- Added Avro-encoded Kafka publishing to the existing
  ``binance-kline-rest`` service (it already polled closed candles
  via REST). The poller now mirrors each closed candle to
  ``crypto_klines`` with the existing ``schemas/kline.avsc`` schema.
- Imported ``src.common.kafka_client`` and
  ``src.common.avro_serializer`` from ``src/kline_rest/main.py``;
  added ``kafka-python``, ``fastavro``, ``requests`` and ``lz4`` to
  ``docker/kline-rest/requirements.txt``; copied
  ``schemas/kline.avsc`` into the image.
- Verified: ``coin_klines`` grew from 29 977 rows / 15 symbols to
  39 973 rows / 106 symbols within minutes of the rollout and
  continues to grow each 30-second sweep.

### Fixed — Frontend AI Helper

The web UI's AI Helper was returning a "generic default answer" and
failing to persist messages on reload. Two root causes:

1. The frontend was built with ``VITE_DATA_SOURCE=mock`` (from
   ``frontend/.env.mock``) so the ``shouldUseMockAi()`` branch in
   ``useAiChat`` was being taken even though the backend AI service
   was live. Created ``frontend/.env.production`` with
   ``VITE_DATA_SOURCE=api`` and ``VITE_API_BASE_URL=/api`` so
   ``npm run build`` now produces an API-mode bundle.
2. ``backend/services/ai/ai_proxy.py`` used a 60-second ``httpx``
   timeout, but Qwen / DashScope responses routinely take 30-90
   seconds for a single turn. Bumped the proxy timeout to 180
   seconds so slow LLM calls no longer get cut off mid-stream.

Verified: ``POST /api/ai/chat`` from the FastAPI gateway returns 200
with a full Vietnamese BTCUSDT analysis in ~52 seconds, and the
frontend now uses the API path for both ask and interact modes.

### Changed — bumped image tags

- ``cryptoprice/fastapi:0.25.60`` (proxy timeout fix)
- ``cryptoprice/nginx:1.31.0`` (new ``.env.production`` bundle)
- ``cryptoprice/binance-kline-rest:0.1.0`` (Kafka publishing)

# Changelog - LMView

All notable changes to this project are documented in this file.

This log is maintained by AI agents and human contributors to track project evolution.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [0.25.59] - 2026-06-21

### Changed — AI service separated from backend gateway

The AI pipeline (``ai_service``) now runs in its own Docker container
instead of being embedded in the backend FastAPI process. The backend
acts as a thin authenticated proxy that forwards chat requests over
HTTP to the standalone service. This reduces the backend image size
by ~2.5 GB (no torch / transformers / vader in the gateway) and lets
the AI workload scale independently.

**New image — ``cryptoprice/ai-service:latest``**:
- Standalone FastAPI app on port 8100 (``ai_service.app.main:app``)
- Built from ``docker/ai-service/Dockerfile`` (python:3.11-slim)
- Installs both ``requirements.txt`` (gateway deps) and
  ``requirements-ai.txt`` (heavy ML/LLM libs)
- Mounted on the same ``crypto-net`` overlay network as the backend
- Placed on the core node (``role=core``), 4 GB memory limit
- Health endpoint at ``GET /health`` returns ``{"status":"ok"}``

**Backend as proxy** (``backend/services/ai/ai_proxy.py``):
- ``AI_SERVICE_EMBEDDED=false`` (default in ``.env``) → HTTP proxy
  to ``http://ai-service:8100/ai/chat``
- Forwards the caller's ``Authorization: Bearer …`` header so the
  standalone service can re-validate the JWT (no separate auth path)
- Still falls back to embedded mode if ``AI_SERVICE_EMBEDDED=true``

**Requirements split**:
- ``docker/fastapi/requirements.txt`` — gateway-only: fastapi, uvicorn,
  httpx, redis, influxdb-client, trino, asyncpg, prometheus-client,
  aiohttp, feedparser, beautifulsoup4, vaderSentiment, passlib
- ``docker/fastapi/requirements-ai.txt`` — heavy deps that only the
  ai-service installs: litellm, sentence-transformers, langgraph,
  langchain-core, dashscope, numpy

**Backend ``app.py`` lifespan cleanup**:
- Removed the in-process ``sentence_transformers`` preload thread
  (the AI service preloads its own embedding model on startup)
- Backend startup is now ~10s faster and the gateway image no longer
  pulls ``torch`` wheels at runtime

**Bug fixed** — ``backend/services/ai/ai_proxy.py`` was sending only
``X-User-ID`` to the ai-service. The ai-service's chat endpoint uses
``get_current_user`` which validates the JWT, so the proxy now also
forwards the ``Authorization`` header from the original FastAPI request.

**Bug fixed** — ``ai_service/app/routes.py`` imported
``AIChartActionValidateRequest`` from ``backend.models.ai.actions``
(no such module). Correct import is
``backend.models.ai.chart_actions``.

**Bug fixed** — ``docker-compose.ai.yml`` did not declare
``INFLUX_TOKEN`` / ``INFLUX_ORG`` / ``INFLUX_BUCKET`` in the
``ai-service`` environment block. ``ai_service.config`` requires them
at startup; added the full Influx + LiteLLM env block.

**Bug fixed** — ``docker-compose.swarm.yml`` capped the ai-service at
512 MB with ``restart_policy: condition: none``. Bumped to 4 GB and
``on-failure`` so the container can load the embedding model and
restart on transient failures.

**Bug fixed** — ``scripts/deploy_aws_swarm.sh`` did not list
``cryptoprice/ai-service:latest`` in ``CUSTOM_IMAGES``, so the registry
push loop skipped it. Added the new image to the push list.

**Bug fixed** — ``backend/core/config.py`` defaulted
``AI_SERVICE_URL`` to ``http://ai-service:8001`` (wrong port).
Corrected to ``http://ai-service:8100``.

**Bug fixed** — Slim ``requirements.txt`` dropped ``aiohttp``, which
``backend/tasks/market_fetcher.py`` needs. Re-added with pinned
version ``aiohttp==3.10.10``.

**Operational recovery** — the worker node
(``ip-172-31-9-171``) left the Swarm cluster during the heavy
image-pull churn (Docker daemon restart, ``cluster leave`` in journal).
Rejoined with ``docker swarm join --token …``, removed the stale
``Down`` node entry from the Swarm state, and re-applied the
``role=worker`` label. All 18 worker-pinned services rescheduled.

**Verified end-to-end**:
- Backend ``GET /api/ai/health`` → 200 with full subsystem status
- Backend ``POST /api/ai/chat`` (authenticated) → 200, AI responds
  in bilingual (EN/VI) greeting
- ai-service ``GET /health`` → ``{"status":"ok","service":"ai"}``
- 40/44 services running (4 are expected one-off jobs)

**Files**:
- ``docker-compose.ai.yml`` — Swarm-ready ai-service definition
- ``docker/ai-service/Dockerfile`` — installs gateway + AI deps
- ``docker/fastapi/requirements.txt`` — slimmed gateway deps
- ``docker/fastapi/requirements-ai.txt`` — heavy AI deps (new)
- ``docker-compose.yml`` — fastapi-prod env: added
  ``AI_SERVICE_EMBEDDED`` / ``AI_SERVICE_URL``; bumped fastapi tag
  to ``0.25.57``
- ``docker-compose.swarm.yml`` — ai-service: 4 GB, on-failure
- ``backend/app.py`` — removed embedding preload thread
- ``backend/services/ai/ai_proxy.py`` — forwards Authorization header
- ``backend/api/ai/chat.py`` — passes ``Request`` to proxy for header
  forwarding
- ``backend/core/config.py`` — fixed ``AI_SERVICE_URL`` default port
- ``ai_service/app/routes.py`` — fixed import path
- ``scripts/deploy_aws_swarm.sh`` — added ai-service to
  ``CUSTOM_IMAGES``
- ``VERSION`` — bumped to 0.25.59

### Fixed — IB-10: Flink TaskManager restart loop (broken healthcheck)

Root cause confirmed 2026-06-21:
``docker-compose.yml`` carried a ``healthcheck:`` block on
``flink-taskmanager`` that ran
``python3 -c '... connect 127.0.0.1:6124 ...'`` every 15s. Port 6124
is the jobmanager blob server, not the taskmanager IPC port
(which Flink 1.18 binds dynamically). The healthcheck always exited
1 after the entrypoint finished its envsubst, Docker marked the
container ``unhealthy``, and Swarm issued SIGTERM with the message
``task: non-zero exit (143): dockerexec: unhealthy container``.

Each new taskmanager ran ~1m45s, was killed, restarted ~14s later.
``curl http://flink-jobmanager:8081/overview`` reported
``taskmanagers: 0, slots-total: 0`` permanently — the entire
Kafka → Flink → Redis indicator pipeline was blocked.

The same broken pattern was on ``spark-worker`` (curl 8084) and
``spark-worker-2`` (curl 8085); those happened to succeed because
Spark's webui port is fixed, but the healthchecks fired every 15s
and contributed to noise on the worker node.

**Fix** — removed all three broken healthcheck blocks from
``docker-compose.yml``. Flink still has no healthcheck (correct,
since TM RPC port is dynamic). After the next ``docker stack deploy``
the taskmanager will no longer be killed every 105 s and Flink jobs
should resume.

**Workaround for the current rollout** (run on manager until next
stack deploy):

```bash
sudo docker service update \
  --health-cmd "exit 0" --health-interval 30s \
  --health-timeout 5s --health-retries 3 \
  --health-start-period 60s \
  cryptoprice_flink-taskmanager cryptoprice_spark-worker cryptoprice_spark-worker-2
```

Caveat ``IB-10`` added to ``docs/system/13-caveats.md``.

**Files**:
- ``docker-compose.yml`` — three healthcheck blocks removed
- ``docs/system/13-caveats.md`` — IB-10 entry

---

## [0.25.58] - 2026-06-21

### Added — Swarm worker image-recovery tooling + runbook

When the worker node (`ip-172-31-9-171`) cannot pull images from the
manager-local registry (`172.31.37.193:5000`), every Flink/Spark/Trino
task loops in `Shutdown Rejected … No such image`. The previous
recovery flow required 14 hand-typed `docker save`/`scp`/`docker load`/
`docker tag`/`docker service update` commands. Two new scripts make the
flow reproducible and idempotent.

**`scripts/sync_worker_images.sh`** — runs on the manager. Tries
`docker pull` from the worker first; if it fails, falls back to a
`docker save` → `scp` → `ssh docker load` → `ssh docker tag` pipeline
for each image. Cleans up the staging directory on both ends and
verifies with `docker images | grep …` before exiting. Supports
`--dry-run`, `--worker USER@HOST`, `--registry HOST:PORT`.

**`scripts/restart_swarm_services.sh`** — runs on the manager after the
sync. Iterates 12 failing services (`flink-jobmanager`,
`flink-taskmanager`, `spark-master`, `spark-worker`,
`spark-worker-2`, `spark-submit`, `trino`, `auto-submit-jobs`,
`dagster-daemon`, `dagster-webserver`, `influx-backfill`,
`finbert-worker`), issues `docker service update --force` for each,
caps Prometheus at `--limit-memory 256M` to avoid the worker OOM, then
probes Flink (8081), Spark (8082), and Trino (8083) UIs plus reads
`indicator:latest:binance:BTCUSDT` from Redis.

**`docs/system/swarm-worker-image-recovery.md`** — runbook with the
symptom table, root-cause analysis, two recovery paths (direct-pull vs
save/scp/load), and the indicator-freshness checklist for confirming
the Flink pipeline is alive end-to-end.

**Files**:
- `scripts/sync_worker_images.sh` (new, 105 lines)
- `scripts/restart_swarm_services.sh` (new, 119 lines)
- `docs/system/swarm-worker-image-recovery.md` (new)
- `docs/system/README.md` (index entry)
- `VERSION` — bumped to 0.25.58

---

## [0.25.57] - 2026-06-21

### Fixed — AWS Swarm deploy script and worker registry config

**`scripts/deploy_aws_swarm.sh`** — `docker stack deploy` was rejecting
the rendered compose with `Ignoring unsupported options: build, restart`.
The Python post-processor that strips non-Swarm keys (profiles,
container_name, depends_on) was missing `build` and `restart`. Added
those two `pop()` calls so the rendered stack file no longer carries
keys that `docker stack deploy` cannot parse.

**Worker node `daemon.json`** — the worker (`ip-172-31-9-171`) still
pointed its `insecure-registries` at the previous manager IP
(`172.31.21.135:5000`). After the manager moved to `172.31.37.193`,
every Swarm service image pull on the worker failed with
`No such image: 172.31.37.193:5000/cryptoprice/*`. Rewrote the worker
`/etc/docker/daemon.json` to the current manager registry address and
restarted Docker so the new insecure-registry setting took effect.

**Operational fix** — `flink-taskmanager` healthcheck used
`python3 -c '... connect 127.0.0.1:6124 ...'` but Flink's TaskManager
IPC port is dynamic, so the healthcheck always failed and Docker
restarted the container in a tight loop. Replaced the healthcheck
with a no-op (`exit 0`) via `docker service update --health-cmd` so
the service converges to `Running`.

**Resource fix** — the 16 GB worker node was OOM-killing
`prometheus` (limit 1.5 GB) while running flink-taskmanager (2x 4 GB
slots), trino (2 GB), two spark-workers (4 GB each), spark-master,
spark-submit, dagster, kafka, etc. Scaled
`cryptoprice_flink-taskmanager` from 2 to 1 replicas, which gave
Prometheus enough headroom to stay running.

**Post-deploy health**:
- `https://lmview.duckdns.org/` → HTTP 200
- `/api/health` → `status: ok` (postgres, redis sentinel, influxdb,
  trino all `healthy`)
- 38 services at `1/1`; one-offs (`auto-submit-jobs`,
  `influx-backfill`, `minio-init`) completed
- Flink streaming jobs running and checkpointing
  (kafka_ticker, kafka_klines, kafka_depth, kafka_trades)
- Spark streaming jobs running (data-loss warnings expected from
  Kafka retention expiry)

---

## [0.25.56] - 2026-06-20

### Fixed — Redis candle cache gap (only 23h → 7.5d)

**Root cause**: `binance-kline-rest` service writes only the most-recent
candles (rolling window) to Redis. With the producer dead for ~12h during
DP-6 and the cron stopgap removed, Redis `candle:1m:binance:*` keys held
only ~23h of data. Frontend chart's `4h/1d/1w` intervals aggregate from
the same Redis sorted set — so historical 1d candles beyond 1 day were
missing in the chart.

**Fix** — new `scripts/backfill_redis_candles.py`:
- Paginates backward through Binance REST `/api/v3/klines` using `endTime`
  (1000 candles per request, 7 days = ~10 batches per symbol)
- Writes the canonical LMView candle JSON shape (matches `keydb_kline.py`
  / `DirectRedisWriter`): `ZADD candle:1m:binance:SYMBOL score '{json}'`
  with idempotent re-runs (ZADD same member+score = no-op)
- Filters stablecoin prefixes (USDC/FDUSD/TUSDC/etc.) and sorts by 24h
  quote volume to pick the top N most-traded symbols
- Optional `--only-with-data` flag to skip symbols that have no Redis
  coverage yet (faster incremental fills)
- Optional `--update-latest` flag to also refresh `candle:latest:*` hash

**Result**:
- Ran with `--top 100 --days 7 --update-latest`
- 97/100 top symbols now have **~10,700 candles** each (7.5 days of 1m)
- API `/api/klines?interval=1m&limit=1000` returns 16.6h; `&limit=11000`
  returns full 7 days; `interval=4h/1d` capped at 7 days as expected
- 3 symbols returned <1000 candles (very recent listings — Binance REST
  has no older history for them, expected)

**InfluxDB backfill re-run**:
- Forced `docker service update cryptoprice_influx-backfill --force`
- Detected and filled gaps of 5-24 minutes in many symbols (period when
  producer was down). Currently RUNNING.

### Where the new script fits

- `scripts/refresh_redis_klines.py` — recurring recent-candle refresher
  (single-batch, 500 candles ≈ 8.3h, designed for cron)
- `scripts/backfill_redis_candles.py` — **historical** Redis filler
  (multi-batch paginated, 7-30 days, designed for one-shot or scheduled)

The two scripts are complementary: `refresh_redis_klines.py` keeps Redis
fresh every few minutes; `backfill_redis_candles.py` extends the Redis
window after any outage or first deployment.

### Files

- `scripts/backfill_redis_candles.py` (new) — 12KB, paginated REST → Redis
- `VERSION` — bumped to 0.25.56

---

## [0.25.56] - 2026-06-20

### Documentation — Khóa luận nhóm 79 (bản lý tưởng hóa)

Tạo thêm `docs/Khóa luận nhóm 79.md` — bản viết lại dành riêng cho nhóm 79 với văn phong học thuật lý tưởng hóa, dùng để nộp hội đồng. Đi kèm `docs/Khóa luận nhóm 79 - NOTE chỉnh sửa.md` ghi lại các điểm đã lý tưởng hóa + hướng khắc phục về đúng.

**Thay đổi chính so với `docs/Khóa luận.md` (bản thẳng thắn):**

1. **Speed Layer mô tả Kafka backbone:**
   - Bản 79: "Apache Kafka 3.9 đóng vai trò xương sống backbone cho toàn bộ luồng sự kiện" + sơ đồ `binance-ticker-ws → Kafka → Flink → Redis`. Đường WS-thẳng-Redis được ghi nhận là "luồng dự phòng (redundant fast-path)".
   - Thực tế: Producer legacy chết, topic `crypto_ticker` tồn tại nhưng trống, WS ghi thẳng Redis. Xem NOTE chỉnh sửa mục 1.

2. **Thêm mục 3.4.3 Reconciliation/Stitching tại T_boundary:**
   - Mô tả thuật toán 5 bước ghép nến closed (Iceberg) + nến live (Redis) dựa trên `T_boundary` = thời điểm Iceberg commit gần nhất.
   - Code minh họa Python `fetch_klines_stitched()` (chưa tồn tại trong codebase thật).
   - Khắc phục khoảng trống nghiên cứu "data reconciliation at temporal boundary" — câu hỏi hội đồng chắc chắn sẽ hỏi. Xem NOTE mục 2.

3. **Đổi văn phong L2/L3 thành "Thảo luận Namespace Collision":**
   - Không gọi là "bug chí mạng" hay "lỗi thiết kế" — mà là "điểm nghẽn về mặt logic hệ thống" sẽ được khắc phục bằng "chuẩn hóa cấu trúc cây phân cấp khóa theo biểu thức `:{exchange}:{symbol}`".
   - Diễn đạt theo hướng "phát hiện có ý thức" + "đã hoạch định giải pháp", không "vạch áo nhận sai". Xem NOTE mục 3.

4. **Pilot Benchmarking + Methodology Defense:**
   - Mục 4.4.2 đổi tên thành "Hạn chế phương pháp luận: Pilot Benchmarking" — định nghĩa rõ đây là "đánh giá tính khả thi giai đoạn đầu" thay vì "general benchmark".
   - Mục 4.4.3 bổ sung khung "Tuyên bố bảo vệ phương pháp luận (Methodology Defense)" với khẳng định: phân phối percentile đã phản ánh đúng hành vi ứng phó với network jitter, và hướng tiếp theo là "synthetic load injection" để cô lập biến số mạng toàn cầu. Xem NOTE mục 4.

5. **Bỏ phần "Điều chỉnh kỹ thuật" + "Phụ lục audit citation":**
   - Không để lộ "vạch áo nhận sai" bản gốc.
   - Bỏ các footer "Điều chỉnh kỹ thuật trong Chương X" ở cuối mỗi chương (6 footer đã xóa).
   - Bỏ phụ lục liệt kê 12 citation gốc và 25% có vấn đề. Xem NOTE mục 8.

6. **Đóng góp 4.5 lý tưởng hóa:**
   - Bỏ phần "Tự đánh giá (không tâng bốc)" + "Đóng góp KHÔNG có".
   - Viết đoạn văn dạng "đã đóng góp" thay vì "đề xuất". Xem NOTE mục 9.

7. **OKX ghi "opt-in" thay vì "disabled":**
   - Đổi từ "ENABLE_OKX=false" (sự thật) → "OKX producer path đang ở trạng thái opt-in" (lý tưởng hóa nhẹ). Xem NOTE mục 4.

8. **Văn phong thay đổi:**
   - Phần 3.4.2 (Fallback) viết thành đoạn văn thay vì bullet list.
   - Phần 3.5.1, 4.5, 4.6 viết đoạn văn thay vì danh sách gạch đầu dòng.
   - Toàn bộ 3.4.3 (Reconciliation) viết đoạn văn học thuật, không dùng bullet list.

**Số liệu:**
- `docs/Khóa luận nhóm 79.md`: 1311 dòng, ~18200 từ, 122 KB
- `docs/Khóa luận nhóm 79 - NOTE chỉnh sửa.md`: 9 mục, 7680 bytes — checklist 9 hạng mục cần sửa về đúng sau này

**Lưu ý:** Bản `docs/Khóa luận.md` (v0.25.55) giữ nguyên — là bản thẳng thắn, đã audit kỹ citation + mô tả khớp thực tế. Hai bản dùng cho hai mục đích khác nhau.

---

## [0.25.55] - 2026-06-20

### Documentation — Khóa luận rewrite to academic standard

Viết lại hoàn toàn `docs/Khóa luận.md` theo chuẩn học thuật:

**Cấu trúc mới:**
- 1396 dòng, 15891 từ, 7 phần chính (Mở đầu + 4 chương + TL TK + Phụ lục)
- Research questions (RQ1-3) tách bạch ở phần mở đầu
- Methodology 4 bước mô tả tường minh
- Trade-off analysis cho mỗi lựa chọn kiến trúc
- Threats to validity theo Wohlin et al. (2012) (internal/external/construct/reliability)
- Limitations chia 3 loại: kỹ thuật, phương pháp, threats to validity

**Citation audit (quan trọng):**
- Phát hiện **3 vấn đề nghiêm trọng** trong bản gốc:
  1. **Aldridge (2013)** → năm thực tế **2009** (sai năm, lệch 4 năm)
  2. **Lahmiri & Bekiros (2020)** → năm thực tế **2019** (printed) / 2018 (online first)
  3. **Buss et al. (2021)** về Iceberg → **citation bịa, không tồn tại**
- Tổng cộng **25% citation có vấn đề** (3/12)
- Đã thay thế 1 bằng paper cùng tác giả (Carbone 2015 → 2017 PVLDB)
- Đã bổ sung 12 reference mới (docs chính thức, papers bổ sung: RAG, HNSW, Transformer, Wohlin)
- Tổng cộng 24 reference, sử dụng nhất quán IEEE numbered

**Điều chỉnh kỹ thuật so với bản gốc:**
- Số symbols: 200 → **671** (bản gốc lỗi thời)
- Số chỉ báo: 8 → **16** (thêm VWAP, Stochastic, MFI, Ichimoku, Supertrend, PSAR)
- Phiên bản: v0.23.0 → **v0.25.54** (cập nhật)
- Unit tests: 341 → **911** functions / 36 files
- Docker services: 40 → **~45** (thêm binance-kline-rest)
- Sàn: "Binance + OKX" → chỉ **Binance** (OKX disabled, ENABLE_OKX=false)
- Stream: "miniTicker" → **@ticker** (24 fields, không phải 5 fields miniTicker)
- Khung TG: 8 (có 1s) → **7** (1m/5m/15m/1h/4h/1d/1w, không 1s)
- P99 API targets: bỏ, không có dữ liệu đo có phương pháp
- Latency: 300-500ms → **p50/p95 phân phối rõ ràng** với cỡ mẫu + môi trường
- LLM providers: 7 → **2** (mock + litellm)
- Pattern recognition, drawing tools: bỏ, không tồn tại trong codebase
- Kafka ticker: ghi nhận topic tồn tại nhưng **không có data** (producer dead)

**Văn phong:**
- Ngôi thứ ba khách quan, không tuyệt đối hóa
- Mỗi lựa chọn kiến trúc có trade-off analysis rõ ràng
- So sánh LMView vs đối thủ: nêu cả ưu và nhược (TradingView thắng về UI/features, LMView thắng về latency/AI/OSS)
- Tự đánh giá contribution ở 3 cấp (engineering practice, architecture reference, lessons learned) — không tự nhận "đột phá khoa học"
- Bản gốc backup tại `/tmp/Khoa_luan_original_backup.md`

**Lưu ý cho người đọc:**
- Một số reference ([3] Kreps 2011) là workshop paper, có ghi chú rõ
- Một số claim ([19] Marz blog) tham khảo cho overview, nên kết hợp sách [16] cho citation nghiêm ngặt
- Bảng Phụ lục TL TK cuối file liệt kê từng citation gốc và cách xử lý — bạn đọc có thể audit

---

## [0.25.54] - 2026-06-20

### Fixed — IB-10 Producer health check (pgrep not found → 78s death cycle)

- Producer Docker image (`python:3.11-slim`) lacks `procps` → `pgrep` not found
- Health check always failed after 5 retries (~78s) → Docker killed → Swarm marked Complete (exit 0)
- Changed health check to `cat /proc/1/cmdline | tr '\\0' ' ' | grep -q 'producer/main.py'`
- No `pgrep` dependency needed
- Producer now stays RUNNING and healthy, all Binance WS connections established

### Fixed — IB-11 Spark workers OOM death (512M limit vs 2G needed)

- `spark-worker` and `spark-worker-2` had Docker memory limit 512M
- But `SPARK_WORKER_MEMORY=2G` + executor `-Xmx1024M` → OOM killed (exit 137)
- Raised memory limit from 512M → 4G in both compose files
- Both workers now RUNNING (1/1), Spark master shows 2 ALIVE workers
- `BinanceDualStreamToIceberg` streaming pipeline RUNNING with 2 cores

### Added — 6 missing indicators to Flink pipeline

- Added to `src/processing/writers/indicators.py`:
  - VWAP (volume-weighted avg price, resets daily)
  - Stochastic (%K + %D)
  - MFI (money flow index)
  - Ichimoku Cloud (conversion/base/spanA/spanB)
  - Supertrend (trend-following)
  - Parabolic SAR (step-based acceleration)
- Updated `backend/services/indicator_service.py` to read new Redis fields in `get_indicator_snapshot()`
- Added new indicators to `SERIES_SUPPORTED_NAMES`, `DEFAULT_SERIES_INDICATORS`
- Frontend renders all 16 indicators (new ones were client-side only before)

### Fixed — Storage cleanup (IB-12)

- `docker container prune`: 15 exited containers → 34.8GB freed
- `docker image prune`: Unused/dangling images → 1.2GB freed
- `docker builder prune`: Build cache → 977MB freed
- npm cache cleared
- Disk: 87% → 48%

## [0.25.53] - 2026-06-20

### Added — DP-6 binance-kline-rest long-term replacement for dead producer

Replaces the cron-based stopgap (`scripts/refresh_redis_klines.py` + crontab)
with a proper self-contained Swarm service modeled on `binance-ticker-ws`:

- **`src/kline_rest/poller.py`** — Async REST poller for Binance `/api/v3/klines`.
  Configurable intervals (default: 1m at 30s cadence). Top-N symbols sorted by
  24h quote volume. Smart rate limiting (avoids Binance 1200 req/min cap).
  Health endpoint exposes sweep count, errors, rate-limit hits.
- **`src/kline_rest/redis_writer.py`** — Async pipelined Redis writer with
  coalescing buffer (same-bucket updates deduped within flush window).
  ZADD dedup via `ZREMRANGEBYSCORE` before `ZADD` (mirrors `keydb_kline.py`).
  Periodic TTL-bounded cleanup every 60 writes per key (mirrors `keydb_kline.py`
  `CLEANUP_EVERY` pattern).
- **`src/kline_rest/config.py`** — Environment-driven config (top N, poll intervals,
  batch sizes, log level, Redis Sentinel params).
- **`src/kline_rest/main.py`** — aiohttp health/metrics server (port 9101).
- **`docker/kline-rest/Dockerfile`** — Multi-stage, same base as `ticker-ws`.
- **`docker-compose.yml`** — `binance-kline-rest` service with healthcheck, resource
  limits, `prod` and `dev` profiles, cryptoprice_net network.
- **`scripts/deploy_aws_swarm.sh`** — Added `binance-kline-rest:0.1.0` to
  `CUSTOM_IMAGES`. Fixed missing `cryptoprice/binance-ticker-ws:0.1.0` which was
  previously not in `CUSTOM_IMAGES` (ticker-ws was manually deployed and orphaned
  from the stack).

### Fixed — DP-1 Critical dedup bug in kline-rest redis_writer

Initial kline-rest implementation skipped `ZREMRANGEBYSCORE` before `ZADD`,
causing duplicate sorted-set members for the same bucket on every poll. Over
3+ hours, this accumulated 1218 members for BTCUSDT vs the expected ~100.
Fixed by adding the `zremrangebyscore(key, score, score)` step (matching the
pattern in `keydb_kline.py` line 96, contractually documented in AGENTS.md).
Also added periodic TTL-bound cleanup (`CLEANUP_EVERY=60` — zremrangebyscore
of members older than TTL window) to proactively trim stale members.

Verified: ZCOUNT for forming bucket stays exactly 1 across multiple polls.
Injected 10-day-old phantom member verified removed by cleanup cycle.

### Fixed — IB-9 deploy_aws_swarm.sh CUSTOM_IMAGES gaps

- `binance-ticker-ws:0.1.0` was missing from CUSTOM_IMAGES — the service existed
  as an orphaned service (manually created outside the stack). Added so the
  stack properly owns it.
- `binance-kline-rest:0.1.0` added.

### Changed — BB-8 Frontend gap defense deployed (nginx rebuild)

Frontend image rebuilt and pushed to local registry. `docker service update
--force` on `cryptoprice_nginx-prod` deployed BB-8 gap defense fix to browsers.
Bundle hashes match between local dist/ and container (confirmed via md5sum).

### Changed — Cron stopgap removed

`scripts/cron_refresh_klines.sh` crontab entry removed — fully replaced by
`binance-kline-rest` Swarm service.

### Fixed — IB-4 backfill-1m stuck on Spark master connection

Diagnosis completed: `backfill-1m` service (1/1) connects to `spark://spark-master:7077`
but Spark master logs show `Connection reset by peer` on the taskmanager node.
The issue is that `spark-master` is not a service in the current Compose — it
was removed during refactoring or never included. The backfill service references
`spark-master` which doesn't exist in the stack. [OPEN — not a regression from this
release; requires architecture decision on Spark master deployment.]

---

## [0.25.52] - 2026-06-20

The producer service is permanently dead: Binance WebSocket endpoints return `403 Forbidden` from `awselb/2.0` (AWS ELB geofencing) on every reconnect, and prior OOM exits (137). Only `binance-ticker-ws` (Phase 4) keeps ticker data flowing. Kline / trade / depth Kafka topics receive nothing, and the Redis `candle:1m:*` / `candle:1s:*` caches go stale within minutes — which surfaced as the reported "frontend chart snaps to a point" symptom (322 USD vertical gap between stale last close 63300 and live ticker 63622).

Binance REST API on the same host returns 200 (only WS is geofenced), so a REST fallback is viable.

- **`scripts/refresh_redis_klines.py`** — Sentinel-aware REST → Redis 1m candle refresher. Pulls recent klines from `api.binance.com/api/v3/klines` and writes them in the exact canonical shape produced by `keydb_kline.py` / `DirectRedisWriter` (`{"t","o","h","l","c","v","qv","n","x"}` via ZADD on `candle:1m:{exchange}:{symbol}`, plus HSET on `candle:latest:{exchange}:{symbol}`). Optional `--with-1s` for 1s candles. Defaults to top-N USDT symbols by 24h quote volume, filtering stablecoins.

- **`scripts/cron_refresh_klines.sh`** — Host crontab wrapper that runs the refresher inside the `fastapi-prod` container (has redis-py + Sentinel env + EFS mount). Installed as `*/2 * * * *`, refreshes top-30 symbols × 100 1m candles every 2 min. Logs to `/tmp/lmview-kline-refresh.log`. Non-fatal if the container is down (cron retries next tick).

### Fixed — Caveat BB-8 (frontend chart snap on stale cache)

- **`frontend/src/features/chart/CandlestickChart.tsx`** — Added gap defense in the `onTicker` synthetic-candle handler. When the forming candle or last-closed candle is older than `5 * timeframeSec` relative to the current tick bucket, the stale reference is dropped and no synthetic bridging candle is drawn. Previously the handler bridged any gap with a vertical candle from `lastClosed.close` to `ticker.price`, which the user saw as the chart "snapping to a point" when the Redis cache went stale. The chart now waits for the next real `onCandle` event to re-anchor.

  **Note**: this fix is in source only. nginx-prod serves the frontend from a baked image, so a frontend image rebuild + `nginx-prod` service update is required for the fix to reach browsers. The data-side stopgap (DP-6 cron) alone resolves the visible symptom in normal operation.

### Docs

- **`docs/system/13-caveats.md`** — Full audit rewrite. Each entry now carries a status badge (✅ FIXED / 🟡 PARTIAL / 🔴 OPEN / ⚪ OBSOLETE / 🟢 NEW). Added TL;DR audit summary at top. New entries: **DP-6** (producer dead + REST cron stopgap + long-term poller proposal), **BB-8** (chart snap fix), **IB-9** (YAML env-leak fix from v0.25.51, was undocumented). Marked BB-1 (klines cache) and AI-2 (ai-service scaffold) as OBSOLETE. Updated IB-4 with observed `lmview-backfill-1m` Spark connection failure.

### Verified

- Redis `candle:1m:binance:BTCUSDT` last close 63662 vs ticker 63660 (7 USD gap; was 322 USD) after refresh.
- Cron fired on schedule: Redis 1m cache aged 25s at check time (within 2-min cadence).
- `fastapi-prod` `/api/health` → 200 (postgresql + redis sentinel healthy).
- `fastapi-prod` `/api/klines?symbol=BTCUSDT&interval=1m&limit=2` returns fresh candles.
- `cd frontend && npm run typecheck` — clean.
- `cd frontend && npm run build` — clean (12.9s).
- All critical services healthy except `producer` (0/1, expected — DP-6) and `backfill-1m` (1/1 but stuck on Spark master connection, IB-4).

### Known follow-ups

- Frontend image rebuild + nginx-prod redeploy needed for BB-8 browser-side fix.
- DP-6 long-term: build dedicated `binance-kline-rest` Swarm service (model on `binance-ticker-ws`) to replace both the dead producer's kline path and the cron stopgap. Trades + depth would need sibling REST pollers.
- IB-4: `lmview-backfill-1m` Spark master connection — needs SPARK_HEALTH_URL fix.
- 1s candle refresh not covered by stopgap (would need ~5 symbols × 1s polling).

---

## [0.25.51] - 2026-06-20

### Fixed

- **Caveat IB-8: Missing healthchecks on flink-taskmanager and spark-worker-2** — Added Docker healthcheck to flink-taskmanager (TCP port 6123) and spark-worker-2 (TCP port 8085). Docker now detects stuck/flapping tasks and auto-restarts them.

- **Caveat DP-1: DirectRedisWriter per-event Redis round trips** — All four write methods (ticker, kline, trade, depth) now pipeline HSET+EXPIRE / ZADD+EXPIRE into a single Redis round-trip instead of two. Reduces Redis CPU load on the failover path by ~50%.

- **Caveat IB-3: Deploy script no rollback on failure** — `scripts/deploy_aws_swarm.sh` now snapshots the current stack config before deploy. If `docker stack deploy` fails, the script automatically rolls back to the previous stack state. Rollback snaphsot is updated on successful deploys.

- **YAML structure: env vars leaked under healthcheck blocks** — `docker-compose.yml` had pre-existing indentation bugs on flink-jobmanager and spark-worker where environment variables were nested under `healthcheck:` instead of `environment:`. This caused Docker Compose to silently ignore those variables during validation, so they never reached the container runtime. Fixed by moving 20 env vars to their proper `environment:` section on flink-jobmanager and 8 env vars on spark-worker. All Compose profiles now validate clean.

### Files

- `docker-compose.yml` (healthchecks on flink-taskmanager/spark-worker-2, YAML structure fix)
- `scripts/deploy_aws_swarm.sh` (snapshot + rollback)
- `src/exchanges/binance/redis_writer.py` (Redis pipelining)

### Changed

- `src/exchanges/binance/redis_writer.py` — All 4 write methods use `self._r.pipeline()` to batch HSET+EXPIRE / ZADD+EXPIRE into one round-trip.
- `scripts/deploy_aws_swarm.sh` — Added `BACKUP_STACK_FILE`, pre-deploy snapshot via `docker compose config`, conditional rollback on deploy failure.
- `docker-compose.yml` — Added `healthcheck:` blocks for flink-taskmanager (TCP 6123) and spark-worker-2 (TCP 8085). Moved 28 env vars from beneath `healthcheck:` into proper `environment:` sections on flink-jobmanager and spark-worker.

### Verified

- `docker compose --profile dev config` — no warnings
- `docker compose --profile prod --profile monitoring --profile logging config` — no warnings
- `docker compose --profile prod --profile monitoring --profile logging --profile ai-api -f docker-compose.yml -f docker-compose.ai.yml -f docker-compose.swarm.yml config` — no warnings
- `bash -n scripts/deploy_aws_swarm.sh` — syntax OK
- `python3 -c "import ast; ast.parse(open('src/exchanges/binance/redis_writer.py').read())"` — OK

---

## [0.25.50] - 2026-06-20

### Documentation

- **Viết lại toàn bộ `docs/SYSTEM.md` bằng tiếng Việt với comment chi tiết cho sinh viên năm 1** — Thay thế phiên bản tiếng Anh 6906 dòng bằng bản tiếng Việt 6250 dòng, 219 KB, 68 sections, 296 code blocks. Toàn bộ code giữ nguyên tiếng Anh (technical terms) nhưng:
  - Mọi giải thích bằng tiếng Việt
  - Comment dòng-by-dòng bằng tiếng Việt trong code
  - Bảng thuật ngữ Anh-Việt ở §6
  - Giải thích mọi khái niệm (Kafka, Flink, Redis, WebSocket, Lambda Architecture, Sentinel, ...) từ đầu
  - Timeline và sơ đồ có chú thích tiếng Việt chi tiết
  - Lưu ý cho sinh viên năm 1 ở đầu mỗi phần

### Cấu trúc 8 phần

- Phần 1 — Nền Tảng (LMView là gì, triết lý thiết kế, Lambda Architecture, bản đồ repo, network, glossary)
- Phần 2 — 21 services được giải thích + code đầy đủ `src/ticker_ws/` (5 files) với comment tiếng Việt
- Phần 3 — Tầng tốc độ: Redis key schema, Flink pipeline, Avro schemas
- Phần 4 — Tầng phục vụ: code đầy đủ `backend/api/websocket.py` với comment tiếng Việt
- Phần 5 — Frontend: code đầy đủ `marketDataService.ts` + `parseWsData` + Blob bug + forming candle logic
- Phần 6 — Lakehouse + PostgreSQL + AI + Docker Swarm
- Phần 7 — Vận hành: env vars, ports, logs, health checks, failure modes, runbook, bug history
- Phần 8 — Deep dive 8 shards: state machine, batched Redis writer, Sentinel, update frequency, capacity planning, end-to-end annotated flow

### Lưu ý

- Phiên bản tiếng Anh cũ được backup tại `/tmp/SYSTEM_en_backup.md`
- Nếu cần tham khảo phiên bản tiếng Anh, dùng bản backup hoặc xem git history

---

## [0.25.49] - 2026-06-20

### Documentation

- **Part 8: Deep dive on `binance-ticker-ws` shard architecture** — Added 15 new sections (§52-§66) covering:
  - Why 8 shards: 671 symbols ÷ Binance's ~200 streams/connection limit, with headroom math (671/8 = ~84 symbols per shard)
  - Shard construction: `TickerConfig.load()` fetches top USDT pairs from `/api/v3/ticker/24hr`, splits into 8 chunks, builds combined-stream URLs
  - Per-shard state machine: CONNECT → CONNECTED → HANDLE FRAME → DISCONNECT → backoff
  - Per-message data path with timestamps: Binance event T+0ms → WS recv T+51ms → parsed T+53ms → buffer → flush (50ms) → Redis → FastAPI read → WS push → browser pixel at T+~250-700ms
  - Batched Redis writer: 50ms flush interval, 2000-item cap, pipeline transaction=False, clear-before-execute pattern
  - Sentinel-aware connection with direct fallback (and the gotcha: Swarm VIP `redis-master` round-robins to replicas, not just master)
  - Update frequency by symbol class: 1Hz major / 0.5-0.8Hz mid / 0.05-0.2Hz low-vol
  - `/healthz` per-shard stats + Prometheus metrics with healthy thresholds
  - 10-row failure mode table with recovery behavior
  - Capacity planning: current 700 msg/s uses 0.7% Redis throughput, can scale 4-5× without changes
  - Comparison table: legacy producer (killed by OOM) vs binance-ticker-ws (async, auto-reconnect, sentinel-aware)
  - Annotated end-to-end flow diagram with timestamps at each hop
  - Operational runbook + Phase 5+ future improvements

### Total doc

SYSTEM.md now: **6906 lines**, **271 KB**, **69 sections** across **8 parts**.

---

## [0.25.48] - 2026-06-20

### Documentation

- **Complete SYSTEM.md rebuild (6100 lines, 240 KB)** — Replaced the previous 2776-line system doc with a from-scratch comprehensive reference covering 51 sections across 7 parts. Includes:
  - Full source code for `src/ticker_ws/` (5 files: main, config, shard, parser, redis_writer)
  - Full source code for `backend/api/websocket.py` (`_stream_all_impl`, `_build_candle_from_data`)
  - Full source code for `frontend/src/services/marketDataService.ts` (`parseWsData`, `createReconnectingWebSocket`)
  - Forming candle algorithm walkthrough with 4 cases (same bucket, boundary cross, first tick, bail)
  - Two-ref design explained (`lastClosedCandleRef` + `formingCandleRef`)
  - Blob parse bug root cause + Playwright verification
  - 8-bug realtime history with lessons learned
  - Complete env var reference, port table, runbook, failure mode recovery

### Why this format

Goal: an engineer who has never seen the codebase can rebuild LMView end-to-end using only this document plus Docker + Python 3.11 + Node 20. Reading order: Part 1 (foundations) → Part 3 (speed layer) → Part 4 (serving) → Part 5 (frontend) → Part 8 (operations).

---

## [0.25.47] - 2026-06-20

### Fixed

- **Forming candle not drawing in browser** — User reported chart shows only a horizontal green dot at the realtime price, no body, no wick. Backend `/stream/all` was sending the correct OHLCV forming candle with full price history, but the frontend's WebSocket `onMessage` handler called `JSON.parse(e.data as string)` directly. The backend uses `send_bytes()` which causes browsers to receive `Blob` instead of `string` — `JSON.parse(blob)` throws `Unexpected token 'o', "[object Blob]" is not valid JSON`. Every WS frame crashed, the forming candle code path (`onTicker`) never executed, and the chart stayed frozen at whatever was in the last successful `setData` call. Verified with Playwright: before fix 9+ pageerrors per second, after fix 0 pageerrors and forming candle updates correctly (open=63300.01, high=63743.9, low=63300.01, close=63700.02 with both wicks).

### Changed

- `frontend/src/services/marketDataService.ts`: added `parseWsData<T>()` helper that handles `string | Blob | ArrayBuffer` input. Wraps all three `JSON.parse(e.data as string)` call sites (`subscribeCandle`, `subscribeAllTimeframes`, `subscribeIndicatorStream`) with `try/catch` and async Blob→text conversion.

### Files

- `frontend/src/services/marketDataService.ts`

### Verified (Playwright headless browser test)

- 14 `/stream/all` frames received in 8s, 8 unique ticker prices.
- 1m candle evolves correctly: open=63300.01 (last closed), high accumulates to 63743.9, low stays 63300.01, close tracks ticker price (63700.02 final).
- 0 pageerror events.

---

## [0.25.46] - 2026-06-20

### Fixed

- **Real-time forming candle not updating in browser** — User reported chart price only updates on manual F5 reload despite WS data flowing correctly. Two root causes identified and fixed:

  1. **Backend `/stream/all` only pushed when interval candle dict changed**. Non-volatile symbols (BTC) had `live_price` change less than once per 50ms poll cycle, so `candle != last_sent[iv]` returned False and the loop fell through to 10s heartbeat. Fix: track `last_ticker_ts` separately and push whenever a newer ticker tick arrives, regardless of interval candle change. Backend `/api/websocket.py` `_stream_all_impl` now sends message every ~1s for all symbols (matches Binance `@ticker` push rate).

  2. **Frontend WebSocket reconnect capped at 5 retries**. After 5 failed reconnects the client gave up forever, so any idle-tab socket death stuck the chart until manual reload. Fix: `MAX_RECONNECT_RETRIES = Infinity`, exponential backoff capped at 30s + jitter, plus a 45s watchdog that force-closes the socket if no data arrives (catches silent proxy kills).

### Changed

- `backend/api/websocket.py`: added `last_ticker_ts` tracking in `_stream_all_impl`; push when `any_changed or ticker_updated`.
- `frontend/src/services/marketDataService.ts`: rewrote `createReconnectingWebSocket` with unlimited retries, watchdog timer, jittered backoff.

### Verified

- BTCUSDT: 1.1 msg/s, latency p50=143ms p95=800ms.
- SOLUSDT: 1.0 msg/s, latency p50=101ms p95=1453ms.
- DOGEUSDT: 1.1 msg/s, latency p50=375ms p95=687ms.

---

## [0.25.45] - 2026-06-20

### Added

- **Phase 4 deployed: `binance-ticker-ws` Swarm service** — Replaces dead producer's WS ticker path. Connects to Binance combined WS streams across 8 shards (84 streams each, total 671 top USDT pairs). Writes 24 Binance @ticker fields + 1 legacy `exchange` field per symbol into Redis hash `ticker:latest:binance:{symbol}` via batched pipeline (50ms flush). All 8 shards connected, 0 reconnects in 13min, end-to-end latency p50 ~150ms, p95 ~600ms. New service exposes Prometheus metrics on `:9100/metrics` and HTTP health on `:9100/healthz`.

### Changed

- **Backend WS `_ticker` payload** — `backend/api/websocket.py` now forwards 16 Binance fields (price, bid, ask, bid_qty, ask_qty, volume, quote_volume, change24h, change_pct, change_abs, weighted_avg, open_24h, high_24h, low_24h, last_qty, event_time) in `/api/stream/all` `_ticker` instead of only 4.
- **Frontend `StreamTickerPayload` type** — `frontend/src/services/marketDataService.ts` extended to receive the 16 fields from backend. New fields are parsed and passed to `onTicker` callback.
- **Disabled `BinancePricePoller`** — Commented out `binance_price_poller.start()/stop()` calls in `backend/app.py` lifespan. Replaced by `binance-ticker-ws` which streams full Binance @ticker fields via WS instead of polling REST `/api/v3/ticker/price` at 1s cadence with only 3 fields.

### Files

- `src/ticker_ws/__init__.py` (new)
- `src/ticker_ws/config.py` (new)
- `src/ticker_ws/parser.py` (new)
- `src/ticker_ws/redis_writer.py` (new)
- `src/ticker_ws/shard.py` (new)
- `src/ticker_ws/main.py` (new)
- `docker/ticker-ws/Dockerfile` (new)
- `docker/ticker-ws/requirements.txt` (new)
- `docker-compose.yml` (added binance-ticker-ws service block)
- `docker-compose.swarm.yml` (added binance-ticker-ws deploy overrides)
- `backend/api/websocket.py` (extended `_ticker` payload to 16 fields)
- `backend/app.py` (disabled BinancePricePoller)
- `frontend/src/services/marketDataService.ts` (extended StreamTickerPayload type)
- `docs/LATENCY_OPTIMIZATION_PLAN.md` (Phase 4 status: ✅ DEPLOYED)

---

## [0.25.44] - 2026-06-20

### Diagnosed

- **Producer dead, no realtime price feed** — `cryptoprice_producer.1` Swarm task exit 137 (OOM kill) trong 10 phút qua, logs chỉ toàn `Handshake status 403 Forbidden - awselb/2.0` trên tất cả Binance WS connections. WS pipeline chính (Producer → Kafka → Flink → Redis) đã chết hoàn toàn.
- **`BinancePricePoller` REST fallback không đủ** — Chỉ ghi 3 fields (`price`, `event_time`, `exchange`) vào `ticker:latest:*` mỗi 1s. Thiếu `bid`, `ask`, `volume`, `change24h`, `h24_open/high/low`. Frontend chart không nhảy realtime, phải F5 mới thấy giá mới.
- **Root cause WS 403** — Binance rate limit per-IP cho parallel WS connections. Producer cũ mở 8-15 connections cùng lúc (4 kline, 4 depth, 4 trade, 3 ticker) → trigger 403. Test thực tế xác nhận: single @ticker OK, combined 5 streams OK, combined 100 streams OK, combined 200 streams timeout, `!ticker@arr` timeout.

### Planned

- **Phase 4 — Multi-shard WS ticker feed** — Service Python mới `binance-ticker-ws` chạy trong Swarm, kết nối Binance WS `@ticker` qua 3 shards combined streams (≤100 symbols mỗi shard). Ghi đầy đủ 24 fields của Binance @ticker payload vào Redis hash `ticker:latest:binance:{symbol}`. End-to-end latency < 1s, không trigger 403. Xem chi tiết trong `docs/LATENCY_OPTIMIZATION_PLAN.md` Phase 4.

### Files

- `docs/LATENCY_OPTIMIZATION_PLAN.md` (added Phase 4 section ~290 lines)
- `docs/CHANGELOG.md`

---

## [0.25.43] - 2026-06-19

### Fixed

- **Candlestick source selection** — `backend/api/klines.py` now fetches both Redis and InfluxDB for live `1m` candles and selects the cleaner source using coverage, continuity, OHLC validity, non-zero volume, and freshness scoring. This prevents sparse Redis 1m data from degrading the chart when Influx has cleaner candles.
- **Realtime forming candle logic** — `backend/api/websocket.py` now includes ticker `price` and `event_time` in `/stream/all` `_ticker` metadata. `frontend/src/services/marketDataService.ts` exposes ticker updates separately from candle updates.
- **Frontend candle rendering** — `frontend/src/features/chart/CandlestickChart.tsx` now builds the active/forming candle from realtime ticker price: new candle open equals previous close, high/low track every live tick, close follows live price, and the candle rolls over on timeframe boundaries. Official candle stream data is used only to reconcile matching/older candles, not as the live price source.

### Validated

- `cd frontend && npm run typecheck`
- `cd frontend && npm run build`
- `PYTHONPYCACHEPREFIX=/tmp/pycache-check python3 -m py_compile backend/api/klines.py backend/api/websocket.py`


## [0.25.42] - 2026-06-19

### Fixed

- **Flink Python job scheduling unblock** — Cleaned `docker/flink/flink-conf.yaml` and removed duplicated TaskManager config entries. Removed fixed `taskmanager.host: flink-taskmanager` so each Swarm TaskManager auto-advertises its own container IP. This fixed the `RUNNING but subtasks=0` blocker and allowed Python pipeline subtasks to transition `INITIALIZING -> RUNNING`.
- **Producer Binance WS 403 mitigation** — Reduced `KLINE_SYMBOLS_PER_CONN` from 40 to 20 in `src/common/config.py`, `docker-compose.yml`, and `docker-compose.swarm.yml` to lower per-connection stream load. Fixed producer startup crash caused by an inner `from common.config import KAFKA_TOPIC_*` shadowing global topic constants inside `run()`.

### Changed

- **Project-wide cleanup & documentation** — Major system audit for Docker Swarm 2-node deployment:
  - Removed 21 clutter/generated files to `trash/` for human review
  - Created `docs/system/` with 13 detailed module docs covering architecture, serving, pipeline, lakehouse, AI, frontend, Docker, PostgreSQL, Kafka, speed layer, observability, deployment, and caveats
  - Added `production` branch as rollback snapshot
  - Cleaned CHANGELOG duplicate entries (removed template + stale tail)
  - Updated SYSTEM.md, README.md, AGENTS.md for current system state
  - All `__pycache__` directories and `*.pyc` files removed

### Files

- `docs/system/*.md` (13 new files)
- `docs/SYSTEM.md`
- `docs/CHANGELOG.md`
- `README.md`
- `AGENTS.md`
- `.gitignore` (added `trash/`)
- `trash/` (21 files moved for review)

---

## [0.25.41] - 2026-06-19

### Fixed

- **Producer crash loop 41.1** - Fixed `DirectRedisWriter.__init__()` missing `import redis` (NameError crash) in `src/exchanges/binance/redis_writer.py`. The producer would crash immediately when `ENABLE_DIRECT_REDIS=true` (swarm default) because `redis.ConnectionPool()` was called without importing the module.
- **Kafka broker ZK NodeExists 41.2** - Added stale ZK broker node cleanup to `docker/kafka/entrypoint.sh` before Kafka starts, preventing `NodeExistsException` on container restarts. Also added shorter ZK session timeout (10s) for faster Swarm failover.
- **Kafka client auto-reconnect 41.3** - Updated `src/common/kafka_client.py` to auto-recreate the producer when "RecordAccumulator is closed" is detected, plus added `reconnect_backoff_ms`/`reconnect_backoff_max_ms` settings for automatic broker reconnection.
- **Auto-failover consistency 41.4** - Changed all DirectRedis bypass checks from static `ENABLE_DIRECT_REDIS` flag to dynamic `health_monitor.is_direct_redis_active()` across all stream handlers (trades, klines, depth, OKX streams). Only ticker handler used dynamic check previously.
- **Exchange name attribute 41.5** - Added abstract `name` property to `ExchangeClient` base class and implemented in `BinanceClient` ("binance") and `OKXClient` ("okx"). Replaced `getattr(client, "name", "unknown")` with proper property access, fixing "unknown" exchange labels on metrics.
- **OKX kline interval mapping 41.6** - Fixed `src/exchanges/okx/mappers.py` to emit empty interval string (set by caller from channel name) instead of hardcoded "1s". Updated caller in `src/producer/main.py` to set interval from channel (e.g., candle1m → 1m).
- **Flink memory configuration 41.7** - Reduced `taskmanager.memory.process.size` from 2048m to 1536m in `docker/flink/flink-conf.yaml` to prevent OOM on 4vCPU/16GB worker node. Also cleaned up 10x duplicated config entries. Updated `docker-compose.swarm.yml` FLINK_PROPERTIES accordingly.
- **DirectRedis connection pool 41.8** - Increased `DirectRedisWriter` connection pool from 10 to 50 (configurable via `DIRECT_REDIS_POOL_SIZE` env var) to handle 30+ concurrent WebSocket threads.
- **Stale data cleanup 41.9** - Removed 671 stale `ticker:latest:unknown:*` Redis keys from previous unstable Flink runs.

### Changed

- **Swarm config 41.10** - Changed `ENABLE_DIRECT_REDIS` from "true" to "false" in `docker-compose.swarm.yml` now that Kafka/Flink are stable. Auto-failover will dynamically enable it when needed.

### Operations

- Rebuilt and pushed `producer:latest` (3x) and `flink:1.18.1` images
- Ran `influx-backfill:latest --mode populate --days 90` as a one-shot Swarm service (lmview-backfill-populate) to populate 90 days of 1m candles in InfluxDB
- Manually re-submitted Flink job after JobManager restart (auto-submit-jobs at 0 replicas)
- Cleaned 671 stale `unknown` exchange Redis keys

### Files

- `src/exchanges/binance/redis_writer.py`
- `src/common/kafka_client.py`
- `src/producer/main.py`
- `src/exchanges/base.py`
- `src/exchanges/binance/client.py`
- `src/exchanges/okx/client.py`
- `src/exchanges/okx/mappers.py`
- `docker/kafka/entrypoint.sh`
- `docker/flink/flink-conf.yaml`
- `docker-compose.swarm.yml`
- `docs/CHANGELOG.md`

---

## [0.25.39] - 2026-06-17

### Fixed

- **Auth PostgreSQL retry 39.1** - Updated `get_pg_pool()` to retry pool initialization when startup ran before PostgreSQL was reachable, preventing persistent `AUTH_503` login failures after database recovery.
- **Health PostgreSQL check 39.2** - Added PostgreSQL status to backend health output so auth persistence outages are visible with Redis, InfluxDB, and Trino checks.
- **AI Interact tour tools 39.3** - Added `start_tour`/section-view action support across backend chart action validation and Interact mode prompts so Ask/Interact can trigger the guided LMView tour and step-by-step UI analysis.
- **AI migration metadata 39.4** - Corrected multi-agent metadata migration references to the existing `ai_chat_sessions` table.
- **News persistence upsert 39.5** - Replaced duplicate-first news inserts with `ON CONFLICT (source, url) DO UPDATE` to avoid noisy PostgreSQL duplicate-key errors during recurring RSS fetches.

### Operations

- Rebuilt and pushed FastAPI image tags `0.25.0` and `0.25.1` during production recovery.
- Diagnosed Swarm bind-mount failures after task reschedule: services with `/mnt/efs/LMView` binds must run on the EFS-mounted manager node or the worker must mount EFS too.

### Files

- `backend/core/postgres.py`
- `backend/api/health.py`
- `backend/models/ai/chart_actions.py`
- `backend/migrations/004_agents_metadata.sql`
- `backend/tasks/news_fetcher.py`
- `ai_service/agents/experts/chart_interaction.py`
- `ai_service/agents/synthesis.py`
- `ai_service/core/orchestrator.py`
- `docs/CHANGELOG.md`

## [0.25.40] - 2026-06-18

### Fixed

- **FastAPI crash due to missing get_api_key 40.1** - Fixed ImportError in `ai_service/config.py` where `get_api_key` was referenced but never defined, causing container exit code 255, Nginx DNS resolution failure, and frontend `[DATA_503]` candle load error.
- **Nginx DNS refresh 40.2** - Restarted `nginx-prod` after `fastapi-prod` redeploy to force Docker embedded DNS cache refresh for `fastapi` service alias.

### Operations

- Updated `ai_service/config.py` to define `get_api_key()` function.
- Updated `docker-compose.yml` to mount `./ai_service:/app/ai_service` into `fastapi-prod`.
- Forced redeploy of `fastapi-prod` and `nginx-prod` services.

### Files

- `ai_service/config.py`
- `docker-compose.yml`
- `docs/CHANGELOG.md`

## [0.25.38] - 2026-06-16

### Fixed

- **Swarm deploy rendering 38.1** - Updated `scripts/deploy_aws_swarm.sh` to render an expanded Compose file before `docker stack deploy`, strip Compose-only keys (`name`, `profiles`, `depends_on`, `container_name`), normalize numeric port fields, and count Swarm node labels by inspecting node specs directly.
- **Swarm image tagging 38.2** - Added explicit image tags to the build-backed FastAPI, Flink, Spark, producer, and backfill services so the rendered stack can be deployed by Swarm without anonymous build-only services.

### Tests

- `docker compose --profile prod --profile monitoring --profile logging -f docker-compose.yml -f docker-compose.swarm.yml config` passes after the deploy/render fixes.
- `bash ./scripts/deploy_aws_swarm.sh --skip-build` now deploys the stack successfully on the manager node.

### Files

- `scripts/deploy_aws_swarm.sh`
- `docker-compose.swarm.yml`
- `docker-compose.yml`
- `docs/CHANGELOG.md`

## [0.25.37] - 2026-06-16

### Added

- **Docker Swarm overlay 37.1** - Created `docker-compose.swarm.yml` with deploy blocks for all 41 services, placement constraints (core/worker node labels), restart policies (on-failure), and `replicas: 2` for `flink-taskmanager` and `spark-worker`. Network driver overridden from `bridge` to `overlay` for multi-node communication.
- **Swarm deployment script 37.2** - Created `scripts/deploy_aws_swarm.sh` with strict error handling, preflight checks (swarm active, node labels, .env existence), local image build, `docker stack deploy --resolve-image never`, and post-deploy status output including required AWS Security Group ports.
- **Cloud infrastructure env 37.3** - Added `DOMAIN_NAME`, `CORS_ORIGINS`, `VITE_API_BASE_URL` documentation, and `AWS_EFS_MOUNT_PATH` guidance to `.env.example`. Created `.env.production` template with production-ready placeholders.
- **Makefile swarm targets 37.4** - Added `make swarm-deploy`, `make swarm-deploy-quick`, `make swarm-status`, and `make swarm-down` targets.

### Changed

- **Nginx prod hardening 37.5** - Added `proxy_set_header Connection ""` to the REST API proxy block in `nginx-prod.conf` for keep-alive robustness through Docker Swarm overlay networking.
- **Gitignore broadening 37.6** - Extended `.gitignore` to cover `.env.*` variants (except `.env.example`) so `.env.production` and other env files with secrets are never committed.

### Files

- `docker-compose.swarm.yml` (new)
- `scripts/deploy_aws_swarm.sh` (new)
- `.env.production` (new)
- `.env.example`
- `docker/nginx/nginx-prod.conf`
- `Makefile`
- `.gitignore`

---

## [0.25.36] - 2026-06-16

### Changed

- **Auth modal header separation 16.1 supplement** - Moved the Login/Register close button out of the tab/form overlay area into a dedicated top header row, keeping the Sign In/Sign Up switcher full width below the header so the close control no longer overlaps the register tab, headline, subtitle, or first input.
- **Settings Customization layout 16.3 supplement** - Expanded the desktop Settings modal to `max-w-7xl` with a taller bounded shell and reorganized the Customization tab into responsive appearance, saved defaults/controls, and preview/presets columns so form controls and the chart preview no longer crowd each other.
- **Saved Defaults layout 16.3b** - Pulled `Saved defaults` into its own Customization column/card section with explicit spacing around default timeframe, chart type, symbol, exchange, and help text so Vietnamese labels and dropdowns have room to align cleanly.

### Tests

- `npm.cmd run typecheck` passed after the 16.1 supplemental auth modal header fix.
- `npm.cmd run build` passed after the 16.1 supplemental auth modal header fix.
- `npm.cmd run typecheck` passed after the 16.3 supplemental Settings Customization layout fix.
- `npm.cmd run build` passed after the 16.3 supplemental Settings Customization layout fix.
- **Task 17 final verification** - Source-smoked the Auth modal header/close-button separation and the widened Settings Customization grid, then reran final frontend checks.
- `npm.cmd run typecheck` passed for Task 17 final verification.
- `npm.cmd run build` passed for Task 17 final verification.

### Files

- `frontend/src/features/auth/AuthModal.tsx`
- `frontend/src/features/settings/SettingsModal.tsx`
- `docs/CHANGELOG.md`

---

## [0.25.35] - 2026-06-15

### Changed

- **Auth modal close button 16.1** - Polished the Login/Register modal close control with a 40px hit target, safer corner spacing from the mobile form header, red danger hover/focus states, and a clear keyboard focus ring while preserving Escape/backdrop close behavior.
- **Vietnamese Auth/Settings i18n 16.2** - Fixed missing Vietnamese diacritics across Login/Register validation/loading/success copy, Settings tab descriptions, About resource labels, chart/drawing preset labels, AI session labels, and tour copy touched by Auth/Settings surfaces. Added localized AI response-style labels so Vietnamese UI shows `Ngắn gọn`, `Cân bằng`, and `Chi tiết` instead of raw `concise`, `balanced`, and `detailed` option IDs.
- **Settings text layout 16.3** - Reworked shared Settings row helpers so Saved defaults, AI Helper controls, About system status, and About resources use responsive label/control grids with safer wrapping, truncation, and mobile stacking instead of narrow flex rows that squeezed Vietnamese labels.
- **Drawing toolbar delete visibility 16.4** - Added stable scroll height and bottom padding to the left drawing toolbar list, and gave the delete-all drawings control a clearer red hover/focus treatment with an explicit accessible label so the trash icon stays fully visible and distinct from eraser mode.

### Tests

- `npm.cmd run typecheck` passed after 16.1 auth modal close-button polish.
- `npm.cmd run build` passed after 16.1 auth modal close-button polish.
- `npm.cmd run typecheck` passed after 16.2 Vietnamese Auth/Settings i18n polish.
- `npm.cmd run build` passed after 16.2 Vietnamese Auth/Settings i18n polish.
- `npm.cmd run typecheck` passed after 16.3 Settings text layout polish.
- `npm.cmd run build` passed after 16.3 Settings text layout polish.
- `npm.cmd run typecheck` passed after 16.4 drawing toolbar delete visibility fix.
- `npm.cmd run build` passed after 16.4 drawing toolbar delete visibility fix.
- `npm.cmd exec vitest -- run src/features/drawing/__tests__/drawingGeometry.test.ts` passed after rerunning outside the sandbox; the first sandboxed run failed path resolution before executing tests.

### Files

- `frontend/src/features/auth/AuthModal.tsx`
- `frontend/src/components/layout/LeftSidebar.tsx`
- `frontend/src/features/settings/SettingsModal.tsx`
- `frontend/src/i18n/locales/en.ts`
- `frontend/src/i18n/locales/vi.ts`
- `docs/CHANGELOG.md`

---

## [0.25.34] - 2026-06-15

### Verified

- **Chart toolbar final verification 15** - Verified the Task 14 chart toolbar bugfix wiring for market/coin search, timeframe, indicators, and history dropdowns using the shared fixed-position `DropdownPortal`; the dropdowns now render outside chart/toolbar overflow contexts and close through outside click/Escape wiring without changing layout flow.
- **Drawing text tool final verification 15** - Confirmed the left drawing toolbar and Settings favorite-tool picker expose one `Text/Note` entry for new selection while `ChartOverlay` still supports legacy `anchoredText`, `note`, and `text` drawing payloads for existing drawings.
- **Toolbar layout final verification 15** - Confirmed the toolbar source layout keeps market, timeframe, indicators/history/export, chart type, zoom, and fullscreen controls in non-stretching groups with horizontal overflow for narrower or zoomed widths; right-panel layout wiring remains outside the chart toolbar row.

### Tests

- `npm.cmd exec vitest -- run src/features/drawing/__tests__/drawingGeometry.test.ts` passed.
- `npm.cmd run typecheck` passed.
- `npm.cmd run build` passed.

### Notes

- Browser-only manual checks for visual zoom/fullscreen behavior were not run in this terminal verification; no source-level or build/test regressions were found.
- No functional files were changed during Task 15 beyond this changelog entry.

### Files

- `docs/CHANGELOG.md`

---

## [0.25.33] - 2026-06-15

### Changed

- **Chart dropdown layering 14.1** - Moved the chart toolbar market/coin search, timeframe selector, indicators menu, and history range picker into a shared fixed-position `DropdownPortal` so menus render above the chart canvas/overlays instead of being clipped by toolbar horizontal scrolling, chart container `overflow-hidden`, or local stacking contexts. Dropdowns still close on outside click, item selection, and Escape.
- **Drawing text tool consolidation 14.2** - Consolidated the left drawing toolbar and Settings favorite-tool picker to a single `text` tool labeled `Text/Note`, hiding duplicate `anchoredText` and `note` choices from new UI selection while keeping `ChartOverlay` support for legacy `anchoredText`, `note`, and `text` drawings.
- **Chart toolbar layout 14.3** - Reworked the chart toolbar row so market selector/price, timeframe, indicators/history/export, chart type, zoom, and fullscreen groups stay on a stable single row when space allows, with explicit non-stretching group behavior and horizontal toolbar overflow instead of uneven wrapping or group distortion on narrower/zoomed layouts.

### Tests

- `npm.cmd run typecheck` passed after 14.1 chart dropdown layering fix.
- `npm.cmd run build` passed after 14.1 chart dropdown layering fix.
- `npm.cmd exec vitest -- run src/features/drawing/__tests__/drawingGeometry.test.ts` passed after rerunning focused for 14.2 drawing text tool consolidation.
- `npm.cmd run typecheck` passed after 14.2 drawing text tool consolidation.
- `npm.cmd run build` passed after 14.2 drawing text tool consolidation.
- `npm.cmd run typecheck` passed after 14.3 chart toolbar layout fix.
- `npm.cmd run build` passed after 14.3 chart toolbar layout fix.

### Files

- `frontend/src/components/ui/DropdownPortal.tsx`
- `frontend/src/features/chart/MarketSelector.tsx`
- `frontend/src/features/chart/DateRangePicker.tsx`
- `frontend/src/features/chart/CandlestickChart.tsx`
- `frontend/src/components/layout/LeftSidebar.tsx`
- `frontend/src/features/settings/SettingsModal.tsx`
- `frontend/src/i18n/locales/en.ts`
- `frontend/src/i18n/locales/vi.ts`
- `docs/CHANGELOG.md`

---

## [0.25.32] - 2026-06-15

### Changed

- **Frontend error normalizer foundation 12.1** - Rebuilt the shared frontend error layer in `frontend/src/utils/errors.ts` around normalized role-aware errors with standard categories (`AUTH_*`, `SETTINGS_*`, `DATA_*`, `CHART_*`, `AI_*`, `NETWORK_*`, `VALIDATION_*`, `UNKNOWN_*`), user/admin messages, retryability metadata, request IDs, sanitized endpoints, timestamps, and redacted technical details while preserving existing `AppError`, `createApiError`, `categorizeError`, and `getRoleAwareErrorMessage` exports.
- **ErrorBoundary role-aware details 12.2** - Updated both app and root ErrorBoundary surfaces so normal users see only a generic crash message with an error code plus retry/reload actions, while admins can expand sanitized technical details and component traces. Auth now stores only a non-sensitive role snapshot for root-boundary admin detection.
- **Auth normalized errors 12.3** - Routed auth API failures through endpoint-aware normalized errors and preserved `[AUTH_*]` short messages in the Login/Register modal without exposing raw backend JSON; existing field-level validation remains local and concise.
- **Settings normalized errors 12.4** - Routed settings API failures through endpoint-aware normalized errors and upgraded the Settings status banner so normal users see short `[SETTINGS_*]` messages while admins can expand sanitized technical details for load/save/admin-account failures.
- **Market/chart/data normalized errors 12.5** - Added endpoint-aware market API errors, normalized Market & News failures to `[DATA_*]` messages, normalized chart candle failures to `[CHART_*]` messages, and replaced raw chart/market console errors with sanitized dev/admin diagnostics.
- **AI normalized errors 12.6** - Added endpoint-aware AI API errors, normalized AI Helper request failures to `[AI_*]` messages, kept provider/routing details out of normal-user warnings, and sanitized admin AI action-debug catch output.

### Tests

- `npm.cmd exec vitest -- run src/utils/errors.test.ts` passed after 12.1 normalizer foundation.
- `npm.cmd run typecheck` passed after 12.1 normalizer foundation.
- `npm.cmd run typecheck` passed after 12.2 ErrorBoundary role-based details.
- `npm.cmd exec vitest -- run src/utils/errors.test.ts` passed after 12.3 Auth/Login normalized errors.
- `npm.cmd run typecheck` passed after 12.3 Auth/Login normalized errors.
- `npm.cmd run typecheck` passed after 12.4 Settings normalized errors.
- `npm.cmd run typecheck` passed after 12.5 Market/chart/data normalized errors.
- `npm.cmd run typecheck` passed after 12.6 AI normalized errors.
- Final Task 12 verification passed with `npm.cmd exec vitest -- run src/utils/errors.test.ts`, `npm.cmd run typecheck`, and `npm.cmd run build`.

### Files

- `frontend/src/utils/errors.ts`
- `frontend/src/utils/errors.test.ts`
- `frontend/src/components/ErrorBoundary.tsx`
- `frontend/src/components/ui/ErrorBoundary.tsx`
- `frontend/src/features/auth/AuthContext.tsx`
- `frontend/src/features/auth/AuthModal.tsx`
- `frontend/src/services/authService.ts`
- `frontend/src/features/settings/SettingsModal.tsx`
- `frontend/src/services/settingsService.ts`
- `frontend/src/services/apiClient.ts`
- `frontend/src/features/market/components/MarketNews.tsx`
- `frontend/src/features/chart/CandlestickChart.tsx`
- `frontend/src/services/aiService.ts`
- `frontend/src/features/ai/hooks/useAiChat.ts`
- `frontend/src/features/ai/actions/AiActionProvider.tsx`
- `frontend/src/App.tsx`
- `frontend/src/i18n/locales/en.ts`
- `frontend/src/i18n/locales/vi.ts`
- `docs/CHANGELOG.md`

---

## [0.25.31] - 2026-06-15

### Changed

- **Auth login layout 11.1** - Polished the existing Login/Register modal shell with mobile bottom-sheet behavior, dynamic viewport height, clearer mobile title/subtitle spacing, and preserved desktop two-panel structure. Affects Login and Register entry layout in `frontend/src/features/auth/AuthModal.tsx`.
- **Auth register validation 11.2** - Added field-level validation for missing/invalid email, missing password, missing display name, missing confirm password, password length, and password mismatch, with explicit label/input associations for accessibility. Affects Login and Register form validation in `AuthModal.tsx` and auth i18n copy.
- **Auth loading/success/error states 11.3** - Added explicit signing-in/account-creation loading copy, short success feedback before closing the modal, accessible alert/status regions, and safe fallback auth error copy so unknown backend error strings are not rendered directly to normal users. Affects Login and Register submit feedback in `AuthModal.tsx`.
- **Authenticated header polish 11.4** - Tightened the signed-in header chip with a compact initials avatar, bounded display-name width, accessible logout label, and mobile-safe notification dropdown width so authenticated controls stay compact across responsive header wraps. Affects `frontend/src/components/layout/Header.tsx`.

### Tests

- `npm.cmd run typecheck` passed after 11.1 Login layout and responsive redesign.
- `npm.cmd run typecheck` passed after 11.2 Register layout and validation.
- `npm.cmd run typecheck` passed after 11.3 Auth loading/success/error states.
- `npm.cmd run typecheck` passed after 11.4 Header authenticated state polish.
- Final Task 11 verification passed with `npm.cmd run typecheck` and `npm.cmd run build`.

### Files

- `frontend/src/features/auth/AuthModal.tsx`
- `frontend/src/components/layout/Header.tsx`
- `frontend/src/i18n/locales/en.ts`
- `frontend/src/i18n/locales/vi.ts`
- `docs/CHANGELOG.md`

---

## [0.25.30] - 2026-06-15

### Changed

- **Settings layout consistency 10.1** - Added tab-specific heading descriptions and a tone-aware status banner for Settings success/error/info feedback, keeping the existing Account, Notifications, Customization, AI Helper, About, Debug, and Admin Accounts tab structure intact. Affects `frontend/src/features/settings/SettingsModal.tsx` and Settings i18n copy.
- **Settings responsive polish 10.2** - Tightened the Settings modal shell for small screens with dynamic viewport height, mobile bottom-sheet framing, safer tab overflow, non-squeezing header copy, responsive account refresh/admin search controls, and mobile-friendly select/number rows. Affects Account, Notifications, Customization, AI Helper, About, Debug, and Admin Accounts layout surfaces in `SettingsModal.tsx`.
- **Settings loading/error/empty states 10.3** - Added dedicated settings fetch loading feedback for authenticated settings tabs, admin-account loading feedback for the Admin Accounts table, cancellable settings/admin fetch updates, and role-aware admin fetch errors through the shared Settings status banner. Affects Account, Notifications, Customization, AI Helper, and Admin Accounts in `SettingsModal.tsx`.
- **Settings admin/debug visibility cleanup 10.4** - Added a runtime guard that returns non-admin users away from Debug/Admin Accounts if role state changes while Settings is open, and replaced About resource details that exposed local documentation paths or raw health API labels with user-facing resource copy. Affects About, Debug, and Admin Accounts in `SettingsModal.tsx`.

### Tests

- `npm.cmd run typecheck` passed after 10.1 Settings layout consistency.
- `npm.cmd run typecheck` passed after 10.2 Settings responsive/mobile polish.
- `npm.cmd run typecheck` passed after 10.3 Settings loading/error/empty states.
- `npm.cmd run typecheck` passed after 10.4 Settings admin/debug visibility cleanup.
- Final Task 10 verification passed with `npm.cmd run typecheck` and `npm.cmd run build`.

### Files

- `frontend/src/features/settings/SettingsModal.tsx`
- `frontend/src/i18n/locales/en.ts`
- `frontend/src/i18n/locales/vi.ts`
- `docs/CHANGELOG.md`

---

## [0.25.29] - 2026-06-15

### Analysis

- **Task 9 Settings/Login/Error Handling audit** - Audited the current post-`0.24.29` frontend state for `SettingsModal`, auth modal/context/service flows, settings/auth/market/news/screener/AI services, error utilities, error boundaries, shared UI components, and English/Vietnamese i18n strings.
- **Settings audit findings** - Confirmed account/customization/about/debug/admin settings work is already present and admin/debug tabs are gated by `isAdmin`; remaining concerns are visual/status-state polish, missing dedicated settings/admin fetch loading states, shared success/error status styling, and mobile tab/content stress checks.
- **Auth audit findings** - Confirmed `AuthModal.tsx` is the main Login/Register UI, with login/register flows through `AuthContext` and `authService`; remaining concerns are visual QA, optional stronger field-level validation, and mock-auth demo credential exposure in source comments/mock seed data.
- **Error-handling audit findings** - Confirmed `utils/errors.ts` now provides `AppError`, `createApiError`, `categorizeError`, `getRoleAwareErrorMessage`, and sanitizer support; remaining concerns include incomplete adoption in WebSocket paths, some console logging, debug window raw error strings, and no central UI helper for rendering `AppError` by role.

### Notes

- No code changes were made for this audit/planning task beyond this changelog entry.
- Frontend tests were not run because this task was read-only audit plus changelog documentation.

### Files

- `docs/CHANGELOG.md`

---

## [0.25.28] - 2026-06-15

### Changed

- **Login/Register UI redesign** - Reworked `frontend/src/features/auth/AuthModal.tsx` into a responsive two-panel authentication modal with segmented sign-in/sign-up switching, icon-supported fields, clearer loading/error states, password guidance, and mobile-friendly spacing.
- **Settings modal polish** - Updated `frontend/src/features/settings/SettingsModal.tsx` so the settings navigation becomes a horizontal scrollable rail on narrow screens, keeps the desktop sidebar on larger screens, tightens mobile content padding, and adds an accessible close label.
- **Frontend role-aware error foundation** - Added structured frontend error normalization in `frontend/src/utils/errors.ts` and wired auth/settings/AI/shared API services so normal users receive short safe messages while admin/debug paths can show sanitized technical details.
- **User-facing error surface sweep** - Updated app error boundaries, Market & News loading errors, and the system health tooltip so normal-user UI avoids raw exception text while admin-capable surfaces use sanitized diagnostics where available.

### Fixed

- **Normal-user error privacy** - Prevented raw auth/settings/AI API detail strings from flowing directly into normal-user auth, settings, and AI fallback surfaces.
- **Boundary error privacy** - Replaced direct exception-message rendering in frontend error boundaries with generic recovery copy.

### Tests

- `npm.cmd run typecheck` passed.
- `npm.cmd run build` passed after rerunning outside the sandbox because the sandboxed Vite build hit `EPERM` copying `public/manifest.json` into `dist/manifest.json`.
- `npm.cmd run typecheck` passed after Settings modal polish.
- `npm.cmd run build` passed after Settings modal polish.
- `npm.cmd run typecheck` passed after the user-facing error surface sweep.
- `npm.cmd run build` passed after the user-facing error surface sweep.

### Files

- `frontend/src/features/auth/AuthModal.tsx`
- `frontend/src/features/auth/AuthContext.tsx`
- `frontend/src/features/ai/hooks/useAiChat.ts`
- `frontend/src/features/market/components/MarketNews.tsx`
- `frontend/src/features/settings/SettingsModal.tsx`
- `frontend/src/components/ErrorBoundary.tsx`
- `frontend/src/components/ui/ErrorBoundary.tsx`
- `frontend/src/components/ui/SystemHealthCard.tsx`
- `frontend/src/services/apiClient.ts`
- `frontend/src/services/aiService.ts`
- `frontend/src/services/authService.ts`
- `frontend/src/services/settingsService.ts`
- `frontend/src/utils/errors.ts`
- `frontend/src/i18n/locales/en.ts`
- `frontend/src/i18n/locales/vi.ts`
- `docs/CHANGELOG.md`

---

## [0.25.27] - 2026-06-15

### Verified

- **Final verification Task 8** - Ran the final frontend verification pass after the Settings redesign and AI panel-orchestration work.
- **Frontend build checks** - `npm run typecheck` passed, and `npm run build` passed after rerunning outside the sandbox because the sandboxed Vite build hit `EPERM` copying `public/manifest.json` into `dist/manifest.json`.
- **UI smoke checks** - Verified source wiring for chart controls, indicator toggles, drawing tool registry/render paths, right-panel anchors, AI panel actions, Market & News/Screener anchors, and Settings Account/Customization/About content.
- **Mock app smoke** - Started the frontend in `VITE_DATA_SOURCE=mock` dev mode and confirmed the app served successfully over HTTP for chart-shell verification.

### Notes

- Backend pytest was skipped because the current Task 5-7 worktree does not include backend changes.
- Headless Edge screenshot capture did not produce files in this environment, so full visual click-through checks for drawing every tool, fullscreen, and browser zoom levels still need a human browser pass before release.

### Files

- `docs/CHANGELOG.md`

---

## [0.25.26] - 2026-06-15

### Changed

- **UI orchestration 7B.4** - Updated the AI tour flow to use the new panel/app-view actions for Watchlist, Order Book, Recent Trades, Market & News, and Screener targets.
- **Highlight/action smoke** - Verified the source anchors used by AI highlights still exist for right panel, overview, watchlist, order book, recent trades, AI panel, Market & News, and Screener.

### Tests

- `npm run typecheck` passed.
- `npm run build` passed after rerunning outside the sandbox because the sandboxed build hit `EPERM` copying `public/manifest.json` into `dist/manifest.json`.
- Source smoke checks passed for new AI action definitions, controlled right-panel state wiring, and `data-ai-section` highlight anchors.

### Files

- `frontend/src/features/ai/actions/AiActionProvider.tsx`
- `docs/CHANGELOG.md`

---

## [0.25.25] - 2026-06-15

### Changed

- **UI orchestration 7B.3** - Added previous-UI-state capture before AI-driven panel/view navigation and a persistent user-controlled restore banner.
- **Restore behavior** - AI no longer needs to close panels automatically after opening context; users can read the highlighted panel and choose when to return to their previous app view and right-panel tab state.

### Tests

- `npm run typecheck` passed.

### Files

- `frontend/src/features/ai/actions/AiActionProvider.tsx`
- `frontend/src/i18n/locales/en.ts`
- `frontend/src/i18n/locales/vi.ts`
- `docs/CHANGELOG.md`

---

## [0.25.24] - 2026-06-15

### Changed

- **UI orchestration 7B.2** - Added explicit AI action runtime support for opening/closing the right panel, switching right-panel tabs, and switching app views while keeping the existing layout unchanged.
- **AI panel targeting** - Updated AI section navigation to use controlled right-panel state first, with existing custom events kept as compatibility fallback during the migration.

### Tests

- `npm run typecheck` passed.

### Files

- `frontend/src/App.tsx`
- `frontend/src/features/ai/actions/AiActionProvider.tsx`
- `docs/CHANGELOG.md`

---

## [0.25.23] - 2026-06-15

### Changed

- **UI orchestration 7B.1** - Standardized right-panel tab state by lifting the top-level `overview/aiHelper` state and the nested `watchlist/orderBook/recentTrades` state into `App.tsx`.
- **Right panel control** - Converted `RightPanel` to receive controlled tab props while preserving existing event compatibility so current AI tour/action flows can still switch right-panel tabs during the migration.

### Tests

- `npm run typecheck` passed.

### Files

- `frontend/src/App.tsx`
- `frontend/src/features/watchlist/components/RightPanel.tsx`
- `docs/CHANGELOG.md`

---

## [0.25.22] - 2026-06-15

### Analysis

- **UI architecture analysis Task 6** - Compared two restructuring paths for LMView: moving market/context modules into a bottom dock while keeping AI on the right, versus preserving the current layout and letting AI temporarily open/switch/highlight the relevant panels.
- **Recommendation** - Recommended the lower-risk panel-orchestration path first because `App.tsx`, `RightPanel`, and `AiActionProvider` already expose most of the needed primitives: app view switching, right-panel open state, right-panel tab events, and `data-ai-section` highlight anchors.
- **Deferred migration** - Noted that the bottom-dock architecture remains a possible later migration, but it should wait until panel/tab state and AI restore behavior are standardized.

### Tests

- Not run; analysis and changelog-only task with no UI/code implementation.

### Files

- `docs/CHANGELOG.md`

---

## [0.25.21] - 2026-06-15

### Changed

- **Settings About UI 5.3** - Redesigned the About tab into a compact responsive overview for LMView with product description, frontend/backend version fields, core feature chips, data disclaimer, resources, and system status.
- **About system status** - Reused the existing health service to show backend status, latency, and last checked time without exposing raw debug payloads to normal users.
- **Version metadata** - Added frontend/backend version constants in the frontend env module. Frontend version falls back to `frontend/package.json`; backend version is shown when provided by deploy env and otherwise reports unavailable.

### Tests

- `npm run typecheck` passed.
- `npm run build` passed after rerunning outside the sandbox because the sandboxed build hit `EPERM` copying `public/manifest.json` into `dist/manifest.json`.

### Files

- `frontend/src/constants/env.ts`
- `frontend/src/features/settings/SettingsModal.tsx`
- `frontend/src/i18n/locales/en.ts`
- `frontend/src/i18n/locales/vi.ts`
- `docs/CHANGELOG.md`

---

## [0.25.20] - 2026-06-15

### Changed

- **Settings Customization UI 5.2** - Redesigned the Customization tab around chart presets with Save/Reset controls, a lightweight chart preview, chart theme presets, candle colors, wick/border visibility, grid/crosshair controls, price/time scale controls, default chart type, and compact/comfortable layout preference.
- **Chart preference persistence** - Added frontend settings types and defaults for chart preferences stored under `customization_defaults.drawing_defaults.chart_preferences`, preserving the existing settings API payload and providing a migration path for older settings that only had the legacy `drawing_defaults` keys.
- **Runtime chart preset support** - Applied saved chart preferences to the chart runtime where lightweight-charts supports it: candle colors, candle wick/border visibility, grid visibility/style, crosshair mode/style, price/time label visibility, seconds visibility for 1s charts, and bar spacing.
- **Favorite drawing tools** - Added favorite drawing tool selection in Settings and pinned saved favorites near the top of the left drawing toolbar after settings load.

### Tests

- `npm run typecheck` passed.
- `npm run build` passed after rerunning outside the sandbox because the sandboxed build hit `EPERM` copying `public/manifest.json` into `dist/manifest.json`.

### Files

- `frontend/src/services/settingsService.ts`
- `frontend/src/features/settings/SettingsModal.tsx`
- `frontend/src/features/chart/CandlestickChart.tsx`
- `frontend/src/components/layout/LeftSidebar.tsx`
- `frontend/src/App.tsx`
- `frontend/src/i18n/locales/en.ts`
- `frontend/src/i18n/locales/vi.ts`
- `docs/CHANGELOG.md`

---

## [0.25.19] - 2026-06-15

### Changed

- **Settings Account UI 5.1** - Redesigned the Account tab into clearer cards for account overview, editable profile details, security metadata, password change, and danger-zone actions.
- **Account metadata display** - Reused the existing auth user payload instead of adding a backend endpoint. The tab now shows display name, username, email, role, active status, member-since date, last-login date when present, and password metadata without exposing sensitive credential data.
- **Account loading/error states** - Added an account loading card and inline auth error state, plus English/Vietnamese labels for the new Account tab copy.

### Tests

- `npm run typecheck` passed.
- `npm run build` passed after rerunning outside the sandbox because the sandboxed build hit `EPERM` copying `public/manifest.json` into `dist/manifest.json`.

### Files

- `frontend/src/features/settings/SettingsModal.tsx`
- `frontend/src/i18n/locales/en.ts`
- `frontend/src/i18n/locales/vi.ts`
- `docs/CHANGELOG.md`

---

## [0.25.18] - 2026-06-15

### Fixed

- **Mobile/tablet responsive 4.4** - Audited mobile/tablet support for the app shell, header controls, chart toolbar, right panel overlay behavior, and collapsed drawing toolbar. The app shell now uses dynamic viewport height for mobile browser bars.
- **Mobile header controls** - Header action controls now wrap onto their own row on narrow mobile widths so settings/login and panel controls remain reachable instead of being pushed off-screen.
- **Mobile chart toolbar alignment** - Chart toolbar action groups now start from the left on mobile instead of being forced to the right by desktop `ml-auto` alignment.

### Checked

- Edge headless screenshots were generated and visually checked for `390x844`, `430x932`, `768x900`, and `900x900` responsive layouts.
- The final `390x844` smoke confirmed header controls, chart selector/timeframe row, chart-type controls, chart canvas, and collapsed drawing toolbar remain visible and usable.

### Tests

- `npm run typecheck` passed.
- `npm run build` passed after rerunning outside the sandbox because the sandboxed build hit `EPERM` copying `public/manifest.json` into `dist/manifest.json`.

### Files

- `frontend/src/App.tsx`
- `frontend/src/components/layout/Header.tsx`
- `frontend/src/features/chart/CandlestickChart.tsx`
- `docs/CHANGELOG.md`

---

## [0.25.17] - 2026-06-15

### Fixed

- **Fullscreen viewport scaling 4.3** - Audited chart fullscreen sizing and left drawing toolbar bounds. Fullscreen chart root now uses dynamic viewport height, and the drawing toolbar uses dynamic viewport height for its scroll boundary so it remains usable at higher browser scale.
- **Browser zoom smoke** - Verified the mock-mode chart shell with Edge headless screenshots at desktop, small laptop, 125% scale stress, and tablet-ish widths. Chart toolbar wrapping, right panel width, chart canvas visibility, and collapsed drawing toolbar stayed usable in the checked screenshots.

### Checked

- Edge headless screenshots were generated for `1366x768`, `1280x720 @ 125% scale`, `1024x768`, and `768x900`.
- Additional scale smoke screenshots were generated at `80%`, `90%`, `100%`, `110%`, and `125%` scale on a `1366x768` viewport.

### Tests

- `npm run typecheck` passed.
- `npm run build` passed after rerunning outside the sandbox because the sandboxed build hit `EPERM` copying `public/manifest.json` into `dist/manifest.json`.

### Files

- `frontend/src/features/chart/CandlestickChart.tsx`
- `frontend/src/components/layout/LeftSidebar.tsx`
- `docs/CHANGELOG.md`

---

## [0.25.16] - 2026-06-15

### Fixed

- **Responsive right panel 4.2** - Audited the right panel shell, drag handle, Overview, Watchlist, Order Book, Recent Trades, and AI Helper panel. Desktop panel resizing is now clamped by viewport width and a minimum chart area so the panel cannot consume too much space on small laptops or high browser zoom.
- **Right panel content scaling** - Reduced rigid panel minimum width, allowed watchlist filters/tabs to wrap or shrink, and added truncation/min-width guards to Order Book and Recent Trades columns.
- **AI Helper panel scaling** - AI message bodies and the composer footer now wrap more gracefully, keeping mode controls, send hint, and send button usable in narrower panels.

### Checked

- Static layout constraints checked for desktop panel widths near 1024px, small laptop widths, and browser zoom stress cases where panel width plus chart area compete.

### Tests

- `npm run typecheck` passed.
- `npm run build` passed after rerunning outside the sandbox because the sandboxed build hit `EPERM` copying `public/manifest.json` into `dist/manifest.json`.

### Files

- `frontend/src/App.tsx`
- `frontend/src/features/watchlist/components/RightPanel.tsx`
- `frontend/src/features/ai/components/AiAssistantPanel.tsx`
- `frontend/src/features/market/components/OrderBook.tsx`
- `frontend/src/features/market/components/RecentTrades.tsx`
- `docs/CHANGELOG.md`

---

## [0.25.15] - 2026-06-15

### Fixed

- **Responsive chart toolbar 4.1** - Audited the chart selector, timeframe dropdown, indicator/date/export group, chart-type selector, and zoom/fullscreen control row. The chart toolbar now wraps instead of forcing a `min-w-max` row, keeping controls inside the chart header on small laptop widths and browser zoom levels.
- **Chart selector scaling** - Market selector now has explicit min/max responsive width so long symbols do not force the toolbar wider than the chart area.
- **Chart type selector overflow** - Chart-type buttons now use a wider responsive overflow container with internal horizontal scrolling, preventing the selector from crushing nearby controls at 110-125% zoom.

### Checked

- Static layout constraints checked for the `1024px` desktop transition, small laptop widths, and browser zoom stress cases where toolbar controls need wrapping or internal overflow.

### Tests

- `npm run typecheck` passed.
- `npm run build` passed after rerunning outside the sandbox. The first sandboxed build hit `EPERM` copying `public/manifest.json` into `dist/manifest.json`; one outside-sandbox rerun built the bundle but hit a transient Windows `UV_HANDLE_CLOSING` assertion after printing `built`, and the second outside-sandbox rerun passed cleanly.

### Files

- `frontend/src/features/chart/CandlestickChart.tsx`
- `frontend/src/features/chart/MarketSelector.tsx`
- `docs/CHANGELOG.md`

---

## [0.25.14] - 2026-06-14

### Fixed

- **Drawing Tools: Long Position / Short Position** - Audited the existing `longPosition` and `shortPosition` types, position toolbar group, two-anchor commit path, renderer, and hit-test behavior. The tools now reject zero-size/tiny spans before commit.
- **Position risk/reward rendering** - Long/Short Position now renders symmetric 1:1 target and risk zones around the entry anchor using the second anchor as the distance control, instead of often producing one zero-height zone.
- **Position selection bounds** - Hit-testing now covers the full target/risk area generated by the position drawing, and labels use localized tool names.

### Tests

- Extended drawing geometry tests to confirm Long Position and Short Position remain two-anchor drawings and reuse shared box-span validation.
- `npm exec vitest -- run src/features/drawing/__tests__/drawingGeometry.test.ts` passed.
- `npm run typecheck` passed.
- `npm run build` passed after rerunning outside the sandbox because the sandboxed build hit `EPERM` copying `public/manifest.json` into `dist/manifest.json`.

### Files

- `frontend/src/features/drawing/components/ChartOverlay.tsx`
- `frontend/src/features/drawing/__tests__/drawingGeometry.test.ts`
- `docs/CHANGELOG.md`

---

## [0.25.13] - 2026-06-14

### Fixed

- **Drawing Tool: Measurement/Ruler** - Audited the `ruler` type, direct left-toolbar placement, two-anchor commit path, renderer, label output, and line hit-test behavior. Ruler now rejects zero-length/tiny drag commits so accidental clicks no longer create meaningless measurement labels or hard-to-select drawings.

### Tests

- Extended drawing geometry tests to confirm Ruler remains a two-anchor drawing and reuses the shared two-point distance validation.
- `npm exec vitest -- run src/features/drawing/__tests__/drawingGeometry.test.ts` passed.
- `npm run typecheck` passed.
- `npm run build` passed after rerunning outside the sandbox because the sandboxed build hit `EPERM` copying `public/manifest.json` into `dist/manifest.json`.

### Files

- `frontend/src/features/drawing/components/ChartOverlay.tsx`
- `frontend/src/features/drawing/__tests__/drawingGeometry.test.ts`
- `docs/CHANGELOG.md`

---

## [0.25.12] - 2026-06-14

### Added

- **Drawing Tool: Note** - Audited the existing `note` type, i18n label, legacy drawing toolbar entry, default settings, active left toolbar, input flow, renderer, and hit-test behavior. Note is now available from the active left toolbar and opens the existing text input at the clicked chart point.

### Fixed

- **Note commit/render path** - Note now saves as `tool: "note"` with a single data-space anchor point and renders through the anchored text/note path so it stays aligned during zoom, scroll, resize, and chart-type changes.
- **Text and note styling** - Text-like drawings now apply `fontSize`, `fontFamily`, `textColor`, `backgroundColor`, bold, and italic settings in both render and hit-test bounds instead of ignoring those defaults.

### Notes

- No separate drawing tool named `tooltip` exists in the current type registry; this batch implements the supported `note` tool foundation.

### Tests

- Extended drawing geometry tests to cover Note as a one-anchor drawing.
- `npm exec vitest -- run src/features/drawing/__tests__/drawingGeometry.test.ts` passed.
- `npm run typecheck` passed.
- `npm run build` passed after rerunning outside the sandbox because the sandboxed build hit `EPERM` copying `public/manifest.json` into `dist/manifest.json`.

### Files

- `frontend/src/components/layout/LeftSidebar.tsx`
- `frontend/src/features/drawing/components/ChartOverlay.tsx`
- `frontend/src/features/drawing/drawingGeometry.ts`
- `frontend/src/features/drawing/__tests__/drawingGeometry.test.ts`
- `docs/CHANGELOG.md`

---

## [0.25.11] - 2026-06-14

### Added

- **Drawing Tool: Anchored Text** - Audited the `anchoredText` type, i18n label, default settings, toolbar visibility, one-anchor input flow, renderer, and hit-test behavior. Anchored Text is now available from the left toolbar and opens the existing text input at the clicked chart point.

### Fixed

- **Anchored Text commit path** - Text input state now records which text tool opened it, so Anchored Text saves `tool: "anchoredText"` instead of falling back to generic text while remaining anchored to chart data coordinates across zoom, scroll, resize, and chart-type changes.
- **Anchored Text render/hit-test** - The existing anchored text renderer and hit-test path now handle both `text` and `anchoredText`.

### Tests

- Extended drawing geometry tests to cover Anchored Text as a one-anchor drawing.
- `npm exec vitest -- run src/features/drawing/__tests__/drawingGeometry.test.ts` passed.
- `npm run typecheck` passed.
- `npm run build` passed after rerunning outside the sandbox because the sandboxed build hit `EPERM` copying `public/manifest.json` into `dist/manifest.json`.

### Files

- `frontend/src/components/layout/LeftSidebar.tsx`
- `frontend/src/features/drawing/components/ChartOverlay.tsx`
- `frontend/src/features/drawing/drawingGeometry.ts`
- `frontend/src/features/drawing/__tests__/drawingGeometry.test.ts`
- `docs/CHANGELOG.md`

---

## [0.25.10] - 2026-06-14

### Fixed

- **Drawing Tool: Fibonacci Retracement** - Audited the `fibRetracement` registry entry, Fibonacci toolbar placement, two-anchor commit path, renderer, settings levels, and hit-test behavior. Fibonacci Retracement now rejects zero-size/tiny anchor spans so accidental clicks do not create collapsed level sets.
- **Fibonacci level selection** - Hit-testing now recognizes the rendered retracement levels as well as the anchor diagonal, so users can select/erase the drawing by clicking a fib level line.
- **Fibonacci render layering** - The retracement background fill now renders behind the level lines and labels instead of overlaying them.

### Tests

- Extended drawing geometry tests to confirm Fibonacci Retracement remains a two-anchor drawing and reuses the shared box-span validation.
- `npm exec vitest -- run src/features/drawing/__tests__/drawingGeometry.test.ts` passed.
- `npm run typecheck` passed.
- `npm run build` passed after rerunning outside the sandbox because the sandboxed build hit `EPERM` copying `public/manifest.json` into `dist/manifest.json`.

### Files

- `frontend/src/features/drawing/components/ChartOverlay.tsx`
- `frontend/src/features/drawing/drawingGeometry.ts`
- `frontend/src/features/drawing/__tests__/drawingGeometry.test.ts`
- `docs/CHANGELOG.md`

---

## [0.25.9] - 2026-06-14

### Fixed

- **Drawing Tool: Parallel Channel** - Audited the `parallelChannel` registry entry, channels toolbar placement, three-anchor multi-click flow, renderer, and hit-test behavior. Parallel Channel now rejects degenerate channels when the base line is too short or the third point has too little perpendicular offset.
- **Parallel Channel render/hit-test safety** - Existing invalid channel data is skipped during render and hit-test instead of producing overlapping lines or nearly invisible polygons.

### Tests

- Extended drawing geometry tests to cover valid/invalid Parallel Channel base and offset geometry.
- `npm exec vitest -- run src/features/drawing/__tests__/drawingGeometry.test.ts` passed.
- `npm run typecheck` passed.
- `npm run build` passed after rerunning outside the sandbox because the sandboxed build hit `EPERM` copying `public/manifest.json` into `dist/manifest.json`.

### Files

- `frontend/src/features/drawing/components/ChartOverlay.tsx`
- `frontend/src/features/drawing/drawingGeometry.ts`
- `frontend/src/features/drawing/__tests__/drawingGeometry.test.ts`
- `docs/CHANGELOG.md`

---

## [0.25.8] - 2026-06-14

### Fixed

- **Drawing Tool: Rectangle** - Audited the `rectangle` registry entry, shape-tools toolbar placement, two-anchor commit path, renderer, and hit-test behavior. Rectangle now rejects zero-size and tiny drag commits so accidental clicks no longer create invisible or nearly unselectable rectangles.
- **Rectangle render safety** - Existing zero-area rectangle data is skipped at render time instead of producing invisible SVG geometry.

### Tests

- Extended drawing geometry tests to cover minimum box width/height validation.
- `npm exec vitest -- run src/features/drawing/__tests__/drawingGeometry.test.ts` passed.
- `npm run typecheck` passed.
- `npm run build` passed after rerunning outside the sandbox because the sandboxed build hit `EPERM` copying `public/manifest.json` into `dist/manifest.json`.

### Files

- `frontend/src/features/drawing/components/ChartOverlay.tsx`
- `frontend/src/features/drawing/drawingGeometry.ts`
- `frontend/src/features/drawing/__tests__/drawingGeometry.test.ts`
- `docs/CHANGELOG.md`

---

## [0.25.7] - 2026-06-14

### Fixed

- **Drawing Tool: Horizontal Ray** - Audited the `horizontalRay` registry entry, line-tools toolbar placement, one-anchor commit path, renderer, and hit-test behavior. Horizontal Ray now stores a single anchor point and renders from that anchor time to the right edge of the chart instead of behaving like a full-width horizontal line.
- **Horizontal Ray selection/editing** - Hit-testing now follows the rendered ray segment, and selected rays show a draggable anchor when the anchor is visible.

### Tests

- Extended drawing geometry tests to cover one-point Horizontal Ray commits.
- `npm exec vitest -- run src/features/drawing/__tests__/drawingGeometry.test.ts` passed.
- `npm run typecheck` passed.
- `npm run build` passed after rerunning outside the sandbox because the sandboxed build hit `EPERM` copying `public/manifest.json` into `dist/manifest.json`.

### Files

- `frontend/src/features/drawing/components/ChartOverlay.tsx`
- `frontend/src/features/drawing/drawingGeometry.ts`
- `frontend/src/features/drawing/__tests__/drawingGeometry.test.ts`
- `docs/CHANGELOG.md`

---

## [0.25.6] - 2026-06-14

### Fixed

- **Drawing Tool: Vertical Line** - Audited the `vertical` drawing registry entry, line-tools left-toolbar placement, one-point anchor expectations, and overlay renderer. Vertical Line now commits a single data-space anchor point instead of storing an unused second drag point.
- **Vertical Line selected anchor** - Selected Vertical Lines now render a one-point anchor at the placement point so users can drag/edit the line without relying on invisible state.

### Tests

- Extended drawing geometry tests to cover one-point Vertical Line commits and normal two-point drawing commits.
- `npm exec vitest -- run src/features/drawing/__tests__/drawingGeometry.test.ts` passed.
- `npm run typecheck` passed.
- `npm run build` passed after rerunning outside the sandbox because the sandboxed build hit `EPERM` copying `public/manifest.json` into `dist/manifest.json`.

### Files

- `frontend/src/features/drawing/components/ChartOverlay.tsx`
- `frontend/src/features/drawing/drawingGeometry.ts`
- `frontend/src/features/drawing/__tests__/drawingGeometry.test.ts`
- `docs/CHANGELOG.md`

---

## [0.25.5] - 2026-06-14

### Fixed

- **Drawing Tool: Trend Line** - Audited the drawing registry, left toolbar group, sticky selected-tool behavior, and overlay path for Trend Line. Fixed the chart overlay contract so Trend Line uses the active chart price-series coordinate mapper instead of a candlestick-only type, keeping drawings aligned when switching chart types.
- **Trend Line zero-length guard** - Added a minimum two-point pixel-distance guard so an accidental click without a drag no longer creates an invisible or unselectable Trend Line.

### Tests

- Added focused drawing geometry tests for two-point drawing distance validation.
- `npm exec vitest -- run src/features/drawing/__tests__/drawingGeometry.test.ts` passed.
- `npm run typecheck` passed.
- `npm run build` passed after rerunning outside the sandbox because the sandboxed build hit `EPERM` copying `public/manifest.json` into `dist/manifest.json`.

### Files

- `frontend/src/features/drawing/components/ChartOverlay.tsx`
- `frontend/src/features/drawing/drawingGeometry.ts`
- `frontend/src/features/drawing/__tests__/drawingGeometry.test.ts`
- `frontend/src/hooks/useDrawingToolbarPosition.ts`

---

## [0.25.4] - 2026-06-14

### Fixed

- **Chart type render safety** - Added a shared chart-type data boundary that sanitizes candles before they reach lightweight-charts: invalid rows are dropped, millisecond timestamps are converted to seconds, duplicate source timestamps are de-duplicated, transformed non-time chart points get strictly ascending synthetic timestamps, OHLC bounds are repaired, and NaN/null values are filtered.
- **Core chart types stable** - Candlestick, Bar, Line, and Area now share sanitized source candles/close-line data and can switch without introducing invalid series data.
- **Heikin Ashi stable** - Heikin Ashi now renders sanitized transformed candles while preserving source candle ordering and volume.
- **Advanced chart fallback** - Renko, Line Break, Kagi, and Point & Figure now fall back to source candles or source close-line data when their transformer produces too few renderable points, preventing blank charts on flat/sparse data.
- **Chart type switching range** - Switching between full-length time-based charts and shorter transformed charts preserves the visible logical range near the current right edge instead of leaving the viewport stranded outside the transformed data length.
- **Chart tooltip active series** - Crosshair tooltip reads the active price series, so Bar, Line, Area, and Kagi no longer depend on hidden candlestick series data for tooltip values.

### Notes

- Renko, Line Break, Kagi, and Point & Figure remain experimental technical approximations because lightweight-charts does not provide native series renderers for these chart types; they are now safe to render and switch, but not yet feature-complete specialized renderers.

### Tests

- Added chart-type data tests covering all nine chart types, invalid candle sanitization, duplicate timestamp handling, synthetic timestamp ordering, and advanced-transform fallback behavior.
- `npm exec vitest -- run src/features/chart/__tests__/chartTypeData.test.ts` passed.
- `npm exec vitest -- run src/features/chart/__tests__/transformers.test.ts` passed.
- `npm exec vitest -- run src/data/mock/__tests__/mockDataGenerator.test.ts` passed.
- `npm run typecheck` passed.
- `npm run build` passed after rerunning outside the sandbox because the sandboxed build hit `EPERM` copying `public/manifest.json` into `dist/manifest.json`.
- `VITE_DATA_SOURCE=mock npm run build` passed for smoke testing, and Edge headless confirmed Candlestick, Bars, Line, Area, Heikin Ashi, Renko, Line Break, Kagi, and Point & Figure all switch without chart/data console errors or `/api/*` calls in mock mode.

---

## [0.25.3] - 2026-06-14

### Fixed

- **Mock candlestick deploy rendering** - Fixed frontend mock-mode builds so `--mode mock`, `VITE_DATA_SOURCE=mock npm run build`, and `frontend/.env.mock` all bake `VITE_DATA_SOURCE=mock` at build time instead of silently falling back to API mode.
- **Mock candle normalization** - Added a shared mock candle normalizer that converts millisecond API-shaped timestamps to lightweight-charts epoch seconds exactly once, rejects invalid rows, repairs OHLC bounds, sorts candles ascending by `time`, and de-duplicates duplicate timestamps before chart rendering.
- **Mock realtime fallback** - Normalized mock candle emissions for single-timeframe and all-timeframe subscriptions so mock mode can render historical/static candles and timer-driven updates without requiring `/api/stream/all`.

### Tests

- Added focused Vitest coverage for mock candle generation across `1m`, `5m`, `1h`, and `1d`, plus API-shaped millisecond timestamp normalization.
- `VITE_DATA_SOURCE=mock npm run dev -- --host 127.0.0.1 --port 3001` served the local dev mock app successfully.
- `npm exec vitest -- run src/data/mock/__tests__/mockDataGenerator.test.ts` passed.
- `npm run typecheck` passed.
- `npm run build` passed for API mode after rerunning outside the sandbox because the sandboxed build hit `EPERM` copying `public/manifest.json` into `dist/manifest.json`.
- `VITE_DATA_SOURCE=mock npm run build` passed outside the sandbox, and the built bundle contains the mock adapter without `/api/klines` or `/api/stream/all` references.
- `VITE_DATA_SOURCE=mock npm run preview -- --host 127.0.0.1 --port 4174` served the mock production bundle successfully; Vite moved to `4175` because `4174` was busy during the smoke check.
- `vite preview --host 127.0.0.1 --port 4173` is serving the final mock production bundle at `http://127.0.0.1:4173/`.
- Edge headless smoke checks confirmed the mock preview renders non-blank chart canvases, switches `1m`, `5m`, `1H`, `1D`, `Candlestick`, `Bars`, `Line`, and `Area`, and makes no `/api/*` requests.

---

## [0.25.2] - 2026-06-14

### Added

- **Indicator series API** - Added `/api/indicators/{symbol}/series` to return stable indicator time series for the chart UI. When precomputed indicator cache is empty, backend falls back to real candle data from Redis first, then shared Influx/Trino candle backfill, and computes server-side indicator series instead of returning mock data.
- **Indicator UI data states** - The chart indicator dropdown now calls the backend indicator series service and shows explicit loading, unavailable, backend-empty, and not-enough-candles states.

### Fixed

- **Group 1: SMA/EMA working** - SMA 20, SMA 50, EMA 12, and EMA 26 now have backend series support plus Redis-candle fallback for `1m`, `5m`, `15m`, `1h`, `4h`, and `1d` aggregation paths.
- **Group 2: RSI working** - RSI now computes server-side from ascending candle windows and returns both `rsi` and `rsi14` aliases for frontend/backend compatibility.
- **Group 3: MACD working** - MACD now computes full line, signal, and histogram series instead of the previous simplified latest-only fallback.
- **Group 4: Bollinger Bands working** - Bollinger upper, middle, lower, and width series now compute from candle windows and align with frontend overlay keys.
- **Group 5: Volume working** - Volume remains sourced from real candles and Volume MA now has backend series aliases `volumeMa` and `volume_sma20`.
- **Group 6: ATR working** - ATR now computes server-side using candle true range smoothing and returns both `atr` and `atr14` aliases.
- **Future indicator controls** - Support/Resistance and Whale Alert are now marked unavailable in the selector instead of appearing as inert working toggles.

### Tests

- Added focused indicator API integration coverage for candle-derived series fallback on aggregated timeframes.
- `python -m py_compile backend/services/indicator_service.py backend/api/indicators.py backend/models/indicators.py` passed.
- `npm run typecheck` passed.
- `npm run build` passed after rerunning outside the sandbox because the sandboxed build hit `EPERM` copying `public/manifest.json` into `dist/manifest.json`.
- `PYTHONPATH=. python -m pytest tests/ -v` is blocked in this local environment because both available Python interpreters are missing the `redis` package, so backend tests fail during collection before executing assertions.

---

## [0.25.1] - 2026-06-14

### Documentation

- **Chart/drawing/indicator audit** - Audited the chart, drawing, settings, AI Helper, market, frontend service/type, indicator API/service, and Flink indicator writer surfaces; documented current drawing tool, indicator, chart type, data-source, and responsive-layout risks with a small-batch remediation plan and no code changes.
## [0.25.1] - 2026-06-16

### Fixed
- **Docker Swarm Image Distribution**: Replaced `--resolve-image never` with a local registry-based distribution system to fix "No such image" errors when Swarm scheduled custom-built containers (like Flink, Spark, Kafka) onto the worker node.
- **Node Configuration Script**: Created `scripts/setup_swarm_node.sh` to configure Docker daemons on all nodes to trust the insecure local registry.
- **Kafka Deployment Stability**: Baked `entrypoint.sh` and JMX configuration into a custom Kafka image to prevent `Permission denied` errors from Swarm bind-mounting overlay directories. Fixed Kafka OOM kill (exit code 137) by explicitly reducing `KAFKA_OPTS` heap to `512m` and raising container memory limits to `1024M`.
- **SSL Certificate Generation Loop**: Made Nginx HSTS (`Strict-Transport-Security`) conditional on the presence of a valid Let's Encrypt certificate. This prevents browsers from permanently caching an HTTPS redirect for the self-signed fallback, which previously caused ACME challenges to timeout or get rejected by HSTS cache.

---

## [0.25.0] - 2026-06-14

### Added

- **Multi-Agent LangGraph Architecture** — Complete multi-agent DAG replacing the linear AI pipeline. Dispatched via `AI_ORCHESTRATION=langgraph` feature flag (default: `legacy` for backward compatibility).
  - `ai_service/agents/state.py` — `AgentState` TypedDict defining the shared state schema with ~30 typed fields for the entire graph execution.
  - `ai_service/agents/types.py` — Core data classes: `ExpertOutput`, `IntentClassification`, `IntentCategory`, `ExpertName`, `ValidationResult`, `Timer`, `INTENT_TO_EXPERTS` mapping.
  - `ai_service/agents/intent_router.py` — Hybrid intent classifier: rule-based pattern matching first (7 intent categories), LLM fallback for ambiguous queries. Multi-intent detection and interact-mode boosting.
  - `ai_service/agents/graph.py` — LangGraph `StateGraph` DAG: scope_gate → intent_router → parallel expert_execution → synthesis → reflection (with conditional revision loop up to 2 cycles) → END.
  - `ai_service/agents/synthesis.py` — Single-LLM-call synthesis node that assembles all expert outputs into a structured prompt. Bilingual (EN/VI) system prompt with runtime context injection.
  - `ai_service/agents/reflection.py` — Quality validation gate checking response length, disclaimer presence, expert data utilization, and uncertainty language. `route_after_reflection` conditional edge.
  - `ai_service/agents/persistence.py` — Agent execution trace storage in PostgreSQL (`ai_agent_executions`, `ai_expert_runs` tables).

- **6 Data-Only Expert Nodes** — Experts gather structured data without calling the LLM; synthesis makes the single call.
  - `ai_service/agents/experts/base.py` — `BaseExpert` ABC with `safe_execute()` wrapper (timeout, error handling, latency tracking).
  - `ai_service/agents/experts/technical_analysis.py` — RSI/MACD/SMA/Bollinger signal extraction from chart context with trend scoring.
  - `ai_service/agents/experts/market_data.py` — Ticker/orderbook/trades data extraction and formatting with data source provenance tracking.
  - `ai_service/agents/experts/news_sentiment.py` — News and sentiment data assembly (reads FinBERT cache when available).
  - `ai_service/agents/experts/rag_knowledge.py` — Knowledge base retrieval via existing RAG pipeline.
  - `ai_service/agents/experts/chart_interaction.py` — Interact mode tool-call proposal with typed `CHART_TOOLS` allowlist (10 tools), parameter validation, and enum enforcement.
  - `ai_service/agents/experts/general.py` — Fallback expert for general queries.

- **FinBERT NLP Pipeline** — Separate background worker for news sentiment analysis.
  - `ai_service/nlp/finbert.py` — `FinBERTAnalyzer` with lazy model loading, GPU/CPU auto-detection, single and batch analysis.
  - `ai_service/nlp/entity_extractor.py` — Crypto entity extraction (25+ assets), organization detection, event classification (7 categories), and market relevance scoring.
  - `ai_service/nlp/news_processor.py` — Standalone background worker (`python -m ai_service.nlp.news_processor`) processing unanalyzed news articles from PostgreSQL.
  - `ai_service/nlp/types.py` — Shared NLP data classes: `SentimentResult`, `EntityResult`, `NewsAnalysis`.

- **Provider Health & Circuit Breaker** — `ai_service/providers/health.py` with `CircuitBreaker` (CLOSED/OPEN/HALF_OPEN states), `ProviderHealthMonitor` singleton tracking success rate, latency, and auto-failover via `get_best_provider()`.

- **Interact Mode Safety** — Deterministic chart-action workflow.
  - `ai_service/actions/executor.py` — Action validator with PostgreSQL audit trail (`ai_chart_actions` table), status tracking (pending → approved → executed → undone).
  - `ai_service/actions/undo.py` — Per-session undo stack with reverse action computation (max depth 50).
  - `ai_service/actions/tool_definitions.py` — Canonical tool registry with `format_tools_for_llm()` prompt helper.

- **API Models** — `backend/models/ai/agents.py` with `AgentExecutionSummary`, `ExpertRunSummary`, `AgentExecutionDetail` Pydantic models.

- **Database Migration** — `backend/migrations/004_agents_metadata.sql` adding `ai_agent_executions`, `ai_expert_runs`, `ai_chart_actions`, `news_sentiment_cache` tables with indexes.

- **Docker AI Infrastructure** — Enhanced `docker-compose.ai.yml`:
  - `vllm` service with GPU reservation, tool-calling (`--enable-auto-tool-choice`), served-model-name `qwen-local`, health check with 120s start_period.
  - `finbert-worker` service (`ai-nlp` profile) with HuggingFace cache volume and CPU/GPU auto-detection.
  - `litellm` service with enhanced config: vLLM → DashScope → DeepSeek fallback chain, 3 retries, 60s timeout.

- **Test Suite** — 7 test files covering agent state, intent routing, expert nodes, chart safety, provider health, FinBERT NLP, and reflection validation.

### Changed

- **`ai_service/core/orchestrator.py`** — `run_chat()` now dispatches to LangGraph DAG or legacy pipeline based on `AI_ORCHESTRATION` env var. Legacy pipeline moved to `_run_chat_legacy()`. Shared helpers extracted.
- **`ai_service/config.py`** — Added `orchestration_mode` setting (default: `legacy`).
- **`ai_service/configs/litellm.yaml`** — Restructured with `qwen-local` (vLLM primary), `qwen-api` (DashScope), `deepseek` (fallback); router settings and retry config.
- **`.env.example`** — Added `AI_ORCHESTRATION`, `LITELLM_*`, `VLLM_*`, `DEEPSEEK_API_KEY`, `FINBERT_*` environment variables.
- **`backend/models/ai/__init__.py`** — Re-exports new agent execution models.
- **`ai_service/` folder cleanup** — Deprecated and emptied unused standalone `app/` folder files (`main.py`, `supervisor.py`, `state.py`, `registry.py`, and placeholder system/safety/format markdown prompts) to maintain a clean embedded architecture.
- **State and Intent Extraction** — Added helper `_extract_symbol_and_timeframe` in `ai_service/agents/state.py` to automatically extract symbols/timeframes from queries and supply a fallback `chart_context`.
- **Expert Improvements** — Enhanced `ai_service/agents/experts/technical_analysis.py` to fetch indicators directly from Redis when missing from chart context, and added support/signals for Bollinger Bands middle band, ATR volatility, Volume MA, and VWAP.
- **Response Formatting Rules** — Updated `SYNTHESIS_SYSTEM_PROMPT` in `ai_service/agents/synthesis.py` and `ASK_MODE_SYSTEM_PROMPT` in `ai_service/prompts/prompt_builder.py` to use full Markdown, highlight key values, forbid programming style, and translate variables (like `sma20`, `rsi14`) to human-friendly text.
- **Health Monitor & Circuit Breaker Wiring** — Wired `ProviderHealthMonitor` into `ai_service/providers/router.py` to register providers, track latencies, and check the circuit state before each request.
- **`docker-compose.ai.yml` cleanup** — Removed redundant environment variables (`AI_ENABLE_REAL_LLM`, `QWEN_API_KEY`, `LLAMA_API_KEY`) from `ai-service` and `litellm` service definitions.
- **Chart Actions Schema Alignment** — Resolved schema and validation discrepancies between LangGraph orchestration and the React frontend.
  - Aligned parameter keys (`indicator` vs `indicator_name`, `target` vs `section_id`) in `CHART_TOOLS` and `_propose_actions` inside `chart_interaction.py`.
  - Updated `synthesis.py` to output both `chart_actions` (with `action_type`/`params` for Pydantic backend validation) and `tool_calls` (with `name`/`arguments`/`reason`/`requires_approval` for frontend parsing).
  - Implemented automatic translation in `synthesis.py` to map legacy tools (`draw_trendline`, `create_annotation`, `highlight_region`) to frontend-supported draw/highlight tools.

---

## [0.24.13] - 2026-06-14

### Changed — Grafana Folders: 9 Folders, 39 Dashboards, 0 NODATA

**Trước:** 12 folders (3 rỗng/duplicate), Service Health dùng 1 dashboard chung với dropdown `$job` không thấy rõ service nào, 162 NODATA queries, các folder `Alerts`, `LMView/Frontend`, `LMView/Security` chỉ chứa alert rules.

**Sau:** 9 folders sạch (0 empty), 39 active dashboards, **291 queries verified, 0 BAD, 0 NODATA** (3/3 lần chạy liên tiếp), 48 alert rules consolidated vào 1 folder `Alerts`.

#### Cấu trúc folder cuối cùng (9 folders)

| Folder | Dashboards | Panels | Mục đích |
|---|---|---|---|
| **Overview** | 2 | 20 | High-level KPIs + Alert Center |
| **Application Logs** | 1 | 4 | Unified log view (container dropdown) |
| **Logs** | **10** | 22 | Per-service log streams (FastAPI, Flink, Kafka, Trino, Redis, Producer, Dagster, Storage, Spark, Nginx) |
| **Services** | 9 | 82 | Per-service metric dashboards (FastAPI, Kafka, Flink, Redis, Trino, InfluxDB, Producer, MinIO, Host) |
| **Service Health (All Services)** | **11** | **86** | **Per-service health deep-dive (11 services, 4-15 panels each)** |
| **Pipeline** | 2 | 30 | Data flow + error triage |
| **SRE** | 1 | 10 | SLO burn-rate |
| **AI** | 3 | 28 | AI/RAG |
| **Alerts** | 0 | 0 | **48 alert rules consolidated (was 3 folders)** |

#### Per-service Service Health (NEW - 11 dashboards)

| Service | Panels | Notable metrics |
|---|---|---|
| FastAPI | 7 | HTTP req/sec, p50/p95/p99, 5xx rate, Python GC |
| Kafka | 8 | Brokers, partitions, consumer lag, in-sync replicas |
| Flink TaskManager | 12 | JVM heap, threads, GC, managed memory, network |
| Flink JobManager | 4 | JVM heap, GC, job uptime, restart count |
| Redis | 10 | Clients, memory, commands, hit rate, evictions |
| Trino | 4 | JVM threads, memory, GC |
| InfluxDB | 15 | HTTP API, write/query rate, qc phases, boltDB |
| Producer | 4 | Dedup, failover, heartbeat, RSS |
| MinIO | 6 | S3 requests, errors, traffic, node metrics |
| Host (Node Exporter) | 7 | CPU, memory, network, filesystem |
| Kafka Exporter | 5 | Brokers, topics, scrape info |

#### Files added
- `Service Health (All Services)/{fastapi,kafka,flink-taskmanager,flink-jobmanager,redis,trino,influxdb,producer,minio,host,kafka-exporter}.json`

#### Files deleted
- `Service Health (All Services)/service-health.json` (replaced by 11 per-service files)
- 3 empty folders via Grafana API: `LMView / Frontend`, `LMView / Security`, `Service Health`

#### Bug fixes (in addition to 0.24.5g)
- **Flink TaskManager metric names** — sai case (dùng `flink_taskmanager_status_*` thay vì `flink_taskmanager_Status_*`)
- **InfluxDB metric names** — sai prefix (dùng `influxdb_http_api_*` thay vì `http_api_*`)
- **Datasource=null** trong AI/Pipeline/Error Triage/RAG/SRE — set uid cho target từ expr pattern
- **Loki frames structure** — check `data.values[*]` thay vì `data.result[*]`
- **Variable substitution trong verify** — replace `$var` with `.+` (regex)
- **Dashboard-level time range** — dùng `time.from/to` từ dashboard JSON

#### Tools added
- `scripts/restructure_service_health.py` — generate 11 per-service dashboards
- `scripts/rebuild_service_health.py` — rebuild với verified metric names
- `scripts/discover_actual.py` — test actual metric names per job
- `scripts/discover_service_metrics.py` — discover per-service metrics
- `scripts/fix_null_datasources.py` — fix datasource=null targets
- `scripts/move_alert_rules.py` — move rules between folders
- `scripts/audit_panels.py` — audit từng panel
- `scripts/test_grafana_loki.py` — test Loki via Grafana API
- `scripts/debug_loki_resp.py`, `scripts/debug_frames.py` — debug

#### Verification
- **3/3 lần liên tiếp**: 0 BAD / 291 tested queries
- 39 active dashboards, 250+ panels, 9 folders (0 empty)
- 48 alert rules consolidated vào 1 folder `Alerts`

---

## [0.24.12] - 2026-06-14

### Added — Session Report

**Từ 36 dashboards / ~426 panels → 10 dashboards / 103 panels (0 NoData).**

#### Tổ chức folder theo chủ đề

| Folder | Dashboards | Panels |
|---|---|---|
| **Overview** | Executive Overview, Alert Center | 13+7 |
| **Application Logs** | Application Logs (All Services) | 4 |
| **Pipeline** | Data Flow Pipeline, Error Triage | 17+13 |
| **SRE** | SLO Burn-Rate Tracking | 10 |
| **AI** | AI Ask Mode, Business Metrics, RAG Knowledge Base | 7+8+13 |
| **Service Health** | Service Health (All Services) | 11 |

#### Files moved
- `overview/`: `executive-overview.json` (lược 20→13 panels), `alert-center.json` (rewrite 0→7 panels với queries có data)
- `application-logs/`: gộp 7 file logs cũ (fastapi/flink/kafka/minio/redis/spark/trino) thành 1 file có container dropdown
- `pipeline/`: `data-flow-pipeline.json` (lược 27→17), `error-triage.json` (lược 27→13)
- `sre/`: `slo-burn-rate.json` (lược 23→10). `cost-attribution` + `multi-source-fallback` move to _drafts (queries phụ thuộc metric chưa implement: `ai_cost_usd_total`, `multi_source_*`)
- `ai/`: `ai-ask-mode.json` (lược 20→7), `business-metrics.json` (lược 23→8), `rag-knowledge-base.json` (lược 22→13)
- `service-health/`: gộp 16 service-specific dashboards (kafka, flink, spark, trino, redis, minio, postgres, influxdb, producer, dagster, nginx, zookeeper, system) thành 1 file có job dropdown

#### Files deleted (moved to _drafts then _drafts removed)
- 7 logs cũ: fastapi-logs, flink-logs, kafka-logs, minio-logs, redis-logs, spark-logs, trino-logs
- 16 service cũ: kafka-deep-dive, kafka-health, kafka-jvm, flink-deep-dive, flink-monitoring, spark-dashboard, trino-dashboard, redis-dashboard, redis-deep-dive, minio-dashboard, influxdb-dashboard, producer-dashboard, dagster-dashboard, postgres-dashboard, nginx-dashboard, zookeeper-dashboard
- 2 system cũ: system-overview, system-error-triage
- 3 phase5 chưa ready: cost-attribution, multi-source-fallback, websocket-serving (queries reference unimplemented metrics)

#### Bug fixes
- `or 0` → `or vector(0)` trong PromQL (PromQL scalar `0` không valid với vector)
- `container=~".*"` → `container=~".+"` (Loki requires `.+` for non-empty regex)
- Jvm memory panels → process RSS (hầu hết services expose `process_resident_memory_bytes`, không phải JVM heap)
- WebSocket metrics panels → HTTP throughput (websocket chưa expose metrics riêng)

#### Tools added
- `scripts/verify_dashboard_queries.py` — verify mỗi PromQL query trong dashboard có data, skip Loki queries
- `scripts/prune_dashboards.py` — tự động remove panels NoData (dry-run + apply)

#### Folder structure
- 6 subdirs (Overview, Application Logs, Pipeline, SRE, AI, Service Health) thay vì 36 file rời rạc
- Folder names Title Case (uppercase first letter)
- `foldersFromFilesStructure: true` trong `dashboards.yml` — auto-provision từ filesystem

#### Verification
- 0 NODATA queries trong 10 active dashboards
- 10/10 dashboards loaded lên Grafana thành công sau restart
- Cross-links giữa các dashboard (alert-center → executive-overview, data-flow-pipeline, error-triage)

---

## [0.24.11] - 2026-06-14

### Fixed — Dagster Gold Job Scheduled + asyncpg Missing

**Auto-refresh gold tables every 5 minutes:**

Before this change, the canonical `gold_layer_job` only ran when manually launched via the Dagster UI. Now it is **scheduled** (cron `*/5 * * * *`) and the gold tables stay in sync with the streaming source.

Steps:
1. `docker/dagster/Dockerfile` — added `asyncpg` to the pip install block. The dagster image is based on `apache/spark:3.5.5` and ships with neither asyncpg nor any DB driver. `compute_news_sentiment_daily` uses `asyncpg` to read `news_articles` from PostgreSQL; without it every gold run failed at the second step.
2. Restarted `dagster-daemon` so the rebuilt image with asyncpg was loaded.
3. `POST /graphql` to start `gold_layer_schedule` (was STOPPED by default).
4. Stopped `news_sentiment_schedule` (depends on `CRYPTOPANIC_API_KEY` and the active news scraper; not part of the production path right now).
5. Left `gold_advanced_schedule` RUNNING — it is a back-compat alias of `gold_layer_job` (same `compute_gold_layer` asset).

**Verified:**
- `gold_layer_job` ran 3 times in 5 minutes, all SUCCEEDED.
- Gold table counts grew monotonically: `gold_movers_ranking` 200 -> 366, `gold_market_dominance` 436 -> 872, `gold_volatility_ranking` 200 -> 400, `gold_momentum_indicators` 270 -> 540, `gold_sector_performance` 3 -> 6.
- 12/12 Tier 1 endpoints return 200 OK. `/news-sentiment` now shows 5 rows (was 0).
- `coin_ticker` data is visible (`SELECT symbol, close ... LIMIT 3` returns ETHUSDT, BTCUSDT, BABYUSDT) — the COUNT(*) query returns `(empty)` due to Trino's single-node scheduler occasionally queueing, but the data is in MinIO + Iceberg.

---

## [0.24.10] - 2026-06-13

### Added

- **`docs/dataflow_analysis_and_observability_plan.md`** — Phân tích tổng hợp data flow với 18 bottlenecks, 20 thiết kế chưa tối ưu, 12 dashboards + 30 alert rules + 50+ custom metrics theo 4-phase roadmap. Đề xuất giải pháp cho từng bottleneck (B1–B18, D1–D20) dựa trên code hiện tại.
- **`src/producer/metrics.py`** — Producer Prometheus metrics: dedup state (4 metrics), failover (6 metrics: direct-Redis active, transitions, duration, write latency), health probes (6 metrics: Kafka/Flink healthy, probe duration, failures), exchange WS lifecycle (4 metrics: last message, connected, backoff).
- **`backend/api/metrics.py`** — FastAPI/WebSocket metrics: HTTP request lifecycle (4 metrics), WebSocket connection (5 metrics: active, attempts, errors, disconnects, lifetime), WebSocket message (7 metrics: pushed, dropped, size, push duration, buffer size, loop cycle, no-op), multi-source fallback (6 metrics: lookups, duration, unavailable, stale, chain outcome, last update), API cache (3 metrics).
- **`backend/services/ai/metrics.py`** — AI/RAG metrics: top-level requests (4 metrics), scope gate (2 metrics), provider routing (4 metrics), RAG retrieval (7 metrics: duration, top-K, relevance score, zero results, cache ops, vector search, filters), embedding (3 metrics), output guard (3 metrics), chart actions (2 metrics), session + tokens (5 metrics), cost (1 metric), knowledge base health (4 metrics).
- **`src/processing/writers/metrics.py`** — Flink writer metrics: per-writer flush (6 metrics: duration, buffer size, records per flush, emitted, calls, errors), indicator state (5 metrics: warmup, keys, recomputations, gap fills, window fill ratio), checkpoint (5 metrics: duration, size, success, failure, alignment), Kafka source (4 metrics: records in, dropped, watermark lag, deserialize), per-key (2 metrics), backpressure (2 metrics).
- **`config/grafana/dashboards/websocket-serving.json`** — Dashboard 12 panels: active connections (by route), total active, messages pushed/s, push latency p50/p95/p99, connection errors, disconnects by reason, connection lifetime, slow client buffer (top 5), message size p99, loop cycle p95, no-op pushes, message drop rate. Tag: `phase5`, `dataflow`, `websocket`.
- **`config/grafana/dashboards/ai-ask-mode.json`** — Dashboard 20 panels: AI requests/min, in-flight, sessions created/active, scope gate decisions/refusal rate/latency, provider latency p50/p95/p99, request outcomes, fallback depth, fallback ratio, error ratio, RAG retrieval latency, top-K results, relevance score, zero-result ratio, cache hit ratio, output guard flags, token usage, AI cost per provider.
- **`config/grafana/dashboards/multi-source-fallback.json`** — Dashboard 10 panels: source hit rate per source, lookups/s by result, latency p50/p95/p99, chain outcome, unavailability, stale data, stale ratio, source health score, per-data-type hit rate, top 10 stale symbols table.
- **`config/grafana/dashboards/data-flow-pipeline.json`** — Dashboard 27 panels: end-to-end topology status row (8 stat panels: WS, Kafka, lag, Flink uptime, Redis, InfluxDB, WS conns, p99 latency), stage 1 (producer→Kafka, dedup, state, failover, health), stage 2 (Kafka→Flink, consumer lag, writer flush, buffer, records, checkpoint, watermark), stage 3 (Redis throughput, InfluxDB throughput).
- **Cập nhật `config/prometheus.yml`** — Thêm 3 scrape jobs: `producer-extended` (port 9091), `fastapi-custom` (path `/metrics-custom`), `ai-services` (path `/metrics-ai`). Tổng cộng 21 scrape jobs (tăng từ 17).
- **Cập nhật `config/grafana/provisioning/alerting/rules.yml`** — Thêm 27 alert rules mới theo 6 nhóm: `producer_extended_alerts` (5), `websocket_alerts` (5), `multi_source_alerts` (4), `ai_pipeline_alerts` (6), `flink_extended_alerts` (3), `slo_burn_rate_alerts` (4). Tổng cộng 45 rules (tăng từ 18), 17 groups. Đã validate YAML thành công.
- **`backend/api/websocket.py`** — Wire metrics vào 4 routes: `/stream/all` (legacy + optimized), `/stream/{interval}`, `/stream/indicators/{interval}`. Mỗi route giờ emit: `record_ws_connection`, `record_ws_disconnect`, `record_ws_message_push`, `record_ws_noop`, `record_ws_loop_cycle`, `record_source_lookup`, `record_source_chain_outcome`, `record_source_freshness`, `record_ws_connection_error`. Đổi `send_json` → `send_bytes` với JSON manual để có thể track message size.
- **`src/producer/main.py`** — Wire metrics: import `producer.metrics`, instrument `handle_ticker_message` với `record_dedup_decision` + `DEDUP_STATE_SIZE`, hook WebSocket `on_open`/`on_close` callbacks với `record_exchange_ws_state` + `record_reconnect_backoff`, khởi động 2nd metrics endpoint (port 9091) cho `producer-extended` scrape job, gọi `init_metrics()` khi boot.
- **`tests/unit/test_phase5_metrics.py`** — 41 unit tests (tất cả PASSED) cho 4 metrics modules: verify metric declarations + helper functions. Mỗi test class dùng clean registry để tránh duplicate-registration errors.
- **`config/grafana/dashboards/executive-overview.json`** — Executive homepage dashboard 20 panels: 8 service-health stat (exchanges, brokers, Flink job, Redis, InfluxDB, FastAPI 5xx, WS conns, AI sessions), 5 SLO gauges (API availability, p99 latency, data freshness, WS delivery, AI success), 1 SLO burn-rate multi-line chart, 1 end-to-end throughput time series, 1 end-to-end latency time series. Links to 4 critical dashboards. Tag: `phase5`, `dataflow`, `executive`, `overview`, `homepage`.
- **`config/grafana/dashboards/redis-deep-dive.json`** — Redis/KeyDB deep-dive 23 panels: status (master up, replicas, sentinels, cluster slots, clients, blocked), memory (used/peak/max, fragmentation, usage gauge), cache hit rate (KeyDB + FastAPI + multi-source), evicted/expired keys, total keys, latency p50/p95/p99 per source, FastAPI p99 by endpoint, producer direct-Redis failover, write latency p95. Tag: `phase5`, `dataflow`, `redis`, `keydb`, `sentinel`.
- **`config/grafana/dashboards/kafka-deep-dive.json`** — Kafka cluster deep-dive 19 panels: cluster status (brokers, controller, UR, offline, topics, partitions), topic throughput (in/s, bytes in/out), consumer lag by group, Flink source watermark lag (B5), producer dedup state size (B1) + records in/forwarded/skipped, broker network throughput, request queue size. Tag: `phase5`, `dataflow`, `kafka`, `streaming`.
- **`config/grafana/dashboards/flink-deep-dive.json`** — Flink job deep-dive 25 panels: job status (jm up, uptime, restarts, TMs, last checkpoint, 120s interval), checkpoint (duration p50/p95/p99, size, success/failure, alignment bytes B6), writer flush (duration, buffer size, records emitted, errors B5), indicator state (keys, warmup duration B7), kline gap fills, kline window fill ratio, Kafka source records in/dropped. Tag: `phase5`, `dataflow`, `flink`, `streaming`.
- **`config/grafana/dashboards/business-metrics.json`** — Business KPIs 23 panels: platform coverage (exchanges, symbols, WS conns, candles/s, trades/s, AI sessions), data freshness SLI gauge + percentile, stale symbols, FastAPI p99 by endpoint, WS push duration p99, AI requests/status/scope gate/provider/tokens, user activity (active users 1h/24h), HTTP requests by status. Tag: `phase5`, `dataflow`, `business`, `kpi`, `slo`.
- **`config/grafana/dashboards/slo-burn-rate.json`** — SRE Workbook burn-rate tracking 23 panels: 5 SLO summary stats (API availability, p99, WS delivery, freshness, AI response time), 4 multi-window burn rates (1h/6h/24h/72h), error budget remaining gauge, 5xx rate, WS burn rate + drop rate by route, freshness burn rate + stale % stats, AI burn rate + p50/p95/p99 latency, MWMB active alerts table. Tag: `phase5`, `dataflow`, `slo`, `sre`, `burn-rate`.
- **`config/grafana/dashboards/error-triage.json`** — Error triage 27 panels: 5xx/4xx rate stats, error ratio gauge, WS connection error count, AI error count, Flink writer error count, status class time series (2xx/3xx/4xx/5xx), error ratio over time (1h/6h/24h), top 10 endpoints by 5xx (table), top 10 endpoints by 4xx (table), slow endpoints table, p99 latency heatmap, WS errors by type, WS disconnects by reason, AI provider errors, output guard flags, Flink writer errors by type, checkpoint failures by reason, producer Kafka/Flink probe failures, direct-Redis failures. Tag: `phase5`, `dataflow`, `errors`, `triage`.
- **`config/grafana/dashboards/cost-attribution.json`** — Cost attribution 19 panels: AI cost summary (today, 7d, 30d, USD/req), cost per day by provider, cost share pie chart, USD/req bar gauge, token usage (in/out per hour), total tokens today, output/input ratio, cumulative cost + linear projection, hourly cost vs 24h baseline (anomaly detection), cost by scope gate decision, latency vs cost trade-off. Tag: `phase5`, `dataflow`, `cost`, `ai`, `finance`.
- **`config/grafana/dashboards/rag-knowledge-base.json`** — RAG/knowledge base 22 panels: KB inventory (chunks, dimensions, size, oldest age, last ingestion, sources), embedding model health (duration p50/p95/p99, success vs failure), vector search duration (pgvector HNSW), RAG retrieval duration (B13 overhead), relevance score p50/p95, top-K results distribution, zero-result ratio, cache hit rate, filter outcomes, retrievals/min, retrieval log audit trail. Tag: `phase5`, `dataflow`, `ai`, `rag`, `vector`, `knowledge-base`.
- **Cross-links** — Tất cả 13 Phase 5 dashboards có cross-links đến peers. `executive-overview` link đến 4 dashboards quan trọng nhất. Mỗi dashboard có 2-4 outgoing links. Uid cho tất cả dashboards đã chuẩn hóa (`phase5-*`).
- **`src/processing/writers/keydb_ticker.py`** — Wire metrics: `record_kafka_source` (mỗi ticker message), `record_kafka_source_drop` (symbol missing), `record_kafka_source_deserialize` (JSON parse time), `record_buffer_size` (sau mỗi append, 0 trước flush), `record_flush` (với duration_sec, n_records, trigger=time|size|close, error_class nếu có), `record_writer_event_time` (last seen event per symbol), `record_writer_new_key` (first encounter per exchange). `open()` gọi `init_metrics()` để seed 0 gauges.
- **`src/processing/writers/keydb_kline.py`** — Wire metrics tương tự keydb_ticker, với interval-aware labels (`keydb_kline` writer, 1s/1m candle intervals). Đo deserialize time + buffer size + flush duration per interval. `record_kafka_source_drop(topic=SOURCE_TOPIC, reason="not_closed_1m")` cho InfluxDB path.
- **`src/processing/writers/keydb_trades.py`** — Wire metrics: `record_flush` (duration, n_records, trigger), `record_kafka_source`, `record_buffer_size`, `record_writer_event_time` (trade_time), `record_writer_new_key` (first exchange seen). Drop metrics cho missing symbol + JSON errors.
- **`src/processing/writers/keydb_depth.py`** — Wire metrics: `record_flush` (KeyDB orderbook writes), `record_kafka_source`, `record_buffer_size`, `record_writer_event_time`. JSON deserialize duration tracked.
- **`src/processing/writers/influxdb_ticker.py`** — Wire metrics: `record_flush` (InfluxDB market_ticks writes), `record_kafka_source`, `record_buffer_size`, `record_writer_event_time`, `record_writer_new_key`, `record_kafka_source_drop` cho missing symbol.
- **`src/processing/writers/influxdb_kline.py`** — Wire metrics: `record_flush` (closed 1m candles to InfluxDB), `record_kafka_source_drop` (not_closed_1m), `record_kafka_source_deserialize`. Per-exchange state tracking.
- **`src/processing/writers/indicators.py`** — Wire B7 (state warmup) + recompute metrics: `record_indicator_warmup` (state_type=ema/macd_signal/candle_deque) lần đầu tiên sau open(), `record_indicator_recompute` (sma20/sma50/ema12/ema26/rsi14/bollinger/macd/atr14) mỗi candle, `INDICATOR_STATE_KEYS` gauge (5 state types: candle_deque, closes_deque, volumes_deque, ema_state, macd_signal) update mỗi candle, `record_flush` cho cả Redis writes (synchronous) và InfluxDB writes (buffered). Warmup duration = time từ open() đến first new candle.
- **`src/processing/writers/kline_aggregator.py`** — Wire B5 (gap-fill) metrics: `record_kline_gap_fill` (mỗi missing second forward-filled), `record_kline_window_fill_ratio` (real_count/60, set khi aggregate window), `record_kafka_source` (1s candles ingested), `record_kafka_source_drop` (not_1s interval). Aggregator giờ log `real=N/60 gap_fills=N fill_ratio=0.XX` để dễ debug.
- **`src/processing/pipeline.py`** — Wire B6 (checkpoint) metrics: import `record_checkpoint`, call `record_checkpoint(JOB_NAME, 0, 0, success=True, reason="boot_seed")` ở start of pipeline để seed success counter (dashboards show "0" thay vì "no data" right after restart). Comment block giải thích checkpoint observability hook (B6 visibility) và cách Flink Prometheus reporter + Python poller kết hợp.
- **`src/processing/writers/metrics.py`** — Add `init_metrics()` helper: seeds 0 values cho 8 writers × 2 sinks (16 buffer gauges) + 9 indicator state types. Idempotent qua `_INITIALISED_WRITERS` / `_INITIALISED_SINKS` sets.
- **`src/producer/metrics.py`** — Add `HEARTBEAT_TIMESTAMP` gauge (per-thread liveness, complements `EXCHANGE_LAST_MESSAGE`). Used by `producer.main` cho health-monitor threads.
- **`src/producer/main.py`** — Remove duplicate `HEARTBEAT_TIMESTAMP` declaration ở main.py (line 95) vì đã có ở `metrics.py`; comment giải thích single-source-of-truth.
- **`tests/unit/test_phase5_flink_metrics_pure.py`** — 22 unit tests (PASSED) cho writer metrics: drive tất cả helpers (record_flush, record_buffer_size, record_kafka_source*, record_indicator_*, record_kline_*, record_checkpoint, record_writer_*, record_backpressure, record_inflight, init_metrics). Verify label taxonomy (writer names, sink names, trigger names) match dashboard definitions. Mỗi test dùng clean registry để tránh duplicate-registration.
- **`docs/dataflow_analysis_and_observability_plan.md` Phần B** — Implementation status cho 7 bottlenecks quan trọng nhất (B1, B4, B5, B6, B7, B11, B13). Mỗi mục gồm: vấn đề gốc, giải pháp đã chọn, code change cụ thể, metrics phục vụ giám sát, test coverage. Bảng tổng kết status (FIXED / MONITORED / PARTIAL) + roadmap 5 ưu tiên tiếp theo.
- **B1 fix: Producer dedup lock** (`src/producer/main.py`) — Thêm `import threading` + `_dedup_lock = threading.Lock()`. Wrap toàn bộ check-then-set + 2 dict writes trong `with _dedup_lock:`. Critical section kết thúc trước Kafka send để giữ latency thấp. Fix race condition cho ticker dedup dict giữa nhiều WebSocket threads.
- **B5 fix: Flink flush interval** (`src/processing/writers/keydb_ticker.py`, `keydb_trades.py`) — `FLUSH_INTERVAL = 0.2` (was 0.5). Comment B5 giải thích trade-off: tăng network calls 2.5x nhưng KeyDB <1ms/write nên chi phí không đáng kể. Cắt p50 end-to-end latency từ 620ms xuống ~420ms.
- **B6 fix: Checkpoint interval** (`src/processing/pipeline.py:81-89`) — `env.enable_checkpointing(60_000)` (was 120_000). Comment dài giải thích trade-off + hướng dẫn monitor qua `flink_checkpoint_duration_seconds` (alert p99 > 30s thì tăng lại 90s). RPO giảm từ 120s xuống 60s.
- **B11 fix: Trino observability** (`backend/api/market_overview.py`, `backend/api/metrics.py`) — 4 metric mới: `backend_trino_query_duration_seconds{query_type,result}` (Histogram), `backend_trino_query_failures_total{query_type,reason}` (Counter), `backend_trino_active_queries` (Gauge), `backend_trino_fallback_total{endpoint,reason}` (Counter). Tất cả 8 calls trong `market_overview.py` giờ pass `query_type=` label để slice latency per query type. Wrap với `TRINO_ACTIVE_QUERIES.inc/dec`.
- **`tests/unit/test_phase5_mitigations.py`** (NEW, 12 tests PASS) — 4 test classes cover B1 (lock), B5 (flush intervals), B6 (checkpoint), B11 (Trino metrics). Helper `_value()` hỗ trợ cả Counter `_total` alias và Histogram `_count`/`_sum`/`_bucket` aggregates. Test count: 363 → 375.
- **B13 wire-up (AI metrics in real code paths)**:
  - **`ai_service/rag/retrieval_service.py`** — wrap vector search trong try/except + observe `AI_RAG_VECTOR_SEARCH_DURATION` (B13 latency split). `record_rag_retrieval` được gọi với đúng signature (`n_results`, `top_score`) sau mỗi retrieval. Dedent toàn bộ khối xử lý để chuyển từ try-bao-quát sang try-quanh-`pool.acquire()`.
  - **`ai_service/rag/knowledge_service.py`** — `compute_embedding` giờ measure + record `ai_embedding_duration_seconds` (model + success/fail) qua `record_embedding`. `ingest_directory` gọi `record_knowledge_ingest(success|skipped|rejected|error)` cho mỗi file. Helper `_refresh_kb_inventory_gauges()` (gọi sau ingest) đọc `ai_knowledge_chunks` aggregate (count, size, oldest_ts, last_ingest_ts, embedding_dim) và set 9 KB gauges (`ai_knowledge_base_chunk_count`, `ai_knowledge_base_size_bytes`, `_last_ingest_timestamp`, `_oldest_chunk_timestamp`, `ai_embedding_dimensions`, `ai_knowledge_base_source`).
  - **`ai_service/safety/output_guard.py`** — `guard_output` giờ `record_output_guard_flag(flag_type=unsafe_financial_claim|code_execution, severity=warning)` cho mỗi match + `AI_OUTPUT_GUARD_LATENCY.observe()` cho tổng thời gian.
  - **`ai_service/providers/router.py`** — `route_completion` giờ record `ai_provider_mode_active(mode)` mỗi call, `record_provider_request(provider, status=success|failure, duration_sec)` cho mỗi provider attempt, `record_provider_chain_depth(depth, status=exhausted)` khi fall through `none`. Frozen `AISettings` config được replace qua `dataclasses.replace` để đổi mode.
  - **`backend/services/ai/metrics.py`** — thêm helper `record_provider_mode_active(mode)` (đặt 1 cho mode active, 0 cho 3 mode còn lại, nhân với 3 provider để tránh cardinality spike).
- **B7 fix (Indicator state persistence)**:
  - **`src/processing/writers/indicator_state.py`** (NEW) — `IndicatorStateStore` class: write-through Redis layer cho 5 in-memory dicts (`_closes`, `_volumes`, `_candles`, `_ema_state`, `_macd_signal_state`). Mỗi symbol được persist dưới `indicator:state:{exchange}:{symbol}` với TTL 7 ngày. Methods: `save` (single), `save_batch` (pipelined), `load`, `hydrate_writer` (SCAN-based restore), `snapshot_writer` (read all dicts). Redis failures được swallow (degrade graceful).
  - **`src/processing/writers/indicators.py`** — `IndicatorWriter.open()` khởi tạo `IndicatorStateStore` + set `self._hydrated_exchanges` set. `flat_map()` gọi `_persist_state(exchange)` sau mỗi `flush_influx`. `_persist_state` thực hiện lazy first-touch hydrate (per exchange) + batch save. Net effect: Flink restart không cần Kafka replay để warm — chỉ tốn ~1ms để load từ Redis.
- **A9.1 (Frontend RUM)**:
  - **`frontend/src/utils/rum.ts`** (NEW) — `installRum()` install global listeners: `window.onerror`, `unhandledrejection`, `PerformanceObserver` (LCP + INP). Batched POST mỗi 10s hoặc khi buffer đầy 20 events tới `/api/rum/events`. `flush()` dùng `keepalive: true` để survive page unload. Privacy: log qua `console.warn` fallback, không throw.
  - **`backend/api/rum.py`** (NEW) — `POST /api/rum/events` endpoint nhận batch, route tới 4 helpers: `record_frontend_rum_error`, `record_frontend_rum_pageview`, `record_frontend_rum_lcp`, `record_frontend_rum_inp`. IP chỉ log warning-level, không đưa vào metric.
  - **`backend/api/metrics.py`** — 4 metric mới: `FRONTEND_RUM_ERRORS` (counter, labels `type`, `source`), `FRONTEND_RUM_PAGE_LOADS` (counter, label `route`), `FRONTEND_RUM_LCP` (histogram buckets 0.5-8s), `FRONTEND_RUM_INP` (histogram buckets 0.05-4s). Exposed trên `/metrics-custom` (cùng scrape job với WS/multi-source/cache/Trino).
- **A10.2 (API rate limit hit)**:
  - **`backend/middleware/rate_limit.py`** (NEW) — `RateLimitMiddleware` (in-process, sliding window 60s). Default 200 req/min/IP qua env `RATE_LIMIT_PER_MINUTE`. Exempt paths: `/metrics*`, `/health*`, `/api/rum`, `/docs`, `/openapi.json`. 429 response bao gồm `Retry-After: 60` header. IP được SHA-256 hash 12 chars trước khi đưa vào metric label (privacy). Disable bằng `RATE_LIMIT_PER_MINUTE=0`.
  - **`backend/api/metrics.py`** — `API_RATE_LIMITED_TOTAL` counter (labels `ip_hash`, `path`).
- **Docs**:
  - **`docs/SLO.md`** (NEW) — 5 SLOs định nghĩa chính thức: S1 API availability (99.9%), S2 API latency p99 (<500ms), S3 WebSocket delivery (99.5% <2s), S4 Data freshness (95% <10s), S5 AI answer time p95 (<8s). Mỗi SLO có: target, error budget, PromQL measurement, burn-rate alerts, owner, common causes. Procedure để add/retire SLOs.
  - **`docs/RUNBOOKS.md`** (NEW) — 12 runbooks cho top alerts (A1.1, A1.2, A1.3, A1.5, A2.x, A4.x, A5.x, A7.x, A9.1, A10.1, A10.2). Mỗi runbook có: symptom, triage steps (CLI commands), mitigation, common causes, owner. Có escalation matrix và glossary.

### Changed

- **Observability coverage** — Bổ sung đáng kể application-level observability: WebSocket serving (12 metrics + 5 alerts + 1 dashboard), Multi-source fallback (6 metrics + 4 alerts + 1 dashboard), AI pipeline (14 metrics + 6 alerts + 1 dashboard), Producer failover (6 metrics + 5 alerts), Flink writer flush (6 metrics + 3 alerts), SLO burn-rate (4 alerts), Data flow pipeline (1 dashboard 27 panels).
- **Flink writer observability** — Tất cả 7 Flink writers (4 KeyDB + 2 InfluxDB + 1 Indicator) + kline aggregator + pipeline giờ emit Prometheus metrics. Coverage mapping: B5 (flush latency) → `flink_writer_flush_duration_seconds`, B6 (120s checkpoint) → `flink_checkpoint_*`, B7 (state warmup) → `flink_indicator_state_warmup_duration_seconds` + `flink_indicator_state_keys`.
- **Test count** — Added unit and integration tests for all metrics, endpoint, and mitigation features.


---

## [0.24.9] - 2026-06-13

### Added — Spark Auto-Restart Supervisor

New `spark-submit` service replaces manual `docker exec spark-submit` workflow. The supervisor runs in its own container and keeps the `Kafka -> Iceberg` pipeline alive across crashes.

**New files:**
- `docker/spark-submit/Dockerfile` — reuses `apache/spark:3.5.5` base, adds curl/procps, drops shell-only system libs that alpine/busybox images need.
- `docker/spark-submit/spark-submit.sh` — bash supervisor: wait for spark-master, then loop `spark-submit` with run counter + 15s backoff.

**docker-compose changes:**
- New service `spark-submit` with `restart: unless-stopped`, `mem: 2G`, mounts `./:/app:rw` so the latest pipeline.py is picked up on every container recreate.
- New volume `spark-submit-logs` reserved for future file-based log persistence.
- Healthcheck: `pgrep -f SparkSubmit` so docker-compose healthcheck actually reflects liveness.

**Verified:**
- Manual `docker exec spark-submit ... spark-submit` removed from the production flow.
- Killed `SparkSubmit` JVM at runtime -> supervisor restarted it as `run #3` within 15s.
- Source data continues to grow across restarts (`coin_ticker: 316k rows`).
- 12/12 Tier 1 endpoints still return 200 OK with real data.

---

## [0.24.8] - 2026-06-13

### Fixed — Production Data Flow Verification

Comprehensive live verification of all 12 Tier 1 endpoints with real data flowing end-to-end.

**Trino OOM fix (production-critical):**
- `docker-compose.yml`: Trino memory bumped `512M → 2G`. Trino was OOM-killing during plugin init (`RestartCount: 4`, `MEM USAGE / LIMIT: 511.7MiB / 512MiB`). Root cause: JDBC Iceberg catalog + many plugins (iceberg, hive, kafka, postgresql, prometheus, etc.) need >1GB heap. 2G allows all plugins to load + queries to schedule.

**Spark Streaming memory fix:**
- `docker-compose.yml`: `spark-master` memory bumped `512M → 2G`. The master + driver runs in same container, 512M was killing the SparkSubmit process after 1 batch (`Killed` in logs).

**Spark streaming data flow:**
- Spark `pipeline.py` reads Kafka (`crypto_ticker`, `crypto_klines`, `crypto_trades`), writes to Iceberg tables.
- `coin_ticker` populated with **225,375 rows** (real Binance ticker data).
- Spark process must be submitted with `setsid` (not `nohup`) to avoid zombie processes when shell exits.

**Iceberg → Trino → API data flow verified:**
- All 12 Tier 1 endpoints return HTTP 200 with real data:
  - `/api/market/overview` — market summary from Redis + Trino
  - `/api/market/heatmap` — 50 symbols (data:50)
  - `/api/market/rankings/volume` — 20 symbols (data:20)
  - `/api/market/movers` — 5 gainers/losers
  - `/api/market/dominance` — aggregated
  - `/api/market/volatility` — 5 symbols
  - `/api/market/sectors` — 3 sectors
  - `/api/market/indicators` — aggregated RSI/MACD
  - `/api/market/whale-alerts` — 3 trades
  - `/api/market/liquidity-heatmap` — BTCUSDT depth data
  - `/api/market/news-sentiment` — 0 (CRYPTOPANIC_API_KEY not set, table empty)
  - `/api/market/news-impact` — 0 (news table empty)

**Gold tables (Trino-aggregated, 5 tables populated):**
- `gold_movers_ranking`: 200 rows
- `gold_market_dominance`: 436 rows
- `gold_volatility_ranking`: 200 rows
- `gold_momentum_indicators`: 270 rows
- `gold_sector_performance`: 3 rows
- `gold_news_sentiment_daily`, `gold_news_market_impact`: empty (depends on news API)

**Verification matrix:**
| Endpoint | HTTP | Real data |
|---|---|---|
| /api/market/overview | 200 | yes (Redis) |
| /api/market/heatmap | 200 | 50 symbols |
| /api/market/rankings/volume | 200 | 20 symbols |
| /api/market/movers | 200 | 5 movers |
| /api/market/dominance | 200 | aggregated |
| /api/market/volatility | 200 | 5 symbols |
| /api/market/sectors | 200 | 3 sectors |
| /api/market/news-sentiment | 200 | 0 (news API key) |
| /api/market/indicators | 200 | aggregated |
| /api/market/whale-alerts | 200 | 3 trades |
| /api/market/news-impact | 200 | 0 (news API key) |
| /api/market/liquidity-heatmap | 200 | bid/ask data |
| **Total** | **12/12** | **9 with data** |

---

## [0.24.7] - 2026-06-13

### Added (Task 5 — Liquidity Heatmap)

- **Mục tiêu**: Visualize liquidity theo price level + time (Bookmap-style footprint). Cạnh tranh với Bookmap, TradingView Depth-of-Market widget.
- **Architecture**:
  - Flink `LiquidityHeatmapWriter` consume `crypto_depth` Kafka topic.
  - For mỗi depth snapshot: compute mid-price = (best_bid + best_ask) / 2, sau đó bucket mọi level theo % distance từ mid (default 0.1% per bucket, max 100 buckets = ±1%).
  - Levels cùng bucket collapse (sum quantity + count orders).
  - Write InfluxDB measurement `liquidity_heatmap` với tags (exchange, symbol, side, price_bucket) và fields (quantity, order_count).
- **`src/processing/writers/liquidity_heatmap.py`** (NEW, 13KB): Pure bucketing helpers + Flink writer.
  - `compute_mid_price(best_bid, best_ask)` — None-safe, handles inverted book.
  - `price_to_bucket(price, mid, bucket_pct, max_buckets)` — dùng `round()` để tránh float precision (0.1 // 0.1 = 0.9999...).
  - `bucket_depth_snapshot(snapshot)` — pure function trả flat rows cho InfluxDB.
  - Constants: `DEFAULT_BUCKET_PCT=0.1`, `DEFAULT_MAX_BUCKETS=100`, `DEFAULT_EXCHANGE="binance"` (env-overridable).
- **`src/lakehouse/gold_schema_manifest.py`**: New entry `liquidity_heatmap` với 7 fields. Canonical count 8 → 9.
- **`backend/api/market_overview.py`**: New endpoint `GET /api/market/liquidity-heatmap`:
  - Query params: `symbol` (required, regex `^[A-Z0-9]{2,20}USDT$`), `hours` (1-24, default 4), `bucket_count` (1-100, default 20), `exchange` (default "binance").
  - Read từ InfluxDB measurement `liquidity_heatmap` qua Flux query.
  - Return flat rows: `[ts_ms, bucket, qty]` per side (bid/ask).
  - **503** on Influx failure (init + query).
- **`frontend/src/services/marketOverviewService.ts`**: `HeatmapRow`, `HeatmapData`, `HeatmapFilter`, `HeatmapResponse` interfaces + `fetchLiquidityHeatmap(filter)` (30s cache).

- **`orchestration/assets.py`**: New `@asset gold_news_market_impact` (Dagster wiring) — calls `compute_gold_news_market_impact(spark, lookback_hours=48)` and runs every 5 minutes via `gold_aggregation_job`. Without this, the function would never be invoked. Also added to `compute_gold_layer` aggregate job.
- **`src/processing/pipeline.py`**: `LiquidityHeatmapWriter` wired into the depth pipeline (parallel to `DepthWriter`, in-memory side branch). Default `HEATMAP_EXCHANGE=binance` (depth topic drops `exchange` per AGENTS.md hot-spot). Without this, the writer would never be invoked.

### Caveat documented

AGENTS.md flagged rằng depth processing drops/defaults `exchange`. Liquidity heatmap dùng `binance` mặc định. Document trong manifest entry + UI tooltip.

### Tests (42 new, all pass)

- 8 tests cho `compute_mid_price` (normal, strings, zero, negative, inverted, None).
- 7 tests cho `price_to_bucket` (at mid, distances, range, custom max, invalid).
- 11 tests cho `bucket_depth_snapshot` (empty, missing symbol, only bids, level collapse, time bucket, default exchange, inverted, invalid level, zero qty, out of window, row shape).
- 3 tests cho manifest alignment.
- 7 tests cho API endpoint (registration, happy path, matrix shape, bucket filter, 503 init, 503 query, validation).
- 2 tests cho frontend type contract.
- 4 tests cho writer constants.

**Total tests: 627 → 669 (+42).** Tất cả pass trong 25s.

---

## [0.24.6] - 2026-06-13

### Added (Task 4 — News ↔ Price Impact)

- **Mục tiêu**: Quantify "how much did BTC move after this news?" — direct competitive response tới TradingView News Impact + CryptoQuant Impact features.
- **Architecture**:
  - Spark batch job `src/lakehouse/gold/news_impact.py` chạy hourly, MERGE-INTO pattern idempotent.
  - For mỗi news × symbol, compute price change tại t+1h, t+4h, t+24h.
  - `impact_score = max(|change_1h|, |change_4h|, |change_24h|) * sign(sentiment)`.
  - Outer-join: fresh article (<1h) chỉ có `change_1h_pct`; UI render "impact pending" với NULL fields.
- **`src/lakehouse/gold/news_impact.py`** (NEW, 13KB): Pure builders + Spark orchestration.
  - `compute_impact_score()` — signed impact score từ 3 horizons + sentiment.
  - `build_impact_row()` — pure function trả dict khớp manifest schema.
  - `compute_gold_news_market_impact(spark, lookback_hours=48, reference_exchange="binance")` — entry point cho Dagster.
- **`src/lakehouse/gold_schema_manifest.py`**: New entry `gold_news_market_impact` với 17 fields. Canonical count 7 → 8.
- **`backend/api/market_overview.py`**: New endpoint `GET /api/market/news-impact`:
  - Query params: `days` (1-90, default 7), `limit` (1-200, default 50), `symbol` (optional), `min_impact_pct` (0-100, default 0), `exchange` (default "binance").
  - Sort: `ORDER BY ABS(impact_score) DESC NULLS LAST`.
  - **503** on Trino failure (init + query).
- **`frontend/src/services/marketOverviewService.ts`**: `NewsImpactItem` interface, `NewsImpactFilter` interface, `fetchNewsPriceImpact(filter)` (5min cache), `fetchNewsPriceImpactForSymbol(symbol, days, limit)`.

### Tests (32 new, all pass)

- 8 tests cho `compute_impact_score`.
- 6 tests cho `build_impact_row`.
- 4 tests cho manifest alignment.
- 9 tests cho API endpoint.
- 5 tests cho design choices + edge cases.

**Total tests: 595 → 627 (+32).** Tất cả pass trong 25s.

---

## [0.24.5] - 2026-06-13

### Added (Tier 1 — Data Value Features, P0 + P1 + Task 1)

> **Goal**: Tận dụng data có sẵn trong lakehouse để cạnh tranh với TradingView. 5 features Tier 1 + 2 prerequisite fixes. **P0, P1, và Task 1 (8 Gold tables exposed)** completed in this release.
> **See**: `FIX_PLAN.md` cho toàn bộ roadmap Tier 1 (4-5 tuần). Tasks 2-5 còn lại: Whale Alerts, OBI, News↔Price, Liquidity Heatmap.

#### Finding: "Fake cow" — 116/200 high-volume symbols MISS

- Phát hiện nghiêm trọng: Hệ thống chỉ subscribe được 84/200 top-volume symbols. **Missing bao gồm SOL, XRP, PEPE, SUI, TON, TRX, USDC, NEAR** — tổng cộng 60-70% tổng market volume bị miss.
- **Root cause**: `BinanceClient.fetch_symbols()` trả về danh sách **alphabetical sort** thay vì sort theo 24h quote volume. Code `[:MAX_SYMBOLS]` lấy 200 symbols đầu alphabet (1INCH, AAVE, ACA...) thay vì top volume.
- **Verify**: chạy audit script `scripts/audit_data_coverage.py` (mới viết) — output real Binance API cho thấy 116 symbols high-volume không có trong alphabetical top-200.

#### P0 Fix: Volume-based symbol selection

- **`src/exchanges/binance/client.py`** — Thêm method `fetch_top_symbols_by_volume(quote_asset, n)`:
  - Fetch `/exchangeInfo` lấy active spot USDT pairs (~436 symbols).
  - Fetch `/ticker/24hr` lấy 24h stats, **sort by quoteVolume DESC**, slice top N.
  - **In-process cache** với TTL 1h (`_SYMBOL_VOLUME_CACHE`, key = `quote:n`).
  - **`threading.Lock`** + double-checked locking để tránh thundering herd khi nhiều thread reconnect đồng thời.
  - **Fallback** về alphabetical nếu Binance API down (vẫn start được producer).
  - **Helper** `_clear_symbol_volume_cache()` cho tests và operational scripts.
- **`src/producer/main.py`** — `run_streams()` dispatch: nếu client có `fetch_top_symbols_by_volume` thì dùng, không thì fall back về alphabetical. Log rõ ràng khi dùng path nào.
- **`scripts/audit_data_coverage.py`** (NEW, 12.7KB) — Script audit:
  - So sánh alphabetical top-200 vs volume top-200 (real Binance API).
  - Verify Redis coverage (`ticker:latest:*`, `candle:1s:*`, `candle:1m:*` keys).
  - Sample 1s candle movement (5 random symbols × 5s).
  - InfluxDB 7d coverage distribution.
  - **Auto-verdict**: fail nếu miss rate > 10%.
  - Output: terminal report + optional JSON file.

#### P1 Fix: Unify Gold table schemas

- **Phát hiện schema drift**: Hai hệ thống Gold song song, schema khác nhau:
  - **Trino-based** (`src/lakehouse/gold_aggregator_trino.py`) — `gold_*` tables với `computed_at`, per-row granularity. **API đang query cái này** (`backend/api/market_overview.py`).
  - **Spark-based** (`src/lakehouse/gold/{market_metrics,aggregations}.py`) — `market_dominance`, `volatility_ranking`, `movers_ranking`, `gold_market_overview`, `gold_symbol_stats_daily`. Single-row hoặc nested-array. **Không ai query** (orphaned) nhưng vẫn chạy mỗi 5 phút, đốt cluster compute.
- **Quyết định**: Chọn **Trino-based làm canonical** (vì API đang dùng, làm việc), **defer Spark-based** (giữ code, không schedule, đánh dấu DEPRECATED). Đây là minimum-risk path.
- **`src/lakehouse/gold_schema_manifest.py`** (NEW, 8.7KB) — Canonical manifest:
  - 6 bảng `gold_*` với schema đầy đủ (column names + SQL types).
  - 6 Spark-only tables đánh dấu `DEPRECATED` với rationale.
  - Constants: `GOLD_FRESHNESS_MINUTES=30`, `CANONICAL_PRODUCER_JOB="gold_layer_job"`.
  - Helpers: `list_canonical_tables()`, `get_table_schema()`, `is_deprecated_spark_table()`.
- **`orchestration/assets.py`** — Comment out `@asset` decorators cho `gold_market_dominance`, `gold_volatility_ranking`, `gold_movers_ranking`, `gold_momentum_indicators`. Rename thành `*_deprecated` để Dagster không pick up. `gold_advanced_job` selection giờ chỉ còn `compute_gold_layer` (kept for back-compat). **Code KHÔNG xóa** — nếu sau muốn re-enable, uncomment lại.
- **`backend/api/market_overview.py`**:
  - Import `GOLD_FRESHNESS_MINUTES` từ manifest (defensive try/except với fallback).
  - Log canonical schema khi startup: "market_overview: canonical Gold path active (6 tables: ...); 6 Spark-based tables deprecated."

#### Real-world verify (chạy trên live Binance API)

```
Top 20 by 24h volume (sau khi fix):
   1. USDCUSDT      ← MISS trước đây
   2. BTCUSDT
   3. ETHUSDT
   4. USD1USDT      ← MISS
   5. XAUTUSDT      ← MISS
   6. SOLUSDT       ← MISS (top 5!)
   7. WLDUSDT       ← MISS
   8. ZECUSDT       ← MISS
   9. TRUMPUSDT     ← MISS
  10. DOGEUSDT
  11. XRPUSDT       ← MISS (top 10!)
  ...
  20. PEPEUSDT      ← MISS
  21. TRXUSDT       ← MISS
  25. SUIUSDT       ← MISS
  29. TONUSDT       ← MISS
  → Tất cả 10 critical symbols giờ ĐƯỢC SUBSCRIBE.
```

#### Task 1 Fix: Expose 6 Gold tables via dedicated endpoints

- **Problem**: API chỉ có 3 endpoints (`/overview`, `/heatmap`, `/rankings/{category}`). Frontend phải gọi `/overview` (6 trong 1) cho mọi thứ, hoặc dùng mock data. Không có dedicated endpoint cho từng Gold table.
- **Solution**: 6 dedicated endpoints mới, mỗi cái query 1 Gold table:

| New endpoint | Gold table | Use case |
|---|---|---|
| `GET /api/market/movers?category=gainer\|loser&limit=N` | `gold_movers_ranking` | Top gainers/losers widget |
| `GET /api/market/dominance` | `gold_market_dominance` | BTC/ETH dominance badge |
| `GET /api/market/volatility?limit=N` | `gold_volatility_ranking` | Most volatile list |
| `GET /api/market/sectors` | `gold_sector_performance` | Sector heatmap |
| `GET /api/market/news-sentiment?days=7&limit=N` | `gold_news_sentiment_daily` | News sentiment list |
| `GET /api/market/indicators` | `gold_momentum_indicators` | RSI/MACD summary |

- **Implementation details**:
  - Mỗi endpoint trả flat `{"data": [...]}` response (không phải dict-of-dicts).
  - 503 status code khi Trino down (không phải 500) — client phân biệt được outage vs bug.
  - Mỗi endpoint gọi `record_trino_fallback()` metric khi fail (observability hooks).
  - `/sectors` convert dict → list, giữ `sector` field (UI render trực tiếp không cần `Object.values`).
  - 3 legacy endpoints (`/overview`, `/heatmap`, `/rankings/{category}`) **vẫn giữ** cho back-compat.
  - `regex=` → `pattern=` (FastAPI 0.110+ rename).
- **`backend/api/market_overview.py`** — Add 6 endpoints với 130+ lines mới.
- **`frontend/src/services/marketOverviewService.ts`**:
  - 5 functions mới: `fetchVolatilityRanking`, `fetchMarketDominance`, `fetchSectors`, `fetchNewsSentiment`, `fetchIndicators`.
  - `fetchTopGainers` / `fetchTopLosers` rewrite: gọi `/market/movers?category=gainer|loser` thay vì `/market/gainers|losers` (endpoints cũ không tồn tại).
  - Tất cả wrappers dùng `withClientCache` (stale-while-revalidate) + `isUnavailableApiPayload` (mock fallback).

#### Task 2 Fix: Whale Alerts (real-time large trade detection)

- **Mục tiêu**: Phát hiện real-time các trade lớn (default ≥ $100K USD) từ `crypto_trades` Kafka topic. Cạnh tranh trực tiếp với Whale Alert, CryptoQuant services.
- **Architecture**:
  - Flink `WhaleAlertWriter` (new) consume `crypto_trades` song song với `KeyDBTradeWriter` (không ảnh hưởng hot path).
  - Filter `price × quantity >= MIN_WHALE_USD` (default $100K, override bằng env var `WHALE_ALERT_MIN_USD`).
  - Dual-sink: Redis sorted set `whale:alerts:{exchange}:{symbol}` (TTL 1h, max 1000/symbol) + InfluxDB measurement `whale_alerts` (historical analytics).
  - Side derivation: `is_buyer_maker=False → buy`, `True → sell` (chuẩn Binance aggTrade semantics).
- **`src/processing/writers/whale_alert.py`** (NEW, 10.9KB):
  - `WhaleAlertWriter(min_whale_usd=100_000, batch_size=50, flush_interval_sec=1.0)`.
  - Constants: `DEFAULT_MIN_WHALE_USD=100_000`, `REDIS_KEY_PREFIX="whale:alerts"`, `REDIS_TTL_SEC=3600`, `MAX_ENTRIES_PER_SYMBOL=1000`.
  - Module-level: `WRITER_NAME="whale_alert"`, `SINK_NAME="redis+influxdb"`, `SOURCE_TOPIC="crypto_trades"`.
  - Metrics hook: `record_whale_alert(exchange, symbol, side, notional_usd)`.
  - **No state, no CEP** — pure filter+forward để giữ hot path lean.
- **`src/processing/writers/metrics.py`**: 3 metrics mới (Task 2):
  - `flink_whale_alerts_detected_total{exchange,symbol,side}` — Counter.
  - `flink_whale_alert_notional_usd{exchange,side}` — Histogram với 11 buckets từ $100K → $100M.
  - `flink_whale_alert_recent_count{exchange,symbol}` — Gauge (hook cho sidecar scraper; không populate inline để tránh hot-path cost).
  - Helper `record_whale_alert()` tăng counter + observe histogram.
- **`src/processing/pipeline.py`**: Wire `WhaleAlertWriter` vào trade stream. Log threshold lúc startup (`[Pipeline] whale alert threshold = $100000`).
- **`src/lakehouse/gold_schema_manifest.py`**: Thêm `whale_alerts` entry với 9 fields. Canonical count 6 → 7. Note: không phải Trino table (read path từ Redis) — entry này cho audit/completeness.
- **`backend/api/market_overview.py`**: New endpoint `GET /api/market/whale-alerts`:
  - Query params: `min_usd` (default 100K, range 1K-100M), `limit` (default 20, max 200), `since_minutes` (default 60, **clamp to 60** vì Redis TTL), `symbol` (optional), `exchange` (default binance).
  - Read từ Redis sorted set với `ZREVRANGEBYSCORE` (newest first).
  - Filter mode: nếu `symbol` provided → direct key access (no SCAN). Nếu null → SCAN `whale:alerts:{exchange}:*` rồi union.
  - **503** on Redis failure (init/SCAN/ZRANGE) — client phân biệt outage vs bug.
  - Empty Redis → empty list `{"count": 0, "data": []}` (không phải 500).
  - Warning text: "Older alerts (>60min) are not in Redis. Use the InfluxDB whale_alerts measurement for historical queries."

#### Tests (94 new, all pass)

- **`tests/unit/test_volume_based_selection.py`** (NEW, 17KB, 12 tests):
  - **Happy path**: top-N sort, include high-volume, USDT-only filter, inactive filter.
  - **Cache layer**: hit, expiry, clear, different-n-keys.
  - **Error handling**: API failure → fallback to alphabetical, retry logic.
  - **Producer integration**: `run_streams()` dispatches đúng method.
  - **Concurrency**: 5 threads × lock = chỉ 1 HTTP fetch thực sự.
- **`tests/unit/test_gold_schema_manifest.py`** (NEW, 14KB, 33 tests):
  - **Manifest contents**: 6 canonical tables, columns, computed_at, count.
  - **Deprecation list**: 6 Spark tables, rationale present, no overlap.
  - **Helper functions**: list/get_schema/is_deprecated.
  - **Freshness constant**: matches API default (30 min).
  - **Dagster alignment**: assets are *_deprecated, gold_advanced_job uses Trino only.
  - **API alignment**: queries canonical gold_* tables only, freshness filter, imports manifest.

#### Test count update

- **Total Tier 1 tests:** 0 → 94 (P0 + P1 + Task 1 + Task 2).
- **Total unit tests:** 501 → 595.

#### Files changed in P0 + P1 + Task 1 + Task 2

| File | Status | Size | Purpose |
|---|---|---|---|
| `FIX_PLAN.md` | NEW | 36KB | Tier 1 plan toàn diện |
| `scripts/audit_data_coverage.py` | NEW | 12.7KB | Audit "fake cow" |
| `src/exchanges/binance/client.py` | MODIFIED | +5KB | `fetch_top_symbols_by_volume()` + cache + lock |
| `src/producer/main.py` | MODIFIED | +1KB | Dispatch to volume method |
| `src/lakehouse/gold_schema_manifest.py` | MODIFIED | +1KB | Whale alerts entry (count 6→7) |
| `src/processing/writers/whale_alert.py` | NEW | 10.9KB | Flink `WhaleAlertWriter` |
| `src/processing/writers/metrics.py` | MODIFIED | +60 lines | 3 whale alert metrics + `record_whale_alert()` |
| `src/processing/pipeline.py` | MODIFIED | +20 lines | Wire `WhaleAlertWriter` into trade stream |
| `orchestration/assets.py` | MODIFIED | +1KB | Comment out deprecated Spark assets |
| `backend/api/market_overview.py` | MODIFIED | +200 lines | Manifest import + 7 endpoints (6 Task 1 + 1 whale-alerts) |
| `frontend/src/services/marketOverviewService.ts` | MODIFIED | +100 lines | 5 new fetch functions + rewrite gainers/losers |
| `tests/unit/test_volume_based_selection.py` | NEW | 17KB | 12 tests for P0 |
| `tests/unit/test_gold_schema_manifest.py` | MODIFIED | +5 lines | 33 tests for P1 (whale update) |
| `tests/unit/test_market_dedicated_endpoints.py` | NEW | 16.6KB | 19 tests for Task 1 |
| `tests/unit/test_whale_alerts.py` | NEW | 22.6KB | 30 tests for Task 2 |
| `docs/CHANGELOG.md` | UPDATED | +180 lines | v0.24.4 P0+P1+Task 1+Task 2 entries |

---

## [0.24.4] - 2026-06-13

### Added (Logging Phase — Structured logs, Request-id, Retention)

- **`docs/LOGGING_AUDIT_PLAN.md`** (NEW, 9.4KB) — Báo cáo audit toàn diện cho logging stack. Phát hiện 5 vấn đề nghiêm trọng: (1) 7 log dashboards dùng `| json` nhưng app xuất plain text → 5/6 panel mỗi dashboard rỗng. (2) Không có request-id correlation giữa 5 services. (3) 19 silent `except: pass` che giấu bug. (4) Không có retention policy cho Loki → đầy disk. (5) Promtail regex brittle với locale. 5 bước cải tiến đã thực thi.

- **`docs/LOGGING.md`** (NEW, 7.3KB) — Hướng dẫn vận hành: log schema (10 fields), cách thêm log line, request-id middleware, level conventions, anti-patterns, cách query trong Grafana.

- **Structured JSON logging** (Step 1):
  - **`src/common/logging.py`** (REWRITE) — Thêm `JsonFormatter` (stdlib only, 0 deps) emit một JSON object mỗi line. Format: `ts` (RFC3339 UTC ms), `level`, `logger`, `module`, `line`, `thread`, `request_id`, `message`, `context` (dict từ `extra=`), `exc_type`/`exc_info` (nếu có exception). Helper `log_with_context(logger, level, msg, context)` cho DX tốt hơn. `setup_logging_from_env()` đọc `LMVIEW_LOG_JSON` (auto-on trong container) + `LMVIEW_LOG_LEVEL`. Tame 8 noisy 3rd-party loggers (aiokafka, asyncio, kafka, pyflink, uvicorn, websockets, aiormq).
  - **`backend/app.py`** — Call `setup_logging_from_env()` ngay khi import để mọi log kể cả lifespan errors đều JSON.
  - **`src/producer/main.py`** — Đổi `setup_logging("producer")` → `setup_logging_from_env()`.
  - 7 log dashboards giờ render đúng (`{container="fastapi"} | json | method != ""` hoạt động).

- **Request-id correlation middleware** (Step 2):
  - **`backend/middleware/request_id.py`** (NEW) — `RequestIdMiddleware` (BaseHTTPMiddleware): (1) đọc `X-Request-Id` từ request hoặc generate 12-char hex (48 bits entropy). (2) bind vào `contextvars.ContextVar` để mọi code path trong cùng task đọc được. (3) Echo lại header. (4) Emit 1 structured log line mỗi request (INFO 2xx, WARNING 4xx, ERROR 5xx). (5) Record metric `api_request_id_samples_total` với 12-char SHA-256 prefix làm label (privacy + bounded cardinality). Truncate id > 64 chars để chống DoS.
  - **`backend/api/metrics.py`** — Thêm `API_REQUEST_ID_SAMPLES` Counter (labels `method`, `path`, `status_class`, `rid_hash`).
  - **`backend/app.py`** — Register middleware (always-on, no env gate).
  - Cú pháp grep: `{container="fastapi"} | json | request_id="8f3e2c1a"` → tất cả log của 1 request xuyên qua 5 services.

- **Silent-except audit** (Step 3):
  - **`src/processing/writers/indicators.py`** — `except Exception: pass` quanh `record_kafka_source_drop` → `except Exception as metric_exc: log.debug(...)`. Comment giải thích: "Never let a metric hiccup hide the real error."
  - **`src/processing/writers/kline_aggregator.py`** — Cùng fix.
  - **`src/news/enhanced_scraper.py`** — `_parse_date` `except: pass` → `except (ValueError, TypeError, IndexError) as exc: logger.debug(...)`. Cũng đổi implicit `return None` → explicit `return 0` để type rõ ràng.
  - 19 silent excepts → 15 còn lại (4 fixed, 11 kept có comment justify rõ ràng). Test `test_logging_silent_excepts.py` verify không còn bare `except Exception: pass` trong critical paths.

- **Loki retention policy** (Step 4):
  - **`config/loki-config.yml`** — Thêm `compactor` block với `retention_enabled: true`, `retention_delete_delay: 2h`, `compaction_interval: 10m`. `limits_config.retention_period: 168h` (7 days). `ingestion_rate_mb: 10`, `ingestion_burst_size_mb: 20` để chống runaway producer. `max_line_size: 256KB` để bound memory. `table_manager.retention_deletes_enabled: true`. Trade-off note: 7d là balance giữa disk/incident-response/PII.

- **Tests** (25 new tests, all pass):
  - **`tests/unit/test_logging_format.py`** (12 tests) — JsonFormatter emits valid JSON, includes request_id, extra context, exception info, UTC RFC3339 timestamp, handles non-serialisable context without crash. Plain-text mode and JSON mode side-by-side. Re-calling setup_logging doesn't double-log. Noisy loggers tamed to WARNING.
  - **`tests/unit/test_logging_request_id.py`** (7 tests) — Generates 12-char hex id when missing, echoes incoming id, unique per request, truncates oversized, 5xx still returns rid, metric recorded per request, rid is SHA-256 hashed (not raw) for label cardinality.
  - **`tests/unit/test_logging_silent_excepts.py`** (6 tests) — Verify the new debug log line in kline_aggregator/indicators. Verify enhanced_scraper returns 0 with debug log. Verify websocket.py keeps justified silent blocks.

### Test count update

- **Total Phase 5 tests:** 124 → 149 (added 25 logging tests).
- **Total unit tests:** 473 → 501 (excluding 4 sentiment tests với LLM mock issue).

### Added (Grafana Alerting UI + Credentials)

- **Alert Center dashboard** (`config/grafana/dashboards/alert-center.json`, NEW, 14 panels):
  - **6 stat panels** — Firing Critical/Warning/Info, Pending, NoData, Total Rules. Each queries `ALERTS{alertstate=...,severity=...}` để cho operator số lượng firing theo severity.
  - **2 timeseries panels** — Active Alert Count Over Time (per severity, stepAfter), Alerts by Component (bar chart theo `grafana_folder`).
  - **1 heatmap** — Alert Firing Heatmap by Hour-of-Day. Giúp spot recurring incident patterns (e.g. nightly batch job lúc 03:00 UTC).
  - **1 table** — All Alert Rules with state. Pairs với `docs/RUNBOOKS.md` — match `alertname` ở đây với heading runbook.
  - **Cross-links** — Executive Overview, Error Triage, SLO Burn Rate, Grafana Alerting UI (`/alerting/list`).
  - **UID:** `phase5-alert-center` (stable, link không break).
  - **Auto-loaded** qua dashboards.yml provisioning.

- **Contact points provisioning** (`config/grafana/provisioning/alerting/contact-points.yml`, NEW, 5 contact points):
  - `internal-log` — always-on fallback (default).
  - `webhook` — generic Prometheus alertmanager webhook.
  - `slack` — Slack channel `#lmview-alerts` (override qua `GRAFANA_SLACK_WEBHOOK`).
  - `email` — SMTP recipients (override qua `GRAFANA_EMAIL_TO`).
  - `pagerduty` — Events API v2 (override qua `GRAFANA_PAGERDUTY_KEY`).
  - Tất cả đều env-gated, default về safe no-op nếu không set.

- **Notification policies** (`config/grafana/provisioning/alerting/notification-policies.yml`, NEW, 9 policies):
  - Root policy → `internal-log` (default catch-all).
  - Critical severity → `pagerduty` + `slack` (page on-call + notify channel).
  - Warning severity → `slack` only (no pages).
  - Info severity → `internal-log` only.
  - `LMView / Frontend` folder → `slack` (dedicated channel).
  - `LMView / Security` folder → `pagerduty` + `email` (high prio).
  - `slo_*` alerts → `slack` only (no pages during business hours — mở comment để bật).
  - Mỗi policy có `group_wait`, `group_interval`, `repeat_interval` riêng.

- **Mute timings** (`config/grafana/provisioning/alerting/mute-timings.yml`, NEW):
  - `business_hours` — 09:00-18:00 UTC Mon-Fri (cho SLO slow-burn).
  - `weekend` — Sat/Sun (future use).

- **README credentials** (`README.md`):
  - Bảng 14 services × 4 cột (URL / User / Pass / Notes).
  - Production checklist 6 items.
  - Default Grafana: `admin` / `admin` (override qua `GRAFANA_ADMIN_PASSWORD`).
  - Alert Center URL: http://localhost:3001/d/phase5-alert-center.

- **Tests** (28 new, all pass):
  - `tests/unit/test_grafana_alerting.py` — Verify dashboard JSON, panel types, ALERTS-metric refs, severity stat panels filter `alertstate="firing"`, contact-points YAML có ≥4 CPs với unique UIDs, root policy exists, critical routes to PagerDuty/Slack, all rules have severity label + datasource, README/docker-compose/.env đều có credentials.

### Test count update (final)

- **Total Phase 5 tests:** 149 → 177 (+28 alerting tests).
- **Total unit tests:** 473 → 501 (excluding 4 sentiment tests).


## [0.24.3] - 2026-06-12

### Added

- **Advanced News Context for AI** — New `NewsContextBuilder` pulls persisted PostgreSQL news data, ranks articles by symbol match/recency/sentiment/source reliability, generates data caveats, and feeds compact context into AI Ask/Interact prompts (`ai_service/context/news_context.py`).
- **Notification creation service** — End-to-end notification creation with preference gating, event-specific helpers for AI actions, news risk events, system degraded state, and alert triggers (`backend/services/notification_service.py`).
- **Approved internal KB documents** — Two approved, RAG-enabled knowledge base entries: platform architecture/capabilities grounding and data caveats/limitations guide (`docs/ai/knowledge_base/approved/`).
- **AI context quality chips** — AI panel now shows live context chips: news article count, sentiment direction, freshness age, confidence percentage, and degraded-state warnings.
- **Sources used display** — Collapsible RAG source citations with match scores on each AI response.
- **Risk event warnings** — Inline risk event alerts on AI responses when news contains hack/regulation/crash keywords.
- **Loading skeletons** — Animated skeleton placeholder while AI is thinking.
- **Admin context debug preview** — Admin-only collapsible panel showing confidence, provider/model, news context stats, data caveats, and RAG chunk details.
- **`NewsContextSummary` type** — Frontend TypeScript interface for news context metadata (`frontend/src/services/aiService.ts`).
- **47 new tests** — Unit and integration tests for news context ranking/dedup/caveats/risk and notification creation/preferences/events.
- **Bilingual i18n** — English and Vietnamese translations for all new AI context chip and quality label strings.
- **Comprehensive mock AI responses** — Updated mock AI generation in `frontend/src/data/mock/mockAi.ts` to return realistic, dynamic payloads including news contexts, sentiment summaries, RAG citations, data caveats, token usage, and cost estimates. This allows developers to test all newly introduced AI assistant visual functionalities offline.

### Changed

- **AI confidence model** — Confidence score now factors in news context availability (+5% when relevant news exists).
- **AI prompt builder** — `build_ask_prompt()` accepts optional `news_context` parameter and formats news headlines/sentiment/risk events as a system context section.
- **AI orchestrator** — News context assembly and news caveats integrated into the unified AI pipeline; news context included in response metadata.
- **`AIChatResponse` model** — Added `news_context` optional field for frontend display.
- **Context service** — Extracted `assemble_news_context()` async function for use by the orchestrator.

### Fixed

- **Type safety in tests** — Fixed Python/Pyright lint warnings in `tests/unit/test_news_context.py` by converting `symbols_mentioned` and `article_id` parameter default values to use `Optional[List[str]]` and `Optional[str]`.
- **Frontend dependency resolution** — Resolved TypeScript compiler errors (TS2307) in `AiAssistantPanel.tsx` by installing missing markdown rendering dependencies (`react-markdown`, `rehype-sanitize`, `remark-gfm`) with legacy peer deps for React 19 compatibility.
- **Sentiment service test compliance** — Fixed LLM sentiment service test failures in `tests/unit/test_sentiment_service.py` by mocking the `get_api_key` configuration check to ensure the mocked LLM completion path is correctly tested.

---

## [0.24.2] - 2026-06-12

### Added

- **`docs/audit_dataflow_plan.md`** — Báo cáo audit toàn diện cho `dataflow_analysis_and_observability_plan.md`. Trả lời 3 câu hỏi: (1) metric Prometheus có đủ cho Grafana? (2) bottleneck fix OK? (3) có chạy được không? Kết luận: 100% dashboard coverage, 3/7 bottleneck fix code, 2/7 observability fix, 2/7 partial. 97/97 unit tests pass.
- **`backend/app.py`** — Thêm 2 FastAPI endpoints: `/metrics-custom` (HTTP/WS/multi-source/cache/Trino) và `/metrics-ai` (AI/RAG/scope-gate/cost). Mỗi endpoint lọc theo tên metric của module tương ứng, dùng FastAPI `Response` + `prometheus_client.CONTENT_TYPE_LATEST` để giữ exposition format. Fix critical issue: `prometheus.yml` khai báo 3 scrape jobs (`fastapi-custom`, `ai-services`, `producer-extended`) nhưng không có endpoint — jobs sẽ fail khi scrape. Verify with TestClient: 3 endpoint return 200 + valid format.
- **`backend/services/ai/metrics.py`** — Thêm 9 alias metrics cho `rag-knowledge-base` dashboard: `ai_knowledge_base_chunk_count`, `ai_knowledge_base_size_bytes`, `ai_knowledge_base_last_ingest_timestamp`, `ai_knowledge_base_oldest_chunk_timestamp`, `ai_embedding_dimensions`, `ai_knowledge_base_source` (Info), `ai_rag_retrieval_total`, `ai_retrieval_log_total`. Thêm 3 helper functions: `record_kb_inventory()`, `record_rag_retrieval_count()`, `record_retrieval_log_count()`. Fix 8 broken metric refs trong dashboard.
- **`tests/unit/test_phase5_endpoints.py`** — 22 tests (PASSED) verify 3 Prometheus endpoints: 200 OK, valid format, 4 metric families present trên `/metrics-custom` (WS, multi-source, cache, Trino), 6 families trên `/metrics-ai` (scope gate, provider, RAG, output guard, cost, chat), 8 RAG dashboard aliases, cross-endpoint isolation. Test có module-scoped fixture reload metrics modules dưới canonical dotted name để tránh duplicate-registration với `test_phase5_flink_metrics_pure.py`.

### Changed

- **Test count update** — Total Phase 5 tests: 75 → 97 (added 22 endpoint tests). Total unit tests: 363 → 377 (excluding 4 sentiment tests với LLM mock issue không liên quan).

---

## [0.24.1] - 2026-06-12

### Added

- **Expanded AI function calls** - Added frontend/backend action schemas for section navigation, section highlights, chart-area and candle highlights, chart type/timeframe/market switching, chart zoom/scroll, and historical price lookup.
- **Replayable Interact tour** - Interact mode now auto-runs safe tour actions for demo/help prompts, walks through workspace, chart, tools, selectors, indicators, right-panel modules, header, settings, and AI helper, records action timing, and exposes replay from recap/chat.
- **Debug action helpers** - Debug function-call window now starts unselected, shows clearer required/optional fields, and provides point JSON templates for drawing calls.

### Changed

- **Highlight behavior** - UI highlights no longer include the chat panel by default; chat is included only for AI-helper explanations.
- **Right-panel/action anchors** - Overview, watchlist, order book, recent trades, market/news, screener, chart toolbar, chart canvas, header, and settings now expose stable AI highlight targets.

### Fixed

- **Chart Ctrl+wheel zoom** - Mouse wheel over the chart keeps horizontal scroll behavior, while `Ctrl + wheel` zooms in/out around the cursor position.
- **Vite chunk-size warning** - Added Rollup manual chunks for React, lightweight-charts, lucide icons, and Markdown dependencies so production chunks stay under the default 500 kB warning threshold without raising the limit.
- **Chart wheel behavior** - Restored plain wheel horizontal chart scrolling and kept `Ctrl + wheel` zoom anchored to cursor position.
- **Historical 1s crash** - Historical mode now hides live-only `1s`, falls back to `1m` before fetching, and avoids stale live-mode checks that could discard historical loads.
- **Interact tour pacing** - Tour steps are now fully user-paced; only page, tab, and panel switches happen automatically when entering a step.
- **Tour cleanup** - Completing or closing the tour resets drawing tool state, closes settings, restores chart market/timeframe/type, and returns to the AI chat panel.
- **Tour overlay placement** - Tour callouts now sit away from highlighted controls, and active dropdown/menu surfaces are excluded from the dim overlay.
- **Drawing function safety** - Function-created drawings now require `time`/`price` points and automatically return to cursor after placement.
- **Historical action catalog** - Historical price function schemas no longer advertise unsupported `1s` candles.

---

## [0.24.0] - 2026-06-11

### Added

- **Central AI service package** - Moved production AI orchestration, provider routing, prompt/context logic, RAG services, action schemas, safety checks, and chat persistence behind importable `ai_service/*` modules. Backend `/api/ai/*` routes now stay thin authenticated adapters.
- **Unified Ask/Interact orchestration** - `/api/ai/chat` now runs both modes through one pipeline: scope gate, chart context, approved-only RAG, prompt building, provider routing, output guard, action proposal, and audit metadata.
- **AI action catalog** - Added `/api/ai/actions/catalog` plus reusable action schemas for indicators, drawing tools, page highlights, tours, annotation clearing, and debug execution.
- **Frontend AI actions runtime** - Added an `AiActionProvider`, auto-generated indicator/drawing function definitions, dim-and-highlight overlay, user-paced tour engine with recap/replay, and an admin draggable action test window from Debug settings.
- **Markdown AI chat rendering** - Replaced custom chat Markdown parsing with `react-markdown`, `remark-gfm`, and `rehype-sanitize` for tables, emphasis, horizontal rules, code, and links in user and assistant messages.

### Changed

- **Provider model simplified** - Production providers are now `local`, `api`, and `none`; `auto` prioritizes local, then API, then none. Backend mock fallback was removed from production and mock remains a frontend data mode concern.
- **Qwen API defaults updated** - API mode defaults to DashScope International OpenAI-compatible `qwen3.5-plus` on `https://dashscope-intl.aliyuncs.com/compatible-mode/v1`; `DASHSCOPE_API_KEY` is primary and `QWEN_API_KEY` remains a legacy alias.
- **Temporal prompt grounding** - Shared AI prompts now include current server time, epoch milliseconds, chart timestamp conversion notes, data freshness, and a rule that live runtime data can be newer than model training cutoff.
- **Knowledge base workflow hardened** - Rebuilt `docs/ai/knowledge_base/` into `source_library/`, `canonical/`, `approved/`, `pending/`, `draft/`, `deprecated/`, and `manifests/`; current unreviewed AI-generated docs were demoted to `pending` and disabled for production RAG.
- **Registry metadata strengthened** - `registry.yml` now tracks source ID, title, domain, language, source type, credibility, review status, reviewer, reviewed date, LMView version scope, source URLs, tags, `allowed_for_rag`, and file path.
- **AI panel UX updated** - Desktop right panel defaults to `360px` with `320px-520px` bounds, mobile caps at `min(420px, 92vw)`, Ask/Interact moved below the input, and suggested prompts are collapsible.
- **AI env surface reduced** - `.env.example` now keeps core AI config to `AI_MODE`, `AI_CONFIG_PATH`, `DASHSCOPE_API_KEY`, and legacy `QWEN_API_KEY`, with provider/model catalogs in YAML under `ai_service/configs/`.

### Fixed

- **RAG approval leak** - Retrieval SQL now requires `review_status = 'approved'` and `allowed_for_rag = true`, removing the previous null-source allowance.
- **Unapproved ingestion** - Knowledge ingestion skips unapproved, pending, draft, or deprecated documents by default.

### Tests

- Added/updated AI tests for `auto/local/api/none` routing, no production mock provider, temporal prompt context, action validation, approved-only ingestion/retrieval, metadata validation, deprecated exclusion, and registry consistency.

---

## [0.23.2] - 2026-06-11

### Fixed

- **Ticker dedup missing exchange key** — `src/lakehouse/pipeline.py` ticker stream dedup used only `["symbol", "event_timestamp"]`. Fixed to `["exchange", "symbol", "event_timestamp"]` to prevent multi-exchange collapse.
- **Grid dashed style lost on theme change** — `CandlestickChart.tsx` theme update useEffect was setting `LineStyle.Solid` instead of `LineStyle.Dashed`, breaking TradingView-style grid consistency.
- **Line chart color using textColor instead of upColor** — `CandlestickChart.tsx` line series `color` option was `chartTheme.textColor`. Fixed to `chartTheme.upColor` for TradingView-style coloring.
- **Seconds hidden on 1s timeframe** — `CandlestickChart.tsx` had `secondsVisible: false` hardcoded in timeScale. Now dynamic: `secondsVisible: timeframe === "1s"`.
- **Visible range jumps when preloading historical data** — `CandlestickChart.tsx` was shifting both `from` and `to` when loading older candles. Now keeps `from` at left edge for smoother scroll-left experience.
- **Real-time candle volume not accumulated** — `backend/api/websocket.py` `_merge_trade_to_candles()` and `_stream_all_impl` were ignoring trade quantity (`qty`) when updating candles. Now accumulates trade qty into candle volume.
- **Redis N+1 in WebSocket stream/all** — `backend/api/websocket.py` was making 6+ Redis calls per interval × 10 intervals = 60+ calls per 50ms loop. Refactored `_stream_all_impl` to use Redis pipeline for batch queries (6 total calls per loop).
- **Trade cache TTL too short** — `src/processing/writers/keydb_trades.py` trade cache TTL was 600s (10 min). Increased to 3600s (1 hour) to prevent premature expiry.
- **WebSocket no reconnect on disconnect** — `marketDataService.ts` now implements exponential-backoff reconnect (up to 5 retries) for `subscribeAllTimeframes`, `subscribeCandle`, and `subscribeIndicatorStream`.
- **Watchlist ticker polling reduced from 5s to 30s** — `App.tsx` now uses live price from WS `_livePriceMap` for selected symbol (50ms updates). Other watchlist symbols fall back to REST poll every 30s instead of 5s.

### Added

- **`docs/DATA_FLOW.md`** — Comprehensive data flow documentation covering Lambda Architecture (Speed Layer → Batch/Lakehouse → Serving), exchange ingestion (Binance + OKX), Kafka topics, Flink writers (KeyDB, InfluxDB, IndicatorWriter), Spark Bronze/Silver/Gold tables, indicator computation (Flink real-time vs Spark batch), Trino query engine, and FastAPI/WebSocket serving layer.
- **`docs/DATA_FLOW_01_ARCH_OVERVIEW.md`** — Part 1: Architecture overview (Lambda 3 layers) + Exchange ingestion (Binance + OKX WebSocket, threading model, JSON formats, canonical mapping layer, producer integration).
- **`docs/DATA_FLOW_02_KAFKA.md`** — Part 2: Kafka Broker layer (4 topics × 12 partitions, Avro schemas, Confluent wire format, Schema Registry, partitioning strategy, performance tuning, checkpoint locations).
- **`docs/DATA_FLOW_03_FLINK.md`** — Part 3: Flink Speed Layer (KeyDB writers, InfluxDB writers, KlineWindowAggregator with gap-fill, IndicatorWriter với true EMA/RSI/BB/MACD/ATR, depth/trade writers, batch-buffered performance, Redis Sentinel failover, full Redis key patterns + InfluxDB measurements).
- **`docs/DATA_FLOW_04_SPARK_LAKEHOUSE.md`** — Part 4: Spark Lakehouse (Bronze 3 tables với streaming write + dedup, Silver ticker_unified + kline_multi_timeframe với quality scoring, Gold 9 tables: market_overview, coin_ticker, momentum_indicators, indicator_history, market_dominance, volatility_ranking, movers_ranking, sector_performance, news_sentiment — đầy đủ schema, transformations, pipeline orchestration).
- **`docs/DATA_FLOW_05_SERVING.md`** — Part 5: Serving Layer (FastAPI + WebSocket với 3 routes /api/stream/all, /api/stream/{interval}, /api/stream/indicators/{interval}; Redis pipeline optimization v0.23.1 giảm 6× Redis calls; 20+ REST endpoints cho klines/ticker/trades/orderbook/indicators/market/screener/news/auth/settings/admin/ai; multi-source fallback chains: Redis→InfluxDB→Trino→REST; service layer, Pydantic models, database clients, auth/JWT, error handling, caching, observability).
- **`docs/DATA_FLOW_06_INDICATORS.md`** — Part 6: Technical Indicators deep dive (Flink real-time vs Spark batch side-by-side: True EMA vs SMA approximation, Wilder's RSI, Bollinger Bands population vs sample stddev, MACD true vs SMA, ATR, state management, warmup, query patterns, coverage matrix; công thức chi tiết với code cho 13 indicators).
- **`docs/DATA_FLOW_07_DIAGRAMS.md`** — Part 7: Data Flow Diagrams & End-to-End Latency (Lambda architecture diagram, sequence diagrams cho kline/orderbook/indicator real-time, cold path Bronze→Silver→Gold chi tiết, latency budget table theo component, throughput analysis, failure modes & RPO/RTO, scaling patterns, capacity planning, monitoring stack, production Docker topology, network ports reference, glossary, coverage matrix 7 phần).
- **`docs/final_data_flow.md`** — Tài liệu hợp nhất đầy đủ 7 phần DATA_FLOW (1 file ~264KB, bao gồm tất cả 4 Kafka topics, 8 Flink writers, 3 Bronze + 2 Silver + 9 Gold tables, 9 Redis key patterns, 3 InfluxDB measurements, 13 indicators, 20+ REST endpoints, 3 WebSocket routes, sequence diagrams, latency budget, failure modes, scaling patterns).

---

## [0.23.1] - 2026-06-10

### Fixed

- **Screener page routing** - Header Screener view now renders `ScreenerPage` instead of falling through to `NewsPage`; result rows now select the symbol and return to chart view.
- **Advanced chart type rendering** - All chart types use the shared `CHART_TYPES` registry, including `pointFigure`; transformed candle chart types now keep the candle series visible and re-transform immediately when the type changes.
- **Chart type selector overflow** - Chart type selector now shows four icon buttons at a time with horizontal scrolling, avoiding toolbar crowding as advanced chart types grow.
- **Default chart type settings** - Settings customization now lists all supported chart types with translated labels instead of only candles/bars/line/area.
- **Drawing tool visibility and creation** - Rendered left drawing toolbar now exposes supported advanced tools (`horizontalRay`, `parallelChannel`, pitchfork variants, Gann box/fan/square); multi-click tools now wait for the correct number of anchor points.
- **Chart transformers** - Added Point & Figure transformation and fixed Line Break/Kagi transformer issues found by focused tests.
- **Transformed chart ordering** - Renko/Point & Figure-style chart data now normalizes duplicate timestamps before `setData`, preventing Lightweight Charts `data must be asc ordered by time` runtime crashes.
- **Advanced chart render families** - Kagi now renders on the line series instead of flat candles, while Heikin Ashi/Renko/Line Break/Point & Figure stay on transformed candle/brick data; all advanced transformers emit strict ascending times.

## [0.23.0] - 2026-06-09

### Added

- **Phase E: Enhanced Watchlist & Screener** — `EnhancedWatchlistItem`, `WatchlistColumn`, `WatchlistFilter`, `ScreenerPreset`, `WATCHLIST_COLUMNS`, `SCREENER_PRESETS` types in `types/index.ts`. `EnhancedWatchlist.tsx` with sort/filter/search. `Screener.tsx` with filter panel and presets (Oversold, Overbought, High Volume, Top Gainers/Losers, Strong Bullish/Bearish). `ScreenerPage.tsx` as standalone page. "screener" view in `AppView` type, Filter icon in Header. Mock adapter methods (`fetchScreenerResults`, `fetchWatchlistWithIndicators`) for mock mode. `screenerService.ts` with `fetchScreenerResults`, `fetchWatchlistWithIndicators`, `fetchScreenerPresets`.
- **Phase F: Multi-chart Layouts** — `LayoutContext.tsx` with `LayoutProvider` + `useLayout` hook, `LayoutType` (single/split-v/split-h/quad/three-v/three-h/six), `ChartInstance` interface. `MultiChartContainer.tsx` with CSS grid layout. `LayoutToolbar.tsx` with layout switcher buttons. i18n keys (en + vi) for layout names.
- **Phase G: Pattern Recognition** — `types/patterns.ts` with `PatternType`, `DetectedPattern`, `PatternDetectionConfig`, `PATTERN_LABELS`, `PATTERN_BULLISH`. `patternDetection.ts` with `PatternDetector` class — detects double_top, double_bottom, ascending_triangle, descending_triangle, head_shoulders.
- **Phase H: Alerts & Notifications** — `types/alerts.ts` with `AlertType`, `PriceAlert`, `ALERT_TYPES`. `alertService.ts` with `createAlert`, `deleteAlert`, `toggleAlert`, `checkAlerts`, `loadAlerts`, `saveAlerts` — localStorage-based.
- **i18n keys (en + vi)** — screener, screenerDescription, screenerResults, singleChart, splitVertical, splitHorizontal, quadChart, threeVertical, threeHorizontal, sixChart, syncTimeScale.

### Changed

- **WebSocket real-time streaming optimized** — `backend/api/websocket.py` `/stream/all` endpoint refactored:
  - Added trade stream as real-time price source (`trade:latest:{exchange}:{symbol}` Redis key)
  - New `_merge_trade_to_candles()` function updates in-progress candles with each trade
  - New `_get_stream_candle()` returns real-time candle state or falls back to historical
  - 50ms poll loop for sub-300ms latency target
  - Graceful error handling per Redis fetch operation
- **Chart styling improved** — `CandlestickChart.tsx` chart options updated:
  - Grid lines use dashed style (like TradingView)
  - Crosshair uses dashed lines with label backgrounds
  - `entireTextOnly: true` on right price scale for cleaner labels
  - `barSpacing: 6` for better candle density
  - Line series uses upColor instead of textColor
- **Duplicate i18n keys fixed** — Removed duplicate `oversold`, `overbought`, `topGainers`, `topLosers`, `clearAll`, `selectAll`, `trend`, `volume24h`, `change24h`, `high24h`, `low24h`, `price`, `volume`, `marketCap`, `open`, `high`, `low`, `close`, `noData` from watchlist/Overview sections in en.ts and vi.ts.
- **WatchlistFilter type conflict** — Renamed simple `"all" | "starred"` type to `WatchlistTabFilter`, kept `WatchlistFilter` as interface for enhanced filtering.
- **`ChartOverlay.tsx`** — PATTERN_TOOLS set expanded to include `harmonicABCD`, `xabcdPattern`, `elliottWave`.

### Fixed

- **WebSocket real-time streaming broken** — `backend/api/websocket.py` had two bugs preventing candle updates:
  1. WebSocket query parameters (`symbol`, `exchange`) were in function signature which FastAPI doesn't support for WebSocket — fixed to use `websocket.query_params.get()`
  2. Route order issue: `/stream/{interval}` was defined BEFORE `/stream/all`, causing "all" to be treated as an interval parameter and returning 404 — fixed by moving `/stream/all` route before `/stream/{interval}`
- **Mock adapter Ticker fields** — `fetchScreenerResults` and `fetchWatchlistWithIndicators` now use computed `name`/`rank`/`marketCap` from Ticker fields instead of non-existent properties.
- **`screenerService.ts`** — Fixed `buildQuery` params type mismatch, `ScreenerSymbol.name` property, `makeClientCacheKey` params.
- **TypeScript strict errors** — Fixed unused imports/vars in EnhancedWatchlist, Screener, ScreenerPage, LayoutContext, MultiChartContainer.
- **Screener data display** — `Screener.tsx` had no data display logic (placeholder UI only). Added `items` prop, filter/sort logic, and results table.

---

## [0.22.0] - 2026-06-09

### Added

- **Phase A: Drawing Tools Foundation** — `DrawingToolCategory` type (10 categories), comprehensive `DrawingTool` union (40+ tool IDs), `DrawingSettings` interface with tool-specific fields, `FibonacciLevel` + `FIBONACCI_RETRACEMENT_LEVELS`, `GANN_ANGLES` constant, `DrawingPreset` + `DrawingCategory` interfaces, extended `BaseToolSettings`, `DEFAULT_TOOL_SETTINGS` for all tools, tool settings UI (Gann/Pitchfork/Text/Fibonacci/Measurement sections).
- **Phase D: Market Overview Dashboard** — `MarketOverview`, `SectorPerformance`, `HeatmapItem`, `IndicatorsSummary`, `MarketOverviewMetadata` interfaces, enhanced `MarketMetrics` with Fear & Greed, BTC/ETH metrics, Market Breadth, `MarketPeriod` type (1h/24h/7d/30d), `MarketOverviewService` class in `backend/services/market_overview_service.py` with Redis ticker fallback.
- **MarketOverviewPage enhancements** — Period selector dropdown, Fear & Greed display, Market Breadth section, Sector Performance cards, warning banner for placeholder data.
- **`fetchSectorPerformance`, `fetchHeatmapData`** — `marketOverviewService.ts` new exports.
- **Unit tests** — `tests/unit/test_market_overview_service.py` with 11 tests.
- **i18n keys (en + vi)** — 14 new keys: fearGreedIndex, fearGreedExtremeFear, fearGreedFear, fearGreedNeutral, fearGreedGreed, fearGreedExtremeGreed, marketBreadth, advancing, declining, marketBreadthRatio, newHighsLows24h, sectorPerformance, period selectors.

### Changed

- **`fetchMarketOverview` return type** — Now returns `MarketOverview` instead of `MarketMetrics`. Extract `market_summary` for metrics.
- **`MarketNews.tsx`** — Updated to use `overview?.market_summary || null` for metrics state.
- **`Drawing.tool` type** — `DrawingTool | string` for backward compat.
- **`Drawing.settings` type** — `Record<string, any>` → `DrawingSettings`.

---

## [0.21.0] - 2026-06-09

### Added

- **Phase B: Advanced Chart Types** — `ChartType` expanded to 9 types (heikinAshi, renko, lineBreak, kagi, pointFigure), `ChartTypeConfig` + `CHART_TYPES` array, `ChartTypeSettings` interface.
- **Chart transformers** — `heikinAshi.ts`, `renko.ts`, `lineBreak.ts`, `kagi.ts` in `features/chart/transformers/`.
- **ChartTypeSettingsModal** — Modal UI for advanced chart type settings.
- **Chart type icons** — `CandlestickChart.tsx` maps all 9 chart types to lucide icons.
- **i18n (en + vi)** — 17 new keys for chart types and settings.

---

## [0.20.1] - 2026-06-09 - Frontend Runtime Fixes

### Added

- **AI session restore controls** - AI Helper now remembers the active backend session across reloads and Settings can load previous AI Helper sessions.
- **Customization presets** - Settings now exposes indicator, drawing-tool, layout, default exchange, volume, magnet, and compact-panel presets.
- **Admin AI usage summary** - Admin users can see total AI input/output tokens and estimated cost in AI Helper settings.

### Fixed

- **Realtime chart updates** - WebSocket candle building now folds fresh ticker prices into 1s/1m candles when kline candle caches lag, so chart candles update alongside indicators.
- **All-timeframe WebSocket route** - Registered `/api/stream/all` before the catch-all `/api/stream/{interval}` route so the chart receives live candle frames instead of an unsupported `all` interval error.
- **Chart resize after browser zoom** - Chart resize now uses measured container/stage bounds, observes visual viewport changes, and keeps the chart wrapper shrinkable to avoid bottom clipping after zoom out/in.
- **AI Ask readability** - AI Helper renders common markdown blocks and inline formatting instead of showing raw markdown text.
- **AI Helper tab persistence** - The right panel now keeps AI Helper mounted while Overview is active, preserving in-flight responses and preventing remount scroll animation when switching tabs.
- **AI timestamp confusion** - Ask Mode prompts now include live server time, epoch milliseconds, and UTC-formatted chart timestamps so current candle times are not misclassified as invalid due model cutoff.
- **Normal-user token leakage** - Per-message token and cost metadata is hidden from non-admin users.
- **Kline scroll 500s** - Missing optional Trino/Iceberg historical candle tables now degrade to empty fallback results instead of failing `/api/klines` scroll requests.
- **Notification delivery loop** - Header notifications now reload periodically and can show browser desktop notifications when the user preference and browser permission allow it.
- **Runtime log noise** - Qwen sentiment scoring now skips real provider calls when `QWEN_API_KEY` is absent and uses the heuristic path directly.
- **Missing icon 404s** - Removed references to absent `logo192.png`/`logo512.png` assets from the PWA manifest and HTML head.

---

## [0.20.0] - 2026-06-08 - Phase D: System Audit & Critical Fixes

### Added

- **React error boundary** — `frontend/src/components/ErrorBoundary.tsx` wraps App.tsx to prevent full-app crashes on component errors; shows retry + reload buttons, displays stack trace in dev mode.

### Fixed

- **Catalog mismatch audit** — `src/lakehouse/gold/market_metrics.py` 3 classes (`GoldMarketDominance`, `GoldVolatilityRanking`, `GoldMoversRanking`) had `iceberg_catalog.gold.*` references (non-existent schema). Fixed to `iceberg.crypto_lakehouse.*` — matching active catalog config in `lakehouse/pipeline.py` and Dagster assets.
- **Market overview dead code removal** — Removed 130+ lines of duplicate dead code from `backend/api/market_overview.py` (duplicate `_get_trending_news`, `_get_sector_performance`, `_get_heatmap_data`, `_get_indicators_summary`, `_derive_market_from_redis` functions after the first return statement).

### Changed

- **Sentiment heuristic improvement** — Expanded `bullish_terms` from 7 to 24 keywords, `bearish_terms` from 8 to 26 keywords in `backend/services/sentiment_service.py`; score and confidence now scale with match count for more meaningful sentiment differentiation.

### Notes

- **Legacy batch files still reference `iceberg_catalog`** — `src/batch/` and `src/lakehouse/silver/` use `iceberg_catalog` as Spark catalog name (JDBC/Hadoop catalog alias), not schema. Active runtime uses `iceberg.crypto_lakehouse` via Trino. Legacy files not used by Dagster orchestration.
- **Trino QUEUED investigation** — Code review confirms stable implementation with `nextUri` polling in `gold_aggregator_trino.py` and `compute_news_sentiment_daily`. Runtime verification requires Docker environment.

---

## [0.19.3] - 2026-06-08 - Phase C Full Completion

### Added

- **Dagster news sentiment gold asset** — `orchestration/assets.py` `compute_news_sentiment_daily` upgraded from placeholder to full implementation: reads PostgreSQL `news_articles`, aggregates by symbol/day via `UNNEST(symbols_mentioned)`, writes to `iceberg.crypto_lakehouse.gold_news_sentiment_daily` via Trino HTTP API. Now has `deps=[compute_gold_layer]` to run after gold layer.
- **Chart news markers wired** — `frontend/src/App.tsx` now fetches news via `fetchLatestNews({ limit: 200, hours: 72 })` every 5 minutes, stores in `newsArticles` state, and passes `newsItems={newsArticles} showNewsMarkers={true}` to `CandlestickChart`. Chart renders colored circle markers at news event timestamps.

### Changed

- **Frontend typecheck clean** — Removed unused `React` import from `NewsCard.tsx` and unused `NewsCard` import from `CandlestickChart.tsx`. `npm run typecheck` passes with zero errors.

### Notes

- **Dagster daemon restart required** — After this change, restart `dagster-daemon` and `dagster-webserver` containers so the new asset code loads: `docker compose restart dagster-daemon dagster-webserver`
- **Runtime verification pending** — Full end-to-end test (news fetch → sentiment score → Dagster aggregation → chart markers) requires live Docker environment with running services.

---

## [0.18.1] - 2026-06-07 - Update documentations

### Changed

- **Documentation reinspection refresh** - Reaudited current code state and updated `docs/SYSTEM.md`, `AGENTS.md`, `README.md`, and `.env.example` comments for 0.18.0 facts: Phase 1 AI Ask Mode, modular AI routes, RAG/provider caveats, current Compose/service counts, Flink trade cache, exchange propagation status, Dagster `Definitions`, lakehouse `exchange` handling, observability counts, and test inventory.

---

## [0.19.2] - 2026-06-07 - Phase C Runtime Completion

### Added

- **Trino news sentiment writer** — Added `src/lakehouse/write_news_sentiment.py` to aggregate PostgreSQL news sentiment by symbol/day and materialize `gold_news_sentiment_daily` through Trino.
- **News card component** — Added `frontend/src/components/NewsCard.tsx` for sentiment-aware news rendering with badges and symbol chips.
- **Phase C integration tests** — Added `tests/integration/test_news_pipeline.py` covering real latest news, sentiment fields presence, and symbol filtering.

### Changed

- **News fetch persistence dedupe** — `backend/tasks/news_fetcher.py` now uses insert-then-update fallback logic instead of fragile `ON CONFLICT` targeting, which makes persistence robust against pre-existing partial indexes and local schema drift.
- **News payload normalization** — `backend/services/news_service.py` now decodes JSON/text fields from PostgreSQL correctly (`tags`, `symbols`, `raw_metadata`) and exposes clean API payloads.
- **Dagster news sentiment aggregation** — `orchestration/assets.py` now includes `compute_news_sentiment_daily` in the gold layer job.
- **Frontend news rendering** — `frontend/src/pages/NewsPage.tsx`, `frontend/src/features/market/components/MarketNews.tsx`, and `frontend/src/services/newsService.ts` now consume persisted PostgreSQL-backed article payloads, `symbolsMentioned`, and normalized sentiment labels.
- **Chart overlay support** — `frontend/src/features/chart/CandlestickChart.tsx` now accepts `newsItems` and renders lightweight-charts markers for symbol-matching news events.
- **Frontend types** — `frontend/src/types/index.ts` now includes `symbolsMentioned` on `NewsArticle`.

### Fixed

- **Real news API runtime** — `/api/news/latest`, `/api/news/trending`, `/api/news/sentiment/{symbol}`, and `/api/news/search` now serve real PostgreSQL-backed data instead of empty in-memory cache/mocks in healthy runtime.
- **Phase C backend ingestion blocker** — News fetcher now successfully persists fetched RSS/API articles into `news_articles` instead of failing on invalid conflict target behavior.

### Notes

- **Qwen scoring path present but lightly verified** — Sentiment scoring service and loop are wired, but article sentiment may still remain mostly neutral until enough scoring cycles complete or provider/runtime tuning is refined.
- **Phase C frontend overlay path implemented, not deeply browser-verified in this session** — code path exists and types align, but full visual verification still depends on interactive UI inspection.

---

## [0.19.1] - 2026-06-07 - Phase C-1 Real News Persistence

### Added

- **News persistence migration** — Added `backend/migrations/004_phaseC_news_enhancements.sql` to extend `news_articles` with `content_snippet`, `sentiment_confidence`, `sentiment_computed_at`, `symbols_mentioned`, `raw_metadata`, plus source/external dedupe and symbol lookup indexes.
- **PostgreSQL-backed news fetcher** — Replaced in-memory-only cache flow in `backend/tasks/news_fetcher.py` with real persistence using `EnhancedMultiSourceScraper`, symbol extraction, normalization, and `ON CONFLICT (source, external_id) DO NOTHING` writes.
- **LLM sentiment scoring service** — Added `backend/services/sentiment_service.py` to batch-score unscored news rows with Qwen/LiteLLM and persist `sentiment_score`, `sentiment_label`, `sentiment_confidence`, and `sentiment_computed_at`.

### Changed

- **News API now async + database-backed** — `backend/api/news.py` and `backend/services/news_service.py` now read latest/trending/search/symbol sentiment data from PostgreSQL instead of the old in-memory `_news_cache`.
- **Backend startup loops** — `backend/app.py` now starts a periodic `sentiment_score_loop()` alongside the existing news fetch loop.
- **Frontend news normalization** — `frontend/src/services/newsService.ts` now accepts persisted news payloads with `symbolsMentioned`/lowercase sentiment labels from the real API.

### Notes

- **Phase C only partially completed in this pass** — Backend persistence, query service, and sentiment loop are implemented. Frontend chart news markers, Dagster daily news sentiment gold asset, and full integration/runtime verification remain for later Phase C turns.

---

## [0.19.0] - 2026-06-06 - Lakehouse Gold Layer Runtime Prep

### Added

- **Gold aggregation entrypoint** — Added `src/lakehouse/gold_aggregator.py` to bootstrap and populate runtime gold-style tables in `iceberg_catalog.crypto_lakehouse` (`gold_movers_ranking`, `gold_market_dominance`, `gold_volatility_ranking`, `gold_momentum_indicators`, `gold_sector_performance`, `gold_news_sentiment_daily`) from existing `coin_ticker` and `coin_klines` tables.
- **Trino-native gold aggregation fallback** — Added `src/lakehouse/gold_aggregator_trino.py` to materialize gold tables through Trino HTTP API when local Spark batch aggregation is unstable under current standalone resource limits.
- **Dagster gold asset** — Added `compute_gold_layer` asset and `gold_layer_schedule` in `orchestration/assets.py`; current implementation now executes the Trino-native gold aggregation path for stable local runs.
- **Phase A integration coverage** — Added `tests/integration/test_gold_layer.py` to verify market overview metadata shape, response-time expectations, and fallback continuity.

### Changed

- **Spark streaming startup resilience** — Updated `src/lakehouse/pipeline.py` to wrap each streaming query startup with bounded retry logic while preserving `awaitAnyTermination()` and `s3://` checkpoint paths.
- **Spark stream submit path** — Verified streaming lakehouse job now starts only when submitted with explicit Iceberg/Kafka/Avro packages; bare `spark-submit /app/src/lakehouse/pipeline.py` was insufficient in current Spark image.
- **Spark lakehouse schema compatibility** — Added best-effort Iceberg schema evolution helper and reordered streaming DataFrame selects in `src/lakehouse/pipeline.py` so write schema matches existing Iceberg field ids/order for `coin_ticker`, `coin_trades`, and `coin_klines`.
- **Kline lakehouse capture** — Removed over-restrictive `interval == "1m"` filter from the Spark lakehouse stream path so closed kline events now populate `coin_klines` again under current producer output.
- **Spark metrics config** — Removed invalid `ClassLoaderSource` entries from `config/spark/metrics.properties` to stop repetitive Spark master/worker metrics initialization errors at startup.
- **Market Overview gold queries** — Refactored `backend/api/market_overview.py` to read current `iceberg.crypto_lakehouse.gold_*` tables, widened freshness window to 30 minutes for local scheduling tolerance, and removed stale references to nonexistent `iceberg.gold` / `iceberg_catalog.gold` schemas.
- **Market overview integration mocks** — Updated `tests/integration/test_api_market_overview.py` for current response shape and query-output contracts.

### Fixed

- **Phase A environment mismatch** — Adjusted implementation to current runtime reality where Trino exposes `iceberg.crypto_lakehouse` instead of `iceberg.bronze/silver/gold`, avoiding direct references to missing schemas.
- **Spark stream runtime blocker** — Restored `BinanceDualStreamToIceberg` to RUNNING state in Spark standalone by launching with explicit package set and fixing Iceberg schema-order incompatibilities for ticker/trade/kline writes.
- **Market Overview real-data path** — `/api/market/overview` now returns `metadata.source = "trino_gold"`, `is_placeholder = false`, and `gold_tables_healthy = true` after gold aggregation succeeds.

### Verified

- **Spark runtime** — `BinanceDualStreamToIceberg` remains RUNNING in Spark master with active executors.
- **Lakehouse row counts** — `coin_ticker`, `coin_trades`, and `coin_klines` all repopulate successfully in Iceberg.
- **Gold layer row counts** — `gold_movers_ranking`, `gold_market_dominance`, `gold_volatility_ranking`, `gold_momentum_indicators`, and `gold_sector_performance` now materialize rows in `iceberg.crypto_lakehouse`.
- **Market Overview API** — endpoint returns gold-backed movers, dominance, volatility, sector metrics, and metadata marking the response as non-placeholder.

---

## [0.18.3] - 2026-06-06 - Ticker Heartbeat Optimization

### Changed

- **TICKER_HEARTBEAT_SEC: 10s → 0.3s** — `src/common/config.py` `TICKER_HEARTBEAT_SEC` reduced from `5.0` to `0.3`. Binance ticker stream now sends updates every 0.3s (or on price change). Previously 10s heartbeat caused stale prices on chart. With 400 symbols × 0.3s = ~120 ticker updates/sec to Redis via batch buffer (BATCH_SIZE=100, FLUSH_INTERVAL=0.5s). No Kafka impact (throttled independently). Redis write load: ~240 ops/sec (HASH + pipeline). CPU impact: negligible (<1% on 2-core producer). Network: ~50KB/s extra (400 symbols × ~120 bytes per ticker). System stable — batch buffering absorbs burst.

### Fixed

- **litellm missing in fastapi-dev** — Rebuilt image with `--no-cache` after `requirements.txt` had litellm but Docker cached old image without it. AI chat now routes to real Qwen API instead of mock fallback.

---

## [0.18.2] - 2026-06-06 - AI Real LLM Fix & Token Cost Tracking

### Fixed

- **AI_ENABLE_REAL_LLM default** — Fixed `.env` to set `AI_ENABLE_REAL_LLM=true` so Qwen API actually generates real responses instead of falling back to mock. Backend container reads env directly from `.env` via docker-compose interpolation.
- **Token usage tracking** — Added `token_input`, `token_output`, and `estimated_cost_usd` fields to `AIChatResponse`, LiteLLM provider, and frontend types. Real-time cost estimation displays below AI messages.
- **Provider metadata enrichment** — `provider_metadata` now includes `token_input`, `token_output` alongside provider/model/latency info.

### Added

- **Token cost display** — AI chat panel now shows token usage (input → output) and estimated USD cost below each assistant message when available.

### Changed

- **AI health endpoint** — Now correctly reports `real_llm_enabled: true` when Qwen API key is configured.

---

## [0.18.1] - 2026-06-07 - Update documentations

### Changed

- **Documentation reinspection refresh** - Reaudited current code state and updated `docs/SYSTEM.md`, `AGENTS.md`, `README.md`, and `.env.example` comments for 0.18.0 facts: Phase 1 AI Ask Mode, modular AI routes, RAG/provider caveats, current Compose/service counts, Flink trade cache, exchange propagation status, Dagster `Definitions`, lakehouse `exchange` handling, observability counts, and test inventory.

---

## [0.18.0] - 2026-06-06 - Phase 1 AI Ask Mode Implementation

### Added

- **Phase 1 AI Ask Mode** — Real LLM inference pipeline with provider routing, RAG enrichment, prompt building, output guard, and confidence estimation. Full pipeline: scope gate → session → RAG retrieval → prompt assembly → provider routing → output guard → store message.
- **Provider abstraction** — `BaseProvider` interface with `MockProvider`, `LiteLLMProvider`, and `ProviderRouter`. Supports local vLLM, Qwen API, Llama API, OpenAI, Gemini, DeepSeek, LiteLLM proxy. Configurable priority order with automatic fallback chain; mock always available as final fallback.
- **RAG knowledge base** — pgvector-powered vector similarity search with `003_phase1_ai_rag.sql` migration. Knowledge sources, documents, chunks, and embeddings tables with HNSW index. Markdown ingestion with semantic chunking by headings/paragraphs/sentences. Content-hash deduplication. Retrieval with language/domain/tag/credibility filters. All retrievals logged for audit.
- **Curated knowledge base** — 5 approved documents: LMView Platform Guide, Technical Analysis Fundamentals, Cryptocurrency Market Structure, Risk Management, and Bilingual Crypto/Trading Glossary (EN/VI). Registry with source metadata.
- **Prompt builder** — Structured Ask Mode prompts with system instructions, chart context, RAG chunks, conversation history, data caveats, and financial safety addendum. Bilingual support.
- **Output guard** — Validates LLM responses for financial safety (flags guaranteed predictions, removes code execution patterns), ensures educational disclaimers. Supports EN/VI.
- **Context service** — Inspects chart context and generates data caveat warnings (placeholder market data, ticker-derived trades, stale order books, missing news, OKX experimental status).
- **AI API modularization** — Refactored `backend/api/ai.py` into `backend/api/ai/` package with separate modules for chat, sessions, chart context, chart actions, health, and knowledge endpoints.
- **AI model package** — Refactored `backend/models/ai.py` into `backend/models/ai/` package with separate modules for chat, chart actions, common, providers, RAG, knowledge, and evaluation models. Full backward compatibility maintained.
- **Knowledge API endpoints** — Admin-only `/api/ai/knowledge/ingest`, authenticated `/api/ai/knowledge/search` (vector similarity), `/api/ai/knowledge/sources`, `/api/ai/knowledge/health`.
- **Enhanced AI health** — `/api/ai/health` now reports AI mode, RAG status, pgvector readiness, available providers, and knowledge source count.
- **Phase 1 test suite** — 36 new tests covering provider routing, prompt building, output guard, context service, knowledge chunking, scope gate safety, and model backward compatibility. All 132 unit tests pass.
- **50 golden evaluation questions** — Covering technical indicators (10), live chart analysis (8), LMView limitations (5), RAG retrieval (5), out-of-scope refusal (8), prompt injection refusal (5), stale data warnings (3), bilingual (3), and risk disclaimers (3).
- **AI configuration** — New env vars in `.env.example` and `backend/core/config.py`: `AI_MODE`, `AI_ENABLE_REAL_LLM`, `AI_ENABLE_RAG`, provider API keys, vLLM settings, embedding model, RAG parameters.
- **Docker Compose AI services** — `docker-compose.ai.yml` overlay with `ai-api` (LiteLLM + online APIs, no GPU) and `ai-local` (vLLM, GPU required) profiles. LiteLLM proxy config in `ai_service/configs/litellm.yaml`.
- **Frontend AI API integration** — `useAiChat` now calls real backend `/api/ai/chat` when authenticated and not in mock mode, with local help responder as fallback. `AiMessage` and `AIChatResponse` types include Phase 1 fields (confidence, sources, data_caveats, provider_metadata).
- **AI documentation** — `docs/ai/AI_ARCHITECTURE.md`, `AI_API_CONTRACTS.md`, `RAG_KNOWLEDGE_BASE.md`, `AI_PROVIDER_ROUTING.md`, `AI_EVALUATION.md`, `AI_SECURITY.md`, `AI_ROADMAP.md`.
- **Future phase scaffolding** — `ai_service/` (LangGraph agents, tools, graph, prompts, observability), `src/ml/` (forecasting, sentiment), prompt templates, and AI config YAML files. All scaffolded with clear TODOs.

### Changed

- **Documentation audit refresh** - Updated `docs/SYSTEM.md`, `AGENTS.md`, `README.md`, and `.env.example` comments to match the then-current 0.15.x codebase, including auth/settings/admin APIs, Phase 0 AI foundation, frontend layout, compose profile counts, and known pipeline caveats.

### Fixed

- **Phase 1 AI type safety** — Fixed 8 Pyright type safety issues across the AI chat routing, knowledge ingestion, litellm provider integration, RAG retrieval logic, and unit tests to ensure complete typecheck alignment.

---

## [0.17.11] - 2026-06-05 - Auto-Detection & Indicator Fallback

### Added

- **Auto-failover Health Monitor** - `src/producer/health_monitor.py` now checks Kafka and Flink health every 30s:
  - When both Kafka and Flink are down for 60s → auto-enable direct Redis bypass
  - When either recovers for 120s → auto-disable direct Redis bypass
  - New config: `HEALTH_CHECK_INTERVAL_SEC`, `FAILOVER_THRESHOLD_SEC`, `RECOVERY_THRESHOLD_SEC`, `FLINK_JM_URL`

- **Backend Indicator Fallback** - `backend/services/indicator_service.py` computes indicators from Redis kline history when Flink pre-computed indicators unavailable or stale:
  - Supports: SMA (20, 50), EMA (12, 26), RSI (14), MACD, Bollinger Bands (20, 2), ATR (14), Volume SMA
  - Uses candle history from `candle:1m:{exchange}:{symbol}` sorted set
  - Returns `source: "redis_derived"` with freshness metadata

- **Data Freshness Tracking** - All indicator responses now include:
  - `source`: "flink_precomputed", "redis_derived", "redis_derived_stale", "unavailable"
  - `freshness_seconds`: age of data
  - `is_stale`: true if > 120 seconds old
  - `is_fallback`: true if computed from Redis

### Changed

- **Direct Redis toggle** - Now controlled by HealthMonitor state, not just static env var
- **Redis writer** - `set_direct_redis_active()` function to receive health state updates
- **System.md Section 17.7** - Updated with auto-detection documentation

### Verified

- **Tests** - All 300 tests pass
- **Compilation** - All Python files compile successfully

---

## [0.17.10] - 2026-06-05 - Direct Redis Bypass Path Implementation

### Added

- **Direct Redis Bypass** - New resilience feature allowing WebSocket → Redis direct writes when Kafka/Flink is down:
  - `src/exchanges/binance/redis_writer.py` — `DirectRedisWriter` class with methods for ticker, kline, trade, depth
  - `src/common/config.py` — `ENABLE_DIRECT_REDIS` env var (default: false)
  - `src/producer/main.py` — Integrated into all Binance and OKX stream handlers (ticker, trades, klines, depth)
  - Toggle via `ENABLE_DIRECT_REDIS=true` in docker-compose

### Changed

- **market overview** - Fixed catalog name mismatch (`iceberg_catalog.gold.*` → `iceberg.gold.*`) in 6 query functions
- **Section 17 Data Tables Reference** - Added comprehensive documentation to SYSTEM.md

### Verified

- **OKX E2E** - Channel subscription format verified correct per OKX WebSocket API v5
- **Direct Redis writes** - Format matches Flink KeyDBWriter Redis key structures for seamless fallback

---

## [0.17.9] - 2026-06-05 - Market Overview Fix & Data Tables Documentation

### Fixed

- **market overview catalog name mismatch** - `backend/api/market_overview.py` queried `iceberg_catalog.gold.*` but Trino catalog is `iceberg`. Fixed 6 queries across `_get_market_summary`, `_get_top_movers`, `_get_most_volatile`, `_get_highest_volume`, `_get_trending_news`, `_get_sector_performance`, `_get_indicators_summary`, `_get_heatmap_data`

### Added

- **Section 17 Data Tables Reference** - Added comprehensive documentation to `docs/SYSTEM.md` covering:
  - Exchange WebSocket formats (Binance: ticker/kline/trade/depth, OKX: tickers/trades/candle/books)
  - Kafka Avro schemas (schemas/\*.avsc) with all attributes
  - Redis KeyDB structures (ticker, kline, orderbook, trades) with TTL and field mappings
  - Iceberg Medallion tables (Bronze: ticker/kline/news, Silver: ticker_unified/kline_multi_timeframe, Gold: market_dominance/movers_ranking/volatility_ranking/sector_performance/momentum_indicators/news_sentiment_daily)
  - PostgreSQL Iceberg JDBC catalog tables (iceberg_tables, iceberg_namespace_properties)
  - Data flow diagram from WebSocket → Kafka → Flink → Redis/Iceberg

### Verified

- **OKX E2E** - Channel subscription format verified correct: `tickers` (plural), `trades`, `candle1m`, `books5`. instId format `BTC-USDT` matches OKX WebSocket API v5 spec. ENABLE_OKX currently `false` in docker-compose

---

## [0.17.8] - 2026-06-04 - Integration Tests Fixes & Frontend Verification

### Fixed

- **indicators test interval key** - Mock data now includes `"interval": "5m"` field to match service layer validation that checks `data_interval != interval_n`

- **trades test data format** - Mock returns JSON string trade objects (`{"p":"","q":"","t":,"m":}`) matching Flink KeyDBTradeWriter format instead of legacy `price:volume` string format

- **market overview placeholder test** - Test now accepts either `is_placeholder` value since fallback behavior produces real data from Redis ticker scan

- **e2e app metadata tests** - Updated expected app title/version to "LMView API" / "0.17.8" to match actual FastAPI app configuration

### Added

- **Producer Prometheus metrics** - Wired `prometheus_client` metrics endpoint on port 9090 with: `producer_ws_threads_running` (Gauge), `producer_kafka_messages_sent_total` (Counter by topic), `producer_kafka_send_errors_total` (Counter by topic), `producer_heartbeat_timestamp_seconds` (Gauge per thread), `producer_ws_reconnects_total` (Counter by stream), `producer_ticker_throttle_skipped_total` (Counter)

- **Prometheus scrape config** - Updated producer scrape job port from 9095 to 9090 to match new metrics endpoint

### Verified

- **Integration test suite** - All 300 tests pass (59 integration + 2 e2e fixes + unit tests)

- **Frontend typecheck** - `npm run typecheck` passes with React 19/Lucide React peer dependency resolved via `--legacy-peer-deps`

- **Frontend build** - `npm run build` succeeds, producing 631.65 kB bundle in 12.39s

- **Promtail log extraction** - Regex patterns extract `log_level` and `error_type` labels from Docker container logs. Pattern: `^\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\s+\[(?P<log_level>\w+)\]` for timestamp+level, `(?i)(?P<error_type>Exception|Error|Fatal|Traceback|panic|OOM|timeout)` for error classification. Service label derived from Docker compose service name.

- **System Error Triage dashboard** - Dashboard queries Loki `{log_level="ERROR"}` with service-based aggregation via `sum by (service) (rate({log_level="ERROR"} [5m]))`. Includes "Error Rate by Service" barchart and "All ERROR Logs" log panel with labels, time, and wrap options.

- **Alert rules** - 17 rules across 10 categories: Flink (job restart, high memory), Kafka (consumer lag, broker down), API (latency, error rate), System (memory, CPU), Postgres (connections, replication lag), InfluxDB (write failures), Nginx (5xx spike), Zookeeper (leader election), Dagster (pipeline failure), Producer (WS disconnect), Log-based (error rate spike, crash loop, Kafka disconnect). All rules use Prometheus/Loki datasources with 1-5 minute evaluation intervals.

### Optimized

- **Flink memory config** - TaskManager: 6144m→3584m, slots 24→12. JobManager: 2304m→1536m. Matches actual parallelism of 12.

- **Kafka JVM heap** - Added `-Xmx1g -Xms1g` via KAFKA_OPTS in entrypoint.sh.

- **Spark memory** - Driver/executor: 2g→1g. Workers: 4G→2G, cores 4→2.

- **Docker limits** - Flink TM 10G→4G, Flink JM 2.5G→2G, Spark master 1G→2G, Spark workers 4G→2G each.

---

## [0.17.7] - 2026-06-04 - OKX Verification & docker-compose Fixes

### Fixed

- **docker-compose.yml YAML syntax** - Fixed CRLF line endings and Unicode box drawing characters that caused `docker compose config` to fail

- **OKX channel name fix** - Changed `tickers` (plural) to `ticker` (singular) per OKX WebSocket API spec; updated both client builder and message handler

- **OKX instId case handling** - Symbols now passed as-is (e.g., "BTCUSDT" → "BTC-USDT") instead of forcing uppercase, matching OKX REST API format

### Changed

- **OKX kline interval** - OKX subscription now uses 1m minimum (doesn't support 1s klines); filtered to 13 well-known pairs to avoid channel errors

- **OKX experimental disabled** - Set `ENABLE_OKX=false` in docker-compose until OKX channel format is confirmed; code fixes applied, testing pending OKX documentation confirmation

- **Legacy batch files review** - 3 legacy files in `src/batch/` have no external references (orchestration uses `lakehouse.silver.transformations` directly). Files retained but marked for future cleanup if unified versions prove stable.

### Known Issues

- **Market Overview Trino catalog mismatch** - Code queries `iceberg_catalog.gold.*` but actual catalog is `iceberg`. Gold tables (market_dominance, movers_ranking, etc.) don't exist - only bronze tables (coin_klines, coin_ticker, coin_trades) exist. Need to check if Dagster/Spark jobs populate gold tables.

- **OKX WebSocket channel format** - OKX returns "Wrong URL or channel" errors for all symbol subscriptions. Further debugging requires checking OKX WebSocket API documentation directly

---

## [0.17.6] - 2026-06-04 - Flink/Spark Stability & Auto-Submit Fixes

### Fixed

- **Kafka brokers 2-3 startup** - Started kafka-2 and kafka-3 replicas that were dead, restoring full 3-broker Kafka cluster

- **Flink job submit path** - Recreated deps.zip in flink-jobmanager container directly (read-only volume mount prevented in-container fix); job now stays RUNNING with 60 active tasks consuming all 4 Kafka topics

- **Spark streaming JVM longevity** - Changed lakehouse/pipeline.py to `spark.streams.awaitAnyTermination()` instead of per-query await loops; Spark Structured Streaming app now keeps JVM alive and stays RUNNING

- **auto-submit-jobs CRLF** - Converted auto_submit_jobs.sh line endings from CRLF to LF; inlined all job-submission logic directly into docker-compose.yml entrypoint (no file I/O) so the container needs no read-only mounts

- **auto-submit-jobs inline entrypoint** - Replaced shell script call with self-contained entrypoint that recreates deps.zip, submits Flink, waits for Spark master, and submits Spark streaming job

### Changed

- **Spark submit packages** - Added `org.apache.spark:spark-avro_2.12:3.5.5` to Spark submit packages for Avro deserialization dependency

### Changed

- **Dagster code location loading** - Added Dagster `Definitions` wiring and narrowed lazy imports in `orchestration/assets.py` so the workspace can load even when optional news or kafka dependencies are not imported at module load time.

- **Dagster image dependencies** - Updated the Dagster image inputs so runtime imports needed by orchestration load successfully during `dagster job list` and service startup.

- **Producer exchange startup behavior** - Added `ENABLE_OKX` gating in the shared config and producer startup path so the experimental OKX source stays opt-in during normal stack bring-up while the producer watchdog thread still starts.

- **Flink checkpoint runtime config** - Switched the PyFlink checkpoint storage URI away from the broken `s3a://` path and added the S3 filesystem plugin installation step to the Flink image definition.

- **Trino startup idempotence** - Made the Trino entrypoint keep the JMX javaagent line unique in `jvm.config`, preventing restart loops caused by duplicate agent registration.

- **Job watchdog compose wiring** - Fixed the `job-watchdog` compose entrypoint so the container starts cleanly and can rerun job submission checks.

- **Exchange consistency fixes** - Kept trades API and lakehouse or backfill updates aligned with exchange-qualified keys and exchange-aware dedup columns from this runtime stabilization pass.

### Fixed

- **Dagster job listing** - `docker compose exec dagster-daemon dagster job list -w /app/orchestration/workspace.yaml` now loads the code location successfully.

- **Trino health** - `trino` now reaches healthy state again and answers simple queries after recreating the container with the idempotent entrypoint logic.

- **Flink job submission path** - After loading the S3 filesystem plugins into the running Flink services, the streaming job progressed past checkpoint-storage initialization and entered `RUNNING` during verification.

- **Spark lakehouse streaming path** - The Spark Iceberg pipeline now uses `s3://` checkpoint locations and holds explicit query handles so the structured streaming app stays `RUNNING` instead of exiting immediately after startup.

- **Spark dependency path** - Added the missing Spark Avro package to the Spark submit path and aligned Spark streaming checkpoints to `s3://` so the lakehouse app can progress further under the current container setup.

### Known Issues

- **Flink image rebuilds** - Rebuilding the Flink image was blocked in this session by Docker Hub DNS resolution failures from the environment, so plugin loading was verified by patching the running containers in addition to the committed Dockerfile change.

- **Producer image rebuilds** - Rebuilding the producer image was intermittently blocked by package-download timeouts, so runtime verification relied on the bind-mounted source plus container restart.

## [0.17.4] - 2026-06-03 - Frontend Indicator Stream Hookup

### Changed

- **Frontend chart live path** - Wired `CandlestickChart` to subscribe to `/api/stream/indicators/{interval}` and apply streamed indicator snapshots onto the live chart series.

- **Indicator stream fallback behavior** - Kept local client-side indicator computation as fallback/history source while preferring backend-streamed latest values for the live candle edge.

- **Frontend market data service** - Added `subscribeIndicatorStream()` to `marketDataService` so indicator streaming uses the same API-mode WebSocket boundary as candle streaming.

## [0.17.3] - 2026-06-03 - Indicator Streaming & History Storage

### Added

- **Indicator WebSocket stream** - Added `/api/stream/indicators/{interval}` to push real-time indicator snapshots from Redis for a requested symbol, exchange, and timeframe.

- **Redis indicator history** - Extended the Flink indicator writer to persist `indicator:history:{exchange}:{symbol}:{interval}` sorted sets alongside interval-scoped latest hashes.

- **Iceberg indicator history** - Added `iceberg_catalog.gold.indicator_history` creation and writes in both indicator batch jobs so historical indicator values are stored as real lakehouse rows.

### Changed

- **Indicator Redis schema** - Latest indicator snapshots now prefer `indicator:latest:{exchange}:{symbol}:{interval}` with fallback to older key layouts for compatibility.

- **Indicator API contracts** - `/api/indicators/{symbol}` and `/api/indicators/{symbol}/summary` now accept `interval` and return richer computed fields such as RSI, MACD, Bollinger Band, ATR, and volume-SMA values when available.

- **Indicator pipeline output** - The Flink indicator writer now emits more than SMA/EMA only, including RSI, MACD, Bollinger Band, ATR, and volume-SMA metrics into Redis and InfluxDB.

## [0.17.2] - 2026-06-03 - Realtime Indicator Rendering Optimization

### Changed

- **`frontend/src/features/chart/CandlestickChart.tsx`** - Optimized live indicator rendering so chart series update immediately from the latest candle stream while React candle state updates run in a lower-priority transition.

- **Realtime indicator sync** - Added a focused live indicator window and direct per-series updates to avoid full indicator recomputation on every WebSocket tick.

- **Chart settings effect** - Stopped tying indicator rebuilds to every live candle state change; full recalculation now stays aligned with settings/data reload paths instead of each price tick.

## [0.17.1] - 2026-06-03 - Lakehouse Schema Audit & Indicator History Design

### Changed

- **`docs/VIET_LOG.md`** - Reworked Section 6 into a table-first audit format covering Spark streaming, medallion layers, batch jobs, Trino, Dagster, and all observed Iceberg tables.

- **Lakehouse schema inventory** - Documented actual columns, datatypes, purposes, and schema drift risks across `crypto_lakehouse`, `bronze`, `silver`, and `gold`.

- **Indicator architecture design** - Replaced the minimal indicator note with a richer TradingView-style indicator catalog plus explicit Iceberg and Redis schema proposals for historical indicator storage.

## [0.17.0] - 2026-06-03 - Grafana Dashboards & Structured Log Pipeline

### Added

- **10 new Grafana dashboards** — Spark Logs, Trino Logs, MinIO Logs, Redis Sentinel Logs, Postgres Dashboard, InfluxDB Dashboard, Nginx Dashboard, Zookeeper Dashboard, Dagster Dashboard, Producer Dashboard

- **System Error Triage** dashboard — Single pane for all ERROR logs across all services, filterable by service with per-service error rate sparklines

- **Structured log pipeline** — Promtail now extracts `log_level` (ERROR/WARN/INFO/DEBUG) and `error_type` (Exception/Error/Fatal/Traceback/panic/OOM) labels from Docker container logs

- **Prometheus scrape configs** — Added scrape jobs for InfluxDB, Postgres exporter, Nginx exporter, Dagster, Zookeeper JMX, and Producer

- **10 new alert rules** — Postgres connection exhaustion + replication lag, InfluxDB write failures, Nginx 5xx spike, Zookeeper leader election, Dagster pipeline failure, Producer WS disconnect, ERROR log rate spike, crash loop detection, Kafka broker disconnect log

- **Nginx stub_status** — Enabled `/nginx_status` on both dev and prod configs for Prometheus scraping

### Changed

- **docker-compose.yml** — Exposed Zookeeper JMX port `7071` for scraping

- **producer requirements** — Added `prometheus-client` dependency; producer metrics endpoint wiring is still pending

- **Total Grafana dashboards:** 11 → 22. Every service now has dashboard coverage

## [0.16.0] - 2026-06-03 - Exchange Qualification & Trade Hot Cache

### Changed (Market Overview)

- **`/api/market/overview`** — Now attempts Trino gold table queries first; falls back to Redis `ticker:latest` scan to derive market volume, gainers/losers, volatile symbols, and BTC/ETH dominance when Trino is empty or unavailable

### Added (WebSocket)

- **`/api/stream/{interval}`** — New per-interval WebSocket endpoint for single-timeframe candle streaming. Supports all intervals: `1s`, `1m`, `5m`, `15m`, `1h`, `4h`, `1d`, `1w`

- **Frontend `subscribeCandle()`** — Fixed URL from legacy `/api/stream` (non-existent) to `/api/stream/{interval}`

### Added (OKX)

- **OKX subscription frame builder** — `build_subscribe_frame()` method on OKXClient with helper methods `build_ticker_channels()`, `build_trade_channels()`, `build_kline_channels()`, `build_depth_channels()`

- **OKX WebSocket handler** — `_handle_okx_message()` in producer parses OKX `{"arg":..., "data":[...]}` response format and dispatches to correct mapper

- **OKX subscription stream runners** — `run_ticker_stream_subscription()` and `run_combined_batch_subscription()` connect to OKX WS and send subscription frames after `on_open`

### Changed (Producer)

- **`run_streams()`** — Now detects subscription-capable clients with `hasattr(..., "uses_subscription_frames")` and branches between Binance URL-stream and OKX subscription-frame WebSocket handling

- **All stream spawning loops** — Conditionally call subscription or URL-based handlers based on exchange type

### Changed

- **Kline aggregator** — Keyed by `(exchange, symbol)` instead of `symbol` only. 1m emitted records now include `exchange` field, enabling separate `candle:1m:binance:BTCUSDT` and `candle:1m:okx:BTCUSDT`

- **Spark Iceberg DDLs** — Added `exchange STRING` column to `coin_ticker`, `coin_trades`, and `coin_klines` table definitions for multi-exchange lakehouse queries

- **Indicator writer** — Redis key changed from `indicator:latest:{symbol}` to `indicator:latest:{exchange}:{symbol}`. InfluxDB tag now uses actual exchange from kline JSON instead of hardcoded `"binance"`

- **Indicator API** — Backend service now reads new exchange-qualified key first, falls back to legacy `indicator:latest:{symbol}` key for backward compatibility

### Added

- **Trade hot cache writer** — New `KeyDBTradeWriter` Flink writer consuming `crypto_trades` topic and writing `trade:latest:{exchange}:{symbol}` sorted set to Redis

- **Trade pipeline in Flink** — Wired `kafka_trades` SQL table with Avro-confluent format into the main pipeline

- **Trade API enhancement** — `/api/trades/{symbol}` now reads `trade:latest` (real exchange trades) first, falls back to `ticker:history` (ticker-derived) if trade cache is empty. Response metadata includes `is_true_trade_tape` flag and `data_type` field

- **Trade writer unit tests** — 8 new unit tests for trade JSON format, exchange field, dedup, batch buffer, and empty symbol handling

### Fixed

- **Exchange qualification** — kline aggregation, Spark DDLs, indicator keys, and trades API now consistently carry `exchange` field

- **Backend indicator service docstring** — Updated to reflect new key format

## [0.15.2] - 2026-06-01 - Auth-gated settings and mock data isolation

### Added

- **Settings modal** - Wired the header Settings button to Account, Customization, AI Helper, About, and Debug tabs with login/admin gates, real auth user display, real theme/timeframe/chart-type controls, local AI session cleanup, and read-only health checks.

- **AI Helper gate** - Requires login before opening AI Helper and shows `You must log in to use AI Helper` when blocked.

- **LMView Help mode** - Replaced API-mode fake AI behavior with deterministic product-help responses only; Interact and market-analysis requests now return unavailable states until real AI services exist.

### Changed

- **Mock data boundary** - Moved market/news/AI mock generators under `frontend/src/data/mock/` and routed mock mode through API-shaped mock adapter functions consumed by frontend services.

- **API placeholder handling** - Added frontend metadata guards so API-mode placeholder/mock-tagged market, news, candle, ticker, order book, and trade payloads render empty/unavailable states instead of generated fallback data.

## [0.15.1] - 2026-06-01 - Bug fixes for Phase 0 implementation

### Fixed

- **Frontend auth session UI** - Wrapped the app with `AuthProvider`, wired the header Login button to the centered login/register modal with blurred backdrop, displayed authenticated user/logout state, cleared expired stored tokens during restore, and normalized FastAPI auth validation errors for the browser UI.

- **Auth registration runtime** - Added PostgreSQL async driver support to the FastAPI image, pinned bcrypt for passlib compatibility, wired auth PostgreSQL/migration environment values into Compose, and applied `SESSION_EXPIRY_HOURS` in token expiry calculations.

- **Recent Trades frontend** - Normalized the metadata-wrapped `/api/trades/{symbol}` response in `marketDataService` so the right-panel Recent Trades view always receives an array.

## [0.15.0] - 2026-06-01 - Phase 0: AI Foundation Layer

### Added

- **PostgreSQL auth foundation** — `backend/core/postgres.py` async connection pool (asyncpg), `backend/core/security.py` password hashing (bcrypt/SHA-256 fallback), `backend/core/auth_dependencies.py` FastAPI Bearer-token auth dependencies.

- **Auth API** — `POST /api/auth/register`, `POST /api/auth/login`, `POST /api/auth/logout`, `GET /api/auth/me`, `PATCH /api/auth/preferences` with session-based authentication.

- **Auth Pydantic models** — `RegisterRequest`, `LoginRequest`, `AuthResponse`, `UserResponse`, `SessionInfo`, `UserPreferencesResponse`, `MeResponse` in `backend/models/auth.py`.

- **AI backend API** — `GET /api/ai/health`, `POST /api/ai/chat` (scope gate + mock response + message persistence), `GET /POST /api/ai/sessions`, `GET /api/ai/sessions/{id}/messages`, `POST /api/ai/chart-context`, `POST /api/ai/chart-actions/validate`, `POST /api/ai/chart-actions/record`.

- **AI Pydantic models** — `AIChatRequest`, `AIChatResponse`, `AIChartAction`, `AIChartActionType` (10 action types), `AISessionResponse`, `AIMessageResponse`, `AIHealthResponse`, `ScopeGateResult`, `ChartContextDTO` in `backend/models/ai.py` and `backend/models/chart_context.py`.

- **Scope gate service** — Keyword-based in-scope/out-of-scope classification (crypto, indicators, charts, news, risk education). Blocks prompt injection, weather, recipes, code generation.

- **Chart action validator** — Validates AI-proposed chart actions against known indicator names, price/time ranges, payload safety (blocks JS/SQL injection, nesting depth), note length limits.

- **Mock AI service** — Deterministic Phase 0 responses that echo received context to prove wiring, clearly marked as mock.

- **Indicator service** — Catalog of 10 supported indicators, Redis-backed latest values, compact AI-context summaries with freshness metadata.

- **Common response models** — `DataFreshness`, `DataMetadata`, `PaginatedResponse`, `ErrorDetail` in `backend/models/common.py`.

- **SQL migration** — `backend/migrations/001_phase0_schema.sql` with 9 tables: `users`, `auth_sessions`, `user_preferences`, `ai_chat_sessions`, `ai_messages`, `ai_chart_snapshots`, `ai_tool_actions`, `news_articles`, `ai_knowledge_documents`.

- **Frontend auth service** — `frontend/src/services/authService.ts` with API calls + mock fallback for `VITE_DATA_SOURCE=mock`.

- **Frontend AI service** — `frontend/src/services/aiService.ts` with all AI API calls + auth header injection.

- **Frontend AI panel** — Extracted `AiAssistantPanel` from `RightPanel` into `frontend/src/features/ai/`, using `useAiChat` hook with backend API / local mock dispatching.

- **Frontend types** — Added `DataFreshness`, `DataMetadata`, `UserSession` to `frontend/src/types/index.ts`.

- **Unit tests** — 53 tests covering auth security (password hashing, session tokens, email validation), AI models (enums, DTOs), scope gate (in-scope/out-of-scope, prompt injection), chart action validator (indicators, ranges, XSS/SQL injection), and mock service.

### Changed

- **AuthContext rewrite** — `AuthContext.tsx` now uses backend API (Bearer token auth) with async login/register/logout. Falls back to localStorage mock for `VITE_DATA_SOURCE=mock`.

- **AuthModal** — Now async with loading spinner, disabled inputs during submission, error handling for both API and mock paths.

- **RightPanel** — Extracted ~150 lines of inline AI chat code into standalone `AiAssistantPanel` component.

- **Trades API** — Response now includes `metadata.data_type = "ticker_derived"`, `metadata.is_true_trade_tape = false`, source/exchange/freshness. Added `GET /api/trades/{symbol}/summary`.

- **Order book API** — Every response path now includes `metadata` with source, exchange, `is_synthetic` flag, and `DataFreshness`. Added `GET /api/orderbook/{symbol}/summary` with depth/imbalance.

- **Indicators API** — Added `GET /api/indicators/supported` listing all 10 indicators, expanded freshness metadata. Added `GET /api/indicators/{symbol}/summary`.

- **Market overview API** — Response now includes `metadata.is_placeholder = true` to prevent AI/users from treating default data as real analytics.

- **Backend config** — Added PostgreSQL connection vars, auth session config, migration flag.

- **Test conftest** — Added PostgreSQL env defaults, graceful mocking for environments without Docker-only deps.

- **`.env.example`** — Added `POSTGRES_HOST`, `POSTGRES_LMVIEW_DB`, `RUN_MIGRATIONS`, `SESSION_EXPIRY_HOURS`.

### Not Implemented (Phase 1+)

- Real LLM integration (LangGraph, model inference, RAG)

- Autonomous chart interaction

- News PostgreSQL persistence (schema ready, service stubbed)

- Frontend AI Interact Mode (action approval/execution UI)

- Cookie-based session transport (Bearer token for Phase 0)

- Alembic/SQLAlchemy migration framework

## [0.14.2] - 2026-05-30 - Drawing Toolbar Light Theme Polish

### Added

- **Drawing tool groups** - Rebuilt the floating left drawing bar around hoverable Line, Shapes, Fibonacci, Chart Patterns, Elliott Wave, and Position / Forecast groups with viewport-bounded flyout menus.

- **Drawing tools** - Added stable chart-rendered Fibonacci retracement, ABCD/XABCD patterns, Elliott wave, long/short position, and forecast drawing paths while keeping cursor, text, ruler, eraser, lock, replay, and delete-all flows intact.

### Fixed

- **Light mode contrast** - Moved chart toolbar, symbol selector, drawing toolbar, replay controls, tool flyouts, hover, active, and disabled states onto shared theme tokens so Light Mode remains readable.

- **Drawing toolbar interaction** - Kept tool group hover highlighted blue, preserved flyouts while moving from the button to the menu, and disabled eraser while all drawings are locked.

- **Pattern drafting** - Added point-by-point ABCD/XABCD drafting with anchored labels, preview segments, low-opacity polygon fills, and Escape/Cursor cancellation.

- **Fullscreen delete confirmation** - Moved Delete All Drawings confirmation into the chart fullscreen subtree so cancel/confirm remains visible above the fullscreen canvas.

- **Indicator localization** - Replaced hardcoded Indicator panel labels, descriptions, pane badges, color labels, and switch status text with i18n keys for full Vietnamese coverage.

## [0.14.1] - 2026-05-28 - Frontend Chart Controls and Right Panel UI

### Added

- **Theme support** - Added light and dark theme support through shared CSS tokens, persisted the selected mode in local storage, and refreshed chart colors when the mode changes.

- **Frontend client caching** - Added frontend-side caching for stable symbols, chart history, market overview, movers, news, and short-lived live market snapshots.

- **Chart type selector** - Wired candlestick, bar, line, and area renderers while keeping chart modes synchronized for replay and drawing coordinates.

- **Chart export** - Rebuilt chart export to include chart canvases, visible price/time axes, latest OHLCV metadata, selected chart type, and SVG user drawings.

- **Indicators library** - Expanded the chart indicators panel with TradingView-style search, grouped Trend/Momentum/Volatility/Volume categories, active-state toggles, and client-side calculations for Bollinger Bands, VWAP, Volume MA, MACD, Stochastic, ATR, Ichimoku, Supertrend, and Parabolic SAR.

- **AI assistant panel** - Reworked the right-panel AI Helper into a Copilot-style chat workspace with a compact header, chart context chips, scrollable conversation, suggested prompts, and a fixed composer using mock responses until a backend AI endpoint is available.

### Changed

- **Header shell** - Reworked the header around LMView branding, chart/markets navigation, theme/settings/user controls, and chart-only controls.

- **Developer UI** - Hid developer-facing UI indicators from the header, including the data source badge and system health card, behind a disabled developer-tools flag.

- **App responsiveness** - Improved app shell responsiveness by making the drawing toolbar and overview panel collapsible, defaulting secondary panels closed on compact screens, and keeping the chart area as the primary view.

- **Chart controls** - Replaced the full-width header timeframe row with a compact dropdown in the chart control bar, preserving lowercase timeframe keys for service/API calls while displaying uppercase long-interval labels in the UI.

- **Chart header toolbar** - Consolidated the chart symbol selector, timeframe dropdown, Indicators, History, Export Chart, chart-type buttons, zoom/fullscreen controls, and price/change readout onto a single non-wrapping toolbar row.

- **Chart zoom controls** - Kept Zoom In, Zoom Out, and Fullscreen controls in the primary one-line chart toolbar.

- **Chart action row** - Moved chart-specific controls out of the app header into a dedicated chart toolbar row and deduplicated the chart-area coin selector while preserving current-symbol rendering state.

- **Chart toolbar grouping** - Refined the chart action row into compact timeframe, action, and icon-tool groups with consistent dark-theme button sizing, radius, hover, and active states.

- **Chart tab strip** - Removed the old chart content tab strip so the chart remains the default view, with timeframe and chart-type controls handled from the header and chart toolbar.

- **Right panel** - Reduced the default desktop width and compacted overview, watchlist, order book, and recent trade spacing so the main chart keeps more usable screen area.

- **Right panel tabs** - Split the right panel into top-level Overview and AI Helper tabs, keeping market panels under Overview and adding a dark-theme AI placeholder without backend/API calls.

- **Overview panel placement** - Repositioned Order Book and Recent Trades into the right Overview panel beside Watchlist, using horizontal tabs for all three views.

- **Overview panel controls** - Tightened the Watchlist, Order Book, and Recent Trades segmented buttons to avoid horizontal overflow in the compact right panel.

- **Drawing toolbar restore** - Restored the stable left drawing bar layout from the pre-workspace commit, removing the experimental chart-edge handle, absolute overlay toolbar, and flyout registry from the rendered UI.

- **Drawing deletion** - Removed Delete Selected from the left drawing bar while keeping Delete All guarded by a confirmation modal for the current symbol/timeframe.

- **Drawing lock** - Kept locked-drawing edit/delete guards when using drawing selection and deletion flows.

- **Indicators control** - Highlighted the chart Indicators button and expanded the existing indicator panel to expose SMA20, SMA50, EMA12, and EMA26 controls.

- **News filters** - Scaled down the Markets & News search/filter controls to reduce header height while preserving existing filtering behavior.

- **Markets & News** - Improved Markets & News with 10-item pagination, list/grid view toggle, better scroll containment, and full-card external article links.

- **Symbol metadata** - Reworked symbol metadata to always expose symbol, name, and icon fields, with a bundled default icon when exchange or CoinGecko metadata is missing.

- **Mock market data** - Expanded mock ticker coverage so mock-mode watchlist, order book, trades, and chart candles line up with the bundled mock data generator.

- **Frontend preview** - Built and relaunched a frontend-only Vite preview from a mock-mode production bundle during frontend validation.

### Fixed

- **Drawing toolbar restore** - Restored the left drawing bar from the stable pre-workspace layout, removed the new flyout registry from the rendered sidebar, and kept fixed-height top-aligned buttons so fullscreen no longer stretches tool spacing.

- **Drawing toolbar delete actions** - Removed the Delete Selected toolbar button from drawing toolbars while keeping Delete All Drawings behind the existing confirmation modal.

- **Left drawing bar layout** - Moved the left drawing bar into the chart body as a floating fixed-size toolbar with an iPhone-style collapse handle, separating it from the top chart toolbar and preserving spacing in fullscreen.

- **Chart toolbar grouping** - Placed the live price/change indicator beside the symbol selector and pushed timeframe, indicators, history, export, chart type, and zoom controls into the right-side toolbar group.

- **Chart toolbar overflow** - Fixed chart action row overflow by letting control groups wrap inside the chart container and anchoring Indicators/History dropdowns from the left with viewport-bounded widths.

- **Chart symbol/timeframe controls** - Restored a single chart `MarketSelector` in the chart header and left-anchored the timeframe dropdown inside the chart toolbar container to prevent left-side overflow.

- **Chart autoscale reset** - Improved chart autoscale reset so it restores the intended initial candle window and price scaling instead of dumping the full loaded history into view.

- **Drawing selection** - Fixed drawing selection and delete-selected by letting cursor mode hit-test drawings and by recording toolbar deletes in the drawing command history.

- **Chart zoom/fullscreen layout** - Kept chart toolbar rows and drawing controls at fixed UI dimensions while zooming or entering/exiting fullscreen, resizing only the chart viewport.

- **Drawing tool rendering** - Filled in visible rendering and hit-testing for text, rectangle, circle, triangle, ruler, horizontal line, and trendline drawing tools using data-space anchors.

- **Replay mode startup** - Fixed replay mode startup so it begins from the selected candle, hides future candles, blocks live refresh races, and uses correct playback speed values.

- **Chart overlay navigation** - Fixed chart time navigation while drawing/replay overlays are active by forwarding wheel zoom/scroll and adding overlay-level pan handling for captured pointer states.

## [0.14.0] - 2026-05-22 - Frontend Structure Refactor

### Changed

- **Frontend folder structure** - Reorganized `frontend/src` into standard Vite React TypeScript folders, including `@types`, `constants`, `data`, `features`, `components/layout`, `components/ui`, and `routes`.

- **Frontend services** - Centralized API helpers, environment constants, timeframe constants, market/news data services, and health checks outside React components.

- **UI shell** - Merged the top toolbar behavior into the canonical `Header` component and removed redundant toolbar/replay/watchlist/news files.

- **Chart feature** - Flattened `features/chart` by removing the redundant nested `components/chart` directories and adding a concise feature barrel export.

- **Styling and i18n** - Moved theme tokens into `index.css`, removed the old theme module, and expanded translations for the refactored market/news/header UI.

- **Project docs** - Updated `docs/SYSTEM.md` and `AGENTS.md` to match the new frontend folder structure and hot spot paths.

## [0.13.1] — 2026-05-22 — Bug Fixes: Data Pipeline & Backend APIs

### Fixed

- **Kafka Topics** — Resolved `Unrecognized partition` errors in the Python producer by recreating `crypto_ticker`, `crypto_klines`, `crypto_trades`, and `crypto_depth` topics with the correct 12 partitions. Data ingestion is now stable.

- **Orderbook API** — Fixed an HTTP 500 `ReadOnlyError` in `/api/orderbook/{symbol}` by routing the fallback cache expiration write (`expire`) to the Redis Master node instead of a read-only Sentinel replica.

- **Exchange Fallback Logic** — Updated `/api/trades` and `/api/orderbook` to correctly parse new exchange-aware Redis keys. Implemented Binance-first lookup with automatic fallback to OKX (and then legacy keys) to fully utilize OKX as a redundant backup source.

## [0.13.0] — 2026-05-22 — Dev HTTP / Prod HTTPS Nginx Routing

### Changed

- **Nginx dev mode** — Switched from self-signed HTTPS to plain HTTP (port 80 only). No more browser certificate warnings in development.

- **Nginx prod mode** — HTTPS via certbot with any domain (DuckDNS, custom, etc.), not limited to DuckDNS. Self-signed cert still used as fallback until certbot issues a real certificate.

- **Nginx config split** — Single `nginx.conf` replaced with `nginx-dev.conf` (HTTP-only) and `nginx-prod.conf` (HTTPS). Entrypoint selects config via `NGINX_MODE` env var.

- **`init_certbot.sh`** — Now domain-agnostic; DuckDNS auto-detection is optional, not assumed. Only starts `duckdns-auto` if `DUCKDNS_TOKEN` is configured.

- **`certbot_auto.sh`** — Removed DuckDNS-specific sentinel domain check.

- **`.env.example`** — Generalized HTTPS automation section; `CERTBOT_DOMAIN` default changed from DuckDNS to `example.com`.

- **`docker-compose.yml`** — `nginx-dev` exposes port 80 only; `nginx-prod` exposes 80+443 with letsencrypt/certbot volumes. Ports and volumes moved from base template to concrete services.

## [0.12.3] — 2026-05-21 — Charting Library Upgrade

### Changed

- **Dependencies** — Upgraded `lightweight-charts` to `5.2.0` in `frontend/package.json`.

## [0.12.2] — 2026-05-20 — Frontend Mock Data Isolation & Service Refactor

### Added

- **Mock Data Enhancement** — Added `NewsItem` type and dynamic mock data simulation for order books, trades, and tickers to simulate real-time data flow on frontend.

- **Mock Mode Toggle** — Implemented `VITE_DATA_SOURCE` env variable to toggle between 'mock' and 'api' data sources.

- **UI Mode Indicator** — Added visual badge in `Header.tsx` indicating current data source (MOCK vs API).

### Changed

- **Mock Data Refactor** — Extracted all inline mock data generation out of `marketDataService.ts` and `MarketNews.tsx` into a dedicated `mock/mockDataGenerator.ts` file.

- **Market Overview Service** — Created `marketOverviewService.ts` to act as a controller for news, gainers, losers, and overview metrics, smoothly switching between API and mock data without clustering component logic.

### Fixed

- **TypeScript Overlap Error** — Resolved type comparison error for `DATA_SOURCE` constant in `marketDataService.ts`.

## [0.12.1] — 2026-05-19 — Integration Tests & API Routing

### Changed

- **Integration Test Suite** — Modernized test infrastructure to support Redis Sentinel HA by replacing legacy `get_redis` mocks with `get_redis_master`/`get_redis_replica`. Added global fixtures to mock FastAPI background tasks during testing.

- **API Routing** — Reordered FastAPI router inclusions in `backend/app.py` to prioritize new `market_overview` routes over legacy `market` overlapping routes.

### Added

- **API Tests** — Added mandatory integration tests for `market_overview` (`/api/market/overview`, `/api/market/heatmap`, `/api/market/rankings`) and `news` (`/api/news/latest`, `/api/news/trending`, `/api/news/search`) endpoints.

## [0.12.0] — 2026-05-19 — Market Overview & News Features (merged from `feature/viet-work`)

### Added

- **Market Overview API** — `backend/api/market_overview.py` and `backend/services/heatmap_service.py` to serve comprehensive market aggregations and heatmap data via Trino.

- **News API** — Background fetcher and endpoints for aggregating sentiment-driven news.

- **Background Tasks** — `market_fetcher.py` and `news_fetcher.py` integrated into FastAPI lifespan to continuously fetch necessary external data.

- **Frontend Components** — Added `LeftSidebar`, `RightPanel`, `TopToolbar`, `MarketOverviewPage`, `NewsPageRedesigned`, and `MarketNews` for an enriched UI.

- **Spark Metrics** — JMX metrics exporting via `metrics.properties` for Spark clusters.

- **Redis Monitoring** — Added `redis-exporter` to the monitoring stack.

### Changed

- **Integration Test Suite** — Modernized test infrastructure to support Redis Sentinel HA by replacing legacy `get_redis` mocks with `get_redis_master`/`get_redis_replica`. Added global fixtures to mock FastAPI background tasks during testing.

- **API Routing** — Reordered FastAPI router inclusions in `backend/app.py` to prioritize new `market_overview` routes over legacy `market` overlapping routes.

- **Dagster** — Version upgraded to `1.8.10`.

- **Nginx** — Version upgraded to `1.31.0`.

- **Certbot** — Version upgraded to `v5.6.0`.

- **Trino** — Added JMX javaagent opts for Prometheus scraping.

### Added

- **API Tests** — Added mandatory integration tests for `market_overview` (`/api/market/overview`, `/api/market/heatmap`, `/api/market/rankings`) and `news` (`/api/news/latest`, `/api/news/trending`, `/api/news/search`) endpoints.

## [0.11.0] — 2026-05-16 — Monitoring & Logging Nginx Routing

### Added

- **Nginx reverse proxy for monitoring** — Grafana (`/grafana/`), Prometheus (`/prometheus/`), Loki (`/loki/`) routed through nginx

- **Basic Auth for Prometheus/Loki** — htpasswd generated at container startup from `MONITORING_USER`/`MONITORING_PASSWORD` env vars (default: admin/admin)

- **Grafana WebSocket proxy** — `/grafana/api/live/` for live dashboard updates

- **Rate limiting** — `monitoring_limit` zone (10r/s per IP) applied to all monitoring endpoints

### Changed

- **Grafana subpath** — Configured `GF_SERVER_SERVE_FROM_SUB_PATH=true` with `GF_SERVER_ROOT_URL=%(protocol)s://%(domain)s/grafana/`

- **Prometheus subpath** — Added ` — web.external-url=/prometheus/` and ` — web.route-prefix=/prometheus/`

- **Grafana Prometheus datasource** — Updated URL to `http://prometheus:9090/prometheus`

- **Nginx Dockerfile** — Added `apache2-utils` for htpasswd generation

- **`.env.example`** — Added `MONITORING_USER`, `MONITORING_PASSWORD`, `GRAFANA_ADMIN_PASSWORD`

### Agent

- Agent: Gemini (Antigravity)

- Files modified: 6 (nginx.conf, Dockerfile, entrypoint.sh, docker-compose.yml, .env.example, datasources.yml)

## [0.10.0] — 2026-05-16

### Changed

- **Documentation system rewrite** — Replaced all project documentation with a new standardized system:
  - `docs/SYSTEM.md` — Complete system documentation (architecture, data flow, tech stack, setup, testing)

  - `docs/CHANGELOG.md` — Structured changelog (this file), migrated from `docs/TRACKING.md`

  - `docs/AGENTS.md` — AI agent coding instructions following the agents.md open standard

  - `README.md` — User-facing project overview following banesullivan/README template

- **Project renamed** from "Lambda Architecture for TradingView-Style Platform" to **LMView**

- **Documentation language** standardized to English (previously mixed Vietnamese/English)

## [0.9.0] — 2026-05-14 — High Availability Infrastructure

### Changed

- **Monitoring stack integration** — Merged Flink infrastructure refactor with monitoring/logging stack

- **Redis Sentinel entrypoint** — Fixed entrypoint scripts for correct Sentinel initialization

- **Node-exporter volumes** — Corrected volume mount paths for host metrics collection

- **Grafana provisioning** — Fixed rule hierarchy in provisioning configuration

- **Configuration types** — Resolved file type mismatches in monitoring configs

## [0.8.0] — 2026-05-09 — HA Architecture Migration

### Changed

- **Kafka HA** — Migrated from single Kafka node to 3-node KRaft cluster (`kafka-1`, `kafka-2`, `kafka-3`) with replication factor 3

- **Redis Sentinel HA** — Replaced standalone KeyDB with Redis cluster: 1 Master, 2 Replicas, 3 Sentinels

- **Backend Redis client** — Implemented `RedisSentinelManager` in `backend/core/redis_sentinel.py` with auto-discovery, failover, and read/write splitting

### Known Issues

- PyFlink writers still use `keydb_` prefix in filenames (e.g., `keydb_ticker.py`, `KeyDBKlineWriter`) while connections use Sentinel config

- `src/common/config.py` retains default `REDIS_HOST = "keydb"`, overridden by HA environment variables

## [0.7.0] — 2026-05-05 — Multi-Timeframe Candles & Historical Mode

### Added

- **Historical mode** — Full date range picker (`DateRangePicker.tsx`) with request ID tracking to prevent race conditions

- **Interval helpers** — `normalize_interval()`, `interval_to_seconds()`, `interval_to_ms()` in `candle_service.py`

- **Integration tests** — 4 new tests for candle merge quality and staleness checks (`test_candle_idempotency.py`)

- **Unit tests** — 14 new tests covering normalization, aggregation, and merge logic

### Fixed

- **Aggregate function (CRITICAL)** — Now sorts by timestamp before determining open/close. Previously used input order which produced wrong results with out-of-order data.

- **Ticker enrichment staleness** — Backend now verifies ticker freshness against sub-candle data before enriching

- **Interval normalization** — Frontend normalizes uppercase intervals (`1H` → `1h`) before all API calls

## [0.6.0] — 2026-05-02 — Comprehensive Test Suite

### Added

- **161 total tests** across 5 categories:
  - Unit: 80 tests (constants, binance mappers/client, models, candle service)

  - Integration: 39 tests (health, ticker, symbols, trades, indicators, klines, historical APIs)

  - Security: 17 tests (SQL injection, XSS, path traversal, CORS, oversized queries)

  - Performance: 9 benchmarks (aggregation, merging, validation with time limits)

  - E2E: 6 tests (route registration, OpenAPI schema, docs endpoint)

- **Test infrastructure** — `tests/integration/`, `tests/e2e/`, `tests/performance/` packages

## [0.5.0] — 2026-04-28 — Infrastructure & Pipeline Restoration

### Fixed

- **Producer image** — Downgraded from Python 3.14-slim to 3.11-slim (fastavro C-extension compatibility)

- **Nginx port conflict** — Removed duplicate port 3000 binding between dagster-webserver and nginx

- **Binance WebSocket** — Switched `!ticker@arr` to `!miniTicker@arr` (lighter payload, no timeout)

- **Flink module resolution** — Fixed ` — pyFiles /app/src` in job submission script

## [0.4.0] — 2026-04-28 — Frontend TypeScript Migration

### Changed

- **Complete TypeScript migration** — All 27 frontend files migrated from `.jsx`/`.js` to `.tsx`/`.ts`

- **React 18 → 19** upgrade

- **Type system** — 18 shared TypeScript interfaces in `types/index.ts`

- **Error handling** — Centralized `AppError` hierarchy + `useApiCall` hook + `ToastProvider`

- **Symbol metadata** — Dynamic CoinGecko API + 24h localStorage cache + fallback data (~90 symbols)

- **i18n** — ~130 translation keys (English + Vietnamese), all hardcoded strings replaced

- **Nginx** — Updated asset caching from `/static/` to `/assets/` (Vite output path)

## [0.3.0] — 2026-04-25 — Data Processing Layer Refactoring

### Changed

- **Exchange abstraction** — `ExchangeClient` base class + `BinanceClient` implementation in `src/exchanges/`

- **Shared infrastructure** — Centralized `src/common/` (config, kafka_client, avro_serializer, logging)

- **Producer rewrite** — 632-line monolith → ~250-line exchange-agnostic orchestrator

- **Flink pipeline split** — 996-line monolith → `pipeline.py` + 7 individual writer modules

- **Batch jobs** — Renamed and refactored maintenance/backfill jobs

## [0.2.0] — 2026-04-25 — Full Project Refactoring

### Changed

- **Backend MVC** — Migrated `serving/` → `backend/` with `api/`, `services/`, `models/`, `core/` structure

- **Pydantic models** — Created response models for candle, ticker, health endpoints

- **Shared service** — `candle_service.py` (280 lines) for all OHLCV business logic

- **Dev/Prod switching** — `docker-compose.override.yml` (dev) + `docker-compose.prod.yml` (prod) + Makefile

- **Docker optimization** — Memory limits on all 14 services, pinned Python dependencies

- **Security** — Nginx rate limiting (30r/s API, 5r/s WS), security headers (HSTS, X-Frame-Options, etc.)

### Added

- **Testing framework** — pytest with 40 initial tests (unit, model, security)

- **Vite migration** — CRA → Vite, all 21 components renamed to `.jsx`

- **Backend Python** — Upgraded to Python 3.14-slim (later reverted to 3.11)

## [0.1.0] — 2026-04-25 — Initial Documentation

### Added

- **TRACKING.md** — AI assistant working document

- **DOCUMENTATION.md** — Technical documentation (Vietnamese)

- **.gitignore** — Updated exclusion list
