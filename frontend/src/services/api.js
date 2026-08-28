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
