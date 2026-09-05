import React, { useState, useEffect, useMemo } from 'react';
import { useTradingStore } from '../stores/trading-store';
import OrderForm from '../components/OrderForm';
import {
  Search,
  RefreshCw,
  XCircle,
  Clock,
  CheckCircle2,
  AlertOctagon,
  Ban,
  ArrowDownLeft,
  ArrowUpRight,
  Filter,
  DollarSign,
  Bot
} from 'lucide-react';

const Orders: React.FC = () => {
  const { orders, setOrders } = useTradingStore();
  const [tab, setTab] = useState<'all' | 'open' | 'completed' | 'rejected' | 'cancelled'>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [refreshing, setRefreshing] = useState(false);
  const [cancellingId, setCancellingId] = useState<string | null>(null);

  const fetchOrders = async (force = false) => {
    try {
      setRefreshing(true);
      const response = await window.electronAPI?.orders.getAll({ force });
      if (response && Array.isArray(response)) {
        setOrders(response);
      }
    } catch (e) {
      console.error('Failed to fetch orders:', e);
    } finally {
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchOrders(false);
    const interval = setInterval(() => fetchOrders(false), 10000);
    return () => clearInterval(interval);
  }, []);

  const handleCancelOrder = async (orderId: string) => {
    try {
      setCancellingId(orderId);
      await window.electronAPI?.orders.cancel(orderId, 'NORMAL');
      await fetchOrders(true);
    } catch (e) {
      console.error('Failed to cancel order:', e);
    } finally {
      setCancellingId(null);
    }
  };

  // Filtered orders computation
  const filteredOrders = useMemo(() => {
    return orders.filter((o) => {
      // Status tab filter
      const statusUpper = (o.status || '').toUpperCase();
      if (tab === 'open' && !statusUpper.includes('OPEN') && !statusUpper.includes('PENDING') && !statusUpper.includes('TRIGGER_PENDING')) {
        return false;
      }
      if (tab === 'completed' && statusUpper !== 'COMPLETE' && statusUpper !== 'COMPLETED') {
        return false;
      }
      if (tab === 'rejected' && statusUpper !== 'REJECTED') {
        return false;
      }
      if (tab === 'cancelled' && statusUpper !== 'CANCELLED' && statusUpper !== 'CANCELED') {
        return false;
      }

      // Search query filter
      if (searchQuery.trim()) {
        const query = searchQuery.toLowerCase().trim();
        const symbolMatch = (o.tradingsymbol || '').toLowerCase().includes(query);
        const idMatch = (o.orderId || '').toLowerCase().includes(query);
        const typeMatch = (o.transactionType || '').toLowerCase().includes(query);
        if (!symbolMatch && !idMatch && !typeMatch) return false;
      }

      return true;
    });
  }, [orders, tab, searchQuery]);

  // Statistics counts
  const totalOrders = orders.length;
  const openCount = orders.filter((o) => {
    const s = (o.status || '').toUpperCase();
    return s.includes('OPEN') || s.includes('PENDING');
  }).length;
  const completedCount = orders.filter((o) => {
    const s = (o.status || '').toUpperCase();
    return s === 'COMPLETE' || s === 'COMPLETED';
  }).length;
  const rejectedCount = orders.filter((o) => (o.status || '').toUpperCase() === 'REJECTED').length;
  const cancelledCount = orders.filter((o) => {
    const s = (o.status || '').toUpperCase();
    return s === 'CANCELLED' || s === 'CANCELED';
  }).length;

  const totalTurnover = orders
    .filter((o) => ['COMPLETE', 'COMPLETED'].includes((o.status || '').toUpperCase()))
    .reduce((acc, o) => acc + (o.averagePrice || o.price || 0) * (o.filledQuantity || o.quantity || 0), 0);

  const getStatusBadge = (status: string, statusMessage?: string) => {
    const s = (status || '').toUpperCase();
    if (s === 'COMPLETE' || s === 'COMPLETED') {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-profit-dark/20 text-profit-light border border-profit/30">
          <CheckCircle2 size={12} />
          Complete
        </span>
      );
    }
    if (s.includes('OPEN') || s.includes('PENDING')) {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-500/20 text-amber-300 border border-amber-500/30">
          <Clock size={12} className="animate-spin" />
          Pending
        </span>
      );
    }
    if (s === 'REJECTED') {
      return (
        <span
          className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-loss-dark/20 text-loss-light border border-loss/30 cursor-help"
          title={statusMessage || 'Order rejected by exchange/RMS'}
        >
          <AlertOctagon size={12} />
          Rejected
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-surface-700 text-surface-300 border border-surface-600">
        <Ban size={12} />
        {status}
      </span>
    );
  };

  return (
    <div className="p-6 h-full flex flex-col space-y-6 max-w-[1600px] mx-auto overflow-auto animate-fade-in">
      {/* ─── HEADER & SUMMARY STATS ──────────────────────────────────── */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-1 border-b border-surface-800/80">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Order Execution & History</h1>
          <p className="text-xs text-surface-400 mt-1">
            Real-time SmartAPI order book with algorithmic and manual executions.
          </p>
        </div>

        <button
          onClick={() => fetchOrders(true)}
          disabled={refreshing}
          className="flex items-center gap-2 px-3.5 py-2 bg-surface-800 hover:bg-surface-750 text-surface-200 hover:text-white border border-surface-700 rounded-xl text-xs font-semibold transition-all shadow-sm cursor-pointer disabled:opacity-50 self-start md:self-auto"
        >
          <RefreshCw size={14} className={refreshing ? 'animate-spin text-accent-light' : 'text-surface-400'} />
          <span>{refreshing ? 'Updating Orders...' : 'Refresh Orders'}</span>
        </button>
      </div>

      {/* ─── STATS STRIP ─────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
        <div className="bg-surface-800/80 backdrop-blur-sm p-4 rounded-xl border border-surface-700/80">
          <span className="text-[11px] uppercase font-semibold text-surface-400 block mb-1">Total Orders</span>
          <span className="text-2xl font-mono font-bold text-white">{totalOrders}</span>
        </div>
        <div className="bg-surface-800/80 backdrop-blur-sm p-4 rounded-xl border border-surface-700/80">
          <span className="text-[11px] uppercase font-semibold text-surface-400 block mb-1">Open / Pending</span>
          <span className={`text-2xl font-mono font-bold ${openCount > 0 ? 'text-amber-300' : 'text-white'}`}>
            {openCount}
          </span>
        </div>
        <div className="bg-surface-800/80 backdrop-blur-sm p-4 rounded-xl border border-surface-700/80">
          <span className="text-[11px] uppercase font-semibold text-surface-400 block mb-1">Executed / Filled</span>
          <span className="text-2xl font-mono font-bold text-profit-light">{completedCount}</span>
        </div>
        <div className="bg-surface-800/80 backdrop-blur-sm p-4 rounded-xl border border-surface-700/80">
          <span className="text-[11px] uppercase font-semibold text-surface-400 block mb-1">Rejected</span>
          <span className={`text-2xl font-mono font-bold ${rejectedCount > 0 ? 'text-loss-light' : 'text-surface-400'}`}>
            {rejectedCount}
          </span>
        </div>
        <div className="bg-surface-800/80 backdrop-blur-sm p-4 rounded-xl border border-surface-700/80 col-span-2 sm:col-span-1">
          <span className="text-[11px] uppercase font-semibold text-surface-400 block mb-1">Filled Turnover</span>
          <span className="text-2xl font-mono font-bold text-accent-light">₹{totalTurnover.toLocaleString('en-IN', { maximumFractionDigits: 0 })}</span>
        </div>
      </div>

      {/* ─── MAIN LAYOUT: ORDER TABLE + ORDER FORM ───────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 flex-1 min-h-0">
        {/* Orders Table Container (3 cols) */}
        <div className="lg:col-span-3 flex flex-col bg-surface-800/90 backdrop-blur-md rounded-2xl border border-surface-700/80 shadow-lg overflow-hidden">
          {/* Filters & Search Toolbar */}
          <div className="p-4 border-b border-surface-700/80 flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-surface-850/60">
            {/* Status Tabs with Badge Counts */}
            <div className="flex items-center gap-1.5 overflow-x-auto pb-1 sm:pb-0">
              {[
                { id: 'all', label: 'All', count: totalOrders },
                { id: 'open', label: 'Open', count: openCount },
                { id: 'completed', label: 'Executed', count: completedCount },
                { id: 'rejected', label: 'Rejected', count: rejectedCount },
                { id: 'cancelled', label: 'Cancelled', count: cancelledCount }
              ].map((t) => (
                <button
                  key={t.id}
                  onClick={() => setTab(t.id as any)}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                    tab === t.id
                      ? 'bg-accent/20 text-accent-light border border-accent/40 shadow-sm'
                      : 'text-surface-400 hover:text-white hover:bg-surface-700/60'
                  }`}
                >
                  <span>{t.label}</span>
                  <span className={`px-1.5 py-0.2 rounded-full text-[10px] font-mono ${
                    tab === t.id ? 'bg-accent text-surface-950 font-bold' : 'bg-surface-700 text-surface-300'
                  }`}>
                    {t.count}
                  </span>
                </button>
              ))}
            </div>

            {/* Instant Search Bar */}
            <div className="relative w-full sm:w-64">
              <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-surface-400" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search symbol or order ID..."
                className="w-full bg-surface-900 border border-surface-700/80 rounded-xl pl-8 pr-3 py-1.5 text-xs text-white placeholder-surface-500 focus:outline-none focus:border-accent-light transition-colors"
              />
            </div>
          </div>

          {/* Orders Table */}
          <div className="flex-1 overflow-auto">
            <table className="w-full text-xs text-left">
              <thead className="text-[11px] text-surface-400 uppercase bg-surface-900/90 border-b border-surface-700/80 sticky top-0 backdrop-blur-sm z-10">
                <tr>
                  <th className="px-5 py-3 font-semibold">Time</th>
                  <th className="px-5 py-3 font-semibold">Symbol</th>
                  <th className="px-5 py-3 font-semibold">Side</th>
                  <th className="px-5 py-3 font-semibold">Product</th>
                  <th className="px-5 py-3 font-semibold">Type</th>
                  <th className="px-5 py-3 font-semibold">Quantity</th>
                  <th className="px-5 py-3 font-semibold">Price</th>
                  <th className="px-5 py-3 font-semibold">Status</th>
                  <th className="px-5 py-3 font-semibold text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-700/50">
                {filteredOrders.length === 0 ? (
                  <tr>
                    <td colSpan={9} className="px-6 py-16 text-center text-surface-400">
                      <div className="flex flex-col items-center justify-center space-y-2">
                        <Filter size={28} className="opacity-40 mb-1" />
                        <span className="font-semibold text-white text-sm">No orders match your filter</span>
                        <p className="text-xs text-surface-500 max-w-sm">
                          {searchQuery
                            ? `No results found for "${searchQuery}". Try searching with a different term.`
                            : `There are currently no orders in the "${tab}" tab.`}
                        </p>
                      </div>
                    </td>
                  </tr>
                ) : (
                  filteredOrders.map((o) => {
                    const isBuy = o.transactionType === 'BUY';
                    const isOpen = (o.status || '').toUpperCase().includes('OPEN') || (o.status || '').toUpperCase().includes('PENDING');
                    const isCancelling = cancellingId === o.orderId;

                    return (
                      <tr key={o.orderId} className="hover:bg-surface-700/40 transition-colors">
                        {/* Time */}
                        <td className="px-5 py-3.5 font-mono text-surface-400 whitespace-nowrap">
                          {o.orderTimestamp ? new Date(o.orderTimestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) : '--:--:--'}
                        </td>

                        {/* Symbol & Source */}
                        <td className="px-5 py-3.5 font-semibold text-white whitespace-nowrap">
                          <div className="flex items-center gap-2">
                            <span>{o.tradingsymbol}</span>
                            <span className="text-[10px] text-surface-400 font-mono bg-surface-700/70 px-1.5 py-0.5 rounded">
                              {o.exchange || 'NSE'}
                            </span>
                            {o.isAppOrder && (
                              <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-bold bg-accent/20 text-accent-light border border-accent/30">
                                <Bot size={11} />
                                AGENT
                              </span>
                            )}
                          </div>
                          {o.orderId && (
                            <div className="text-[10px] text-surface-500 font-mono mt-0.5">
                              ID: {o.orderId.slice(-8)}
                            </div>
                          )}
                        </td>

                        {/* Side */}
                        <td className="px-5 py-3.5 whitespace-nowrap">
                          <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded font-bold text-[11px] ${
                            isBuy ? 'bg-profit-dark/20 text-profit-light border border-profit/30' : 'bg-loss-dark/20 text-loss-light border border-loss/30'
                          }`}>
                            {isBuy ? <ArrowUpRight size={12} /> : <ArrowDownLeft size={12} />}
                            {o.transactionType}
                          </span>
                        </td>

                        {/* Product */}
                        <td className="px-5 py-3.5 whitespace-nowrap text-surface-300 font-medium">
                          <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-surface-750 border border-surface-700">
                            {o.product || 'MIS'}
                          </span>
                        </td>

                        {/* Order Type */}
                        <td className="px-5 py-3.5 whitespace-nowrap text-surface-300 font-mono">
                          {o.orderType || 'LIMIT'}
                        </td>

                        {/* Quantity */}
                        <td className="px-5 py-3.5 whitespace-nowrap font-mono">
                          <span className="text-white font-bold">{o.filledQuantity ?? o.quantity}</span>
                          <span className="text-surface-500"> / {o.quantity}</span>
                        </td>

                        {/* Price */}
                        <td className="px-5 py-3.5 whitespace-nowrap font-mono text-white font-semibold">
                          ₹{(o.averagePrice || o.price || 0).toFixed(2)}
                        </td>

                        {/* Status */}
                        <td className="px-5 py-3.5 whitespace-nowrap">
                          {getStatusBadge(o.status, o.statusMessage)}
                          {o.statusMessage && o.status === 'REJECTED' && (
                            <div className="text-[10px] text-loss-light/80 truncate max-w-[160px] mt-0.5" title={o.statusMessage}>
                              {o.statusMessage}
                            </div>
                          )}
                        </td>

                        {/* Actions */}
                        <td className="px-5 py-3.5 whitespace-nowrap text-right">
                          {isOpen ? (
                            <button
                              onClick={() => handleCancelOrder(o.orderId)}
                              disabled={isCancelling}
                              className="px-2.5 py-1 bg-loss-dark/30 hover:bg-loss-dark text-loss-light hover:text-white border border-loss/40 rounded-lg text-xs font-semibold transition-all cursor-pointer disabled:opacity-50"
                            >
                              {isCancelling ? 'Cancelling...' : 'Cancel'}
                            </button>
                          ) : (
                            <span className="text-surface-600 font-mono text-xs">—</span>
                          )}
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Manual Order Placement Card (1 col) */}
        <div className="flex flex-col space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-bold text-white">Manual Order</h2>
            <span className="text-[11px] text-surface-400">Direct SmartAPI</span>
          </div>
          <OrderForm />
        </div>
      </div>
    </div>
  );
};

export default Orders;
