import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

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

// -------------------------------------------------------------------------
// Multi-Source Data Collection & Knowledge API Methods
// -------------------------------------------------------------------------

export const fetchSymptomMaster = async () => {
  try {
    const response = await axios.get(`${API_BASE}/data-collection/symptom-master`);
    return response.data;
  } catch (error) {
    console.error("Fetch symptom master error:", error);
    return { symptoms: [], total_symptoms: 0 };
  }
};

export const fetchSyndromeMaster = async () => {
  try {
    const response = await axios.get(`${API_BASE}/data-collection/syndrome-master`);
    return response.data;
  } catch (error) {
    console.error("Fetch syndrome master error:", error);
    return { syndromes: [], total_syndromes: 0 };
  }
};

export const fetchDiseaseReference = async () => {
  try {
    const response = await axios.get(`${API_BASE}/data-collection/disease-reference`);
    return response.data;
  } catch (error) {
    console.error("Fetch disease reference error:", error);
    return { conditions: [], total_conditions: 0 };
  }
};

export const fetchSourceWeights = async () => {
  try {
    const response = await axios.get(`${API_BASE}/data-collection/source-weights`);
    return response.data;
  } catch (error) {
    console.error("Fetch source weights error:", error);
    return { source_reliability: {}, pharmacy_mapping: {}, testing_mapping: {} };
  }
};

export const submitCommunitySymptomReport = async (reportData) => {
  try {
    const response = await axios.post(`${API_BASE}/data-collection/community-report`, reportData);
    return response.data;
  } catch (error) {
    console.error("Community report submission error:", error);
    throw error;
  }
};

export const submitDoctorObservation = async (obsData) => {
  try {
    const response = await axios.post(`${API_BASE}/data-collection/doctor-observation`, obsData);
    return response.data;
  } catch (error) {
    console.error("Doctor observation submission error:", error);
    throw error;
  }
};

export const submitClinicDemand = async (demandData) => {
  try {
    const response = await axios.post(`${API_BASE}/data-collection/clinic-demand`, demandData);
    return response.data;
  } catch (error) {
    console.error("Clinic demand submission error:", error);
    throw error;
  }
};

export const submitPharmacyDemand = async (pharmData) => {
  try {
    const response = await axios.post(`${API_BASE}/data-collection/pharmacy-demand`, pharmData);
    return response.data;
  } catch (error) {
    console.error("Pharmacy demand submission error:", error);
    throw error;
  }
};

export const submitTestingData = async (testData) => {
  try {
    const response = await axios.post(`${API_BASE}/data-collection/testing-data`, testData);
    return response.data;
  } catch (error) {
    console.error("Testing data submission error:", error);
    throw error;
  }
};

export const submitAbsenteeism = async (absenteeData) => {
  try {
    const response = await axios.post(`${API_BASE}/data-collection/absenteeism`, absenteeData);
    return response.data;
  } catch (error) {
    console.error("Absenteeism submission error:", error);
    throw error;
  }
};

export const submitEmergencyCalls = async (emergencyData) => {
  try {
    const response = await axios.post(`${API_BASE}/data-collection/emergency-calls`, emergencyData);
    return response.data;
  } catch (error) {
    console.error("Emergency calls submission error:", error);
    throw error;
  }
};

export const submitWastewater = async (wastewaterData) => {
  try {
    const response = await axios.post(`${API_BASE}/data-collection/wastewater`, wastewaterData);
    return response.data;
  } catch (error) {
    console.error("Wastewater submission error:", error);
    throw error;
  }
};

export const fetchWeatherContext = async (nodeId = "inst-a", queryDate = null) => {
  try {
    const url = queryDate
      ? `${API_BASE}/data-collection/weather?node_id=${nodeId}&query_date=${queryDate}`
      : `${API_BASE}/data-collection/weather?node_id=${nodeId}`;
    const response = await axios.get(url);
    return response.data;
  } catch (error) {
    console.error("Weather context fetch error:", error);
    return null;
  }
};

export const fetchAlertDossier = async (alertId) => {
  try {
    const response = await axios.get(`${API_BASE}/alerts/${alertId}/dossier`);
    return response.data;
  } catch (error) {
    console.error("Fetch alert dossier error:", error);
    throw error;
  }
};

export const triggerDailyAggregation = async (nodeId = null, kThreshold = 11) => {
  try {
    const url = nodeId
      ? `${API_BASE}/data-collection/aggregate-now?node_id=${nodeId}&k_threshold=${kThreshold}`
      : `${API_BASE}/data-collection/aggregate-now?k_threshold=${kThreshold}`;
    const response = await axios.post(url);
    return response.data;
  } catch (error) {
    console.error("Aggregation trigger error:", error);
    throw error;
  }
};

export const fetchZoneRollup = async (zoneId = null, syndrome = null, daysLookback = 7) => {
  try {
    let url = `${API_BASE}/data-collection/zone-rollup?days_lookback=${daysLookback}`;
    if (zoneId) url += `&zone_id=${zoneId}`;
    if (syndrome) url += `&syndrome=${syndrome}`;
    const response = await axios.get(url);
    return response.data;
  } catch (error) {
    console.error("Zone rollup fetch error:", error);
    return { zone_rollups: [], results_count: 0 };
  }
};

export const triggerEventSimulation = async (scenario, seed = 42, days = 365) => {
  try {
    const response = await axios.post(`${API_BASE}/data-collection/simulate-event`, {
      scenario,
      seed,
      days
    });
    return response.data;
  } catch (error) {
    console.error("Event simulation trigger error:", error);
    throw error;
  }
};

export const triggerMultiSymptomSimulation = async (nodeId = "inst-a", patternKey = "respiratory", count = 15) => {
  try {
    const response = await axios.post(`${API_BASE}/data-collection/simulate-multi-symptoms`, {
      node_id: nodeId,
      pattern_key: patternKey,
      count: count,
      zone_id: "zone-1"
    });
    return response.data;
  } catch (error) {
    console.error("Multi-symptom simulation error:", error);
    throw error;
  }
};

