/**
 * Utility functions for evaluating live trading signal statuses and formatting timestamps.
 */

export type SignalStatus = 'active' | 'expired' | 'not in range';

export interface SignalStatusInfo {
  status: SignalStatus;
  label: 'ACTIVE' | 'EXPIRED' | 'NOT IN RANGE';
  reason: string;
  badgeBg: string;
  badgeText: string;
  badgeBorder: string;
  dotColor: string;
  currentPrice: number;
  priceDiff: number;
  priceDiffPercent: number;
}

export interface SignalParams {
  direction: 'BUY' | 'SELL';
  entryPrice: number;
  stopLoss: number;
  target: number;
  timestamp?: string;
}

/**
 * Determine dynamic signal status (active, expired, not in range) based on current market price.
 */
export function getSignalStatus(
  signal: SignalParams,
  currentPrice: number
): SignalStatusInfo {
  const { direction, entryPrice, stopLoss, target, timestamp } = signal;
  const isBuy = direction === 'BUY';

  // Defensive guard: Normalize paise price (e.g. 100x entry price)
  let normalizedPrice = currentPrice;
  if (entryPrice > 0 && normalizedPrice > entryPrice * 20) {
    normalizedPrice = Math.round((normalizedPrice / 100) * 100) / 100;
  }

  // Default when no tick price is available yet
  if (!normalizedPrice || normalizedPrice <= 0) {
    return {
      status: 'active',
      label: 'ACTIVE',
      reason: `Awaiting live quote (Entry: ₹${entryPrice.toFixed(2)})`,
      badgeBg: 'bg-emerald-500/10',
      badgeText: 'text-emerald-400',
      badgeBorder: 'border-emerald-500/30',
      dotColor: 'bg-emerald-400',
      currentPrice: entryPrice,
      priceDiff: 0,
      priceDiffPercent: 0,
    };
  }

  const priceDiff = normalizedPrice - entryPrice;
  const priceDiffPercent = entryPrice > 0 ? (priceDiff / entryPrice) * 100 : 0;

  // 1. Check Target Hit (Opportunity fulfilled -> EXPIRED)
  const targetHit = isBuy ? normalizedPrice >= target : normalizedPrice <= target;
  if (targetHit) {
    return {
      status: 'expired',
      label: 'EXPIRED',
      reason: `Target reached (LTP ₹${normalizedPrice.toFixed(2)} ${isBuy ? '≥' : '≤'} ₹${target.toFixed(2)})`,
      badgeBg: 'bg-surface-800',
      badgeText: 'text-surface-400',
      badgeBorder: 'border-surface-700',
      dotColor: 'bg-surface-500',
      currentPrice: normalizedPrice,
      priceDiff,
      priceDiffPercent,
    };
  }

  // 2. Check Stop Loss Hit (Setup invalidated -> EXPIRED)
  const slHit = isBuy ? normalizedPrice <= stopLoss : normalizedPrice >= stopLoss;
  if (slHit) {
    return {
      status: 'expired',
      label: 'EXPIRED',
      reason: `Stop loss breached (LTP ₹${normalizedPrice.toFixed(2)} ${isBuy ? '≤' : '≥'} ₹${stopLoss.toFixed(2)})`,
      badgeBg: 'bg-loss-dark/20',
      badgeText: 'text-loss-light',
      badgeBorder: 'border-loss/30',
      dotColor: 'bg-loss-light',
      currentPrice: normalizedPrice,
      priceDiff,
      priceDiffPercent,
    };
  }

  // 3. Check Session Timeout (>2.5 hours old -> EXPIRED)
  if (timestamp) {
    const sigTime = new Date(timestamp).getTime();
    if (!isNaN(sigTime) && Date.now() - sigTime > 150 * 60 * 1000) {
      return {
        status: 'expired',
        label: 'EXPIRED',
        reason: 'Signal session timed out (>2.5h old)',
        badgeBg: 'bg-surface-800',
        badgeText: 'text-surface-400',
        badgeBorder: 'border-surface-700',
        dotColor: 'bg-surface-500',
        currentPrice: normalizedPrice,
        priceDiff,
        priceDiffPercent,
      };
    }
  }

  // 4. Check Entry Range Tolerance (Optimal entry window)
  // Tolerance is the lesser of 0.4% or 25% of the distance between Entry and Target
  const targetDist = Math.abs(target - entryPrice);
  const entryTolerance = Math.max(entryPrice * 0.004, targetDist * 0.25);

  if (isBuy) {
    // Runaway above entry: price moved too high towards target, unfavorable R:R
    if (normalizedPrice > entryPrice + entryTolerance) {
      return {
        status: 'not in range',
        label: 'NOT IN RANGE',
        reason: `Price runaway (+${priceDiffPercent.toFixed(2)}% above entry zone)`,
        badgeBg: 'bg-amber-500/15',
        badgeText: 'text-amber-300',
        badgeBorder: 'border-amber-500/30',
        dotColor: 'bg-amber-400',
        currentPrice: normalizedPrice,
        priceDiff,
        priceDiffPercent,
      };
    }
    // Deep dip below entry towards SL
    if (normalizedPrice < entryPrice - entryTolerance * 1.5) {
      return {
        status: 'not in range',
        label: 'NOT IN RANGE',
        reason: `Price below entry zone (${priceDiffPercent.toFixed(2)}% near SL)`,
        badgeBg: 'bg-amber-500/15',
        badgeText: 'text-amber-300',
        badgeBorder: 'border-amber-500/30',
        dotColor: 'bg-amber-400',
        currentPrice: normalizedPrice,
        priceDiff,
        priceDiffPercent,
      };
    }
  } else {
    // SELL signal
    // Runaway below entry: price dropped too low towards target, unfavorable R:R
    if (normalizedPrice < entryPrice - entryTolerance) {
      return {
        status: 'not in range',
        label: 'NOT IN RANGE',
        reason: `Price runaway (${priceDiffPercent.toFixed(2)}% below entry zone)`,
        badgeBg: 'bg-amber-500/15',
        badgeText: 'text-amber-300',
        badgeBorder: 'border-amber-500/30',
        dotColor: 'bg-amber-400',
        currentPrice: normalizedPrice,
        priceDiff,
        priceDiffPercent,
      };
    }
    // Bounce above entry towards SL
    if (normalizedPrice > entryPrice + entryTolerance * 1.5) {
      return {
        status: 'not in range',
        label: 'NOT IN RANGE',
        reason: `Price above entry zone (+${priceDiffPercent.toFixed(2)}% near SL)`,
        badgeBg: 'bg-amber-500/15',
        badgeText: 'text-amber-300',
        badgeBorder: 'border-amber-500/30',
        dotColor: 'bg-amber-400',
        currentPrice: normalizedPrice,
        priceDiff,
        priceDiffPercent,
      };
    }
  }

  // 5. Active: In the sweet spot entry zone
  return {
    status: 'active',
    label: 'ACTIVE',
    reason: `In optimal entry zone (${priceDiff >= 0 ? '+' : ''}${priceDiffPercent.toFixed(2)}%)`,
    badgeBg: 'bg-emerald-500/15',
    badgeText: 'text-emerald-400',
    badgeBorder: 'border-emerald-500/30',
    dotColor: 'bg-emerald-400',
    currentPrice: normalizedPrice,
    priceDiff,
    priceDiffPercent,
  };
}

