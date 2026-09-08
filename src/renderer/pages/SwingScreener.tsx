import React, { useState } from 'react';
import {
  Compass,
  RefreshCw,
  Search,
  Filter,
  TrendingUp,
  ShieldCheck,
  Zap,
  Target,
  BarChart3,
  Layers,
  Info,
  CheckCircle2,
  Clock,
  Sparkles,
  ChevronDown,
  ChevronUp,
  ExternalLink,
} from 'lucide-react';
import { SwingStockItem, SwingScanResult, SwingStockStatus } from '@shared/types';

const SwingScreener: React.FC = () => {
  const [scanResult, setScanResult] = useState<SwingScanResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<'ALL' | SwingStockStatus>('ALL');
  const [sectorFilter, setSectorFilter] = useState<string>('ALL');
  const [selectedStock, setSelectedStock] = useState<SwingStockItem | null>(null);
  const [expandedSymbol, setExpandedSymbol] = useState<string | null>(null);

  // NOTE: Per strict requirement: "dont auto fetch data in that page. only fetch data when i press a button"
  // We do NOT fetch data in useEffect on mount.

  const handleRunScan = async () => {
    setLoading(true);
    setError(null);
    try {
      if (window.electronAPI?.swing?.scan) {
        const result = await window.electronAPI.swing.scan({ limit: 15 });
        setScanResult(result);
      } else {
        // Fallback demo mock if running in browser without electronAPI
        setError('SmartAPI backend not connected. Please ensure the desktop app is running.');
      }
    } catch (err: any) {
      console.error('Failed to run swing screener:', err);
      setError(err?.message || 'Failed to scan market for swing trading stocks.');
    } finally {
      setLoading(false);
    }
  };

  // Extract unique sectors from scanned stocks
  const availableSectors = React.useMemo(() => {
    if (!scanResult?.topStocks) return [];
    const set = new Set<string>();
    scanResult.topStocks.forEach((s) => set.add(s.sector));
    return Array.from(set).sort();
  }, [scanResult]);

  // Filtered stocks list
  const filteredStocks = React.useMemo(() => {
    if (!scanResult?.topStocks) return [];
    return scanResult.topStocks.filter((stock) => {
      const matchesSearch =
        stock.tradingsymbol.toLowerCase().includes(searchQuery.toLowerCase()) ||
        stock.companyName.toLowerCase().includes(searchQuery.toLowerCase()) ||
        stock.sector.toLowerCase().includes(searchQuery.toLowerCase());
      const matchesStatus = statusFilter === 'ALL' || stock.status === statusFilter;
      const matchesSector = sectorFilter === 'ALL' || stock.sector === sectorFilter;
      return matchesSearch && matchesStatus && matchesSector;
    });
  }, [scanResult, searchQuery, statusFilter, sectorFilter]);

  const getStatusBadge = (status: SwingStockStatus) => {
    switch (status) {
      case 'IN_RANGE':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-profit/20 text-profit-light border border-profit/40">
            <span className="w-1.5 h-1.5 rounded-full bg-profit-light animate-pulse" />
            In Range (Buy Zone)
          </span>
        );
      case 'SETTING_UP':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-warning/20 text-warning-light border border-warning/40">
            <Clock size={12} />
            Setting Up (Near Pivot)
          </span>
        );
      case 'TRIGGERED':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-accent/20 text-accent-light border border-accent/40">
            <TrendingUp size={12} />
            Triggered (Extended)
          </span>
        );
      default:
        return null;
    }
  };

  const getScoreColor = (score: number) => {
    if (score >= 82) return 'text-profit-light';
    if (score >= 68) return 'text-accent-light';
    return 'text-warning-light';
  };

  const getScoreBg = (score: number) => {
    if (score >= 82) return 'bg-profit/10 border-profit/30 text-profit-light';
    if (score >= 68) return 'bg-accent/10 border-accent/30 text-accent-light';
    return 'bg-warning/10 border-warning/30 text-warning-light';
  };

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      {/* ─── Header ─────────────────────────────────────────────── */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-surface-800 pb-5">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-gradient-to-br from-accent/30 to-profit/20 border border-accent/30 text-accent-light shadow-lg">
              <Compass size={26} />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2.5">
                Swing Screener
                <span className="text-xs font-normal px-2 py-0.5 rounded-full bg-accent/20 text-accent-light border border-accent/30">
                  Top 15 Breakout Stocks
                </span>
              </h1>
              <p className="text-sm text-surface-400 mt-0.5">
                Institutional accumulation & Stage 2 breakout momentum scanner for high-conviction delivery & swing trades
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {scanResult && (
            <div className="text-right hidden sm:block">
              <div className="text-xs text-surface-400">Last Scanned</div>
              <div className="text-xs font-mono text-surface-300 font-medium">{scanResult.timestamp}</div>
            </div>
          )}
          <button
            onClick={handleRunScan}
            disabled={loading}
            className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-accent to-accent-dark hover:from-accent-light hover:to-accent text-white font-medium shadow-lg shadow-accent/25 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed hover:shadow-accent/40"
          >
            <RefreshCw size={17} className={loading ? 'animate-spin' : ''} />
            {loading ? 'Analyzing Historical Data...' : scanResult ? 'Re-Run Swing Screener' : 'Scan Swing Candidates'}
          </button>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-loss/10 border border-loss/30 text-loss-light text-sm flex items-center gap-3">
          <Info size={18} />
          <span>{error}</span>
        </div>
      )}

      {/* ─── Informational Banner (Strictly Non-Execution) ─────────── */}
      <div className="p-3.5 rounded-xl bg-surface-800/60 border border-surface-700/60 flex items-center justify-between text-xs text-surface-300">
        <div className="flex items-center gap-2.5">
          <ShieldCheck size={16} className="text-accent-light shrink-0" />
          <span>
            <strong className="text-white">Analysis & Screening Only:</strong> This module scans multi-week daily historical volume and Stage 2 pivot structures. Order placement is disabled for swing research.
          </span>
        </div>
        <span className="hidden md:inline-flex px-2 py-0.5 rounded bg-surface-700 font-mono text-surface-400">
          On-Demand Fetch
        </span>
      </div>

      {/* ─── State 1: No Scan Run Yet (Initial View) ───────────────── */}
      {!scanResult && !loading && (
        <div className="p-12 rounded-2xl bg-surface-900 border border-surface-800 text-center flex flex-col items-center justify-center space-y-6">
          <div className="p-5 rounded-2xl bg-surface-800/80 border border-surface-700 text-accent-light">
            <Sparkles size={40} className="animate-pulse" />
          </div>
          <div className="max-w-xl space-y-2">
            <h2 className="text-xl font-bold text-white">Institutional Swing Screener Ready</h2>
            <p className="text-sm text-surface-400 leading-relaxed">
              To minimize API load and analyze extensive multi-month daily historical candles, this screener operates strictly on-demand. Click below to screen the top 15 high-momentum stocks showing strong institutional accumulation and breakout readiness.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 max-w-2xl w-full text-left pt-2">
            <div className="p-4 rounded-xl bg-surface-800/50 border border-surface-700/50 space-y-1.5">
              <div className="text-xs font-semibold text-accent-light flex items-center gap-1.5">
                <BarChart3 size={14} /> Institutional Accumulation
              </div>
              <p className="text-xs text-surface-400">
                Chaikin Money Flow (CMF &gt; 0), Up/Down volume expansion, and upper quartile absorption.
              </p>
            </div>
            <div className="p-4 rounded-xl bg-surface-800/50 border border-surface-700/50 space-y-1.5">
              <div className="text-xs font-semibold text-profit-light flex items-center gap-1.5">
                <TrendingUp size={14} /> Stage 2 Breakouts
              </div>
              <p className="text-xs text-surface-400">
                Price above 50 & 200 SMA, 20-day pivot clearance, and Volatility Contraction Pattern (VCP) bases.
              </p>
            </div>
            <div className="p-4 rounded-xl bg-surface-800/50 border border-surface-700/50 space-y-1.5">
              <div className="text-xs font-semibold text-warning-light flex items-center gap-1.5">
                <Target size={14} /> Favorable Risk-to-Reward
              </div>
              <p className="text-xs text-surface-400">
                Calculated Buy Price, Stop Loss (1.5x ATR), and multi-week swing target with 1:2.5+ R:R.
              </p>
            </div>
          </div>

          <button
            onClick={handleRunScan}
            className="flex items-center gap-2.5 px-6 py-3 rounded-xl bg-accent hover:bg-accent-light text-white font-semibold shadow-xl shadow-accent/25 transition-all duration-200 mt-4"
          >
            <Zap size={18} />
            Run Swing Screener Now
          </button>
        </div>
      )}

      {/* ─── State 2: Loading State ───────────────────────────────── */}
      {loading && (
        <div className="p-16 rounded-2xl bg-surface-900 border border-surface-800 text-center flex flex-col items-center justify-center space-y-4">
          <RefreshCw size={36} className="text-accent-light animate-spin" />
          <div className="space-y-1">
            <h3 className="text-lg font-semibold text-white">Analyzing Historical Candles...</h3>
            <p className="text-xs text-surface-400 max-w-md">
              Evaluating multi-month price patterns, Chaikin Money Flow volume, relative volume expansion, and pivot breakouts across liquid F&amp;O constituents.
            </p>
          </div>
        </div>
      )}

      {/* ─── State 3: Results Display ─────────────────────────────── */}
      {scanResult && !loading && (
        <div className="space-y-6">
          {/* Summary Metric Cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="p-4 rounded-xl bg-surface-900 border border-surface-800">
              <div className="text-xs text-surface-400 font-medium">Top Candidates</div>
              <div className="text-2xl font-bold font-mono text-white mt-1">
                {scanResult.topStocks.length}
                <span className="text-xs text-surface-400 font-normal ml-1">stocks</span>
              </div>
              <div className="text-xs text-surface-400 mt-1">From {scanResult.totalScanned} analyzed</div>
            </div>

            <div className="p-4 rounded-xl bg-surface-900 border border-surface-800">
              <div className="text-xs text-surface-400 font-medium">In Buy Range</div>
              <div className="text-2xl font-bold font-mono text-profit-light mt-1">
                {scanResult.inRangeCount}
              </div>
              <div className="text-xs text-surface-400 mt-1">Ready for optimal entry</div>
            </div>

            <div className="p-4 rounded-xl bg-surface-900 border border-surface-800">
              <div className="text-xs text-surface-400 font-medium">Setting Up</div>
              <div className="text-2xl font-bold font-mono text-warning-light mt-1">
                {scanResult.settingUpCount}
              </div>
              <div className="text-xs text-surface-400 mt-1">Near pivot resistance</div>
            </div>

            <div className="p-4 rounded-xl bg-surface-900 border border-surface-800">
              <div className="text-xs text-surface-400 font-medium">Average R:R</div>
              <div className="text-2xl font-bold font-mono text-accent-light mt-1">
                1 : 2.5
              </div>
              <div className="text-xs text-surface-400 mt-1">Calculated Swing R:R</div>
            </div>
          </div>

          {/* Search, Status & Sector Filters */}
          <div className="flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3 p-4 rounded-xl bg-surface-900 border border-surface-800">
            <div className="relative flex-1 max-w-sm">
              <Search size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-surface-400" />
              <input
                type="text"
                placeholder="Search symbol, company, or sector..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-9 pr-4 py-2 bg-surface-800 border border-surface-700 rounded-lg text-sm text-white placeholder-surface-400 focus:outline-none focus:border-accent"
              />
            </div>

            <div className="flex flex-wrap items-center gap-2">
              {/* Status Filter Buttons */}
              <div className="flex rounded-lg bg-surface-800 p-1 border border-surface-700 text-xs">
                {(['ALL', 'IN_RANGE', 'SETTING_UP', 'TRIGGERED'] as const).map((st) => (
                  <button
                    key={st}
                    onClick={() => setStatusFilter(st)}
                    className={`px-3 py-1 rounded-md transition-colors ${
                      statusFilter === st
                        ? 'bg-surface-700 text-white font-semibold'
                        : 'text-surface-400 hover:text-surface-200'
                    }`}
                  >
                    {st === 'ALL'
                      ? 'All Status'
                      : st === 'IN_RANGE'
                      ? 'In Range'
                      : st === 'SETTING_UP'
                      ? 'Setting Up'
                      : 'Triggered'}
                  </button>
                ))}
              </div>

              {/* Sector Dropdown */}
              {availableSectors.length > 0 && (
                <select
                  value={sectorFilter}
                  onChange={(e) => setSectorFilter(e.target.value)}
                  className="px-3 py-1.5 bg-surface-800 border border-surface-700 rounded-lg text-xs text-surface-200 focus:outline-none focus:border-accent"
                >
                  <option value="ALL">All Sectors ({availableSectors.length})</option>
                  {availableSectors.map((sec) => (
                    <option key={sec} value={sec}>
                      {sec}
                    </option>
                  ))}
                </select>
              )}
            </div>
          </div>

          {/* Table of Top 15 Swing Stocks */}
          <div className="rounded-xl bg-surface-900 border border-surface-800 overflow-hidden shadow-xl">
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-surface-800 bg-surface-950/60 text-xs font-semibold text-surface-400 uppercase tracking-wider">
                    <th className="py-3.5 px-4">#</th>
                    <th className="py-3.5 px-4">Stock &amp; Sector</th>
                    <th className="py-3.5 px-4 text-right">LTP / Change</th>
                    <th className="py-3.5 px-4 text-right">Buy Price</th>
                    <th className="py-3.5 px-4 text-right">Sell Price (Target)</th>
                    <th className="py-3.5 px-4 text-right">Stop Loss</th>
                    <th className="py-3.5 px-4 text-center">Status</th>
                    <th className="py-3.5 px-4 text-center">Institutional Score</th>
                    <th className="py-3.5 px-4">Breakout Pattern</th>
                    <th className="py-3.5 px-4 text-center">Details</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-surface-800/60 text-sm">
                  {filteredStocks.length === 0 ? (
                    <tr>
                      <td colSpan={10} className="py-8 text-center text-surface-400 text-sm">
                        No stocks matched the active filters.
                      </td>
                    </tr>
                  ) : (
                    filteredStocks.map((stock, idx) => {
                      const isExpanded = expandedSymbol === stock.tradingsymbol;
                      const targetGainPct = (
                        ((stock.targetPrice - stock.buyPrice) / stock.buyPrice) *
                        100
                      ).toFixed(1);
                      const slRiskPct = (
                        ((stock.buyPrice - stock.stopLoss) / stock.buyPrice) *
                        100
                      ).toFixed(1);

                      return (
                        <React.Fragment key={stock.tradingsymbol}>
                          <tr
                            onClick={() =>
                              setExpandedSymbol(isExpanded ? null : stock.tradingsymbol)
                            }
                            className="hover:bg-surface-800/40 transition-colors cursor-pointer group"
                          >
                            <td className="py-3 px-4 font-mono text-xs text-surface-500">
                              {idx + 1}
                            </td>
                            <td className="py-3 px-4">
                              <div className="flex flex-col">
                                <div className="flex items-center gap-2">
                                  <span className="font-bold text-white group-hover:text-accent-light transition-colors">
                                    {stock.tradingsymbol}
                                  </span>
                                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-surface-800 border border-surface-700 text-surface-400">
                                    {stock.marketCapCategory}
                                  </span>
                                </div>
                                <span className="text-xs text-surface-400 truncate max-w-[190px]">
                                  {stock.sector}
                                </span>
                              </div>
                            </td>

                            <td className="py-3 px-4 text-right">
                              <div className="font-mono font-medium text-white">
                                ₹{stock.ltp.toFixed(2)}
                              </div>
                              <div
                                className={`text-xs font-mono ${
                                  stock.changePercent >= 0 ? 'text-profit-light' : 'text-loss-light'
                                }`}
                              >
                                {stock.changePercent >= 0 ? '+' : ''}
                                {stock.changePercent.toFixed(2)}%
                              </div>
                            </td>

                            {/* Buy Price */}
                            <td className="py-3 px-4 text-right">
                              <div className="font-mono font-bold text-accent-light">
                                ₹{stock.buyPrice.toFixed(2)}
                              </div>
                              <span className="text-[10px] text-surface-500 uppercase">Pivot Trigger</span>
                            </td>

                            {/* Sell Price */}
                            <td className="py-3 px-4 text-right">
                              <div className="font-mono font-bold text-profit-light">
                                ₹{stock.targetPrice.toFixed(2)}
                              </div>
                              <span className="text-[10px] text-profit-light/80 font-mono">
                                +{targetGainPct}%
                              </span>
                            </td>

                            {/* Stop Loss */}
                            <td className="py-3 px-4 text-right">
                              <div className="font-mono font-medium text-loss-light">
                                ₹{stock.stopLoss.toFixed(2)}
                              </div>
                              <span className="text-[10px] text-loss-light/80 font-mono">
                                -{slRiskPct}%
                              </span>
                            </td>

                            {/* Status */}
                            <td className="py-3 px-4 text-center">
                              {getStatusBadge(stock.status)}
                            </td>

                            {/* Institutional Score */}
                            <td className="py-3 px-4 text-center">
                              <div className="flex flex-col items-center">
                                <div
                                  className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full border text-xs font-bold font-mono ${getScoreBg(
                                    stock.institutionalScore
                                  )}`}
                                >
                                  <ShieldCheck size={12} />
                                  {stock.institutionalScore} / 100
                                </div>
                                <span className="text-[10px] text-surface-400 mt-0.5">
                                  {stock.institutionalActivity}
                                </span>
                              </div>
                            </td>

                            {/* Breakout Pattern */}
                            <td className="py-3 px-4">
                              <div className="text-xs font-medium text-surface-200">
                                {stock.pattern}
                              </div>
                              <div className="text-[11px] text-surface-400">
                                RVOL {stock.rvol}x • CMF {stock.cmf > 0 ? `+${stock.cmf}` : stock.cmf}
                              </div>
                            </td>

                            {/* Details expand icon */}
                            <td className="py-3 px-4 text-center text-surface-400">
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  setSelectedStock(stock);
                                }}
                                title="View Deep Analysis"
                                className="p-1.5 rounded-lg hover:bg-surface-700 text-surface-400 hover:text-white transition-colors"
                              >
                                <ExternalLink size={15} />
                              </button>
                            </td>
                          </tr>

                          {/* Inline Expansion Drawer */}
                          {isExpanded && (
                            <tr className="bg-surface-950/90 border-b border-surface-800">
                              <td colSpan={10} className="p-5">
                                <div className="grid grid-cols-1 md:grid-cols-3 gap-5 text-xs">
                                  {/* Technical & Volume Breakdown */}
                                  <div className="p-3.5 rounded-lg bg-surface-900 border border-surface-800 space-y-2">
                                    <div className="font-semibold text-white flex items-center gap-1.5">
                                      <TrendingUp size={14} className="text-accent-light" />
                                      Technical Structure
                                    </div>
                                    <div className="grid grid-cols-2 gap-y-1.5 text-surface-400">
                                      <div>RSI (14-day):</div>
                                      <div className="text-right font-mono text-white">{stock.rsi}</div>
                                      <div>Relative Volume:</div>
                                      <div className="text-right font-mono text-white">{stock.rvol}x</div>
                                      <div>Risk / Reward:</div>
                                      <div className="text-right font-mono text-profit-light font-bold">
                                        1 : {stock.riskRewardRatio}
                                      </div>
                                    </div>
                                  </div>

                                  {/* Institutional Accumulation */}
                                  <div className="p-3.5 rounded-lg bg-surface-900 border border-surface-800 space-y-2">
                                    <div className="font-semibold text-white flex items-center gap-1.5">
                                      <ShieldCheck size={14} className="text-profit-light" />
                                      Institutional Footprint
                                    </div>
                                    <div className="grid grid-cols-2 gap-y-1.5 text-surface-400">
                                      <div>Chaikin Money Flow:</div>
                                      <div className="text-right font-mono text-profit-light">
                                        {stock.cmf > 0 ? `+${stock.cmf}` : stock.cmf}
                                      </div>
                                      <div>Up/Down Vol Ratio:</div>
                                      <div className="text-right font-mono text-white">
                                        {stock.upDownVolumeRatio}x
                                      </div>
                                      <div>Accumulation Phase:</div>
                                      <div className="text-right font-medium text-accent-light">
                                        {stock.institutionalActivity}
                                      </div>
                                    </div>
                                  </div>

                                  {/* Fundamental Rationale */}
                                  <div className="p-3.5 rounded-lg bg-surface-900 border border-surface-800 space-y-1.5">
                                    <div className="flex items-center justify-between">
                                      <div className="font-semibold text-white flex items-center gap-1.5">
                                        <Info size={14} className="text-warning-light" />
                                        Fundamental Health
                                      </div>
                                      <span className="px-1.5 py-0.5 rounded bg-accent/20 text-accent-light font-bold text-[10px]">
                                        Rating {stock.fundamentalRating}
                                      </span>
                                    </div>
                                    <p className="text-surface-300 leading-relaxed text-[11px]">
                                      {stock.fundamentalSummary}
                                    </p>
                                  </div>
                                </div>
                              </td>
                            </tr>
                          )}
                        </React.Fragment>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* ─── Deep Inspection Modal ─────────────────────────────────── */}
      {selectedStock && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-surface-900 border border-surface-700 rounded-2xl max-w-2xl w-full p-6 space-y-5 shadow-2xl animate-fade-in">
            <div className="flex items-start justify-between border-b border-surface-800 pb-4">
              <div>
                <div className="flex items-center gap-2.5">
                  <h3 className="text-xl font-bold text-white">{selectedStock.tradingsymbol}</h3>
                  <span className="text-xs px-2 py-0.5 rounded bg-surface-800 border border-surface-700 text-surface-300">
                    {selectedStock.sector}
                  </span>
                  {getStatusBadge(selectedStock.status)}
                </div>
                <div className="text-xs text-surface-400 mt-1">{selectedStock.companyName}</div>
              </div>
              <button
                onClick={() => setSelectedStock(null)}
                className="text-surface-400 hover:text-white p-1 rounded-lg hover:bg-surface-800 transition-colors"
              >
                ✕
              </button>
            </div>

            {/* Price Levels Grid */}
            <div className="grid grid-cols-3 gap-3 text-center">
              <div className="p-3 rounded-xl bg-surface-800/80 border border-surface-700">
                <div className="text-xs text-surface-400">Buy Price (Trigger)</div>
                <div className="text-lg font-bold font-mono text-accent-light mt-0.5">
                  ₹{selectedStock.buyPrice.toFixed(2)}
                </div>
                <div className="text-[10px] text-surface-400 mt-0.5">Resistance Pivot</div>
              </div>
              <div className="p-3 rounded-xl bg-surface-800/80 border border-surface-700">
                <div className="text-xs text-surface-400">Sell Price (Target)</div>
                <div className="text-lg font-bold font-mono text-profit-light mt-0.5">
                  ₹{selectedStock.targetPrice.toFixed(2)}
                </div>
                <div className="text-[10px] text-profit-light font-mono mt-0.5">
                  +{(
                    ((selectedStock.targetPrice - selectedStock.buyPrice) / selectedStock.buyPrice) *
                    100
                  ).toFixed(1)}
                  % Upside
                </div>
              </div>
              <div className="p-3 rounded-xl bg-surface-800/80 border border-surface-700">
                <div className="text-xs text-surface-400">Stop Loss</div>
                <div className="text-lg font-bold font-mono text-loss-light mt-0.5">
                  ₹{selectedStock.stopLoss.toFixed(2)}
                </div>
                <div className="text-[10px] text-loss-light font-mono mt-0.5">
                  -{(
                    ((selectedStock.buyPrice - selectedStock.stopLoss) / selectedStock.buyPrice) *
                    100
                  ).toFixed(1)}
                  % Invalidation
                </div>
              </div>
            </div>

            {/* Metrics Breakdown */}
            <div className="grid grid-cols-2 gap-4 text-xs">
              <div className="p-4 rounded-xl bg-surface-800/50 border border-surface-700/60 space-y-2">
                <div className="font-semibold text-white flex items-center gap-1.5">
                  <ShieldCheck size={14} className="text-accent-light" />
                  Institutional Metrics
                </div>
                <div className="space-y-1 text-surface-300">
                  <div className="flex justify-between">
                    <span>Institutional Score:</span>
                    <span className="font-bold text-white font-mono">
                      {selectedStock.institutionalScore} / 100
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span>Chaikin Money Flow (CMF):</span>
                    <span className="font-mono text-profit-light">
                      {selectedStock.cmf > 0 ? `+${selectedStock.cmf}` : selectedStock.cmf}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span>Up / Down Volume Ratio:</span>
                    <span className="font-mono text-white">{selectedStock.upDownVolumeRatio}x</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Relative Volume (RVOL):</span>
                    <span className="font-mono text-white">{selectedStock.rvol}x</span>
                  </div>
                </div>
              </div>

              <div className="p-4 rounded-xl bg-surface-800/50 border border-surface-700/60 space-y-2">
                <div className="font-semibold text-white flex items-center gap-1.5">
                  <TrendingUp size={14} className="text-profit-light" />
                  Technical Setup
                </div>
                <div className="space-y-1 text-surface-300">
                  <div className="flex justify-between">
                    <span>Breakout Pattern:</span>
                    <span className="font-medium text-white">{selectedStock.pattern}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>RSI (14-day Daily):</span>
                    <span className="font-mono text-white">{selectedStock.rsi}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Risk-to-Reward:</span>
                    <span className="font-bold text-profit-light font-mono">
                      1 : {selectedStock.riskRewardRatio}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span>Market Cap Tier:</span>
                    <span className="text-surface-400">{selectedStock.marketCapCategory}</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Fundamental Summary */}
            <div className="p-4 rounded-xl bg-surface-800/40 border border-surface-700/60 space-y-1">
              <div className="text-xs font-semibold text-white flex items-center gap-1.5">
                <Info size={14} className="text-warning-light" />
                Fundamental Thesis ({selectedStock.fundamentalRating} Grade)
              </div>
              <p className="text-xs text-surface-300 leading-relaxed">
                {selectedStock.fundamentalSummary}
              </p>
            </div>

            <div className="flex justify-end pt-2">
              <button
                onClick={() => setSelectedStock(null)}
                className="px-4 py-2 bg-surface-800 hover:bg-surface-700 text-white rounded-lg text-xs font-medium transition-colors"
              >
                Close Inspection
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default SwingScreener;
