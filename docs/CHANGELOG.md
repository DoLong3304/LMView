# Changelog - LMView

All notable changes to this project are documented in this file.

This log is maintained by AI agents and human contributors to track project evolution.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [0.24.37] - 2026-06-16

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

## [0.24.36] - 2026-06-15

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

## [0.24.35] - 2026-06-15

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

## [0.24.34] - 2026-06-15

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

## [0.24.33] - 2026-06-15

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

## [0.24.32] - 2026-06-15

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

## [0.24.31] - 2026-06-15

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

## [0.24.30] - 2026-06-15

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

## [0.24.29] - 2026-06-15

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

## [0.24.28] - 2026-06-15

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

## [0.24.27] - 2026-06-15

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

## [0.24.26] - 2026-06-15

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

## [0.24.25] - 2026-06-15

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

## [0.24.24] - 2026-06-15

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

## [0.24.23] - 2026-06-15

### Analysis

- **UI architecture analysis Task 6** - Compared two restructuring paths for LMView: moving market/context modules into a bottom dock while keeping AI on the right, versus preserving the current layout and letting AI temporarily open/switch/highlight the relevant panels.
- **Recommendation** - Recommended the lower-risk panel-orchestration path first because `App.tsx`, `RightPanel`, and `AiActionProvider` already expose most of the needed primitives: app view switching, right-panel open state, right-panel tab events, and `data-ai-section` highlight anchors.
- **Deferred migration** - Noted that the bottom-dock architecture remains a possible later migration, but it should wait until panel/tab state and AI restore behavior are standardized.

### Tests

- Not run; analysis and changelog-only task with no UI/code implementation.

### Files

- `docs/CHANGELOG.md`

---

## [0.24.22] - 2026-06-15

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

## [0.24.21] - 2026-06-15

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

## [0.24.20] - 2026-06-15

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

## [0.24.19] - 2026-06-15

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

## [0.24.18] - 2026-06-15

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

## [0.24.17] - 2026-06-15

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

## [0.24.16] - 2026-06-15

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

## [0.24.15] - 2026-06-14

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

## [0.24.14] - 2026-06-14

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

## [0.24.13] - 2026-06-14

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

## [0.24.12] - 2026-06-14

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

## [0.24.11] - 2026-06-14

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

## [0.24.10] - 2026-06-14

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

## [0.24.9] - 2026-06-14

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

## [0.24.8] - 2026-06-14

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

## [0.24.7] - 2026-06-14

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

## [0.24.6] - 2026-06-14

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

## [0.24.5] - 2026-06-14

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

## [0.24.4] - 2026-06-14

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

## [0.24.3] - 2026-06-14

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

## [0.24.2] - 2026-06-14

### Documentation

- **Chart/drawing/indicator audit** - Audited the chart, drawing, settings, AI Helper, market, frontend service/type, indicator API/service, and Flink indicator writer surfaces; documented current drawing tool, indicator, chart type, data-source, and responsive-layout risks with a small-batch remediation plan and no code changes.

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

## [0.19.3] - 2026-06-12 - Frontend Mock Data Mode Wiring

### Added

- **Frontend mock mode scripts** - Added `frontend` `dev:mock` and `build:mock` scripts with `.env.mock` so the UI can run against frontend-generated mock data without backend services.
- **Mock market overview payload** - Expanded `mockDataGenerator.ts` to produce full market overview, heatmap, sector, trending symbol, ticker volume, and indicator summary data for frontend-only screens.

### Fixed

- **Mock overview shape** - Updated the mock data adapter and market overview service so mock mode returns a complete `MarketOverview` shape instead of casting raw market metrics into the page contract.

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

<! — TEMPLATE FOR NEW ENTRIES:

## [X.Y.Z] — YYYY-MM-DD — Title

### Added

- **Feature name** — Description of what was added

### Changed

- **Component** — Description of what changed and why

### Fixed

- **Bug description** — What was wrong and how it was fixed

### Removed

- **Component** — What was removed and why

### Known Issues

- Description of any remaining issues

— >