/**
 * Formats an ISO signal timestamp into readable local time and relative elapsed time.
 */
export function formatSignalTime(timestampStr?: string): {
  formattedTime: string;
  relativeTime: string;
  fullDate: string;
} {
  if (!timestampStr) {
    return { formattedTime: '--:--', relativeTime: 'Live', fullDate: '' };
  }

  const date = new Date(timestampStr);
  if (isNaN(date.getTime())) {
    return { formattedTime: '--:--', relativeTime: 'Live', fullDate: '' };
  }

  const formattedTime = date.toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: true,
  });

  const fullDate = date.toLocaleString([], {
    dateStyle: 'medium',
    timeStyle: 'medium',
  });

  const diffMs = Date.now() - date.getTime();
  const diffSec = Math.max(0, Math.floor(diffMs / 1000));
  const diffMin = Math.floor(diffSec / 60);
  const diffHours = Math.floor(diffMin / 60);

  let relativeTime = 'Just now';
  if (diffSec >= 60 && diffMin < 60) {
    relativeTime = `${diffMin}m ago`;
  } else if (diffMin >= 60 && diffHours < 24) {
    relativeTime = `${diffHours}h ago`;
  } else if (diffHours >= 24) {
    relativeTime = `${Math.floor(diffHours / 24)}d ago`;
  }

  return { formattedTime, relativeTime, fullDate };
}
