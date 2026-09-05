import React, { useState } from 'react';
import { useSmartAPI } from '../hooks/useSmartAPI';
import { useTradingStore } from '../stores/trading-store';

const LoginModal: React.FC = () => {
  const { login } = useSmartAPI();
  const setAuth = useTradingStore((state) => state.setAuth);
  const [apiKey, setApiKey] = useState('');
  const [clientCode, setClientCode] = useState('');
  const [pin, setPin] = useState('');
  const [totpSecret, setTotpSecret] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      const res = await login({
        apiKey: apiKey.trim(),
        clientCode: clientCode.trim().toUpperCase(),
        pin: pin.trim(),
        totpSecret: totpSecret.trim(),
      });
      if (!res) {
        setError('Fatal Error: IPC bridge response is undefined.');
      } else if (res.error) {
        setError(`Login failed: ${res.error}`);
      } else if (res.isLoggedIn) {
        setAuth(res);
      } else {
        setError(`Unexpected response: ${JSON.stringify(res)}`);
      }
    } catch (err: any) {
      setError(`Caught Exception: ${err.message || 'Unknown error'}`);
    }
    setLoading(false);
  };

  return (
    <div className="absolute inset-0 bg-surface-950/80 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-surface-900 border border-surface-700 rounded-xl p-8 max-w-md w-full shadow-2xl animate-slide-up">
        <div className="flex items-center justify-center gap-2 mb-2">
          <div className="w-8 h-8 rounded-lg bg-accent/20 border border-accent/40 flex items-center justify-center font-bold text-accent-light">
            A1
          </div>
          <h2 className="text-2xl font-bold text-white text-center">
            Angel One SmartAPI
          </h2>
        </div>
        <p className="text-surface-400 text-sm text-center mb-6">
          Enter your SmartAPI credentials to start agentic trading.
        </p>

        <form onSubmit={handleSubmit} className="space-y-3.5">
          <div>
            <label className="block text-surface-300 text-sm font-medium mb-1">
              API Key
            </label>
            <input
              required
              type="text"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              className="w-full bg-surface-800 border border-surface-700 rounded-lg px-4 py-2.5 text-white focus:outline-none focus:border-accent-light transition-colors text-sm"
              placeholder="e.g. your_smartapi_key"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-surface-300 text-sm font-medium mb-1">
                Client Code
              </label>
              <input
                required
                type="text"
                value={clientCode}
                onChange={(e) => setClientCode(e.target.value)}
                className="w-full bg-surface-800 border border-surface-700 rounded-lg px-4 py-2.5 text-white focus:outline-none focus:border-accent-light transition-colors text-sm uppercase"
                placeholder="e.g. A123456"
              />
            </div>
            <div>
              <label className="block text-surface-300 text-sm font-medium mb-1">
                PIN / Password
              </label>
              <input
                required
                type="password"
                value={pin}
                onChange={(e) => setPin(e.target.value)}
                className="w-full bg-surface-800 border border-surface-700 rounded-lg px-4 py-2.5 text-white focus:outline-none focus:border-accent-light transition-colors text-sm"
                placeholder="4-digit MPIN"
              />
            </div>
          </div>

          <div>
            <label className="block text-surface-300 text-sm font-medium mb-1">
              TOTP Secret Key / 6-Digit Code
            </label>
            <input
              required
              type="password"
              value={totpSecret}
              onChange={(e) => setTotpSecret(e.target.value)}
              className="w-full bg-surface-800 border border-surface-700 rounded-lg px-4 py-2.5 text-white focus:outline-none focus:border-accent-light transition-colors text-sm"
              placeholder="Authenticator secret key or 6-digit code"
            />
            <p className="text-[11px] text-surface-400 mt-1">
              Tip: Provide the TOTP Secret Key for automatic, hands-free 2FA generation.
            </p>
          </div>

          {error && (
            <div className="text-loss-light text-xs bg-loss-fade p-3 rounded border border-loss/30">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-accent hover:bg-accent-light text-surface-950 font-bold py-3 rounded-lg transition-colors mt-2 shadow-lg shadow-accent/20"
          >
            {loading ? 'Connecting to SmartAPI...' : 'Connect & Login'}
          </button>
        </form>

        <div className="mt-6 text-center text-xs text-surface-500">
          <a
            href="https://smartapi.angelbroking.com/"
            target="_blank"
            rel="noreferrer"
            className="hover:text-accent-light underline transition-colors"
          >
            Get your credentials from Angel One SmartAPI Developer Portal
          </a>
        </div>
      </div>
    </div>
  );
};

export default LoginModal;
