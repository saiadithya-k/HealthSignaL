import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_URL || '/api/v1';

export const fetchHealthStatus = async () => {
  try {
    const response = await axios.get(`${API_BASE}/health`);
    return response.data;
  } catch (error) {
    console.error("Health check error:", error);
    return {
      status: "offline",
      project: "HealthSignal",
      environment: "unknown",
      database: "unreachable"
    };
  }
};

export const fetchVersionInfo = async () => {
  try {
    const response = await axios.get(`${API_BASE}/version`);
    return response.data;
  } catch (error) {
    console.error("Version fetch error:", error);
    return null;
  }
};

export const fetchInstitutionsStatus = async () => {
  try {
    const response = await axios.get(`${API_BASE}/institutions/status`);
    return response.data;
  } catch (error) {
    console.error("Institutions status error:", error);
    return { institutions: [], total_nodes: 0 };
  }
};

export const fetchNonIidSummary = async () => {
  try {
    const response = await axios.get(`${API_BASE}/institutions/non-iid-summary`);
    return response.data;
  } catch (error) {
    console.error("Non-IID summary error:", error);
    return null;
  }
};

export const triggerDataGeneration = async (scenario = "NORMAL", seed = 42, days = 365) => {
  try {
    const response = await axios.post(`${API_BASE}/institutions/generate-data?scenario=${scenario}&seed=${seed}&days=${days}`);
    return response.data;
  } catch (error) {
    console.error("Data generation error:", error);
    throw error;
  }
};

export const fetchBaselineComparison = async () => {
  try {
    const response = await axios.get(`${API_BASE}/models/baselines`);
    return response.data;
  } catch (error) {
    console.error("Baseline comparison error:", error);
    return null;
  }
};

export const triggerTrainLocalModels = async (forecastHorizon = 7, alpha = 1.0) => {
  try {
    const response = await axios.post(`${API_BASE}/models/train-local?forecast_horizon=${forecastHorizon}&alpha=${alpha}`);
    return response.data;
  } catch (error) {
    console.error("Train local models error:", error);
    throw error;
  }
};

export const fetchFederationStatus = async () => {
  try {
    const response = await axios.get(`${API_BASE}/federation/status`);
    return response.data;
  } catch (error) {
    console.error("Federation status error:", error);
    return null;
  }
};

export const triggerStartFederatedRound = async (forecastHorizon = 7, alpha = 1.0) => {
  try {
    const response = await axios.post(`${API_BASE}/federation/start?forecast_horizon=${forecastHorizon}&alpha=${alpha}`);
    return response.data;
  } catch (error) {
    console.error("Start federated round error:", error);
    throw error;
  }
};

export const fetchForecasts = async () => {
  try {
    const response = await axios.get(`${API_BASE}/forecasts`);
    return response.data;
  } catch (error) {
    console.error("Fetch forecasts error:", error);
    return null;
  }
};

export const triggerGenerateForecast = async (horizon = 7, missingNodes = 0) => {
  try {
    const response = await axios.post(`${API_BASE}/forecasts/generate?horizon=${horizon}&missing_nodes=${missingNodes}`);
    return response.data;
  } catch (error) {
    console.error("Generate forecast error:", error);
    throw error;
  }
};

export const fetchAlertsQueue = async (status = null) => {
  try {
    const url = status ? `${API_BASE}/alerts?status=${status}` : `${API_BASE}/alerts`;
    const response = await axios.get(url);
    return response.data;
  } catch (error) {
    console.error("Fetch alerts queue error:", error);
    return { alerts: [], total_alerts: 0, candidate_count: 0, approved_count: 0, rejected_count: 0 };
  }
};

export const approveAlert = async (alertId, reviewerId = "public_health_analyst", reason = "Verified surge candidate") => {
  try {
    const response = await axios.post(`${API_BASE}/alerts/${alertId}/approve?reviewer_id=${reviewerId}&reason=${encodeURIComponent(reason)}`);
    return response.data;
  } catch (error) {
    console.error("Approve alert error:", error);
    throw error;
  }
};

export const rejectAlert = async (alertId, reviewerId = "public_health_analyst", reason = "False positive noise") => {
  try {
    const response = await axios.post(`${API_BASE}/alerts/${alertId}/reject?reviewer_id=${reviewerId}&reason=${encodeURIComponent(reason)}`);
    return response.data;
  } catch (error) {
    console.error("Reject alert error:", error);
    throw error;
  }
};

export const triggerAnomalyDetection = async (driftK = 0.5, thresholdH = 4.0, missingNodes = 0) => {
  try {
    const response = await axios.post(`${API_BASE}/alerts/detect?drift_k=${driftK}&threshold_h=${thresholdH}&missing_nodes=${missingNodes}`);
    return response.data;
  } catch (error) {
    console.error("Trigger anomaly detection error:", error);
    throw error;
  }
};
