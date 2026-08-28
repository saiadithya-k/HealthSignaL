import React, { useEffect, useState } from 'react';
import {
  fetchHealthStatus,
  fetchVersionInfo,
  fetchInstitutionsStatus,
  fetchNonIidSummary,
  triggerDataGeneration,
  fetchBaselineComparison,
  triggerTrainLocalModels,
  fetchFederationStatus,
  triggerStartFederatedRound,
  fetchForecasts,
  triggerGenerateForecast,
  fetchAlertsQueue,
  approveAlert,
  rejectAlert,
  triggerAnomalyDetection
} from './services/api';

export default function App() {
  const [health, setHealth] = useState(null);
  const [version, setVersion] = useState(null);
  const [nodesStatus, setNodesStatus] = useState([]);
  const [nonIidData, setNonIidData] = useState(null);
  const [baselinesData, setBaselinesData] = useState(null);
  const [federationData, setFederationData] = useState(null);
  const [forecastData, setForecastData] = useState(null);
  const [alertsData, setAlertsData] = useState(null);

  const [loading, setLoading] = useState(true);
  const [selectedScenario, setSelectedScenario] = useState('NORMAL');
  const [generating, setGenerating] = useState(false);
  const [training, setTraining] = useState(false);
  const [runningFed, setRunningFed] = useState(false);
  const [generatingFcst, setGeneratingFcst] = useState(false);
  const [detectingAnomaly, setDetectingAnomaly] = useState(false);
  const [fcstHorizon, setFcstHorizon] = useState(7);
  const [missingNodes, setMissingNodes] = useState(0);

  const loadAllData = async () => {
    setLoading(true);
    const hData = await fetchHealthStatus();
    const vData = await fetchVersionInfo();
    const nData = await fetchInstitutionsStatus();
    const niData = await fetchNonIidSummary();
    const bData = await fetchBaselineComparison();
    const fData = await fetchFederationStatus();
    const fcData = await fetchForecasts();
    const aData = await fetchAlertsQueue();

    setHealth(hData);
    setVersion(vData);
    setNodesStatus(nData?.institutions || []);
    setNonIidData(niData);
    setBaselinesData(bData);
    setFederationData(fData);
    setForecastData(fcData);
    setAlertsData(aData);
    setLoading(false);
  };

  useEffect(() => {
    loadAllData();
  }, []);

  const handleGenerateData = async (scenario) => {
    setSelectedScenario(scenario);
    setGenerating(true);
    try {
      await triggerDataGeneration(scenario, 42, 365);
      await loadAllData();
    } catch (err) {
      alert("Failed to generate data: " + err.message);
    } finally {
      setGenerating(false);
    }
  };

  const handleTrainLocalModels = async () => {
    setTraining(true);
    try {
      await triggerTrainLocalModels(7, 1.0);
      await loadAllData();
    } catch (err) {
      alert("Failed to train models: " + err.message);
    } finally {
      setTraining(false);
    }
  };

  const handleStartFederatedRound = async () => {
    setRunningFed(true);
    try {
      await triggerStartFederatedRound(7, 1.0);
      await loadAllData();
    } catch (err) {
      alert("Failed to run federated round: " + err.message);
    } finally {
      setRunningFed(false);
    }
  };

  const handleGenerateForecast = async (horizon, missing) => {
    setFcstHorizon(horizon);
    setMissingNodes(missing);
    setGeneratingFcst(true);
    try {
      await triggerGenerateForecast(horizon, missing);
      await loadAllData();
    } catch (err) {
      alert("Failed to generate forecast: " + err.message);
    } finally {
      setGeneratingFcst(false);
    }
  };

  const handleRunAnomalyDetection = async () => {
    setDetectingAnomaly(true);
    try {
      await triggerAnomalyDetection(0.5, 4.0, missingNodes);
      await loadAllData();
    } catch (err) {
      alert("Failed to run anomaly detection: " + err.message);
    } finally {
      setDetectingAnomaly(false);
    }
  };

  const handleApproveAlert = async (alertId) => {
    try {
      await approveAlert(alertId, "public_health_analyst", "Approved after statistical review");
      await loadAllData();
    } catch (err) {
      alert("Failed to approve alert: " + (err.response?.data?.detail || err.message));
    }
  };

  const handleRejectAlert = async (alertId) => {
    try {
      await rejectAlert(alertId, "public_health_analyst", "Rejected false positive noise");
      await loadAllData();
    } catch (err) {
      alert("Failed to reject alert: " + (err.response?.data?.detail || err.message));
    }
  };

  const compMatrix = baselinesData?.comparison_matrix;
  const baseDetails = baselinesData?.baselines;
  const fedReport = federationData?.federated_report;
  const fcstReport = forecastData?.report;
  const fcstList = forecastData?.forecasts || [];
  const alertList = alertsData?.alerts || [];

  return (
    <div className="app-container">
      <header>
        <div className="brand">
          <div className="brand-icon">HS</div>
          <div>
            <h1 className="brand-title">HealthSignal</h1>
            <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Federated Community Health Trend Forecasting — Phase 6 CUSUM Surge & Reviewer Queue
            </p>
          </div>
        </div>

        <div>
          {loading ? (
            <span className="badge" style={{ background: '#334155', color: '#94a3b8' }}>Checking...</span>
          ) : health?.status === 'online' ? (
            <span className="badge badge-online">● System Online</span>
          ) : (
            <span className="badge badge-offline">● System Offline</span>
          )}
        </div>
      </header>

      <main>
        {/* Control Header Card */}
        <div className="card">
          <div className="card-header">
            <h2 className="card-title">HealthSignal Platform Controls</h2>
            <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
              Synthetic Generation, FedAvg Training, Forecasts & Anomaly Detection
            </span>
          </div>

          <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap', marginTop: '0.75rem', alignItems: 'center' }}>
            <span style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-main)' }}>
              Scenario:
            </span>
            {['NORMAL', 'REGIONAL_SURGE', 'DISTRIBUTION_SHIFT', 'MISSING_DATA'].map((scen) => (
              <button
                key={scen}
                disabled={generating || training || runningFed || generatingFcst || detectingAnomaly}
                onClick={() => handleGenerateData(scen)}
                style={{
                  padding: '0.4rem 0.85rem',
                  borderRadius: '6px',
                  border: '1px solid var(--border-color)',
                  background: selectedScenario === scen ? 'var(--accent-blue)' : 'rgba(30, 41, 59, 0.8)',
                  color: '#fff',
                  fontWeight: 600,
                  fontSize: '0.8rem',
                  cursor: 'pointer'
                }}
              >
                {generating && selectedScenario === scen ? 'Generating...' : scen}
              </button>
            ))}

            <button
              disabled={training || generating || runningFed || generatingFcst || detectingAnomaly}
              onClick={handleTrainLocalModels}
              style={{
                marginLeft: 'auto',
                padding: '0.45rem 0.85rem',
                borderRadius: '6px',
                border: '1px solid var(--border-color)',
                background: 'rgba(30, 41, 59, 0.8)',
                color: '#fff',
                fontWeight: 600,
                fontSize: '0.8rem',
                cursor: 'pointer'
              }}
            >
              {training ? 'Training...' : 'Train Local Baselines'}
            </button>

            <button
              disabled={runningFed || generating || training || generatingFcst || detectingAnomaly}
              onClick={handleStartFederatedRound}
              style={{
                padding: '0.45rem 1rem',
                borderRadius: '6px',
                border: 'none',
                background: 'linear-gradient(135deg, #0ea5e9, #6366f1)',
                color: '#fff',
                fontWeight: 700,
                fontSize: '0.85rem',
                cursor: 'pointer'
              }}
            >
              {runningFed ? 'Running FedAvg...' : '🌐 Run 4-Client FedAvg'}
            </button>

            <button
              disabled={detectingAnomaly || generating || training || runningFed}
              onClick={handleRunAnomalyDetection}
              style={{
                padding: '0.45rem 1rem',
                borderRadius: '6px',
                border: 'none',
                background: 'linear-gradient(135deg, #f59e0b, #ef4444)',
                color: '#fff',
                fontWeight: 700,
                fontSize: '0.85rem',
                cursor: 'pointer'
              }}
            >
              {detectingAnomaly ? 'Detecting Surges...' : '🚨 Run CUSUM Anomaly Detection'}
            </button>
          </div>
        </div>

        {/* Phase 6 — Reviewer Queue UI Card */}
        <div className="card" style={{ borderLeft: '4px solid #f59e0b' }}>
          <div className="card-header">
            <h2 className="card-title">Phase 6 — Anomaly Detection & Human Reviewer Queue</h2>
            <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
              <span className="badge" style={{ background: 'rgba(234, 179, 8, 0.2)', color: '#fde047', border: '1px solid #eab308' }}>
                {alertsData?.candidate_count || 0} Candidate Alerts
              </span>
              <span className="badge" style={{ background: 'rgba(34, 197, 94, 0.2)', color: '#4ade80', border: '1px solid #22c55e' }}>
                {alertsData?.approved_count || 0} Approved
              </span>
              <span className="badge" style={{ background: 'rgba(239, 68, 68, 0.2)', color: '#f87171', border: '1px solid #ef4444' }}>
                {alertsData?.rejected_count || 0} Rejected
              </span>
            </div>
          </div>

          <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '0.75rem' }}>
            Statistical Process Control (CUSUM $h=4.0$) flags candidate surges relative to the Phase 5 baseline. Public Health Analysts review evidence and decide to <strong>APPROVE</strong> or <strong>REJECT</strong> alerts.
          </p>

          <div style={{ overflowX: 'auto', marginTop: '0.5rem' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.82rem', textAlign: 'left' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border-color)', color: 'var(--accent-cyan)' }}>
                  <th style={{ padding: '0.5rem' }}>Alert ID</th>
                  <th style={{ padding: '0.5rem' }}>Date</th>
                  <th style={{ padding: '0.5rem' }}>Syndrome</th>
                  <th style={{ padding: '0.5rem' }}>Observed</th>
                  <th style={{ padding: '0.5rem' }}>Expected</th>
                  <th style={{ padding: '0.5rem' }}>Residual</th>
                  <th style={{ padding: '0.5rem' }}>CUSUM ($S^+$)</th>
                  <th style={{ padding: '0.5rem' }}>Confidence</th>
                  <th style={{ padding: '0.5rem' }}>Status</th>
                  <th style={{ padding: '0.5rem' }}>Reviewer Action</th>
                </tr>
              </thead>
              <tbody>
                {alertList.length > 0 ? (
                  alertList.map((a) => {
                    const ev = a.evidence_data || {};
                    return (
                      <tr key={a.id} style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.05)' }}>
                        <td style={{ padding: '0.5rem', fontFamily: 'monospace', fontSize: '0.75rem' }}>{a.id.substring(0, 8)}...</td>
                        <td style={{ padding: '0.5rem' }}>{ev.forecast_date || a.detected_at}</td>
                        <td style={{ padding: '0.5rem', textTransform: 'capitalize' }}>{a.syndrome_category}</td>
                        <td style={{ padding: '0.5rem', fontWeight: 700, color: '#f87171' }}>{ev.observed_value ?? '-'}</td>
                        <td style={{ padding: '0.5rem' }}>{ev.expected_value ?? '-'}</td>
                        <td style={{ padding: '0.5rem', color: '#eab308' }}>+{ev.residual ?? '-'}</td>
                        <td style={{ padding: '0.5rem', fontWeight: 700 }}>{a.shift_score}</td>
                        <td style={{ padding: '0.5rem' }}>{ev.confidence_score ? `${(ev.confidence_score * 100).toFixed(0)}%` : '100%'}</td>
                        <td style={{ padding: '0.5rem' }}>
                          {a.status === 'CANDIDATE' && <span className="badge" style={{ background: 'rgba(234, 179, 8, 0.2)', color: '#fde047' }}>CANDIDATE</span>}
                          {a.status === 'APPROVED' && <span className="badge badge-online">APPROVED</span>}
                          {a.status === 'REJECTED' && <span className="badge badge-offline">REJECTED</span>}
                        </td>
                        <td style={{ padding: '0.5rem' }}>
                          {a.status === 'CANDIDATE' ? (
                            <div style={{ display: 'flex', gap: '0.4rem' }}>
                              <button
                                onClick={() => handleApproveAlert(a.id)}
                                style={{
                                  padding: '0.25rem 0.5rem',
                                  borderRadius: '4px',
                                  border: 'none',
                                  background: '#22c55e',
                                  color: '#fff',
                                  fontWeight: 700,
                                  fontSize: '0.75rem',
                                  cursor: 'pointer'
                                }}
                              >
                                APPROVE
                              </button>
                              <button
                                onClick={() => handleRejectAlert(a.id)}
                                style={{
                                  padding: '0.25rem 0.5rem',
                                  borderRadius: '4px',
                                  border: 'none',
                                  background: '#ef4444',
                                  color: '#fff',
                                  fontWeight: 700,
                                  fontSize: '0.75rem',
                                  cursor: 'pointer'
                                }}
                              >
                                REJECT
                              </button>
                            </div>
                          ) : (
                            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Action Recorded</span>
                          )}
                        </td>
                      </tr>
                    );
                  })
                ) : (
                  <tr>
                    <td colSpan="10" style={{ padding: '1rem', textAlign: 'center', color: 'var(--text-muted)' }}>
                      No alert candidates in queue. Click "Run CUSUM Anomaly Detection" above to test surge detection.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Phase 5 — Forecasting & Uncertainty Card */}
        <div className="card" style={{ borderLeft: '4px solid #818cf8' }}>
          <div className="card-header">
            <h2 className="card-title">Phase 5 — 7–14 Day Forecast & Uncertainty Engine</h2>
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              <button
                disabled={generatingFcst}
                onClick={() => handleGenerateForecast(7, 0)}
                style={{
                  padding: '0.35rem 0.75rem',
                  borderRadius: '6px',
                  border: '1px solid #6366f1',
                  background: fcstHorizon === 7 && missingNodes === 0 ? '#6366f1' : 'transparent',
                  color: '#fff',
                  fontSize: '0.8rem',
                  fontWeight: 600,
                  cursor: 'pointer'
                }}
              >
                7-Day Forecast (All Nodes)
              </button>
              <button
                disabled={generatingFcst}
                onClick={() => handleGenerateForecast(14, 0)}
                style={{
                  padding: '0.35rem 0.75rem',
                  borderRadius: '6px',
                  border: '1px solid #6366f1',
                  background: fcstHorizon === 14 && missingNodes === 0 ? '#6366f1' : 'transparent',
                  color: '#fff',
                  fontSize: '0.8rem',
                  fontWeight: 600,
                  cursor: 'pointer'
                }}
              >
                14-Day Forecast
              </button>
            </div>
          </div>

          {fcstReport && (
            <div>
              <div className="grid-2" style={{ marginTop: '0.75rem', gap: '1rem' }}>
                <div style={{ background: 'rgba(30, 41, 59, 0.5)', padding: '0.75rem', borderRadius: '6px' }}>
                  <div><strong>Global Model Version:</strong> {fcstReport.model_version}</div>
                  <div><strong>Requested Horizon:</strong> {fcstReport.horizon_days} Days</div>
                  <div><strong>Data Coverage Ratio:</strong> <span style={{ color: fcstReport.coverage_ratio < 1.0 ? '#eab308' : 'var(--accent-green)', fontWeight: 700 }}>{(fcstReport.coverage_ratio * 100).toFixed(0)}%</span></div>
                </div>

                <div style={{ background: 'rgba(30, 41, 59, 0.5)', padding: '0.75rem', borderRadius: '6px' }}>
                  <div><strong>Forecast Confidence Score:</strong> <span style={{ color: 'var(--accent-cyan)', fontWeight: 700 }}>{(fcstReport.confidence_score * 100).toFixed(0)}%</span></div>
                  <div><strong>80% Empirical Coverage:</strong> {(fcstReport.empirical_coverage?.empirical_80 * 100).toFixed(1)}%</div>
                  <div><strong>95% Empirical Coverage:</strong> {(fcstReport.empirical_coverage?.empirical_95 * 100).toFixed(1)}%</div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Baseline Comparison Matrix Card */}
        {compMatrix && (
          <div className="card">
            <div className="card-header">
              <h2 className="card-title">Model Performance Matrix (7-Day Horizon MAE)</h2>
              <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                Comparing Naive vs Local vs Federated vs Pooled
              </span>
            </div>

            <div style={{ overflowX: 'auto', marginTop: '0.5rem' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem', textAlign: 'left' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid var(--border-color)', color: 'var(--accent-cyan)' }}>
                    <th style={{ padding: '0.6rem' }}>Model Architecture</th>
                    <th style={{ padding: '0.6rem' }}>Inst A MAE</th>
                    <th style={{ padding: '0.6rem' }}>Inst B MAE</th>
                    <th style={{ padding: '0.6rem' }}>Inst C MAE</th>
                    <th style={{ padding: '0.6rem' }}>Inst D MAE</th>
                    <th style={{ padding: '0.6rem' }}>Overall MAE</th>
                    <th style={{ padding: '0.6rem' }}>Overall RMSE</th>
                  </tr>
                </thead>
                <tbody>
                  <tr style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.05)' }}>
                    <td style={{ padding: '0.6rem', fontWeight: 600 }}>Naive Baseline (lag_7)</td>
                    <td style={{ padding: '0.6rem' }}>{compMatrix['inst-a'].naive_mae}</td>
                    <td style={{ padding: '0.6rem' }}>{compMatrix['inst-b'].naive_mae}</td>
                    <td style={{ padding: '0.6rem' }}>{compMatrix['inst-c'].naive_mae}</td>
                    <td style={{ padding: '0.6rem' }}>{compMatrix['inst-d'].naive_mae}</td>
                    <td style={{ padding: '0.6rem', fontWeight: 700 }}>{compMatrix['overall'].naive_mae}</td>
                    <td style={{ padding: '0.6rem' }}>{baseDetails?.naive_lag7?.overall?.rmse}</td>
                  </tr>

                  <tr style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.05)', background: 'rgba(56, 189, 248, 0.05)' }}>
                    <td style={{ padding: '0.6rem', fontWeight: 700, color: 'var(--accent-blue)' }}>
                      Baseline A — Local Ridge Models
                    </td>
                    <td style={{ padding: '0.6rem' }}>{compMatrix['inst-a'].local_ridge_mae}</td>
                    <td style={{ padding: '0.6rem' }}>{compMatrix['inst-b'].local_ridge_mae}</td>
                    <td style={{ padding: '0.6rem' }}>{compMatrix['inst-c'].local_ridge_mae}</td>
                    <td style={{ padding: '0.6rem' }}>{compMatrix['inst-d'].local_ridge_mae}</td>
                    <td style={{ padding: '0.6rem', fontWeight: 700, color: 'var(--accent-blue)' }}>{compMatrix['overall'].local_ridge_mae}</td>
                    <td style={{ padding: '0.6rem' }}>{baseDetails?.local_ridge?.overall?.rmse}</td>
                  </tr>

                  {fedReport && (
                    <tr style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.05)', background: 'rgba(99, 102, 241, 0.1)' }}>
                      <td style={{ padding: '0.6rem', fontWeight: 700, color: '#818cf8' }}>
                        Federated Model (Flower FedAvg)
                      </td>
                      <td style={{ padding: '0.6rem' }}>{fedReport.global_model_metrics?.by_institution?.['inst-a']?.mae}</td>
                      <td style={{ padding: '0.6rem' }}>{fedReport.global_model_metrics?.by_institution?.['inst-b']?.mae}</td>
                      <td style={{ padding: '0.6rem' }}>{fedReport.global_model_metrics?.by_institution?.['inst-c']?.mae}</td>
                      <td style={{ padding: '0.6rem' }}>{fedReport.global_model_metrics?.by_institution?.['inst-d']?.mae}</td>
                      <td style={{ padding: '0.6rem', fontWeight: 700, color: '#818cf8' }}>{fedReport.global_model_metrics?.overall?.mae}</td>
                      <td style={{ padding: '0.6rem' }}>{fedReport.global_model_metrics?.overall?.rmse}</td>
                    </tr>
                  )}

                  <tr style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.05)', background: 'rgba(16, 185, 129, 0.05)' }}>
                    <td style={{ padding: '0.6rem', fontWeight: 700, color: 'var(--accent-green)' }}>
                      Baseline B — Pooled Ridge (Upper Bound)*
                    </td>
                    <td style={{ padding: '0.6rem' }}>{compMatrix['inst-a'].pooled_ridge_mae}</td>
                    <td style={{ padding: '0.6rem' }}>{compMatrix['inst-b'].pooled_ridge_mae}</td>
                    <td style={{ padding: '0.6rem' }}>{compMatrix['inst-c'].pooled_ridge_mae}</td>
                    <td style={{ padding: '0.6rem' }}>{compMatrix['inst-d'].pooled_ridge_mae}</td>
                    <td style={{ padding: '0.6rem', fontWeight: 700, color: 'var(--accent-green)' }}>{compMatrix['overall'].pooled_ridge_mae}</td>
                    <td style={{ padding: '0.6rem' }}>{baseDetails?.pooled_ridge_upper_bound?.overall?.rmse}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        )}
      </main>

      <footer>
        Interdisciplinary Innovation Challenge 2026 — Problem S5 Prototype Specification
      </footer>
    </div>
  );
}
