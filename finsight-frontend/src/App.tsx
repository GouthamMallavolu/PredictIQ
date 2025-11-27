import React, { useEffect, useState } from "react";
import "./App.css";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ResponsiveContainer,
  BarChart,
  Bar,
} from "recharts";


const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

type RawPrediction = {
  symbol?: string;
  predictions?: Record<string, number>;
  prediction_timestamp?: string;
  target_timestamp?: string;
  current_price?: number;
  error?: string;
};

type RecommendResponse = {
  request_id: string;
  timestamp: string;
  status: string;
  results: Record<string, RawPrediction>;
  model_used: string;
};

type ModelMeta = {
  name: string;
  type?: string;
  description?: string;
};

type AbMetricsResponse = {
  error?: string;
  date?: string;
  test_config?: {
    control: string;
    treatment: string;
  };
  results?: {
    [variant: string]: {
      total_requests: number;
      successful_requests: number;
      errors: number;
      success_rate: number;
      avg_latency_ms: number;
      p95_latency_ms: number;
      total_predictions: number;
      successful_predictions: number;
      error_rate: number;
    };
  };
};

type HistoricalPoint = {
  timestamp: string;
  close: number;
};

type HistoricalResponse = {
  symbol: string;
  points: HistoricalPoint[];
};

type AbSummaryProps = {
  abMetrics: AbMetricsResponse;
};

