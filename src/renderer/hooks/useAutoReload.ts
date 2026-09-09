import { useEffect, useRef, useState, useCallback } from 'react';
import { useLocation } from 'react-router-dom';

export interface UseAutoReloadOptions {
  /** Periodic interval in milliseconds (default: 8000ms). Set to 0 to disable periodic interval. */
  intervalMs?: number;
  /** Whether auto-reload is enabled (default: true). */
  enabled?: boolean;
}

export interface UseAutoReloadReturn {
  /** Formatted timestamp of the last successful sync (e.g. "02:34:10 PM"). */
  lastSynced: string;
  /** True while the reload action is in progress. */
  isReloading: boolean;
  /** Manually trigger an immediate reload. */
  reload: () => Promise<void>;
}

/**
 * Custom hook to automatically keep page data fresh:
 * 1. Fetches on mount
 * 2. Fetches immediately upon route navigation (switching tabs/pages)
 * 3. Fetches immediately when the user refocuses the app window (window 'focus' or document 'visibilitychange')
 * 4. Periodically polls fresh data on an interval (default 8s) while the tab is active
 */
export function useAutoReload(
  fetchFn: (force: boolean) => Promise<void> | void,
  options: UseAutoReloadOptions = {}
): UseAutoReloadReturn {
  const { intervalMs = 8000, enabled = true } = options;
  const location = useLocation();
  const [isReloading, setIsReloading] = useState(false);
  const [lastSynced, setLastSynced] = useState<string>(() =>
    new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
  );

  const isFetchingRef = useRef(false);
  const fetchFnRef = useRef(fetchFn);
  fetchFnRef.current = fetchFn;

  const triggerReload = useCallback(async (force = true) => {
    if (isFetchingRef.current || !enabled) return;
    isFetchingRef.current = true;
    setIsReloading(true);
    try {
      await fetchFnRef.current(force);
      setLastSynced(
        new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
      );
    } catch (err) {
      console.error('AutoReload fetch error:', err);
    } finally {
      isFetchingRef.current = false;
      setIsReloading(false);
    }
  }, [enabled]);

  // 1. Fetch on route navigation or component mount
  useEffect(() => {
    if (!enabled) return;
    triggerReload(true);
  }, [location.pathname, enabled, triggerReload]);

  // 2. Fetch on window focus / tab visibility return
  useEffect(() => {
    if (!enabled) return;

    const handleFocus = () => {
      triggerReload(true);
    };

    const handleVisibility = () => {
      if (document.visibilityState === 'visible') {
        triggerReload(true);
      }
    };

    window.addEventListener('focus', handleFocus);
    document.addEventListener('visibilitychange', handleVisibility);

    return () => {
      window.removeEventListener('focus', handleFocus);
      document.removeEventListener('visibilitychange', handleVisibility);
    };
  }, [enabled, triggerReload]);

  // 3. Periodic background refresh while active
  useEffect(() => {
    if (!enabled || intervalMs <= 0) return;

    const timer = setInterval(() => {
      if (document.visibilityState === 'visible') {
        triggerReload(true);
      }
    }, intervalMs);

    return () => clearInterval(timer);
  }, [enabled, intervalMs, triggerReload]);

  return {
    lastSynced,
    isReloading,
    reload: () => triggerReload(true),
  };
}
