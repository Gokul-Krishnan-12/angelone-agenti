import React, { useState, useMemo, useRef, useEffect } from 'react';
import { useTradingStore } from '../stores/trading-store';
import {
  Info,
  AlertTriangle,
  AlertCircle,
  CheckCircle2,
  Zap,
  Search,
  Trash2,
  Copy,
  Check,
  Calendar,
  Layers,
  ArrowDownCircle,
  Activity
} from 'lucide-react';

const ActivityLog: React.FC = () => {
  const { activityLog, setActivityLog } = useTradingStore();
  const [filter, setFilter] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [copied, setCopied] = useState<boolean>(false);
  const [showClearConfirm, setShowClearConfirm] = useState<boolean>(false);
  const [autoScroll, setAutoScroll] = useState<boolean>(true);

  const logsEndRef = useRef<HTMLDivElement>(null);

  // Format local date YYYY-MM-DD reliably
  const getLocalDateStr = (d: Date) =>
    `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;

  const todayStr = getLocalDateStr(new Date());
  const [selectedDate, setSelectedDate] = useState<string>(todayStr);

  const availableDates = useMemo(() => {
    const dates = Array.from(
      new Set(activityLog.map((l) => getLocalDateStr(new Date(l.timestamp || new Date()))))
    ).sort((a, b) => b.localeCompare(a));

    if (!dates.includes(todayStr)) {
      dates.unshift(todayStr);
    }
    return dates;
  }, [activityLog, todayStr]);

  // Filter logs by date, level, and search keyword
  const filteredLogs = useMemo(() => {
    return activityLog.filter((log) => {
      // Date filter
      if (selectedDate !== 'all') {
        const logDate = getLocalDateStr(new Date(log.timestamp || new Date()));
        if (logDate !== selectedDate) return false;
      }

      // Level filter
      const level = (log.level || 'info').toLowerCase();
      if (filter === 'signal' && level !== 'signal') return false;
      if (filter === 'order' && level !== 'order') return false;
      if (filter === 'error' && level !== 'error' && level !== 'warning') return false;
      if (filter === 'info' && level !== 'info' && level !== 'engine') return false;

      // Search keyword filter
      if (searchQuery.trim()) {
        const query = searchQuery.toLowerCase().trim();
        const msgMatch = (log.message || '').toLowerCase().includes(query);
        const levelMatch = level.includes(query);
        if (!msgMatch && !levelMatch) return false;
      }

      return true;
    });
  }, [activityLog, selectedDate, filter, searchQuery]);

  // Statistics
  const totalLogsCount = activityLog.length;
  const signalCount = activityLog.filter((l) => (l.level || '').toLowerCase() === 'signal').length;
  const orderCount = activityLog.filter((l) => (l.level || '').toLowerCase() === 'order').length;
  const errorCount = activityLog.filter((l) => ['error', 'warning'].includes((l.level || '').toLowerCase())).length;

  // Auto-scroll when new logs arrive
  useEffect(() => {
    if (autoScroll && logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [filteredLogs.length, autoScroll]);

  const handleCopyLogs = () => {
    const text = filteredLogs
      .map((l) => `[${new Date(l.timestamp).toLocaleString()}] [${(l.level || 'INFO').toUpperCase()}] ${l.message}`)
      .join('\n');
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleClearLogs = () => {
    setActivityLog([]);
    window.electronAPI?.log.clear();
    setShowClearConfirm(false);
  };

  const getLevelBadge = (level: string) => {
    const l = (level || 'info').toLowerCase();
    switch (l) {
      case 'signal':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold bg-amber-500/20 text-amber-300 border border-amber-500/30">
            <Zap size={11} />
            SIGNAL
          </span>
        );
      case 'order':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold bg-profit-dark/20 text-profit-light border border-profit/30">
            <CheckCircle2 size={11} />
            ORDER
          </span>
        );
      case 'error':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold bg-loss-dark/20 text-loss-light border border-loss/30">
            <AlertCircle size={11} />
            ERROR
          </span>
        );
      case 'warning':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold bg-amber-500/20 text-amber-300 border border-amber-500/30">
            <AlertTriangle size={11} />
            WARN
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold bg-blue-500/20 text-blue-300 border border-blue-500/30">
            <Info size={11} />
            INFO
          </span>
        );
    }
  };

  return (
    <div className="p-6 h-full flex flex-col space-y-5 max-w-[1600px] mx-auto overflow-auto animate-fade-in">
      {/* ─── HEADER & ACTIONS ────────────────────────────────────────── */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-1 border-b border-surface-800/80">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-3">
            System & Trading Activity
          </h1>
          <p className="text-xs text-surface-400 mt-1">
            Auditable execution trail including strategy signals, risk validations, and SmartAPI broker events.
          </p>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-2.5">
          <button
            onClick={handleCopyLogs}
            disabled={filteredLogs.length === 0}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-surface-800 hover:bg-surface-750 text-surface-300 hover:text-white border border-surface-700 rounded-xl text-xs font-semibold transition-all cursor-pointer disabled:opacity-50"
            title="Copy displayed logs to clipboard"
          >
            {copied ? <Check size={13} className="text-profit-light" /> : <Copy size={13} />}
            <span>{copied ? 'Copied!' : 'Copy Logs'}</span>
          </button>

          {showClearConfirm ? (
            <div className="flex items-center gap-1.5 bg-surface-900 border border-loss/40 p-1 rounded-xl">
              <span className="text-[11px] text-loss-light px-2">Clear all?</span>
              <button
                onClick={handleClearLogs}
                className="px-2.5 py-1 bg-loss text-white rounded-lg text-xs font-bold hover:bg-loss-dark transition-colors"
              >
                Yes, Clear
              </button>
              <button
                onClick={() => setShowClearConfirm(false)}
                className="px-2 py-1 bg-surface-800 text-surface-300 rounded-lg text-xs hover:text-white"
              >
                Cancel
              </button>
            </div>
          ) : (
            <button
              onClick={() => setShowClearConfirm(true)}
              disabled={activityLog.length === 0}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-surface-800 hover:bg-surface-750 text-surface-400 hover:text-loss-light border border-surface-700 hover:border-loss/40 rounded-xl text-xs font-semibold transition-all cursor-pointer disabled:opacity-50"
            >
              <Trash2 size={13} />
              <span>Clear</span>
            </button>
          )}
        </div>
      </div>

      {/* ─── SUMMARY KPI STRIP ───────────────────────────────────────── */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="bg-surface-800/80 backdrop-blur-sm p-3.5 rounded-xl border border-surface-700/80 flex items-center justify-between">
          <div>
            <span className="text-[10px] uppercase font-bold text-surface-400 block">Total Events</span>
            <span className="text-xl font-mono font-bold text-white mt-0.5 block">{totalLogsCount}</span>
          </div>
          <div className="w-8 h-8 rounded-lg bg-surface-700/50 flex items-center justify-center text-surface-300">
            <Layers size={16} />
          </div>
        </div>

        <div className="bg-surface-800/80 backdrop-blur-sm p-3.5 rounded-xl border border-surface-700/80 flex items-center justify-between">
          <div>
            <span className="text-[10px] uppercase font-bold text-surface-400 block">Signals Fired</span>
            <span className="text-xl font-mono font-bold text-amber-300 mt-0.5 block">{signalCount}</span>
          </div>
          <div className="w-8 h-8 rounded-lg bg-amber-500/10 flex items-center justify-center text-amber-300">
            <Zap size={16} />
          </div>
        </div>

        <div className="bg-surface-800/80 backdrop-blur-sm p-3.5 rounded-xl border border-surface-700/80 flex items-center justify-between">
          <div>
            <span className="text-[10px] uppercase font-bold text-surface-400 block">Orders Executed</span>
            <span className="text-xl font-mono font-bold text-profit-light mt-0.5 block">{orderCount}</span>
          </div>
          <div className="w-8 h-8 rounded-lg bg-profit-dark/10 flex items-center justify-center text-profit-light">
            <CheckCircle2 size={16} />
          </div>
        </div>

        <div className="bg-surface-800/80 backdrop-blur-sm p-3.5 rounded-xl border border-surface-700/80 flex items-center justify-between">
          <div>
            <span className="text-[10px] uppercase font-bold text-surface-400 block">Errors & Warnings</span>
            <span className={`text-xl font-mono font-bold mt-0.5 block ${errorCount > 0 ? 'text-loss-light' : 'text-surface-400'}`}>
              {errorCount}
            </span>
          </div>
          <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${errorCount > 0 ? 'bg-loss-dark/10 text-loss-light' : 'bg-surface-700/50 text-surface-400'}`}>
            <AlertCircle size={16} />
          </div>
        </div>
      </div>

      {/* ─── FILTERS & LOG STREAM CONTAINER ─────────────────────────── */}
      <div className="flex-1 flex flex-col bg-surface-800/90 backdrop-blur-md rounded-2xl border border-surface-700/80 shadow-lg overflow-hidden min-h-[450px]">
        {/* Filter Controls Toolbar */}
        <div className="p-4 border-b border-surface-700/80 flex flex-col md:flex-row md:items-center justify-between gap-3 bg-surface-850/60">
          {/* Level Tabs */}
          <div className="flex items-center gap-1.5 overflow-x-auto pb-1 md:pb-0">
            {[
              { id: 'all', label: 'All Logs' },
              { id: 'signal', label: 'Signals' },
              { id: 'order', label: 'Orders' },
              { id: 'info', label: 'Engine' },
              { id: 'error', label: 'Errors' }
            ].map((t) => (
              <button
                key={t.id}
                onClick={() => setFilter(t.id)}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                  filter === t.id
                    ? 'bg-accent/20 text-accent-light border border-accent/40 shadow-sm'
                    : 'text-surface-400 hover:text-white hover:bg-surface-700/60'
                }`}
              >
                {t.label}
              </button>
            ))}
          </div>

          {/* Date Picker + Search Bar + Auto Scroll */}
          <div className="flex items-center gap-2.5 flex-wrap sm:flex-nowrap">
            {/* Date Select */}
            <div className="flex items-center gap-1.5 bg-surface-900 border border-surface-700/80 rounded-xl px-2.5 py-1.5 text-xs">
              <Calendar size={13} className="text-surface-400 shrink-0" />
              <select
                value={selectedDate}
                onChange={(e) => setSelectedDate(e.target.value)}
                className="bg-transparent text-surface-200 outline-none text-xs cursor-pointer"
              >
                <option value="all" className="bg-surface-900 text-white">All Dates</option>
                {availableDates.map((d) => (
                  <option key={d} value={d} className="bg-surface-900 text-white">
                    {d === todayStr ? `Today (${d})` : d}
                  </option>
                ))}
              </select>
            </div>

            {/* Keyword Search */}
            <div className="relative w-full sm:w-56">
              <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-surface-400" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search log messages..."
                className="w-full bg-surface-900 border border-surface-700/80 rounded-xl pl-8 pr-3 py-1.5 text-xs text-white placeholder-surface-500 focus:outline-none focus:border-accent-light transition-colors"
              />
            </div>

            {/* Auto-scroll toggle */}
            <label className="flex items-center gap-1.5 text-xs text-surface-400 select-none cursor-pointer whitespace-nowrap pl-1">
              <input
                type="checkbox"
                checked={autoScroll}
                onChange={(e) => setAutoScroll(e.target.checked)}
                className="rounded bg-surface-900 border-surface-700 text-accent focus:ring-0 cursor-pointer"
              />
              <span>Auto-scroll</span>
            </label>
          </div>
        </div>

        {/* Log Entries Viewport */}
        <div className="flex-1 overflow-auto p-3 space-y-1.5 font-mono text-xs">
          {filteredLogs.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-20 text-center text-surface-400">
              <Activity size={32} className="opacity-30 mb-2" />
              <span className="font-semibold text-white text-sm">No activity records found</span>
              <p className="text-xs text-surface-500 max-w-sm mt-1">
                {searchQuery
                  ? `No logs match "${searchQuery}".`
                  : 'Events, strategy signals, and broker orders will appear here in real time.'}
              </p>
            </div>
          ) : (
            filteredLogs.map((log, index) => {
              const timestamp = log.timestamp || new Date().toISOString();
              const level = log.level || 'info';
              const dateObj = new Date(timestamp);
              const timeStr = dateObj.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
              const dateStr = dateObj.toLocaleDateString([], { month: 'short', day: 'numeric' });

              return (
                <div
                  key={log.id || index}
                  className="p-2.5 rounded-xl bg-surface-900/40 hover:bg-surface-750/50 border border-surface-750/60 transition-colors flex items-start gap-3.5 group"
                >
                  {/* Timestamp */}
                  <div className="shrink-0 text-surface-500 text-[11px] leading-tight select-none pt-0.5 min-w-[70px]">
                    <span className="text-surface-300 font-semibold">{timeStr}</span>
                    <span className="text-[10px] text-surface-500 block">{dateStr}</span>
                  </div>

                  {/* Level Badge */}
                  <div className="shrink-0 pt-0.5">{getLevelBadge(level)}</div>

                  {/* Message */}
                  <div className="flex-1 text-surface-200 font-sans text-xs leading-relaxed break-words select-text">
                    {log.message}
                  </div>
                </div>
              );
            })
          )}
          <div ref={logsEndRef} />
        </div>
      </div>
    </div>
  );
};

export default ActivityLog;
