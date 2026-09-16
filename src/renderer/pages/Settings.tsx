import React, { useState, useEffect } from 'react';
import { useTradingStore } from '../stores/trading-store';
import { SETTINGS_SAVE, TELEGRAM_TEST } from '@shared/ipc-channels';
import { Shield, ShieldCheck, Key, HelpCircle, RotateCcw, Check, Sparkles, TrendingUp, AlertCircle, Send } from 'lucide-react';

const Settings: React.FC = () => {
  const settings = useTradingStore((s) => s.settings);
  const setSettings = useTradingStore((s) => s.setSettings);
  const [localSettings, setLocalSettings] = useState<any>(settings);
  const [saveStatus, setSaveStatus] = useState<string>('');
  const [isSaving, setIsSaving] = useState<boolean>(false);
  const [testTelegramStatus, setTestTelegramStatus] = useState<string>('');
  const [isTestingTelegram, setIsTestingTelegram] = useState<boolean>(false);

  // Sync local state when global settings load
  useEffect(() => {
    if (settings) {
      setLocalSettings(settings);
    }
  }, [settings]);

  if (!localSettings) {
    return <div className="p-6 text-white">Loading settings...</div>;
  }

  const handleTelegramChange = (key: string, value: any) => {
    setLocalSettings((prev: any) => ({
      ...prev,
      notifications: {
        ...prev?.notifications,
        telegram: {
          ...prev?.notifications?.telegram,
          [key]: value
        }
      }
    }));
  };

  const handleTestTelegram = async () => {
    const tg = localSettings.notifications?.telegram || {};
    if (!tg.botToken || !tg.chatId) {
      setTestTelegramStatus('Please enter both Bot Token and Chat ID.');
      return;
    }
    try {
      setIsTestingTelegram(true);
      setTestTelegramStatus('Sending test message...');
      const res = window.electronAPI?.telegram?.test
        ? await window.electronAPI.telegram.test({
            botToken: tg.botToken,
            chatId: tg.chatId
          })
        : await window.electronAPI?.invoke(TELEGRAM_TEST, {
            botToken: tg.botToken,
            chatId: tg.chatId
          });
      if (res?.success) {
        setTestTelegramStatus('✅ Test message delivered to Telegram!');
      } else {
        setTestTelegramStatus(`❌ ${res?.message || 'Failed to send'}`);
      }
    } catch (e: any) {
      setTestTelegramStatus(`❌ Error: ${e.message}`);
    } finally {
      setIsTestingTelegram(false);
      setTimeout(() => setTestTelegramStatus(''), 5000);
    }
  };

  const handleRiskChange = (key: string, value: any) => {
    setLocalSettings((prev: any) => {
      let finalValue = value;
      if (typeof value === 'string' && !value.includes(':')) {
        if (value === '') {
          finalValue = '';
        } else if (value.endsWith('.')) {
          finalValue = value;
        } else {
          const parsed = parseFloat(value);
          finalValue = isNaN(parsed) ? value : parsed;
        }
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
      // Clean up stringified numbers before saving
      const cleanedRisk = { ...localSettings.risk };
      const numericKeys = [
        'maxCapitalPerTrade',
        'riskPerTrade',
        'maxDailyLoss',
        'maxSimultaneousPositions',
        'maxDailyTrades',
        'defaultStopLossPercent',
        'defaultTargetPercent'
      ];
      numericKeys.forEach((k) => {
        if (cleanedRisk[k] !== undefined && cleanedRisk[k] !== '') {
          cleanedRisk[k] = parseFloat(cleanedRisk[k]) || 0;
        }
      });
      const settingsToSave = {
        ...localSettings,
        risk: cleanedRisk
      };
      setLocalSettings(settingsToSave);
      setSettings(settingsToSave);
      await window.electronAPI?.invoke(SETTINGS_SAVE, settingsToSave);
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
        maxCapitalPerTrade: 4000,
        riskPerTrade: 500,
        maxDailyLoss: 800,
        maxSimultaneousPositions: 4,
        maxDailyTrades: 8,
        autoSquareOff: true,
        squareOffTime: "15:15",
        defaultStopLossPercent: 1.2,
        defaultTargetPercent: 2.5
      }
    }));
  };

  const slPct = Number(localSettings.risk?.defaultStopLossPercent) || 1.2;
  const tgtPct = Number(localSettings.risk?.defaultTargetPercent) || 2.5;
  const maxCap = Number(localSettings.risk?.maxCapitalPerTrade) || 4000;
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

            <div className="mb-4 p-3 rounded-xl bg-accent/10 border border-accent/20 text-xs text-surface-300 flex items-center gap-2.5">
              <Sparkles size={16} className="text-accent-light shrink-0" />
              <span>
                <strong>20% Sizing Rule:</strong> ₹4,000 margin/trade is calibrated for a ₹20,000 account, holding up to 4 concurrent positions with 5x MIS leverage (₹20,000 exposure each) and a 20% cash reserve.
              </span>
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
                  value={localSettings.risk?.maxCapitalPerTrade ?? ''} 
                  onChange={(e) => handleRiskChange('maxCapitalPerTrade', e.target.value)}
                  className="w-full bg-surface-900 border border-surface-700 rounded-lg px-4 py-2 text-white font-mono focus:border-accent-light outline-none transition-colors" 
                  placeholder="4000"
                />
                <div className="p-2 rounded bg-surface-800/80 border border-surface-700/60 text-[11px] text-surface-400 flex items-start gap-1.5">
                  <Sparkles size={14} className="text-accent-light mt-0.5 shrink-0" />
                  <span>
                    <strong>5x Intraday Leverage:</strong> With Angel One MIS (20% margin), ₹{maxCap.toLocaleString('en-IN')} margin controls up to <strong className="text-white">₹{effectiveLeverageExposure}</strong> in position value.
                  </span>
                </div>
              </div>

              {/* 1R Risk Budget Per Trade */}
              <div className="bg-surface-900/50 p-4 rounded-xl border border-surface-800 space-y-2">
                <div className="flex justify-between items-center">
                  <label className="block text-surface-300 text-xs font-semibold">1R Risk Budget Per Trade (₹)</label>
                  <span className="text-[11px] font-mono text-accent-light">₹{Number(localSettings.risk?.riskPerTrade || 500).toLocaleString('en-IN')}</span>
                </div>
                <input 
                  type="number" 
                  value={localSettings.risk?.riskPerTrade ?? ''} 
                  onChange={(e) => handleRiskChange('riskPerTrade', e.target.value)}
                  className="w-full bg-surface-900 border border-surface-700 rounded-lg px-4 py-2 text-white font-mono focus:border-accent-light outline-none transition-colors" 
                  placeholder="500"
                />
                <div className="p-2 rounded bg-surface-800/80 border border-surface-700/60 text-[11px] text-surface-400 flex items-start gap-1.5">
                  <ShieldCheck size={14} className="text-profit-light mt-0.5 shrink-0" />
                  <span>
                    <strong>1R Constant Risk Sizing:</strong> Dynamically calculates shares as <code className="text-accent-light">floor(Risk / |Entry - SL|)</code> so every trade risks exactly 1R.
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
                  value={localSettings.risk?.maxDailyLoss ?? ''} 
                  onChange={(e) => handleRiskChange('maxDailyLoss', e.target.value)}
                  className="w-full bg-surface-900 border border-surface-700 rounded-lg px-4 py-2 text-white font-mono focus:border-accent-light outline-none transition-colors" 
                  placeholder="800"
                />
                <p className="text-[11px] text-surface-500">
                  Agent halts all new trades and protects capital immediately if daily losses reach this threshold (4% drawdown limit).
                </p>
              </div>

              {/* Max Simultaneous Positions */}
              <div className="bg-surface-900/50 p-4 rounded-xl border border-surface-800 space-y-2">
                <label className="block text-surface-300 text-xs font-semibold">Max Simultaneous Positions</label>
                <input 
                  type="number" 
                  value={localSettings.risk?.maxSimultaneousPositions ?? ''} 
                  onChange={(e) => handleRiskChange('maxSimultaneousPositions', e.target.value)}
                  className="w-full bg-surface-900 border border-surface-700 rounded-lg px-4 py-2 text-white font-mono focus:border-accent-light outline-none transition-colors" 
                  placeholder="4"
                />
                <p className="text-[11px] text-surface-500">
                  Caps concurrent open positions to prevent over-diversification and excessive margin drawdown (max 4 positions × 20% = 80%).
                </p>
              </div>

              {/* Max Daily Trades */}
              <div className="bg-surface-900/50 p-4 rounded-xl border border-surface-800 space-y-2">
                <label className="block text-surface-300 text-xs font-semibold">Max Trades Per Day (6–8)</label>
                <input 
                  type="number" 
                  value={localSettings.risk?.maxDailyTrades ?? ''} 
                  onChange={(e) => handleRiskChange('maxDailyTrades', e.target.value)}
                  className="w-full bg-surface-900 border border-surface-700 rounded-lg px-4 py-2 text-white font-mono focus:border-accent-light outline-none transition-colors" 
                  placeholder="8"
                />
                <p className="text-[11px] text-surface-500">
                  Caps total executed trades per day (6–8 recommended) to eliminate overtrading and brokerage fee drain.
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

              {/* Market Regime Filter Toggle */}
              <div className="bg-surface-900/50 p-4 rounded-xl border border-surface-800 space-y-3">
                <div className="flex items-center justify-between">
                  <div>
                    <label className="block text-surface-300 text-xs font-semibold">Market Regime Filter</label>
                    <p className="text-[11px] text-surface-500">Inhibits false-breakout strategies when ADX &lt; 20 or during choppy consolidation squeeze.</p>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input 
                      type="checkbox" 
                      className="sr-only peer" 
                      checked={localSettings.risk?.marketRegimeFilterEnabled ?? true}
                      onChange={(e) => handleRiskChange('marketRegimeFilterEnabled', e.target.checked)}
                    />
                    <div className="w-11 h-6 bg-surface-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-profit-dark"></div>
                  </label>
                </div>
                <div className="flex items-center justify-between text-[11px] text-surface-400 font-mono">
                  <span>Regime Gate: ADX ≥ {localSettings.risk?.marketRegimeMinADX ?? 20} &bull; KER ≥ {localSettings.risk?.marketRegimeMinKER ?? 0.35}</span>
                  <span className="text-accent-light font-bold">1:2 R:R Active</span>
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
                  value={localSettings.risk?.defaultStopLossPercent ?? ''} 
                  onChange={(e) => handleRiskChange('defaultStopLossPercent', e.target.value)}
                  className="w-full bg-surface-900 border border-surface-700 rounded-lg px-4 py-2 text-white font-mono focus:border-accent-light outline-none transition-colors" 
                  placeholder="1.2"
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
                  value={localSettings.risk?.defaultTargetPercent ?? ''} 
                  onChange={(e) => handleRiskChange('defaultTargetPercent', e.target.value)}
                  className="w-full bg-surface-900 border border-surface-700 rounded-lg px-4 py-2 text-white font-mono focus:border-accent-light outline-none transition-colors" 
                  placeholder="2.4"
                />
                <p className="text-[11px] text-surface-500">
                  Target exit price for capturing gains (1:2.0 risk-reward against 1.2% stop-loss).
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

          {/* Telegram Notifications Section */}
          <section className="bg-surface-800/90 backdrop-blur-sm p-6 rounded-2xl border border-surface-700/80 shadow-lg space-y-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-sky-500/20 text-sky-400 flex items-center justify-center border border-sky-500/30">
                  <Send size={18} />
                </div>
                <div>
                  <h2 className="text-lg font-semibold text-white">Telegram Alerts</h2>
                  <p className="text-xs text-surface-400">Receive instant trade profit/loss exit receipts and daily session summaries.</p>
                </div>
              </div>
              <label className="relative inline-flex items-center cursor-pointer">
                <input 
                  type="checkbox" 
                  className="sr-only peer" 
                  checked={localSettings.notifications?.telegram?.enabled ?? false}
                  onChange={(e) => handleTelegramChange('enabled', e.target.checked)}
                />
                <div className="w-11 h-6 bg-surface-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-sky-500"></div>
              </label>
            </div>

            {/* Quick 60-Second Setup Guide */}
            <div className="bg-sky-500/5 border border-sky-500/20 rounded-xl p-4 text-xs space-y-2">
              <div className="font-semibold text-sky-300 flex items-center gap-1.5">
                <Sparkles size={14} />
                <span>60-Second Telegram Setup Guide</span>
              </div>
              <ol className="list-decimal list-inside space-y-1 text-surface-300">
                <li>Search <strong>@BotFather</strong> on Telegram and send <code>/newbot</code> to get your <strong>Bot Token</strong>.</li>
                <li>Search <strong>@userinfobot</strong> on Telegram to copy your personal <strong>Chat ID</strong>.</li>
                <li>Open a chat with your newly created bot and click <strong>/start</strong> so it has permission to message you.</li>
                <li><strong>2-Way Remote Control Active:</strong> You can send <code>/status</code>, <code>/positions</code>, <code>/start auto</code>, <code>/stop</code>, or <code>/squareoff</code> directly to your bot!</li>
              </ol>
            </div>

            <div className={`grid grid-cols-1 md:grid-cols-2 gap-5 ${!(localSettings.notifications?.telegram?.enabled ?? false) ? 'opacity-50 pointer-events-none' : ''}`}>
              {/* Bot Token */}
              <div className="bg-surface-900/50 p-4 rounded-xl border border-surface-800 space-y-2">
                <label className="block text-surface-300 text-xs font-semibold">Telegram Bot Token</label>
                <input 
                  type="password" 
                  value={localSettings.notifications?.telegram?.botToken || ''} 
                  onChange={(e) => handleTelegramChange('botToken', e.target.value)}
                  className="w-full bg-surface-900 border border-surface-700 rounded-lg px-4 py-2 text-white font-mono text-xs focus:border-sky-400 outline-none transition-colors" 
                  placeholder="e.g. 7123456789:AAFxxx..."
                />
                <p className="text-[11px] text-surface-500">
                  HTTP API access token generated by @BotFather.
                </p>
              </div>

              {/* Chat ID */}
              <div className="bg-surface-900/50 p-4 rounded-xl border border-surface-800 space-y-2">
                <label className="block text-surface-300 text-xs font-semibold">Your Chat ID</label>
                <input 
                  type="text" 
                  value={localSettings.notifications?.telegram?.chatId || ''} 
                  onChange={(e) => handleTelegramChange('chatId', e.target.value)}
                  className="w-full bg-surface-900 border border-surface-700 rounded-lg px-4 py-2 text-white font-mono text-xs focus:border-sky-400 outline-none transition-colors" 
                  placeholder="e.g. 987654321"
                />
                <p className="text-[11px] text-surface-500">
                  Your numeric user ID obtained from @userinfobot.
                </p>
              </div>

              {/* Alert Preferences */}
              <div className="md:col-span-2 bg-surface-900/50 p-4 rounded-xl border border-surface-800 space-y-3">
                <span className="text-xs font-semibold text-surface-300 block">Notification Events</span>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <label className="flex items-center gap-2.5 text-xs text-surface-300 cursor-pointer">
                    <input 
                      type="checkbox" 
                      checked={localSettings.notifications?.telegram?.notifyOnTradeExit ?? true}
                      onChange={(e) => handleTelegramChange('notifyOnTradeExit', e.target.checked)}
                      className="rounded border-surface-700 text-sky-500 focus:ring-0 w-4 h-4 bg-surface-900 cursor-pointer"
                    />
                    <span>Notify on Trade Exit (Target / Stop Loss Hit)</span>
                  </label>
                  <label className="flex items-center gap-2.5 text-xs text-surface-300 cursor-pointer">
                    <input 
                      type="checkbox" 
                      checked={localSettings.notifications?.telegram?.notifyOnSessionEnd ?? true}
                      onChange={(e) => handleTelegramChange('notifyOnSessionEnd', e.target.checked)}
                      className="rounded border-surface-700 text-sky-500 focus:ring-0 w-4 h-4 bg-surface-900 cursor-pointer"
                    />
                    <span>Notify on Session End (Total Daily P&L)</span>
                  </label>
                </div>
              </div>

              {/* Test Message Button */}
              <div className="md:col-span-2 flex items-center justify-between pt-2">
                <div className="text-xs font-semibold">
                  {testTelegramStatus && (
                    <span className={testTelegramStatus.includes('✅') ? 'text-profit-light' : 'text-loss-light'}>
                      {testTelegramStatus}
                    </span>
                  )}
                </div>
                <button
                  type="button"
                  onClick={handleTestTelegram}
                  disabled={isTestingTelegram || !localSettings.notifications?.telegram?.botToken || !localSettings.notifications?.telegram?.chatId}
                  className="flex items-center gap-2 px-4 py-2 bg-sky-500/20 hover:bg-sky-500/30 text-sky-300 border border-sky-500/30 rounded-xl text-xs font-bold transition-all disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
                >
                  {isTestingTelegram ? (
                    <div className="w-3.5 h-3.5 border-2 border-sky-400 border-t-transparent rounded-full animate-spin" />
                  ) : (
                    <Send size={13} />
                  )}
                  <span>Send Test Message</span>
                </button>
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
