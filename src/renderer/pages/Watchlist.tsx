import React, { useState, useEffect, useRef } from 'react';
import { useTradingStore } from '../stores/trading-store';
import { useSmartAPI } from '../hooks/useSmartAPI';
import { WatchlistItem, TransactionType } from '@shared/types';
import { Search, X, Plus, TrendingUp, TrendingDown, RefreshCw, ShoppingCart } from 'lucide-react';

const Watchlist: React.FC = () => {
  const { watchlist, setWatchlist, ticks, settings } = useTradingStore();
  const { placeOrder } = useSmartAPI();

  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [showDropdown, setShowDropdown] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  // Quick order state
  const [orderModal, setOrderModal] = useState<{
    open: boolean;
    symbol: string;
    type: TransactionType;
    price: number;
    qty: number;
    submitting: boolean;
    error: string | null;
    success: string | null;
  }>({
    open: false,
    symbol: '',
    type: 'BUY',
    price: 0,
    qty: 1,
    submitting: false,
    error: null,
    success: null,
  });

  const searchRef = useRef<HTMLDivElement>(null);

  // Load watchlist on mount or fallback to settings
  const loadWatchlist = async () => {
    try {
      setRefreshing(true);
      let symbols: string[] = [];
      if (window.electronAPI?.watchlist) {
        symbols = await window.electronAPI.watchlist.get();
      }
      if (!symbols || symbols.length === 0) {
        symbols = settings?.watchlist || ['RELIANCE', 'TCS', 'HDFCBANK', 'INFY', 'ICICIBANK', 'SBIN'];
      }

      // Fetch quotes to get initial prices
      let quoteData: Record<string, any> = {};
      try {
        if (window.electronAPI?.market?.quote) {
          quoteData = await window.electronAPI.market.quote(symbols);
        }
      } catch (e) {
        console.warn('Could not fetch quotes for watchlist:', e);
      }

      const items: WatchlistItem[] = symbols.map((sym: string) => {
        const clean = sym.replace('NSE:', '').replace('-EQ', '').toUpperCase();
        const quote = quoteData[sym] || quoteData[`NSE:${clean}`] || quoteData[clean];
        const lastPrice = quote?.last_price || quote?.lastPrice || 0;
        const close = quote?.ohlc?.close || quote?.close || lastPrice;
        const change = close > 0 && lastPrice > 0 ? lastPrice - close : 0;
        const changePercent = close > 0 ? (change / close) * 100 : 0;

        return {
          tradingsymbol: clean,
          exchange: 'NSE',
          instrumentToken: quote?.instrument_token || 0,
          lastPrice,
          change: Math.round(change * 100) / 100,
          changePercent: Math.round(changePercent * 100) / 100,
          open: quote?.ohlc?.open || 0,
          high: quote?.ohlc?.high || 0,
          low: quote?.ohlc?.low || 0,
          close,
          volume: quote?.volume || 0,
          activeSignals: [],
        };
      });

      setWatchlist(items);
    } catch (err) {
      console.error('Failed to load watchlist:', err);
    } finally {
      setRefreshing(false);
    }
  };

  useEffect(() => {
    loadWatchlist();
  }, []);

  // Close search dropdown on click outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (searchRef.current && !searchRef.current.contains(e.target as Node)) {
        setShowDropdown(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Debounced instrument search
  useEffect(() => {
    if (!searchQuery.trim() || searchQuery.length < 2) {
      setSearchResults([]);
      setShowDropdown(false);
      return;
    }

    const timer = setTimeout(async () => {
      setIsSearching(true);
      try {
        if (window.electronAPI?.market?.search) {
          const res = await window.electronAPI.market.search(searchQuery.trim());
          if (Array.isArray(res)) {
            setSearchResults(res.slice(0, 8));
            setShowDropdown(true);
          }
        }
      } catch (e) {
        console.error('Search error:', e);
      } finally {
        setIsSearching(false);
      }
    }, 250);

    return () => clearTimeout(timer);
  }, [searchQuery]);

  const handleAddSymbol = async (symbolToAdd: string) => {
    const clean = symbolToAdd.replace('NSE:', '').replace('-EQ', '').toUpperCase().trim();
    if (!clean) return;

    if (watchlist.some((w) => w.tradingsymbol === clean)) {
      setSearchQuery('');
      setShowDropdown(false);
      return;
    }

    try {
      if (window.electronAPI?.watchlist?.add) {
        await window.electronAPI.watchlist.add(clean);
      }
      setSearchQuery('');
      setShowDropdown(false);
      await loadWatchlist();
    } catch (err) {
      console.error('Failed to add symbol:', err);
    }
  };

  const handleRemoveSymbol = async (symbolToRemove: string) => {
    try {
      if (window.electronAPI?.watchlist?.remove) {
        await window.electronAPI.watchlist.remove(symbolToRemove);
      }
      setWatchlist(watchlist.filter((w) => w.tradingsymbol !== symbolToRemove));
    } catch (err) {
      console.error('Failed to remove symbol:', err);
    }
  };

  const handleOpenOrder = (symbol: string, type: TransactionType, currentPrice: number) => {
    setOrderModal({
      open: true,
      symbol,
      type,
      price: currentPrice || 100,
      qty: 1,
      submitting: false,
      error: null,
      success: null,
    });
  };

  const handleQuickOrderSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setOrderModal((prev) => ({ ...prev, submitting: true, error: null, success: null }));
    try {
      await placeOrder({
        tradingsymbol: orderModal.symbol,
        exchange: 'NSE',
        transactionType: orderModal.type,
        quantity: orderModal.qty,
        orderType: 'LIMIT',
        product: 'MIS',
        price: orderModal.price,
      });
      setOrderModal((prev) => ({
        ...prev,
        submitting: false,
        success: `Order placed: ${orderModal.type} ${orderModal.qty} ${orderModal.symbol} @ ₹${orderModal.price}`,
      }));
      setTimeout(() => {
        setOrderModal((prev) => ({ ...prev, open: false, success: null }));
      }, 1500);
    } catch (err: any) {
      setOrderModal((prev) => ({
        ...prev,
        submitting: false,
        error: err.message || 'Failed to place order',
      }));
    }
  };

  return (
    <div className="p-6 h-full flex flex-col space-y-6">
      {/* Header & Search Bar */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            Watchlist
            <span className="text-xs bg-surface-800 text-surface-400 font-mono px-2 py-0.5 rounded">
              {watchlist.length} instruments
            </span>
          </h1>
          <p className="text-xs text-surface-400 mt-0.5">
            Monitor real-time quotes, fast execution, and active intraday candidates
          </p>
        </div>

        <div className="flex items-center gap-3 w-full sm:w-auto">
          <button
            onClick={loadWatchlist}
            disabled={refreshing}
            className="p-2 rounded-lg bg-surface-800 hover:bg-surface-700 text-surface-300 hover:text-white border border-surface-700 transition-colors"
            title="Refresh prices"
          >
            <RefreshCw size={16} className={refreshing ? 'animate-spin' : ''} />
          </button>

          {/* Search Input with Auto-complete */}
          <div ref={searchRef} className="relative w-full sm:w-72">
            <Search
              className="absolute left-3 top-1/2 transform -translate-y-1/2 text-surface-400"
              size={16}
            />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && searchQuery.trim()) {
                  handleAddSymbol(searchQuery.trim());
                }
              }}
              placeholder="Search or add (e.g. INFY)..."
              className="w-full bg-surface-800 border border-surface-700 rounded-lg pl-9 pr-8 py-2 text-sm text-white placeholder-surface-500 focus:outline-none focus:border-accent-light"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery('')}
                className="absolute right-2.5 top-1/2 transform -translate-y-1/2 text-surface-500 hover:text-surface-300"
              >
                <X size={14} />
              </button>
            )}

            {/* Dropdown Suggestions */}
            {showDropdown && searchResults.length > 0 && (
              <div className="absolute top-full left-0 right-0 mt-1.5 bg-surface-800 border border-surface-700 rounded-lg shadow-xl overflow-hidden z-50">
                {searchResults.map((item, idx) => {
                  const sym = item.tradingsymbol || item.symbol || '';
                  const clean = sym.replace('-EQ', '');
                  const alreadyInWatchlist = watchlist.some((w) => w.tradingsymbol === clean);

                  return (
                    <div
                      key={idx}
                      onClick={() => !alreadyInWatchlist && handleAddSymbol(clean)}
                      className={`px-3 py-2 flex items-center justify-between cursor-pointer border-b border-surface-700/50 last:border-0 ${
                        alreadyInWatchlist
                          ? 'opacity-50 cursor-not-allowed bg-surface-900/50'
                          : 'hover:bg-surface-700/80'
                      }`}
                    >
                      <div>
                        <div className="text-sm font-semibold text-white">{clean}</div>
                        <div className="text-xs text-surface-400 truncate max-w-[180px]">
                          {item.name || item.exchange || 'NSE'}
                        </div>
                      </div>
                      {alreadyInWatchlist ? (
                        <span className="text-[10px] text-surface-500 font-medium">Added</span>
                      ) : (
                        <Plus size={14} className="text-accent-light" />
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Grid of Watchlist Items */}
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4 overflow-auto pb-4">
        {watchlist.length === 0 ? (
          <div className="col-span-full py-16 text-center text-surface-400 border border-dashed border-surface-700 rounded-xl bg-surface-800/30">
            <Search className="mx-auto text-surface-500 mb-2" size={32} />
            <p className="font-semibold text-white">Your Watchlist is empty</p>
            <p className="text-xs text-surface-500 mt-1">
              Search for Nifty 50 or custom stocks above to monitor prices and trade.
            </p>
          </div>
        ) : (
          watchlist.map((item) => {
            const tick = ticks[item.tradingsymbol] || ticks[`${item.tradingsymbol}-EQ`];
            const price = tick?.lastPrice || item.lastPrice || 0;
            const change = tick?.change || item.change || 0;
            const changePercent = tick?.changePercent || item.changePercent || 0;
            const isPos = changePercent >= 0;

            return (
              <div
                key={item.tradingsymbol}
                className="bg-surface-800 rounded-xl p-4 border border-surface-700 hover:border-surface-600 transition-all flex flex-col justify-between group shadow-sm"
              >
                <div>
                  <div className="flex justify-between items-start mb-2">
                    <div>
                      <h3 className="font-bold text-base text-white tracking-wide">
                        {item.tradingsymbol}
                      </h3>
                      <span className="text-[10px] text-surface-400 uppercase font-mono">NSE • EQ</span>
                    </div>
                    <button
                      onClick={() => handleRemoveSymbol(item.tradingsymbol)}
                      className="text-surface-500 hover:text-loss-light opacity-0 group-hover:opacity-100 transition-opacity p-1 rounded hover:bg-surface-700"
                      title={`Remove ${item.tradingsymbol}`}
                    >
                      <X size={14} />
                    </button>
                  </div>

                  <div className="flex items-end justify-between mt-4">
                    <div className="font-mono text-xl font-bold text-white">
                      {price > 0 ? `₹${price.toFixed(2)}` : '—'}
                    </div>
                    <div
                      className={`font-mono text-xs flex items-center gap-0.5 font-semibold ${
                        isPos ? 'text-profit-light' : 'text-loss-light'
                      }`}
                    >
                      {isPos ? <TrendingUp size={12} /> : <TrendingDown size={12} />}
                      {isPos ? '+' : ''}
                      {changePercent.toFixed(2)}%
                    </div>
                  </div>
                </div>

                <div className="flex gap-2 mt-4 pt-3 border-t border-surface-700/80">
                  <button
                    onClick={() => handleOpenOrder(item.tradingsymbol, 'BUY', price)}
                    className="flex-1 bg-profit-dark hover:bg-profit py-1.5 rounded-lg text-white text-xs font-bold transition-colors shadow-sm"
                  >
                    BUY
                  </button>
                  <button
                    onClick={() => handleOpenOrder(item.tradingsymbol, 'SELL', price)}
                    className="flex-1 bg-loss-dark hover:bg-loss py-1.5 rounded-lg text-white text-xs font-bold transition-colors shadow-sm"
                  >
                    SELL
                  </button>
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Quick Order Modal */}
      {orderModal.open && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4 z-50 animate-fade-in">
          <div className="bg-surface-800 border border-surface-700 rounded-2xl p-6 max-w-sm w-full shadow-2xl space-y-4">
            <div className="flex justify-between items-center pb-2 border-b border-surface-700">
              <div className="flex items-center gap-2">
                <ShoppingCart size={18} className="text-accent-light" />
                <h3 className="font-bold text-white text-lg">
                  Place {orderModal.type} Order
                </h3>
              </div>
              <button
                onClick={() => setOrderModal((prev) => ({ ...prev, open: false }))}
                className="text-surface-400 hover:text-white"
              >
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleQuickOrderSubmit} className="space-y-4 text-sm">
              <div className="flex justify-between items-center bg-surface-900 p-3 rounded-lg border border-surface-700">
                <div>
                  <span className="text-xs text-surface-400 block">Instrument</span>
                  <span className="font-bold text-white text-base">{orderModal.symbol}</span>
                </div>
                <div
                  className={`px-3 py-1 rounded text-xs font-bold ${
                    orderModal.type === 'BUY'
                      ? 'bg-profit-dark/20 text-profit-light border border-profit/30'
                      : 'bg-loss-dark/20 text-loss-light border border-loss/30'
                  }`}
                >
                  {orderModal.type} (MIS)
                </div>
              </div>

              <div>
                <label className="block text-xs text-surface-400 mb-1">Limit Price (₹)</label>
                <input
                  type="number"
                  step="0.05"
                  required
                  value={orderModal.price}
                  onChange={(e) =>
                    setOrderModal((prev) => ({ ...prev, price: parseFloat(e.target.value) || 0 }))
                  }
                  className="w-full bg-surface-900 border border-surface-700 rounded-lg px-3 py-2 text-white font-mono focus:outline-none focus:border-accent-light"
                />
              </div>

              <div>
                <label className="block text-xs text-surface-400 mb-1">Quantity (Shares)</label>
                <input
                  type="number"
                  min="1"
                  required
                  value={orderModal.qty}
                  onChange={(e) =>
                    setOrderModal((prev) => ({ ...prev, qty: parseInt(e.target.value) || 1 }))
                  }
                  className="w-full bg-surface-900 border border-surface-700 rounded-lg px-3 py-2 text-white font-mono focus:outline-none focus:border-accent-light"
                />
              </div>

              <div className="text-xs text-surface-400 flex justify-between">
                <span>Est. Value:</span>
                <span className="font-mono text-white font-semibold">
                  ₹{(orderModal.price * orderModal.qty).toFixed(2)}
                </span>
              </div>

              {orderModal.error && (
                <div className="text-xs text-loss-light bg-loss-dark/20 border border-loss/30 p-2.5 rounded-lg">
                  {orderModal.error}
                </div>
              )}

              {orderModal.success && (
                <div className="text-xs text-profit-light bg-profit-dark/20 border border-profit/30 p-2.5 rounded-lg">
                  {orderModal.success}
                </div>
              )}

              <div className="flex gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setOrderModal((prev) => ({ ...prev, open: false }))}
                  className="flex-1 bg-surface-700 hover:bg-surface-600 text-surface-200 py-2 rounded-lg font-medium transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={orderModal.submitting}
                  className={`flex-1 py-2 rounded-lg font-bold text-white transition-colors ${
                    orderModal.type === 'BUY'
                      ? 'bg-profit-dark hover:bg-profit'
                      : 'bg-loss-dark hover:bg-loss'
                  }`}
                >
                  {orderModal.submitting ? 'Placing...' : `Confirm ${orderModal.type}`}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default Watchlist;
