// ─── Authentication ───────────────────────────────────────────────

export interface SmartApiCredentials {
  apiKey: string;
  clientCode: string;
  pin: string;
  totpSecret?: string;
  totp?: string;
  jwtToken?: string;
  feedToken?: string;
  userId?: string;
  userName?: string;
  apiSecret?: string;
  accessToken?: string;
}

export type KiteCredentials = SmartApiCredentials;

export interface AuthState {
  isLoggedIn: boolean;
  credentials: SmartApiCredentials | null;
  loginUrl: string | null;
  error: string | null;
}

// ─── Market Data ──────────────────────────────────────────────────

export interface Tick {
  instrumentToken: number;
  tradingsymbol: string;
  lastPrice: number;
  change: number;
  changePercent: number;
  volume: number;
  open: number;
  high: number;
  low: number;
  close: number;
  buyQuantity: number;
  sellQuantity: number;
  ohlc: OHLC;
  timestamp: string;
}

export interface OHLC {
  open: number;
  high: number;
  low: number;
  close: number;
}

export interface Candle {
  time: number; // Unix timestamp in seconds
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface Instrument {
  instrumentToken: number;
  exchangeToken: string;
  tradingsymbol: string;
  name: string;
  lastPrice: number;
  tickSize: number;
  lotSize: number;
  instrumentType: string;
  segment: string;
  exchange: string;
}

// ─── Orders ───────────────────────────────────────────────────────

export type OrderType = 'MARKET' | 'LIMIT' | 'SL' | 'SL-M';
export type TransactionType = 'BUY' | 'SELL';
export type ProductType = 'MIS' | 'CNC' | 'NRML';
export type OrderVariety = 'regular' | 'amo' | 'co' | 'iceberg';
export type OrderValidity = 'DAY' | 'IOC' | 'TTL';

export type OrderStatus =
  | 'OPEN'
  | 'COMPLETE'
  | 'CANCELLED'
  | 'REJECTED'
  | 'TRIGGER PENDING'
  | 'MODIFY PENDING'
  | 'CANCEL PENDING'
  | 'PUT ORDER REQ RECEIVED'
  | 'VALIDATION PENDING';

export interface OrderRequest {
  tradingsymbol: string;
  exchange: string;
  transactionType: TransactionType;
  quantity: number;
  product: ProductType;
  orderType: OrderType;
  price?: number;
  triggerPrice?: number;
  validity?: OrderValidity;
  tag?: string;
  variety?: OrderVariety;
}

export interface Order {
  orderId: string;
  isAppOrder?: boolean;
  tradingsymbol: string;
  exchange: string;
  transactionType: TransactionType;
  quantity: number;
  filledQuantity: number;
  pendingQuantity: number;
  price: number;
  averagePrice: number;
  triggerPrice: number;
  product: ProductType;
  orderType: OrderType;
  variety: string;
  status: OrderStatus;
  statusMessage: string;
  tag: string;
  orderTimestamp: string;
  exchangeTimestamp: string;
}

// ─── Positions & Holdings ─────────────────────────────────────────

export interface Position {
  tradingsymbol: string;
  exchange: string;
  instrumentToken: number;
  product: ProductType;
  quantity: number;
  overnightQuantity: number;
  averagePrice: number;
  lastPrice: number;
  closePrice: number;
  pnl: number;
  unrealised: number;
  realised: number;
  buyQuantity: number;
  sellQuantity: number;
  buyPrice: number;
  sellPrice: number;
  multiplier: number;
  value: number;
  dayBuyQuantity: number;
  daySellQuantity: number;
}

export interface Holding {
  tradingsymbol: string;
  exchange: string;
  instrumentToken: number;
  quantity: number;
  averagePrice: number;
  lastPrice: number;
  pnl: number;
  closePrice: number;
}

// ─── Margins ──────────────────────────────────────────────────────

export interface Margins {
  enabled: boolean;
  net: number;
  available: {
    cash: number;
    collateral: number;
    intradayPayin: number;
    adhocMargin: number;
    liveBalance: number;
  };
  utilised: {
    debits: number;
    exposure: number;
    m2mRealised: number;
    m2mUnrealised: number;
    optionPremium: number;
    payout: number;
    span: number;
    holdingSales: number;
    turnover: number;
  };
}

// ─── Trading Signals & Strategy ───────────────────────────────────

export type StrategyName =
  | 'ema_crossover'
  | 'rsi_reversal'
  | 'vwap_bounce'
  | 'supertrend'
  | 'macd_cross'
  | 'bollinger_breakout'
  | 'stochastic_reversal'
  | 'adx_momentum'
  | 'psar_trend'
  | 'donchian_breakout'
  | 'cci_reversal'
  | 'williams_r'
  | 'mfi_exhaustion'
  | 'keltner_breakout'
  | 'awesome_oscillator'
  | 'tsi_cross'
  | 'stoc_rsi'
  | 'institutional_absorption'
  | 'order_block_fvg'
  | 'cmf_accumulation'
  | string;
export type SignalDirection = 'BUY' | 'SELL';
export type AgentMode = 'auto' | 'confirm';

export interface Signal {
  id: string;
  tradingsymbol: string;
  exchange: string;
  strategy: StrategyName;
  direction: SignalDirection;
  confidence: number; // 0-100
  entryPrice: number;
  stopLoss: number;
  target: number;
  riskReward: number;
  reasoning: string;
  timestamp: string;
  indicators: Record<string, number>;
}

export interface AgentState {
  running: boolean;
  mode: AgentMode;
  enabledStrategies: StrategyName[];
  tradesToday: number;
  signalsGenerated: number;
  currentPnl: number;
  maxDrawdownToday: number;
  lastScanTime: string | null;
  status: 'idle' | 'scanning' | 'placing_order' | 'monitoring' | 'stopped' | 'error';
  statusMessage: string;
}

// ─── Risk Management ──────────────────────────────────────────────

export interface RiskConfig {
  maxCapitalPerTrade: number;
  maxDailyLoss: number;
  maxOpenPositions: number;
  noNewTradesAfter: string; // "14:30" format
  autoSquareOff: boolean;
  squareOffTime: string; // "15:10" format
  defaultStopLossPercent: number;
  defaultTargetPercent: number;
  trailingStopEnabled: boolean;
  trailingStopPercent: number;
}

// ─── Strategy Configuration ───────────────────────────────────────

export interface StrategyConfig {
  ema_crossover: {
    fastPeriod: number;
    slowPeriod: number;
    volumeConfirmation: boolean;
    volumePeriod: number;
  };
  rsi_reversal: {
    period: number;
    oversold: number;
    overbought: number;
    useVwapConfirmation: boolean;
  };
  vwap_bounce: {
    atrPeriod: number;
    atrMultiplier: number;
    rsiFloor: number;
  };
  supertrend: {
    period: number;
    multiplier: number;
    adxThreshold: number;
    useTrailingStop: boolean;
  };
}

// ─── Activity Log ─────────────────────────────────────────────────

export type LogLevel = 'info' | 'signal' | 'order' | 'warning' | 'error' | 'success';

export interface ActivityLogEntry {
  id: string;
  timestamp: string;
  level: LogLevel;
  message: string;
  details?: Record<string, unknown>;
  strategy?: StrategyName;
  tradingsymbol?: string;
}

// ─── Watchlist ────────────────────────────────────────────────────

export interface WatchlistItem {
  tradingsymbol: string;
  exchange: string;
  instrumentToken: number;
  lastPrice: number;
  change: number;
  changePercent: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  activeSignals: Signal[];
}

// ─── App Settings ─────────────────────────────────────────────────

export interface AppSettings {
  credentials: KiteCredentials;
  risk: RiskConfig;
  strategies: StrategyConfig;
  watchlist: string[]; // ["NSE:RELIANCE", "NSE:INFY", ...]
  agentMode: AgentMode;
  enabledStrategies: StrategyName[];
  scanIntervalSeconds: number;
  candleInterval: string; // "5minute", "15minute", etc.
  theme: 'dark' | 'light';
  notifications: {
    soundEnabled: boolean;
    desktopNotifications: boolean;
    notifyOnSignal: boolean;
    notifyOnOrder: boolean;
    notifyOnStopLoss: boolean;
  };
}

// ─── Python Backend RPC ───────────────────────────────────────────

export interface RPCRequest {
  id: number;
  method: string;
  params: Record<string, unknown>;
}

export interface RPCResponse {
  id: number;
  result?: unknown;
  error?: {
    code: number;
    message: string;
    data?: unknown;
  };
}

export interface RPCEvent {
  event: string;
  data: unknown;
}

// ─── Dashboard Summary ────────────────────────────────────────────

export interface DashboardSummary {
  totalPnl: number;
  realisedPnl: number;
  unrealisedPnl: number;
  tradesToday: number;
  winningTrades: number;
  losingTrades: number;
  winRate: number;
  maxDrawdown: number;
  openPositionsCount: number;
  availableMargin: number;
  usedMargin: number;
}

// ─── Electron Bridge API ──────────────────────────────────────────

export interface ElectronAPI {
  invoke(channel: string, ...args: any[]): Promise<any>;
  on(channel: string, listener: (...args: any[]) => void): any;
  removeListener(channel: string, listener: (...args: any[]) => void): void;
  removeAllListeners(channel: string): void;

