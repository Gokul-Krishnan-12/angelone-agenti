import React, { useState, useEffect } from 'react';
import { useTradingStore } from '../stores/trading-store';
import { SETTINGS_SAVE } from '@shared/ipc-channels';
import { Shield, Key, HelpCircle, RotateCcw, Check, Sparkles, TrendingUp, AlertCircle } from 'lucide-react';

const Settings: React.FC = () => {
  const { settings, setSettings } = useTradingStore();
  const [localSettings, setLocalSettings] = useState<any>(settings);
  const [saveStatus, setSaveStatus] = useState<string>('');
  const [isSaving, setIsSaving] = useState<boolean>(false);

  // Sync local state when global settings load
  useEffect(() => {
    if (settings) {
      setLocalSettings(settings);
    }
  }, [settings]);

  if (!localSettings) {
    return <div className="p-6 text-white">Loading settings...</div>;
  }

  const handleRiskChange = (key: string, value: any) => {
    setLocalSettings((prev: any) => {
      let finalValue = value;
      if (typeof value === 'string' && !value.includes(':')) {
        finalValue = parseFloat(value) || 0;
      }
      return {
        ...prev,
        risk: {
          ...prev.risk,
          [key]: finalValue
        }
      };
    });
  };

  const saveChanges = async () => {
    try {
      setIsSaving(true);
      setSaveStatus('Saving changes...');
      // Optimistically update memory store immediately
      setSettings(localSettings);
      await window.electronAPI?.invoke(SETTINGS_SAVE, localSettings);
      setSaveStatus('Saved successfully!');
      setTimeout(() => setSaveStatus(''), 3000);
    } catch (error) {
      console.error('Failed to save settings:', error);
      setSaveStatus('Error saving settings');
    } finally {
      setIsSaving(false);
    }
  };

  const resetToDefaults = () => {
    setLocalSettings((prev: any) => ({
      ...prev,
      risk: {
        ...prev.risk,
        maxCapitalPerTrade: 10000,
        maxDailyLoss: 2000,
        maxSimultaneousPositions: 5,
        autoSquareOff: true,
        squareOffTime: "15:15",
        defaultStopLossPercent: 1.5,
        defaultTargetPercent: 3
      }
    }));
  };

  const slPct = Number(localSettings.risk?.defaultStopLossPercent) || 1.5;
  const tgtPct = Number(localSettings.risk?.defaultTargetPercent) || 3.0;
  const maxCap = Number(localSettings.risk?.maxCapitalPerTrade) || 10000;
  const rrRatio = slPct > 0 ? (tgtPct / slPct).toFixed(1) : '0';
  const exampleEntry = 1000;
  const exampleTarget = (exampleEntry * (1 + tgtPct / 100)).toFixed(2);
  const exampleSL = (exampleEntry * (1 - slPct / 100)).toFixed(2);
  const profitPerShare = (exampleEntry * (tgtPct / 100)).toFixed(2);
  const lossPerShare = (exampleEntry * (slPct / 100)).toFixed(2);
  const effectiveLeverageExposure = (maxCap * 5).toLocaleString('en-IN');

  return (
    <div className="p-6 h-full overflow-auto max-w-4xl mx-auto space-y-8 animate-fade-in">
      <div>
        <div className="flex justify-between items-center mb-6">
          <div>
            <h1 className="text-2xl font-bold text-white tracking-tight">Trading Settings</h1>
            <p className="text-sm text-surface-400 mt-1">Configure SmartAPI security parameters, risk boundaries, and execution rules.</p>
          </div>
          {saveStatus && (
            <div className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold border ${saveStatus.includes('Error') ? 'bg-loss-fade text-loss-light border-loss/30' : 'bg-profit-fade text-profit-light border-profit/30'}`}>
              {saveStatus.includes('Saved') ? <Check size={14} /> : <AlertCircle size={14} />}
              <span>{saveStatus}</span>
            </div>
          )}
        </div>
        
        <div className="space-y-6">
          {/* SmartAPI Credentials Section */}
          <section className="bg-surface-800/90 backdrop-blur-sm p-6 rounded-2xl border border-surface-700/80 shadow-lg">
            <div className="flex items-center gap-2.5 mb-4">
              <div className="w-8 h-8 rounded-lg bg-accent/20 text-accent-light flex items-center justify-center border border-accent/30">
                <Key size={18} />
              </div>
              <div>
                <h2 className="text-lg font-semibold text-white">Angel One SmartAPI Credentials</h2>
                <p className="text-xs text-surface-400">Encrypted and securely stored on your local machine.</p>
              </div>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="bg-surface-900/60 p-3 rounded-xl border border-surface-800">
                <label className="block text-surface-400 text-xs font-medium mb-1">SmartAPI API Key</label>
                <input type="password" value="••••••••••••••••" readOnly className="w-full bg-surface-900 border border-surface-700/70 rounded-lg px-3.5 py-2 text-white font-mono text-sm" />
              </div>
              <div className="bg-surface-900/60 p-3 rounded-xl border border-surface-800">
                <label className="block text-surface-400 text-xs font-medium mb-1">Client Code (User ID)</label>
                <input type="text" value="••••••••" readOnly className="w-full bg-surface-900 border border-surface-700/70 rounded-lg px-3.5 py-2 text-white font-mono text-sm" />
              </div>
              <div className="bg-surface-900/60 p-3 rounded-xl border border-surface-800">
                <label className="block text-surface-400 text-xs font-medium mb-1">Trading MPIN / Password</label>
                <input type="password" value="••••" readOnly className="w-full bg-surface-900 border border-surface-700/70 rounded-lg px-3.5 py-2 text-white font-mono text-sm" />
              </div>
              <div className="bg-surface-900/60 p-3 rounded-xl border border-surface-800">
                <label className="block text-surface-400 text-xs font-medium mb-1">TOTP Secret Key / 2FA</label>
                <input type="password" value="••••••••••••••••" readOnly className="w-full bg-surface-900 border border-surface-700/70 rounded-lg px-3.5 py-2 text-white font-mono text-sm" />
              </div>
            </div>
            <p className="text-xs text-surface-500 mt-3.5 flex items-center gap-1.5">
              <HelpCircle size={13} />
              To change your SmartAPI credentials, log out via the bottom sidebar to enter new keys.
            </p>
          </section>

          {/* Risk Management Section */}
          <section className="bg-surface-800/90 backdrop-blur-sm p-6 rounded-2xl border border-surface-700/80 shadow-lg space-y-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-profit-dark/20 text-profit-light flex items-center justify-center border border-profit/30">
                  <Shield size={18} />
                </div>
                <div>
                  <h2 className="text-lg font-semibold text-white">Risk Management & Position Sizing</h2>
                  <p className="text-xs text-surface-400">Controls automated sizing, daily circuit breakers, and square-off rules.</p>
                </div>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              {/* Max Capital Per Trade */}
              <div className="bg-surface-900/50 p-4 rounded-xl border border-surface-800 space-y-2">
                <div className="flex justify-between items-center">
                  <label className="block text-surface-300 text-xs font-semibold">Max Capital Per Trade (₹)</label>
                  <span className="text-[11px] font-mono text-accent-light">₹{maxCap.toLocaleString('en-IN')}</span>
                </div>
                <input 
                  type="number" 
                  value={localSettings.risk?.maxCapitalPerTrade || ''} 
                  onChange={(e) => handleRiskChange('maxCapitalPerTrade', e.target.value)}
                  className="w-full bg-surface-900 border border-surface-700 rounded-lg px-4 py-2 text-white font-mono focus:border-accent-light outline-none transition-colors" 
                  placeholder="10000"
                />
                <div className="p-2 rounded bg-surface-800/80 border border-surface-700/60 text-[11px] text-surface-400 flex items-start gap-1.5">
                  <Sparkles size={14} className="text-accent-light mt-0.5 shrink-0" />
                  <span>
                    <strong>5x Intraday Leverage:</strong> With Angel One MIS (20% margin), ₹{maxCap.toLocaleString('en-IN')} margin controls up to <strong className="text-white">₹{effectiveLeverageExposure}</strong> in position value.
                  </span>
                </div>
              </div>

              {/* Max Daily Loss */}
              <div className="bg-surface-900/50 p-4 rounded-xl border border-surface-800 space-y-2">
                <div className="flex justify-between items-center">
                  <label className="block text-surface-300 text-xs font-semibold">Max Daily Loss Cutoff (₹)</label>
                  <span className="text-[11px] font-mono text-loss-light">-₹{Number(localSettings.risk?.maxDailyLoss || 0).toLocaleString('en-IN')}</span>
                </div>
                <input 
                  type="number" 
                  value={localSettings.risk?.maxDailyLoss || ''} 
                  onChange={(e) => handleRiskChange('maxDailyLoss', e.target.value)}
                  className="w-full bg-surface-900 border border-surface-700 rounded-lg px-4 py-2 text-white font-mono focus:border-accent-light outline-none transition-colors" 
                  placeholder="2000"
                />
                <p className="text-[11px] text-surface-500">
                  Agent halts all new trades and protects capital immediately if daily losses reach this threshold.
                </p>
              </div>

              {/* Max Simultaneous Positions */}
              <div className="bg-surface-900/50 p-4 rounded-xl border border-surface-800 space-y-2">
                <label className="block text-surface-300 text-xs font-semibold">Max Simultaneous Positions</label>
                <input 
                  type="number" 
                  value={localSettings.risk?.maxSimultaneousPositions || ''} 
                  onChange={(e) => handleRiskChange('maxSimultaneousPositions', e.target.value)}
                  className="w-full bg-surface-900 border border-surface-700 rounded-lg px-4 py-2 text-white font-mono focus:border-accent-light outline-none transition-colors" 
                  placeholder="5"
                />
                <p className="text-[11px] text-surface-500">
                  Caps concurrent open positions to prevent over-diversification and excessive margin drawdown.
                </p>
              </div>

              {/* Auto Square Off & Time */}
              <div className="bg-surface-900/50 p-4 rounded-xl border border-surface-800 space-y-3">
                <div className="flex items-center justify-between">
                  <div>
                    <label className="block text-surface-300 text-xs font-semibold">Intraday Auto Square Off</label>
                    <p className="text-[11px] text-surface-500">Automatically closes open positions before market close.</p>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input 
                      type="checkbox" 
                      className="sr-only peer" 
                      checked={localSettings.risk?.autoSquareOff ?? true}
                      onChange={(e) => handleRiskChange('autoSquareOff', e.target.checked)}
                    />
                    <div className="w-11 h-6 bg-surface-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-profit-dark"></div>
                  </label>
                </div>
                <div>
                  <label className="block text-surface-400 text-[11px] mb-1">Square Off Cutoff Time</label>
                  <input 
                    type="time" 
                    value={localSettings.risk?.squareOffTime || '15:15'} 
                    onChange={(e) => handleRiskChange('squareOffTime', e.target.value)}
                    disabled={!(localSettings.risk?.autoSquareOff ?? true)}
                    className={`w-full bg-surface-900 border border-surface-700 rounded-lg px-4 py-1.5 text-white font-mono text-sm focus:border-accent-light outline-none ${!(localSettings.risk?.autoSquareOff ?? true) ? 'opacity-40 cursor-not-allowed' : ''}`} 
                  />
                </div>
              </div>

              {/* Default Stop Loss */}
              <div className="bg-surface-900/50 p-4 rounded-xl border border-surface-800 space-y-2">
                <div className="flex justify-between items-center">
                  <label className="block text-surface-300 text-xs font-semibold">Default Stop Loss (%)</label>
                  <span className="text-[11px] font-mono text-loss-light font-bold">-{slPct}%</span>
                </div>
                <input 
                  type="number" 
                  step="0.1"
                  value={localSettings.risk?.defaultStopLossPercent || ''} 
                  onChange={(e) => handleRiskChange('defaultStopLossPercent', e.target.value)}
                  className="w-full bg-surface-900 border border-surface-700 rounded-lg px-4 py-2 text-white font-mono focus:border-accent-light outline-none transition-colors" 
                  placeholder="1.5"
                />
                <p className="text-[11px] text-surface-500">
                  Fixed distance below entry price for automatic protective stop loss orders.
                </p>
              </div>

              {/* Default Target */}
              <div className="bg-surface-900/50 p-4 rounded-xl border border-surface-800 space-y-2">
                <div className="flex justify-between items-center">
                  <label className="block text-surface-300 text-xs font-semibold">Default Profit Target (%)</label>
                  <span className="text-[11px] font-mono text-profit-light font-bold">+{tgtPct}%</span>
                </div>
                <input 
                  type="number" 
                  step="0.1"
                  value={localSettings.risk?.defaultTargetPercent || ''} 
                  onChange={(e) => handleRiskChange('defaultTargetPercent', e.target.value)}
                  className="w-full bg-surface-900 border border-surface-700 rounded-lg px-4 py-2 text-white font-mono focus:border-accent-light outline-none transition-colors" 
                  placeholder="3.0"
                />
                <p className="text-[11px] text-surface-500">
                  Target exit price for capturing gains when price swings in trade direction.
                </p>
              </div>

              {/* LIVE TRADE MATH & RISK-REWARD PREVIEW BOX */}
              <div className="md:col-span-2 bg-gradient-to-br from-surface-900 via-surface-900 to-surface-850 p-5 rounded-2xl border border-surface-700/80 space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <TrendingUp size={16} className="text-accent-light" />
                    <span className="text-xs font-bold uppercase tracking-wider text-white">Live Trade Order Preview</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-surface-400">Risk : Reward Ratio</span>
                    <span className={`text-xs px-2.5 py-0.5 rounded-full font-mono font-bold border ${Number(rrRatio) >= 2 ? 'bg-profit-dark/20 text-profit-light border-profit/40' : 'bg-warning-dark/20 text-warning-light border-warning/40'}`}>
                      1 : {rrRatio} {Number(rrRatio) >= 2 ? '(Favorable)' : ''}
                    </span>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                  <div className="bg-surface-800/90 p-3.5 rounded-xl border border-surface-700">
                    <span className="text-[11px] text-surface-400 block font-medium">1. Entry Price (Example)</span>
                    <span className="text-xl font-mono font-bold text-white block mt-0.5">₹{exampleEntry.toFixed(2)}</span>
                    <span className="text-[10px] text-surface-400 block mt-1">Base stock price</span>
                  </div>

                  <div className="bg-profit-dark/10 p-3.5 rounded-xl border border-profit/30">
                    <div className="flex justify-between items-center">
                      <span className="text-[11px] text-surface-400 font-medium">2. Target (+{tgtPct}%)</span>
                      <span className="text-[10px] font-bold text-profit-light uppercase">Take Profit</span>
                    </div>
                    <span className="text-xl font-mono font-bold text-profit-light block mt-0.5">₹{exampleTarget}</span>
                    <span className="text-[10px] text-profit-light/80 block mt-1">+₹{profitPerShare} profit per share</span>
                  </div>

                  <div className="bg-loss-dark/10 p-3.5 rounded-xl border border-loss/30">
                    <div className="flex justify-between items-center">
                      <span className="text-[11px] text-surface-400 font-medium">3. Stop Loss (-{slPct}%)</span>
                      <span className="text-[10px] font-bold text-loss-light uppercase">Capital Guard</span>
                    </div>
                    <span className="text-xl font-mono font-bold text-loss-light block mt-0.5">₹{exampleSL}</span>
                    <span className="text-[10px] text-loss-light/80 block mt-1">-₹{lossPerShare} risk per share</span>
                  </div>
                </div>

                <p className="text-xs text-surface-300 bg-surface-950/60 p-2.5 rounded-lg border border-surface-800">
                  💡 <strong>How it works:</strong> If you buy a stock at ₹1,000 with these settings, the agent will exit at <strong className="text-profit-light">₹{exampleTarget}</strong> for profit, or square off at <strong className="text-loss-light">₹{exampleSL}</strong> if price moves against you.
                </p>
              </div>
            </div>
          </section>
        </div>
      </div>
      
      <div className="flex justify-end items-center gap-4 pb-8 pt-2">
        <button 
          onClick={resetToDefaults}
          className="flex items-center gap-2 px-5 py-2.5 bg-surface-800 hover:bg-surface-700 border border-surface-700 rounded-xl text-surface-300 hover:text-white font-medium text-sm transition-all"
        >
          <RotateCcw size={15} />
          <span>Reset to Defaults</span>
        </button>
        <button 
          onClick={saveChanges}
          disabled={isSaving}
          className="flex items-center gap-2 px-6 py-2.5 bg-accent hover:bg-accent-light disabled:opacity-60 text-surface-950 font-bold rounded-xl text-sm transition-all shadow-lg shadow-accent/20 cursor-pointer disabled:cursor-not-allowed"
        >
          {isSaving ? (
            <div className="w-4 h-4 border-2 border-surface-950 border-t-transparent rounded-full animate-spin" />
          ) : (
            <Check size={16} />
          )}
          <span>{isSaving ? 'Saving...' : 'Save Changes'}</span>
        </button>
      </div>
    </div>
  );
};

export default Settings;