const AbSummaryAndChart: React.FC<AbSummaryProps> = ({ abMetrics }) => {
  if (!abMetrics.results) return null;

  const entries = Object.entries(abMetrics.results);
  if (entries.length === 0) return null;

  // Only consider variants that actually have traffic
  const validEntries = entries.filter(
    ([, m]) => m.total_requests && m.total_requests > 0
  );

  if (validEntries.length === 0) {
    return (
      <div className="ab-summary ab-summary-empty">
        <p className="ab-summary-body">
          No A/B traffic has been recorded yet. Send some requests from
          different user IDs to start the experiment.
        </p>
      </div>
    );
  }

  const chartData = validEntries.map(([variant, m]) => ({
    variant,
    success_rate: m.success_rate,
  }));

  // Winner by success rate among non-empty variants
  const sorted = [...validEntries].sort(
    (a, b) => b[1].success_rate - a[1].success_rate
  );
  const [winnerVariant, winnerMetrics] = sorted[0];
  const loser = sorted.length > 1 ? sorted[1] : null;
  const diffSuccess =
    loser != null
      ? winnerMetrics.success_rate - loser[1].success_rate
      : 0;

  return (
    <div className="ab-summary">
      <div className="ab-summary-text">
        <h3 className="ab-summary-title">Variant comparison</h3>
        <p className="ab-summary-body">
          Variant <strong>{winnerVariant}</strong> currently has the highest
          success rate ({winnerMetrics.success_rate.toFixed(2)}%).
          {loser && (
            <>
              {" "}
              It is ahead of variant <strong>{loser[0]}</strong> by{" "}
              {diffSuccess.toFixed(2)} percentage points.
            </>
          )}
          {!loser && " Collect more traffic on the other variant to compare."}
        </p>
      </div>
      <div className="ab-summary-chart">
        <ResponsiveContainer width="100%" height={140}>
          <BarChart data={chartData}>
            <XAxis dataKey="variant" />
            <YAxis
              tickFormatter={(v: number) => `${v.toFixed(0)}%`}
              domain={[0, "auto"]}
            />
            <Tooltip
              formatter={(value: any) => [
                `${Number(value).toFixed(2)}%`,
                "Success rate",
              ]}
            />
            <Bar dataKey="success_rate" />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};


const DEFAULT_SYMBOLS = ["AAPL", "MSFT", "NVDA", "META", "TSLA", "AMZN"];

const App: React.FC = () => {
  const [userId, setUserId] = useState<string>("test-user");
  const [symbols] = useState<string[]>(DEFAULT_SYMBOLS);
  const [selectedSymbols, setSelectedSymbols] = useState<string[]>([
    "AAPL"
  ]);

  const [models, setModels] = useState<ModelMeta[]>([]);
  const [selectedModel, setSelectedModel] = useState<string>("all");

  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [response, setResponse] = useState<RecommendResponse | null>(null);

  const [metricsLoading, setMetricsLoading] = useState<boolean>(false);
  const [metricsError, setMetricsError] = useState<string | null>(null);
  const [abMetrics, setAbMetrics] = useState<AbMetricsResponse | null>(null);
  const [selectedChartSymbol, setSelectedChartSymbol] = useState<string | null>(null);
  const [historicalLoading, setHistoricalLoading] = useState(false);
  const [historicalError, setHistoricalError] = useState<string | null>(null);
  const [historicalData, setHistoricalData] = useState<HistoricalPoint[]>([]);

  // Load list of available models from /models on mount
  useEffect(() => {
    const loadModels = async () => {
      try {
        const res = await fetch(`${API_BASE_URL}/models`);
        if (!res.ok) {
          throw new Error(`Failed to load models: ${res.statusText}`);
        }
        const data = await res.json();
        const available = (data?.available_models || []) as ModelMeta[];

        // Add an "All (A/B)" pseudo-option
        setModels(available);
      } catch (err: any) {
        console.warn("Could not fetch /models, using defaults", err);
        // Fallback static list
        setModels([
          {
            name: "LSTM",
            type: "neural_network",
            description: "Long Short-Term Memory neural network",
          },
          {
            name: "RandomForest",
            type: "ensemble",
            description: "Random Forest regressor",
          },
          {
            name: "MovingAverage",
            type: "baseline",
            description: "Simple moving average baseline model",
          },
        ]);
      }
    };

    loadModels();
  }, []);

  useEffect(() => {
    if (response && response.results) {
      const symbols = Object.keys(response.results);
      if (symbols.length > 0) {
        const first = symbols[0];
        setSelectedChartSymbol(first);
        fetchHistorical(first);
      }
    }
  }, [response]);


  const toggleSymbol = (symbol: string) => {
    setSelectedSymbols((prev) =>
      prev.includes(symbol)
        ? prev.filter((s) => s !== symbol)
        : [...prev, symbol]
    );
  };

  const handleSelectAllSymbols = () => {
    setSelectedSymbols([...symbols]);
  };

  const handleClearSymbols = () => {
    setSelectedSymbols([]);
  };

  const fetchHistorical = async (symbol: string) => {
    setHistoricalLoading(true);
    setHistoricalError(null);
    setHistoricalData([]);

    try {
      const res = await fetch(`${API_BASE_URL}/historical/${symbol}?limit=120`);
      if (!res.ok) {
        throw new Error(`Failed to load history: ${res.statusText}`);
      }
      const data = (await res.json()) as HistoricalResponse;
      setHistoricalData(data.points || []);
    } catch (err: any) {
      setHistoricalError(err.message || "Error loading history");
    } finally {
      setHistoricalLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (selectedSymbols.length === 0) {
      setError("Please select at least one symbol.");
      return;
    }

    setLoading(true);
    setError(null);
    setResponse(null);

    try {
      const res = await fetch(`${API_BASE_URL}/recommend`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          user_id: userId.trim() || "test-user",
          symbols: selectedSymbols,
          model: selectedModel === "all" ? "all" : selectedModel,
        }),
      });

      if (!res.ok) {
        let msg = `Request failed (${res.status})`;
        try {
          const text = await res.text();
          msg = `${msg}: ${text}`;
        } catch {
          // ignore
        }
        throw new Error(msg);
      }

      const data = (await res.json()) as RecommendResponse;
      setResponse(data);
    } catch (err: any) {
      console.error(err);
      setError(err.message || "Unexpected error while calling /recommend");
    } finally {
      setLoading(false);
    }
  };

  const handleLoadAbMetrics = async () => {
    setMetricsLoading(true);
    setMetricsError(null);
    setAbMetrics(null);

    try {
      const res = await fetch(`${API_BASE_URL}/ab-test-metrics`);
      if (!res.ok) {
        let msg = `Failed to fetch A/B metrics (${res.status})`;
        try {
          const text = await res.text();
          msg = `${msg}: ${text}`;
        } catch {
          // ignore
        }
        throw new Error(msg);
      }
      const data = (await res.json()) as AbMetricsResponse;
      setAbMetrics(data);
    } catch (err: any) {
      console.error(err);
      setMetricsError(err.message || "Error while fetching A/B metrics");
    } finally {
      setMetricsLoading(false);
    }
  };

  const formatNumber = (value: number | undefined, decimals = 4) => {
    if (value === undefined || value === null || Number.isNaN(value)) {
      return "-";
    }
    return value.toFixed(decimals);
  };

  const formatTimestamp = (ts?: string) => {
    if (!ts) return "-";
    const d = new Date(ts);
    if (Number.isNaN(d.getTime())) return ts;
    return d.toLocaleString();
  };

  return (
    <div className="app-root">
      <header className="app-header">
        <div className="app-header-left">
          <h1 className="app-title">FinSightAI Dashboard</h1>
          <p className="app-subtitle">
            Real-time stock predictions from LSTM, Random Forest, and Moving
            Average models.
          </p>
        </div>
        <div className="app-header-right">
          <span className="api-chip">
            API: <code>{API_BASE_URL}</code>
          </span>
        </div>
      </header>

      <main className="app-main">
        <section className="panel panel-left">
          <h2 className="panel-title">Request Builder</h2>

          <form className="request-form" onSubmit={handleSubmit}>
            <div className="form-group">
              <label htmlFor="userId">User ID</label>
              <input
                id="userId"
                type="text"
                value={userId}
                onChange={(e) => setUserId(e.target.value)}
                placeholder="demo-user-123"
              />
              <small className="help-text">
                Used for A/B testing assignment (variants A/B).
              </small>
            </div>

            <div className="form-group">
              <label>Symbols</label>
              <div className="symbols-actions">
                <button
                  type="button"
                  className="secondary-button"
                  onClick={handleSelectAllSymbols}
                >
                  Select all
                </button>
                <button
                  type="button"
                  className="secondary-button"
                  onClick={handleClearSymbols}
                >
                  Clear
                </button>
              </div>
              <div className="symbols-grid">
                {symbols.map((symbol) => {
                  const active = selectedSymbols.includes(symbol);
                  return (
                    <button
                      key={symbol}
                      type="button"
                      className={`symbol-pill ${
                        active ? "symbol-pill-active" : ""
                      }`}
                      onClick={() => toggleSymbol(symbol)}
                    >
                      {symbol}
                    </button>
                  );
                })}
              </div>
            </div>

            <div className="form-group">
              <label htmlFor="modelSelect">Model</label>
              <select
                id="modelSelect"
                value={selectedModel}
                onChange={(e) =>
                  setSelectedModel(e.target.value || "all")
                }
              >
                <option value="all">All / A/B test (backend decides)</option>
                {models.map((m) => (
                  <option key={m.name} value={m.name.toLowerCase()}>
                    {m.name}
                  </option>
                ))}
              </select>
              <small className="help-text">
                If you choose “All / A/B test”, the backend may assign a variant
                (LSTM vs RandomForest).
              </small>
            </div>

            <div className="form-footer">
              <button
                type="submit"
                className="primary-button"
                disabled={loading}
              >
                {loading ? "Requesting..." : "Get Predictions"}
              </button>
              {error && <p className="error-text">{error}</p>}
            </div>
          </form>
        </section>

        <section className="panel panel-right">
          <div className="panel-right-top">
            <div className="subpanel">
              <h2 className="panel-title">Prediction Results</h2>
                            {selectedChartSymbol && (
                <div className="chart-wrapper">
                  <div className="chart-header-row">
                    <div>
                      <h3 className="chart-title">
                        {selectedChartSymbol} price history
                      </h3>
                      <p className="chart-subtitle">
                        Recent close prices from the model&apos;s historical
                        buffer.
                      </p>
                    </div>
                    {historicalLoading && (
                      <span className="chart-status">Loading…</span>
                    )}
                    {historicalError && (
                      <span className="chart-status chart-status-error">
                        {historicalError}
                      </span>
                    )}
                  </div>

                  {historicalData.length > 0 && (
                    <div className="chart-container">
                    <ResponsiveContainer width="100%" height={260}>
                      <LineChart data={historicalData}>
                        <CartesianGrid strokeDasharray="4 4" vertical={false} />
                        <XAxis
                          dataKey="timestamp"
                          minTickGap={32}
                          tickFormatter={(value: string) => {
                            const d = new Date(value);
                            // e.g. "11/25 14:00"
                            const mm = (d.getMonth() + 1).toString().padStart(2, "0");
                            const dd = d.getDate().toString().padStart(2, "0");
                            const hh = d.getHours().toString().padStart(2, "0");
                            return `${mm}/${dd} ${hh}:00`;
                          }}
                        />
                        <YAxis
                          domain={["dataMin - 2", "dataMax + 2"]}
                          tickFormatter={(v: number) => `$${v.toFixed(2)}`}
                        />
                        <Tooltip
                          labelFormatter={(value: any) => {
                            const d = new Date(value);
                            return d.toLocaleString();
                          }}
                          formatter={(value: any) => [
                            `$${Number(value).toFixed(2)}`,
                            "Close",
                          ]}
                        />
                        <Line
                          type="monotone"
                          dataKey="close"
                          dot={false}
                          strokeWidth={2.2}
                        />
                      </LineChart>
                    </ResponsiveContainer>
                    </div>
                  )}

                  {!historicalLoading &&
                    !historicalError &&
                    historicalData.length === 0 && (
                      <p className="chart-empty-text">
                        No historical data available for{" "}
                        <strong>{selectedChartSymbol}</strong>.
                      </p>
                    )}
                </div>
              )}
              {!response && !loading && (
                <p className="placeholder-text">
                  Submit a request to see predictions.
                </p>
              )}
              {loading && (
                <p className="placeholder-text">
                  Calling <code>/recommend</code>...
                </p>
              )}
              {response && (
                <div className="results-container">
                  <div className="results-meta">
                    <div>
                      <span className="label">Request ID:</span>{" "}
                      <code>{response.request_id}</code>
                    </div>
                    <div>
                      <span className="label">Status:</span>{" "}
                      <span
                        className={
                          response.status === "success"
                            ? "status-chip status-ok"
                            : "status-chip status-bad"
                        }
                      >
                        {response.status}
                      </span>
                    </div>
                    <div>
                      <span className="label">Timestamp:</span>{" "}
                      {formatTimestamp(response.timestamp)}
                    </div>
                    <div>
                      <span className="label">Model used:</span>{" "}
                      <code>{response.model_used}</code>
                    </div>
                  </div>

                  <div className="results-grid">
                    {Object.entries(response.results).map(
                      ([symbol, result]) => {
                        const hasError =
                          !!result.error &&
                          (!result.predictions ||
                            Object.keys(result.predictions).length === 0);

                        return (
                          <div key={symbol} className="result-card" onClick={() => {
                                setSelectedChartSymbol(symbol);
                                fetchHistorical(symbol);}}>
                            <div className="result-card-header">
                              <h3>{symbol}</h3>
                              {hasError ? (
                                <span className="status-chip status-bad">
                                  Error
                                </span>
                              ) : (
                                <span className="status-chip status-ok">
                                  OK
                                </span>
                              )}
                            </div>

                            {hasError && (
                              <p className="error-text">
                                {result.error || "Prediction failed"}
                              </p>
                            )}

                            {!hasError && (
                              <>
                                <div className="price-row">
                                  <span className="label">
                                    Current Price:
                                  </span>
                                  <span className="value">
                                    $
                                    {formatNumber(
                                      result.current_price,
                                      2
                                    )}
                                  </span>
                                </div>

                                <div className="time-row">
                                  <div>
                                    <span className="label">Predicted at:</span>{" "}
                                    <span className="value">
                                      {formatTimestamp(
                                        result.prediction_timestamp
                                      )}
                                    </span>
                                  </div>
                                  <div>
                                    <span className="label">
                                      Target horizon:
                                    </span>{" "}
                                    <span className="value">
                                      {formatTimestamp(
                                        result.target_timestamp
                                      )}
                                    </span>
                                  </div>
                                </div>

                                <table className="pred-table">
                                  <thead>
                                    <tr>
                                      <th>Model</th>
                                      <th>Predicted Price Δ / Value</th>
                                    </tr>
                                  </thead>
                                  <tbody>
                                    {result.predictions &&
                                      Object.entries(
                                        result.predictions
                                      ).map(
                                        ([modelName, value]) => (
                                          <tr key={modelName}>
                                            <td>{modelName}</td>
                                            <td>
                                              {formatNumber(
                                                value,
                                                4
                                              )}
                                            </td>
                                          </tr>
                                        )
                                      )}
                                  </tbody>
                                </table>
                              </>
                            )}
                          </div>
                        );
                      }
                    )}
                  </div>
                </div>
              )}
            </div>

            <div className="subpanel">
              <h2 className="panel-title">A/B Test Metrics</h2>
                            <div className="metrics-controls">
                <button
                  type="button"
                  className="secondary-button"
                  onClick={handleLoadAbMetrics}
                  disabled={metricsLoading}
                >
                  {metricsLoading
                    ? "Loading metrics..."
                    : "Load latest A/B metrics"}
                </button>
                {metricsError && (
                  <p className="error-text">{metricsError}</p>
                )}
              </div>

              {!abMetrics && !metricsLoading && (
                <p className="placeholder-text">
                  Load metrics to compare control vs treatment variants.
                </p>
              )}

              {abMetrics && (
                <div className="metrics-container">
                  {abMetrics.error && (
                    <p className="error-text">
                      Backend returned error: {abMetrics.error}
                    </p>
                  )}

                  <div className="metrics-meta">
                    <div>
                      <span className="label">Date:</span>{" "}
                      {abMetrics.date || "-"}
                    </div>
                    {abMetrics.test_config && (
                      <div>
                        <span className="label">Control:</span>{" "}
                        <code>{abMetrics.test_config.control}</code>{" "}
                        <span className="label">Treatment:</span>{" "}
                        <code>{abMetrics.test_config.treatment}</code>
                      </div>
                    )}
                  </div>

                  {abMetrics.results && (
                    <>
                      {/* Summary + bar chart */}
                      <AbSummaryAndChart abMetrics={abMetrics} />

                      {/* Detailed cards */}
                      <div className="metrics-grid">
                        {Object.entries(abMetrics.results).map(([variant, m]) => {
                          const hasData = m.total_requests > 0;

                          return (
                            <div key={variant} className="metrics-card">
                              <div className="metrics-card-header">
                                <h3>Variant {variant}</h3>
                                {!hasData && (
                                  <span className="no-data-pill">no data yet</span>
                                )}
                              </div>

                              <div className="metrics-row">
                                <span className="label">Total requests:</span>
                                <span className="value">
                                  {hasData ? m.total_requests : "—"}
                                </span>
                              </div>
                              <div className="metrics-row">
                                <span className="label">Success rate:</span>
                                <span className="value">
                                  {hasData ? `${formatNumber(m.success_rate, 2)}%` : "—"}
                                </span>
                              </div>
                              <div className="metrics-row">
                                <span className="label">Error rate:</span>
                                <span className="value">
                                  {hasData ? `${formatNumber(m.error_rate, 2)}%` : "—"}
                                </span>
                              </div>
                              <div className="metrics-row">
                                <span className="label">Avg latency:</span>
                                <span className="value">
                                  {hasData ? `${formatNumber(m.avg_latency_ms, 1)} ms` : "—"}
                                </span>
                              </div>
                              <div className="metrics-row">
                                <span className="label">P95 latency:</span>
                                <span className="value">
                                  {hasData ? `${formatNumber(m.p95_latency_ms, 1)} ms` : "—"}
                                </span>
                              </div>
                              <div className="metrics-row">
                                <span className="label">
                                  Predictions (ok / total):
                                </span>
                                <span className="value">
                                  {hasData
                                    ? `${m.successful_predictions} / ${m.total_predictions}`
                                    : "—"}
                                </span>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </>
                  )}
                </div>
              )}
            </div>
          </div>
        </section>
      </main>

      <footer className="app-footer">
        <span>
          FinSightAI • Backend: FastAPI & Kafka • Frontend: React + TypeScript
        </span>
      </footer>
    </div>
  );
};

export default App;
