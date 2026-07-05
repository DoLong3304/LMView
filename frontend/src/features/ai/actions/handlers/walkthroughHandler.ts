/**
 * Walkthrough-specific action handlers for Interact mode.
 *
 * Handlers for actions unique to the guided analysis walkthrough:
 * open_news_popup, navigate_tab, enter_replay.
 */
import type { ActionHandler } from "./index";

/**
 * Open a draggable news article popup.
 * Dispatches an event that the AI Action Provider / panel listens for
 * to create an overlay with the specified URL.
 *
 * @param ctx.args.url    The news article URL to load.
 * @param ctx.args.title  Optional display title.
 */
export const handleOpenNewsPopup: ActionHandler = ({ args }) => {
  const url = String(args.url || "").trim();
  if (!url) {
    return "error: 'url' is required for open_news_popup";
  }
  if (typeof window !== "undefined") {
    window.dispatchEvent(
      new CustomEvent("lmview:open-news-popup", {
        detail: {
          url,
          title: String(args.title || "News Article"),
        },
      }),
    );
  }
  return `success: opened news popup for ${url.slice(0, 60)}`;
};

/**
 * Navigate to a specific tab panel in the UI.
 * Maps semantic tab names to their section selectors.
 *
 * @param ctx.args.tab   Tab/panel name.
 */
export const handleNavigateTab: ActionHandler = ({ showSection, args }) => {
  const tab = String(args.tab || "").trim().toLowerCase();
  if (!tab) {
    return "error: 'tab' is required for navigate_tab";
  }

  // Map common tab names to section selectors
  const tabMap: Record<string, string> = {
    chart: "chart",
    overview: "rightPanelOverview",
    watchlist: "watchlist",
    orderbook: "orderBook",
    "order book": "orderBook",
    trades: "recentTrades",
    "recent trades": "recentTrades",
    "trade tape": "recentTrades",
    news: "marketsNews",
    screener: "screener",
    ai: "ai",
    "ai helper": "ai",
    settings: "settings",
    account: "account",
    drawings: "drawingTools",
    "drawing tools": "drawingTools",
  };

  const target = tabMap[tab] || tab;
  showSection(target);
  return `success: navigated to "${tab}" panel`;
};

/**
 * Enter replay mode for a specific time range.
 * Dispatches a replay-start event with the given bounds.
 *
 * @param ctx.args.from_time  Start time (unix seconds).
 * @param ctx.args.to_time    End time (unix seconds).
 */
export const handleEnterReplay: ActionHandler = ({ args }) => {
  const fromTime = Number(args.from_time);
  const toTime = Number(args.to_time);
  if (!Number.isFinite(fromTime) || !Number.isFinite(toTime)) {
    return "error: 'from_time' and 'to_time' are required (unix seconds)";
  }
  if (typeof window !== "undefined") {
    window.dispatchEvent(
      new CustomEvent("lmview:replay-start", {
        detail: {
          from_time: fromTime,
          to_time: toTime,
        },
      }),
    );
  }
  return `success: entered replay mode from ${fromTime} to ${toTime}`;
};