  auth: {
    login: (creds: any, apiSecret?: string) => Promise<any>;
    logout: () => Promise<any>;
    status: () => Promise<any>;
  };
  orders: {
    place: (orderParams: any) => Promise<any>;
    modify: (orderParams: any) => Promise<any>;
    cancel: (orderId: string, variety?: string) => Promise<any>;
    getAll: (params?: any) => Promise<any>;
    getTrades: () => Promise<any>;
  };
  portfolio: {
    positions: (params?: any) => Promise<any>;
    holdings: () => Promise<any>;
    margins: (params?: any) => Promise<any>;
  };
  market: {
    quote: (instruments: string[]) => Promise<any>;
    ltp: (instruments: string[]) => Promise<any>;
    ohlc: (instruments: string[]) => Promise<any>;
    historical: (params: any) => Promise<any>;
    instruments: (exchange: string) => Promise<any>;
    search: (query: string) => Promise<any>;
  };
  ticker: {
    subscribe: (tokens: (number | string)[]) => Promise<any>;
    unsubscribe: (tokens: (number | string)[]) => Promise<any>;
    status: () => Promise<any>;
    onTick: (callback: (data: any) => void) => () => void;
    onOrderUpdate: (callback: (data: any) => void) => () => void;
  };
  agent: {
    start: (params?: any) => Promise<any>;
    stop: () => Promise<any>;
    status: () => Promise<any>;
    executeSignal: (signal: any) => Promise<any>;
    dismissSignal: (signalId: string) => Promise<any>;
    scanNow: () => Promise<any>;
    onStateUpdate: (callback: (data: any) => void) => () => void;
    onSignal: (callback: (data: any) => void) => () => void;
  };
  log: {
    getAll: () => Promise<any>;
    clear: () => Promise<any>;
    onEntry: (callback: (data: any) => void) => () => void;
  };
  settings: {
    get: () => Promise<any>;
    save: (settings: any) => Promise<any>;
    reset: () => Promise<any>;
  };
  watchlist: {
    get: () => Promise<any>;
    add: (symbol: string) => Promise<any>;
    remove: (symbol: string) => Promise<any>;
    onUpdate: (callback: (data: any) => void) => () => void;
  };
  dashboard: {
    summary: (params?: any) => Promise<DashboardSummary>;
  };
  app: {
    onPythonStatus: (callback: (data: any) => void) => () => void;
    onError: (callback: (data: any) => void) => () => void;
  };
}

declare global {
  interface Window {
    electronAPI?: ElectronAPI;
  }
}

