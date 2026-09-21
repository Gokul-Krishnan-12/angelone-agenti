import React, { useState, useMemo } from 'react';
import { PaperOrder } from '../stores/paper-trading-store';
import {
  ChevronLeft,
  ChevronRight,
  Calendar as CalendarIcon,
  TrendingUp,
  TrendingDown,
  Award,
  BarChart3,
  CheckCircle2,
  XCircle,
  ArrowUpRight,
  ArrowDownRight,
  Sparkles,
  Layers,
  Clock,
  DollarSign
} from 'lucide-react';

interface PaperTradingCalendarProps {
  orders: PaperOrder[];
}

interface DayTradeSummary {
  dateStr: string; // YYYY-MM-DD
  dayNum: number;
  trades: PaperOrder[];
  ordersCount: number;
  winningCount: number;
  losingCount: number;
  breakevenCount: number;
  grossPnl: number;
  brokerage: number;
  netPnl: number;
  winRate: number;
}

export const PaperTradingCalendar: React.FC<PaperTradingCalendarProps> = ({ orders }) => {
  // Current view year & month
  const today = new Date();
  const todayIstStr = today.toLocaleDateString('en-CA', { timeZone: 'Asia/Kolkata' });

  // If there are orders, pick the latest order's month, otherwise current month
  const initialDate = useMemo(() => {
    if (orders.length > 0) {
      const dates = orders
        .filter((o) => o.entryTime)
        .map((o) => new Date(o.entryTime).getTime())
        .filter((t) => !isNaN(t));
      if (dates.length > 0) {
        const latest = new Date(Math.max(...dates));
        return { year: latest.getFullYear(), month: latest.getMonth() };
      }
    }
    return { year: today.getFullYear(), month: today.getMonth() };
  }, [orders]);

  const [currentYear, setCurrentYear] = useState<number>(initialDate.year);
  const [currentMonth, setCurrentMonth] = useState<number>(initialDate.month); // 0-11
  const [selectedDateStr, setSelectedDateStr] = useState<string | null>(todayIstStr);

  // Month navigation handlers
  const handlePrevMonth = () => {
    if (currentMonth === 0) {
      setCurrentMonth(11);
      setCurrentYear((y) => y - 1);
    } else {
      setCurrentMonth((m) => m - 1);
    }
  };

  const handleNextMonth = () => {
    if (currentMonth === 11) {
      setCurrentMonth(0);
      setCurrentYear((y) => y + 1);
    } else {
      setCurrentMonth((m) => m + 1);
    }
  };

  const handleCurrentMonth = () => {
    setCurrentYear(today.getFullYear());
    setCurrentMonth(today.getMonth());
    setSelectedDateStr(todayIstStr);
  };

  // Group all closed orders by IST date (YYYY-MM-DD)
  const dailySummariesMap = useMemo(() => {
    const map = new Map<string, DayTradeSummary>();

    orders.forEach((o) => {
      if (!o.entryTime || o.status === 'OPEN') return;
      const orderDate = new Date(o.entryTime);
      if (isNaN(orderDate.getTime())) return;

      const dateStr = orderDate.toLocaleDateString('en-CA', { timeZone: 'Asia/Kolkata' });
      const pnl = o.pnl ?? 0;

      if (!map.has(dateStr)) {
        const parts = dateStr.split('-');
        map.set(dateStr, {
          dateStr,
          dayNum: parseInt(parts[2], 10),
          trades: [],
          ordersCount: 0,
          winningCount: 0,
          losingCount: 0,
          breakevenCount: 0,
          grossPnl: 0,
          brokerage: 0,
          netPnl: 0,
          winRate: 0
        });
      }

      const summary = map.get(dateStr)!;
      summary.trades.push(o);
      summary.ordersCount += 1;
      summary.grossPnl += pnl;

      if (pnl > 0) summary.winningCount += 1;
      else if (pnl < 0) summary.losingCount += 1;
      else summary.breakevenCount += 1;

      // ₹20 per entry + ₹20 per exit = ₹40 statutory estimate per trade roundtrip
      summary.brokerage = summary.ordersCount * 40;
      summary.netPnl = summary.grossPnl - summary.brokerage;
      summary.winRate = summary.ordersCount > 0 ? (summary.winningCount / summary.ordersCount) * 100 : 0;
    });

    return map;
  }, [orders]);

  // Compute monthly stats for the currently selected month
  const monthlyStats = useMemo(() => {
    let totalMonthlyTrades = 0;
    let totalGrossPnl = 0;
    let totalBrokerage = 0;
    let tradedDaysCount = 0;
    let greenDaysCount = 0;
    let redDaysCount = 0;
    let bestDay: { dateStr: string; netPnl: number } | null = null;
    let worstDay: { dateStr: string; netPnl: number } | null = null;

    for (const [dateStr, summary] of dailySummariesMap.entries()) {
      const [y, m] = dateStr.split('-').map(Number);
      if (y === currentYear && m === currentMonth + 1) {
        tradedDaysCount += 1;
        totalMonthlyTrades += summary.ordersCount;
        totalGrossPnl += summary.grossPnl;
        totalBrokerage += summary.brokerage;

        if (summary.netPnl > 0) greenDaysCount += 1;
        else if (summary.netPnl < 0) redDaysCount += 1;

        if (!bestDay || summary.netPnl > bestDay.netPnl) {
          bestDay = { dateStr, netPnl: summary.netPnl };
        }
        if (!worstDay || summary.netPnl < worstDay.netPnl) {
          worstDay = { dateStr, netPnl: summary.netPnl };
        }
      }
    }

    const totalNetPnl = totalGrossPnl - totalBrokerage;
    const profitableDayRate = tradedDaysCount > 0 ? (greenDaysCount / tradedDaysCount) * 100 : 0;
    const avgDailyNet = tradedDaysCount > 0 ? totalNetPnl / tradedDaysCount : 0;

    return {
      totalMonthlyTrades,
      totalGrossPnl,
      totalBrokerage,
      totalNetPnl,
      tradedDaysCount,
      greenDaysCount,
      redDaysCount,
      profitableDayRate,
      avgDailyNet,
      bestDay,
      worstDay
    };
  }, [dailySummariesMap, currentYear, currentMonth]);

  // Construct Calendar Grid for current month
  // We align to Monday as 1st day of the week (standard trading week)
  const calendarCells = useMemo(() => {
    const firstDayOfMonth = new Date(currentYear, currentMonth, 1);
    const lastDayOfMonth = new Date(currentYear, currentMonth + 1, 0);
    const totalDaysInMonth = lastDayOfMonth.getDate();

    // getDay: 0 is Sunday, 1 is Monday ... 6 is Saturday
    // Convert to Monday=0 ... Sunday=6
    let startDayOfWeek = firstDayOfMonth.getDay() - 1;
    if (startDayOfWeek === -1) startDayOfWeek = 6;

    const cells: {
      day: number;
      isCurrentMonth: boolean;
      dateStr: string;
      isWeekend: boolean;
      isToday: boolean;
      summary?: DayTradeSummary;
    }[] = [];

    // Leading days from previous month
    const prevMonthLastDay = new Date(currentYear, currentMonth, 0).getDate();
    for (let i = startDayOfWeek - 1; i >= 0; i--) {
      const day = prevMonthLastDay - i;
      const prevDate = new Date(currentYear, currentMonth - 1, day);
      const dateStr = prevDate.toLocaleDateString('en-CA', { timeZone: 'Asia/Kolkata' });
      const dayOfWeek = prevDate.getDay();
      cells.push({
        day,
        isCurrentMonth: false,
        dateStr,
        isWeekend: dayOfWeek === 0 || dayOfWeek === 6,
        isToday: dateStr === todayIstStr,
        summary: dailySummariesMap.get(dateStr)
      });
    }

    // Days in current month
    for (let day = 1; day <= totalDaysInMonth; day++) {
      const cellDate = new Date(currentYear, currentMonth, day);
      const dateStr = cellDate.toLocaleDateString('en-CA', { timeZone: 'Asia/Kolkata' });
      const dayOfWeek = cellDate.getDay();
      cells.push({
        day,
        isCurrentMonth: true,
        dateStr,
        isWeekend: dayOfWeek === 0 || dayOfWeek === 6,
        isToday: dateStr === todayIstStr,
        summary: dailySummariesMap.get(dateStr)
      });
    }

    // Trailing days to fill the complete grid row (multiple of 7)
    const remainingCells = 7 - (cells.length % 7);
    if (remainingCells < 7) {
      for (let day = 1; day <= remainingCells; day++) {
        const nextDate = new Date(currentYear, currentMonth + 1, day);
        const dateStr = nextDate.toLocaleDateString('en-CA', { timeZone: 'Asia/Kolkata' });
        const dayOfWeek = nextDate.getDay();
        cells.push({
          day,
          isCurrentMonth: false,
          dateStr,
          isWeekend: dayOfWeek === 0 || dayOfWeek === 6,
          isToday: dateStr === todayIstStr,
          summary: dailySummariesMap.get(dateStr)
        });
      }
    }

    return cells;
  }, [currentYear, currentMonth, dailySummariesMap, todayIstStr]);

  const monthNames = [
    'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December'
  ];

  // Selected day details
  const selectedDaySummary = selectedDateStr ? dailySummariesMap.get(selectedDateStr) : undefined;

  return (
    <div className="space-y-6 animate-fade-in p-2">
      {/* ─── 1. TOP HEADER & MONTH CONTROLS ───────────────────────────── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-surface-700/60">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-2xl bg-gradient-to-br from-accent/25 to-accent-dark/30 text-accent-light flex items-center justify-center border border-accent/40 shadow-md">
            <CalendarIcon size={20} />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-xl font-extrabold text-white tracking-tight">
                {monthNames[currentMonth]} {currentYear}
              </h2>
              <span className="text-[10px] uppercase font-mono font-bold px-2 py-0.5 rounded-full bg-accent/15 text-accent-light border border-accent/30">
                P&L Matrix
              </span>
            </div>
            <p className="text-xs text-surface-400">
              Interactive calendar view tracking daily virtual returns, friction, and win ratios.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 self-start sm:self-auto">
          <button
            onClick={handlePrevMonth}
            className="p-2 rounded-xl bg-surface-800 hover:bg-surface-700 text-surface-300 hover:text-white border border-surface-700 transition-all cursor-pointer shadow-sm"
            title="Previous Month"
          >
            <ChevronLeft size={16} />
          </button>
          <button
            onClick={handleCurrentMonth}
            className="px-3 py-1.5 rounded-xl text-xs font-bold bg-surface-800 hover:bg-surface-700 text-surface-200 hover:text-white border border-surface-700 transition-all cursor-pointer shadow-sm"
          >
            Current Month
          </button>
          <button
            onClick={handleNextMonth}
            className="p-2 rounded-xl bg-surface-800 hover:bg-surface-700 text-surface-300 hover:text-white border border-surface-700 transition-all cursor-pointer shadow-sm"
            title="Next Month"
          >
            <ChevronRight size={16} />
          </button>
        </div>
      </div>

      {/* ─── 2. MONTHLY PERFORMANCE SUMMARY CARDS ─────────────────────── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Card 1: Monthly Net P&L */}
        <div
          className={`p-4 rounded-2xl border backdrop-blur-md bg-surface-850/80 shadow-lg ${
            monthlyStats.totalNetPnl >= 0 ? 'border-profit/30' : 'border-loss/30'
          }`}
        >
          <div className="flex items-center justify-between text-xs font-semibold text-surface-400 mb-1.5">
            <span className="uppercase tracking-wider">Monthly Net P&L</span>
            <span
              className={`flex items-center gap-0.5 text-xs font-mono font-bold px-2 py-0.5 rounded-full ${
                monthlyStats.totalNetPnl >= 0
                  ? 'bg-profit-dark/20 text-profit-light border border-profit/30'
                  : 'bg-loss-dark/20 text-loss-light border border-loss/30'
              }`}
            >
              {monthlyStats.totalNetPnl >= 0 ? <ArrowUpRight size={13} /> : <ArrowDownRight size={13} />}
              <span>{monthlyStats.totalNetPnl >= 0 ? '+' : ''}₹{monthlyStats.totalNetPnl.toFixed(2)}</span>
            </span>
          </div>
          <div
            className={`text-2xl font-mono font-extrabold tracking-tight ${
              monthlyStats.totalNetPnl >= 0 ? 'text-profit-light' : 'text-loss-light'
            }`}
          >
            {monthlyStats.totalNetPnl >= 0 ? '+' : ''}₹{monthlyStats.totalNetPnl.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
          </div>
          <div className="flex items-center justify-between text-[11px] text-surface-400 mt-2.5 pt-2 border-t border-surface-700/60">
            <span>Gross: <strong className={monthlyStats.totalGrossPnl >= 0 ? 'text-profit-light' : 'text-loss-light'}>₹{monthlyStats.totalGrossPnl.toFixed(2)}</strong></span>
            <span>Friction: <strong className="text-amber-400">₹{monthlyStats.totalBrokerage.toFixed(2)}</strong></span>
          </div>
        </div>

        {/* Card 2: Profitable Days Ratio */}
        <div className="p-4 rounded-2xl border border-surface-700/80 bg-surface-850/80 backdrop-blur-md shadow-lg flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between text-xs font-semibold text-surface-400 mb-1.5">
              <span className="uppercase tracking-wider">Profitable Days</span>
              <span className="text-[11px] font-mono font-bold px-2 py-0.5 rounded-full bg-surface-750 text-surface-200 border border-surface-700">
                {monthlyStats.profitableDayRate.toFixed(1)}% Win Days
              </span>
            </div>
            <div className="flex items-baseline gap-2">
              <span className="text-2xl font-mono font-extrabold text-profit-light">
                {monthlyStats.greenDaysCount}W
              </span>
              <span className="text-sm font-mono text-surface-500">/</span>
              <span className="text-2xl font-mono font-extrabold text-loss-light">
                {monthlyStats.redDaysCount}L
              </span>
              <span className="text-xs text-surface-400 ml-1">({monthlyStats.tradedDaysCount} traded days)</span>
            </div>
          </div>
          <div className="text-[11px] text-surface-400 mt-2.5 pt-2 border-t border-surface-700/60 flex items-center justify-between">
            <span>Avg Daily Net:</span>
            <span className={`font-mono font-bold ${monthlyStats.avgDailyNet >= 0 ? 'text-profit-light' : 'text-loss-light'}`}>
              {monthlyStats.avgDailyNet >= 0 ? '+' : ''}₹{monthlyStats.avgDailyNet.toFixed(2)} / day
            </span>
          </div>
        </div>

        {/* Card 3: Best & Worst Days */}
        <div className="p-4 rounded-2xl border border-surface-700/80 bg-surface-850/80 backdrop-blur-md shadow-lg flex flex-col justify-between">
          <div className="flex items-center justify-between text-xs font-semibold text-surface-400 mb-1.5">
            <span className="uppercase tracking-wider">High / Low Watermark</span>
            <Award size={14} className="text-accent-light" />
          </div>
          <div className="space-y-1">
            <div className="flex items-center justify-between text-xs">
              <span className="text-surface-400 flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-profit"></span> Best Day:
              </span>
              <span className="font-mono font-bold text-profit-light">
                {monthlyStats.bestDay ? `+₹${monthlyStats.bestDay.netPnl.toFixed(2)}` : '—'}
              </span>
            </div>
            <div className="flex items-center justify-between text-xs">
              <span className="text-surface-400 flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-loss"></span> Worst Day:
              </span>
              <span className="font-mono font-bold text-loss-light">
                {monthlyStats.worstDay ? `${monthlyStats.worstDay.netPnl < 0 ? '' : '+'}₹${monthlyStats.worstDay.netPnl.toFixed(2)}` : '—'}
              </span>
            </div>
          </div>
          <div className="text-[11px] text-surface-500 mt-2 pt-2 border-t border-surface-700/60 truncate">
            {monthlyStats.bestDay ? `Peak session: ${monthlyStats.bestDay.dateStr}` : 'No sessions recorded yet'}
          </div>
        </div>

        {/* Card 4: Month Total Executed Trades */}
        <div className="p-4 rounded-2xl border border-surface-700/80 bg-surface-850/80 backdrop-blur-md shadow-lg flex flex-col justify-between">
          <div className="flex items-center justify-between text-xs font-semibold text-surface-400 mb-1.5">
            <span className="uppercase tracking-wider">Monthly Setups</span>
            <Layers size={14} className="text-accent-light" />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-mono font-extrabold text-white">
              {monthlyStats.totalMonthlyTrades}
            </span>
            <span className="text-xs text-surface-400 font-medium">completed orders</span>
          </div>
          <div className="text-[11px] text-surface-400 mt-2.5 pt-2 border-t border-surface-700/60 flex items-center justify-between">
            <span>Brokerage Saved:</span>
            <span className="font-mono font-bold text-profit-light">
              ₹{(monthlyStats.totalMonthlyTrades * 40).toLocaleString('en-IN')}
            </span>
          </div>
        </div>
      </div>

      {/* ─── 3. CALENDAR GRID ─────────────────────────────────────────── */}
      <div className="bg-surface-850/90 rounded-2xl border border-surface-700/80 shadow-xl overflow-hidden backdrop-blur-md">
        {/* Day of Week Header */}
        <div className="grid grid-cols-7 border-b border-surface-700/80 bg-surface-900/60 text-center text-xs font-bold text-surface-400 uppercase tracking-wider py-3">
          <div>Mon</div>
          <div>Tue</div>
          <div>Wed</div>
          <div>Thu</div>
          <div>Fri</div>
          <div className="text-surface-500">Sat</div>
          <div className="text-surface-500">Sun</div>
        </div>

        {/* Days Grid */}
        <div className="grid grid-cols-7 gap-[1px] bg-surface-800/80 p-[1px]">
          {calendarCells.map((cell, idx) => {
            const hasTrades = Boolean(cell.summary && cell.summary.ordersCount > 0);
            const isProfitable = hasTrades && cell.summary!.netPnl >= 0;
            const isLoss = hasTrades && cell.summary!.netPnl < 0;
            const isSelected = selectedDateStr === cell.dateStr;

            return (
              <div
                key={`${cell.dateStr}-${idx}`}
                onClick={() => setSelectedDateStr(cell.dateStr)}
                className={`min-h-[100px] p-2.5 flex flex-col justify-between transition-all relative cursor-pointer select-none group ${
                  cell.isCurrentMonth ? 'bg-surface-850' : 'bg-surface-900/50 text-surface-600'
                } ${
                  hasTrades
                    ? isProfitable
                      ? 'bg-gradient-to-b from-emerald-950/30 to-surface-850 hover:from-emerald-950/50 hover:border-emerald-500/50'
                      : 'bg-gradient-to-b from-rose-950/30 to-surface-850 hover:from-rose-950/50 hover:border-rose-500/50'
                    : cell.isWeekend
                      ? 'bg-surface-900/30 hover:bg-surface-800/40'
                      : 'hover:bg-surface-800/50'
                } ${
                  isSelected
                    ? 'ring-2 ring-accent border-accent z-10 shadow-lg shadow-accent/10'
                    : 'border border-transparent'
                }`}
              >
                {/* Day Header Row */}
                <div className="flex items-center justify-between">
                  <span
                    className={`text-xs font-mono font-bold rounded-md px-1.5 py-0.5 ${
                      cell.isToday
                        ? 'bg-accent text-white font-extrabold shadow-sm'
                        : cell.isCurrentMonth
                          ? 'text-surface-300 group-hover:text-white'
                          : 'text-surface-600'
                    }`}
                  >
                    {cell.day}
                  </span>

                  {cell.isToday && (
                    <span className="text-[9px] font-mono uppercase font-bold text-accent-light tracking-wider">
                      Today
                    </span>
                  )}
                </div>

                {/* Trade Metrics Content */}
                {hasTrades && cell.summary ? (
                  <div className="mt-1.5 space-y-1">
                    {/* Net P&L */}
                    <div
                      className={`text-sm font-mono font-black tracking-tight leading-tight ${
                        isProfitable ? 'text-profit-light' : 'text-loss-light'
                      }`}
                    >
                      {isProfitable ? '+' : ''}₹{cell.summary.netPnl.toFixed(2)}
                    </div>

                    {/* Trade Count and Win/Loss pill */}
                    <div className="flex items-center gap-1 text-[10px] font-mono text-surface-400">
                      <span className="px-1 py-0.2 rounded bg-surface-750 text-surface-200 border border-surface-700">
                        {cell.summary.ordersCount}T
                      </span>
                      <span className={`px-1 py-0.2 rounded border ${
                        isProfitable ? 'bg-profit-dark/15 text-profit-light border-profit/30' : 'bg-loss-dark/15 text-loss-light border-loss/30'
                      }`}>
                        {cell.summary.winningCount}W {cell.summary.losingCount}L
                      </span>
                    </div>
                  </div>
                ) : (
                  <div className="flex-1 flex items-end">
                    {cell.isWeekend ? (
                      <span className="text-[10px] text-surface-600 font-mono italic">Closed</span>
                    ) : (
                      <span className="text-[10px] text-surface-650 font-mono opacity-40">—</span>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* ─── 4. SELECTED DAY TRADE DRILLDOWN DRAWER ───────────────────── */}
      {selectedDateStr && (
        <div className="bg-surface-850/90 rounded-2xl border border-surface-700/80 shadow-xl overflow-hidden backdrop-blur-md">
          {/* Header */}
          <div className="p-4 border-b border-surface-700/80 flex flex-col md:flex-row md:items-center justify-between gap-3 bg-surface-900/40">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-xl bg-accent/20 text-accent-light flex items-center justify-center border border-accent/30">
                <Clock size={16} />
              </div>
              <div>
                <h3 className="text-base font-bold text-white tracking-tight flex items-center gap-2">
                  <span>Trades for {new Date(selectedDateStr + 'T00:00:00').toLocaleDateString('en-US', {
                    weekday: 'long',
                    year: 'numeric',
                    month: 'long',
                    day: 'numeric'
                  })}</span>
                  {selectedDateStr === todayIstStr && (
                    <span className="text-[10px] uppercase font-mono font-bold px-2 py-0.5 rounded bg-accent/20 text-accent-light border border-accent/30">
                      Today
                    </span>
                  )}
                </h3>
                <span className="text-xs text-surface-400">
                  {selectedDaySummary
                    ? `${selectedDaySummary.ordersCount} executed orders in this session`
                    : 'No virtual trades executed on this day'}
                </span>
              </div>
            </div>

            {selectedDaySummary && (
              <div className="flex items-center gap-4 flex-wrap">
                <div className="text-right">
                  <span className="text-[10px] text-surface-400 block uppercase tracking-wider font-semibold">Gross P&L</span>
                  <span className={`font-mono font-bold text-sm ${selectedDaySummary.grossPnl >= 0 ? 'text-profit-light' : 'text-loss-light'}`}>
                    {selectedDaySummary.grossPnl >= 0 ? '+' : ''}₹{selectedDaySummary.grossPnl.toFixed(2)}
                  </span>
                </div>
                <div className="text-right">
                  <span className="text-[10px] text-surface-400 block uppercase tracking-wider font-semibold">Est. Friction</span>
                  <span className="font-mono font-bold text-sm text-amber-400">
                    -₹{selectedDaySummary.brokerage.toFixed(2)}
                  </span>
                </div>
                <div className="text-right pl-3 border-l border-surface-700">
                  <span className="text-[10px] text-surface-400 block uppercase tracking-wider font-semibold">Net Day P&L</span>
                  <span className={`font-mono font-extrabold text-base ${selectedDaySummary.netPnl >= 0 ? 'text-profit-light' : 'text-loss-light'}`}>
                    {selectedDaySummary.netPnl >= 0 ? '+' : ''}₹{selectedDaySummary.netPnl.toFixed(2)}
                  </span>
                </div>
              </div>
            )}
          </div>

          {/* Trade Table or Empty State */}
          {!selectedDaySummary || selectedDaySummary.trades.length === 0 ? (
            <div className="py-14 text-center text-surface-400">
              <CalendarIcon size={32} className="mx-auto mb-2 opacity-30 text-accent-light" />
              <p className="text-sm font-semibold text-surface-300">No trading activity recorded for {selectedDateStr}</p>
              <p className="text-xs text-surface-500 mt-1 max-w-sm mx-auto">
                No orders triggered confluence gates or entered on this calendar date.
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-surface-700/80 text-surface-400 uppercase text-[10px] tracking-wider bg-surface-900/60 font-semibold">
                    <th className="px-5 py-3">Time</th>
                    <th className="px-5 py-3">Symbol</th>
                    <th className="px-5 py-3">Side</th>
                    <th className="px-5 py-3">Strategy</th>
                    <th className="px-5 py-3">Qty</th>
                    <th className="px-5 py-3">Entry (₹)</th>
                    <th className="px-5 py-3">Exit (₹)</th>
                    <th className="px-5 py-3">Status</th>
                    <th className="px-5 py-3 text-right">Net Return (₹)</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-surface-700/40">
                  {selectedDaySummary.trades.map((o) => {
                    const isProf = (o.pnl ?? 0) >= 0;
                    return (
                      <tr key={o.orderId} className="hover:bg-surface-750/30 transition-colors">
                        <td className="px-5 py-3 text-surface-400 font-mono text-[11px] whitespace-nowrap">
                          {o.entryTime ? new Date(o.entryTime).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '—'}
                        </td>
                        <td className="px-5 py-3 font-bold text-white tracking-wide">
                          <div className="flex items-center gap-1.5">
                            <span>{o.tradingsymbol}</span>
                            {o.partialBooked && (
                              <span className="text-[9px] font-mono font-bold px-1.5 py-0.2 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30">
                                50% T1
                              </span>
                            )}
                          </div>
                        </td>
                        <td className="px-5 py-3">
                          <span
                            className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                              o.direction === 'BUY'
                                ? 'bg-profit-dark/20 text-profit-light border border-profit/30'
                                : 'bg-loss-dark/20 text-loss-light border border-loss/30'
                            }`}
                          >
                            {o.direction}
                          </span>
                        </td>
                        <td className="px-5 py-3 text-surface-300 font-mono text-[11px]">
                          {o.strategy}
                        </td>
                        <td className="px-5 py-3 font-mono text-white">
                          {o.originalQuantity || o.quantity}
                        </td>
                        <td className="px-5 py-3 font-mono text-white">
                          ₹{o.entryPrice.toFixed(2)}
                        </td>
                        <td className="px-5 py-3 font-mono text-white">
                          {o.exitPrice ? `₹${o.exitPrice.toFixed(2)}` : '—'}
                        </td>
                        <td className="px-5 py-3">
                          <span
                            className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                              o.status === 'TARGET_HIT'
                                ? 'bg-profit-dark/20 text-profit-light border border-profit/30'
                                : o.status === 'STOPLOSS_HIT'
                                  ? 'bg-loss-dark/20 text-loss-light border border-loss/30'
                                  : o.status === 'AUTO_SQUARE_OFF'
                                    ? 'bg-purple-500/20 text-purple-300 border border-purple-500/30'
                                    : 'bg-surface-700 text-surface-300'
                            }`}
                          >
                            {o.status.replace(/_/g, ' ')}
                          </span>
                        </td>
                        <td className="px-5 py-3 font-mono font-bold text-right">
                          {o.pnl !== undefined ? (
                            <div>
                              <span className={isProf ? 'text-profit-light' : 'text-loss-light'}>
                                {isProf ? '+' : ''}₹{o.pnl.toFixed(2)}
                              </span>
                              {o.partialBooked && o.partialPnl !== undefined && (
                                <span className="block text-[10px] font-normal text-surface-400 mt-0.5">
                                  T1: +₹{o.partialPnl.toFixed(2)} | Leg 2: {o.pnl - o.partialPnl >= 0 ? '+' : ''}₹{(o.pnl - o.partialPnl).toFixed(2)}
                                </span>
                              )}
                            </div>
                          ) : (
                            <span className="text-surface-500 font-normal">Active</span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
export default PaperTradingCalendar;
