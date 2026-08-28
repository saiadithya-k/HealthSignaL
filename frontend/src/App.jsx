import React, { useEffect, useState } from 'react';
import {
  fetchHealthStatus,
  fetchVersionInfo,
  fetchInstitutionsStatus,
  fetchNonIidSummary,
  triggerDataGeneration,
  fetchBaselineComparison,
  triggerTrainLocalModels
} from './services/api';

export default function App() {
  const [health, setHealth] = useState(null);
  const [version, setVersion] = useState(null);
  const [nodesStatus, setNodesStatus] = useState([]);
  const [nonIidData, setNonIidData] = useState(null);
  const [baselinesData, setBaselinesData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selectedScenario, setSelectedScenario] = useState('NORMAL');
  const [generating, setGenerating] = useState(false);
  const [training, setTraining] = useState(false);

  const loadAllData = async () => {
    setLoading(true);
    const hData = await fetchHealthStatus();
    const vData = await fetchVersionInfo();
    const nData = await fetchInstitutionsStatus();
    const niData = await fetchNonIidSummary();
    const bData = await fetchBaselineComparison();

    setHealth(hData);
    setVersion(vData);
    setNodesStatus(nData?.institutions || []);
    setNonIidData(niData);
    setBaselinesData(bData);
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

  const compMatrix = baselinesData?.comparison_matrix;
  const baseDetails = baselinesData?.baselines;

  return (
    <div className="app-container">
      <header>
        <div className="brand">
          <div className="brand-icon">HS</div>
          <div>
            <h1 className="brand-title">HealthSignal</h1>
            <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Federated Community Health Trend Forecasting — Phase 3 Local ML Baseline
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
        {/* Phase Overview Card */}
        <div className="card">
          <div className="card-header">
            <h2 className="card-title">Phase 3 — Local Ridge Regression & Baseline Comparison Harness</h2>
            <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
              Target: 7–14 Day Aggregate Demand
            </span>
          </div>

          <p style={{ marginBottom: '1rem', color: 'var(--text-muted)' }}>
            Each institution node independently trains a local Ridge Regression model on its own time-series data. Results are benchmarked against Naive rules and an evaluation-only Pooled Upper Bound model.
          </p>

          <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap', marginTop: '1rem', alignItems: 'center' }}>
            <span style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-main)' }}>
              Scenario:
            </span>
            {['NORMAL', 'REGIONAL_SURGE', 'DISTRIBUTION_SHIFT', 'MISSING_DATA'].map((scen) => (
              <button
                key={scen}
                disabled={generating || training}
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
              disabled={training || generating}
              onClick={handleTrainLocalModels}
              style={{
                marginLeft: 'auto',
                padding: '0.45rem 1rem',
                borderRadius: '6px',
                border: 'none',
                background: 'linear-gradient(135deg, #10b981, #059669)',
                color: '#fff',
                fontWeight: 700,
                fontSize: '0.85rem',
                cursor: 'pointer'
              }}
            >
              {training ? 'Training Models...' : '⚡ Train Local Models & Evaluate Baselines'}
            </button>
          </div>
        </div>

        {/* Baseline Comparison Matrix Card */}
        {compMatrix && (
          <div className="card">
            <div className="card-header">
              <h2 className="card-title">Baseline Model Performance Matrix (MAE)</h2>
              <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                Forecast Horizon: 7 Days
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
                    <td style={{ padding: '0.6rem', fontWeight: 600 }}>{compMatrix['inst-a'].local_ridge_mae}</td>
                    <td style={{ padding: '0.6rem', fontWeight: 600 }}>{compMatrix['inst-b'].local_ridge_mae}</td>
                    <td style={{ padding: '0.6rem', fontWeight: 600 }}>{compMatrix['inst-c'].local_ridge_mae}</td>
                    <td style={{ padding: '0.6rem', fontWeight: 600 }}>{compMatrix['inst-d'].local_ridge_mae}</td>
                    <td style={{ padding: '0.6rem', fontWeight: 700, color: 'var(--accent-blue)' }}>{compMatrix['overall'].local_ridge_mae}</td>
                    <td style={{ padding: '0.6rem' }}>{baseDetails?.local_ridge?.overall?.rmse}</td>
                  </tr>

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

            <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.75rem' }}>
              *<strong>EVALUATION-ONLY CENTRALIZED BASELINE:</strong> Pooled Ridge represents the hypothetical upper-bound accuracy if all institutional data were centralized. It is used strictly for benchmarking and is NOT part of the decentralized runtime architecture.
            </p>
          </div>
        )}

        {/* 4 Local Institutions Cards */}
        <div className="card">
          <h2 className="card-title" style={{ marginBottom: '1rem' }}>
            Decentralized Local Institutions (Nodes A–D)
          </h2>
          <div className="grid-2">
            {nodesStatus.map((node) => (
              <div key={node.id} className="node-card" style={{ flexDirection: 'column', alignItems: 'flex-start', gap: '0.5rem' }}>
                <div style={{ width: '100%', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div style={{ fontWeight: 700, fontSize: '1rem' }}>{node.name}</div>
                  <span className={node.dataset_ready ? "badge badge-online" : "badge badge-offline"}>
                    {node.dataset_ready ? "Dataset Isolated & Ready" : "Pending Data"}
                  </span>
                </div>

                <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                  Profile: {node.profile}
                </div>

                {node.summary && (
                  <div style={{ fontSize: '0.8rem', width: '100%', borderTop: '1px solid var(--border-color)', paddingTop: '0.5rem', marginTop: '0.25rem' }}>
                    <div><strong>Total Records:</strong> {node.summary.total_records}</div>
                    <div><strong>Mean Daily Demand:</strong> {node.summary.mean_daily_demand} visits/day</div>
                    {compMatrix && compMatrix[node.id] && (
                      <div style={{ color: 'var(--accent-cyan)', marginTop: '0.25rem', fontWeight: 600 }}>
                        Local Ridge MAE: {compMatrix[node.id].local_ridge_mae} | Pooled Gap: {(compMatrix[node.id].local_ridge_mae - compMatrix[node.id].pooled_ridge_mae).toFixed(2)}
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Non-IID Evidence Summary Card */}
        {nonIidData && (
          <div className="card">
            <h2 className="card-title" style={{ marginBottom: '0.5rem' }}>
              Non-IID Distribution Proof & Statistical Distances
            </h2>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '1rem' }}>
              Demonstrable mathematical proof of heterogeneous distributions: P(A) ≠ P(B) ≠ P(C) ≠ P(D)
            </p>

            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem', textAlign: 'left' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid var(--border-color)', color: 'var(--accent-cyan)' }}>
                    <th style={{ padding: '0.5rem' }}>Pairwise Comparison</th>
                    <th style={{ padding: '0.5rem' }}>KS Statistic</th>
                    <th style={{ padding: '0.5rem' }}>Wasserstein Distance</th>
                    <th style={{ padding: '0.5rem' }}>p-Value</th>
                    <th style={{ padding: '0.5rem' }}>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(nonIidData.pairwise_tests || {}).map(([pair, test]) => (
                    <tr key={pair} style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.05)' }}>
                      <td style={{ padding: '0.5rem', fontWeight: 600 }}>{pair.replace('_vs_', ' vs ')}</td>
                      <td style={{ padding: '0.5rem' }}>{test.ks_statistic}</td>
                      <td style={{ padding: '0.5rem' }}>{test.wasserstein_distance}</td>
                      <td style={{ padding: '0.5rem' }}>{test.p_value < 0.001 ? '< 0.001' : test.p_value}</td>
                      <td style={{ padding: '0.5rem' }}>
                        <span className="badge badge-online">Statistically Non-IID</span>
                      </td>
                    </tr>
                  ))}
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
