/**
 * Real User Monitoring (RUM) — captures frontend JavaScript errors and
 * performance metrics, then exposes them to a Prometheus-compatible
 * endpoint.
 *
 * Why this exists
 * ---------------
 * A9.1 (Frontend JS error rate) in
 * ``docs/dataflow_analysis_and_observability_plan.md`` calls for
 * observability of in-browser errors. Without RUM we only see the
 * 5xx error rate on the server, not the silent failures users hit
 * in their browser.
 *
 * How it works
 * ------------
 * 1. ``window.onerror`` and ``unhandledrejection`` listeners catch
 *    any uncaught exception or promise rejection.
 * 2. Errors are batched and POSTed to ``/api/rum/events`` every
 *    ``BATCH_INTERVAL_MS`` or when ``BATCH_SIZE`` is reached.
 * 3. The backend ``/api/rum/events`` endpoint ingests the events
 *    and exposes Prometheus metrics on the ``/metrics-custom`` scrape
 *    path so Grafana can chart them.
 *
 * Metrics produced (see ``backend/api/metrics.py``):
 *   - ``frontend_rum_errors_total{type,source}``
 *   - ``frontend_rum_page_loads_total{route}``
 *   - ``frontend_rum_lcp_seconds{route}`` (Largest Contentful Paint)
 *   - ``frontend_rum_inp_seconds{route}`` (Interaction to Next Paint)
 */
import { logger } from "@/utils/logger";

const BATCH_SIZE = 20;
const BATCH_INTERVAL_MS = 10_000;
const ENDPOINT = "/api/rum/events";

/** A single captured RUM event. */
export interface RumEvent {
  type: "error" | "pageview" | "perf";
  source: string;
  route: string;
  message?: string;
  stack?: string;
  /** Performance metrics, seconds. */
  lcp?: number;
  inp?: number;
  ts: number;
}

let buffer: RumEvent[] = [];
let flushTimer: number | null = null;
let installed = false;

/**
 * Install the global RUM listeners. Idempotent: calling twice is a
 * no-op. We expose this on ``window`` so it can be turned on/off
 * from a feature flag.
 */
export function installRum(): void {
  if (installed || typeof window === "undefined") return;
  installed = true;

  window.addEventListener("error", (ev) => {
    push({
      type: "error",
      source: "window.onerror",
      route: window.location.pathname,
      message: ev.message,
      stack: ev.error instanceof Error ? ev.error.stack : undefined,
      ts: Date.now(),
    });
  });

  window.addEventListener("unhandledrejection", (ev) => {
    const reason = ev.reason;
    push({
      type: "error",
      source: "unhandledrejection",
      route: window.location.pathname,
      message:
        reason instanceof Error
          ? reason.message
          : typeof reason === "string"
            ? reason
            : JSON.stringify(reason),
      stack: reason instanceof Error ? reason.stack : undefined,
      ts: Date.now(),
    });
  });

  // PerformanceObserver for LCP (Largest Contentful Paint)
  try {
    const lcpObserver = new PerformanceObserver((list) => {
      const entries = list.getEntries();
      const last = entries[entries.length - 1];
      if (last) {
        push({
          type: "perf",
          source: "lcp",
          route: window.location.pathname,
          lcp: last.startTime / 1000,
          ts: Date.now(),
        });
      }
    });
    lcpObserver.observe({ type: "largest-contentful-paint", buffered: true });
  } catch (e) {
    // PerformanceObserver may not be supported in older browsers.
    log("RUM: LCP observer unavailable", e);
  }

  // PerformanceObserver for INP (Interaction to Next Paint)
  try {
    const inpObserver = new PerformanceObserver((list) => {
      for (const entry of list.getEntries()) {
        // eventLatency is the metric that approximates INP.
        const latency = (entry as PerformanceEventTiming).processingEnd -
          entry.startTime;
        push({
          type: "perf",
          source: "inp",
          route: window.location.pathname,
          inp: latency / 1000,
          ts: Date.now(),
        });
      }
    });
    inpObserver.observe({ type: "event", buffered: true } as PerformanceObserverInit);
  } catch (e) {
    log("RUM: INP observer unavailable", e);
  }

  // Periodic flush
  flushTimer = window.setInterval(flush, BATCH_INTERVAL_MS);

  // Also flush on visibility change (page hide / tab switch).
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "hidden") flush();
  });
}

/** Push a RUM event into the in-memory buffer. */
export function push(event: RumEvent): void {
  buffer.push(event);
  if (buffer.length >= BATCH_SIZE) flush();
}

/** Manually flush the buffer to the backend. */
export async function flush(): Promise<void> {
  if (buffer.length === 0) return;
  const events = buffer;
  buffer = [];
  try {
    await fetch(ENDPOINT, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ events }),
      // Use keepalive so the request survives page unload.
      keepalive: true,
    });
  } catch (e) {
    // If the network call fails, push the events back to the buffer
    // (with a cap to avoid unbounded growth if the backend is down).
    buffer = events.concat(buffer).slice(-BATCH_SIZE * 2);
    log("RUM: flush failed", e);
  }
}

/** Track a pageview — call from your router on every route change. */
export function trackPageview(route: string): void {
  push({ type: "pageview", source: "router", route, ts: Date.now() });
}
