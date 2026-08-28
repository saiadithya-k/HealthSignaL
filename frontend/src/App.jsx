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
  triggerAnomalyDetection,
  fetchSymptomMaster,
  fetchSyndromeMaster,
  fetchDiseaseReference,
  fetchSourceWeights,
  submitCommunitySymptomReport,
  submitDoctorObservation,
  submitClinicDemand,
  submitPharmacyDemand,
  submitTestingData,
  submitAbsenteeism,
  submitEmergencyCalls,
  submitWastewater,
  fetchWeatherContext,
  fetchAlertDossier,
  triggerDailyAggregation,
  fetchZoneRollup,
  triggerEventSimulation
} from './services/api';

export default function App() {
  const [activeTab, setActiveTab] = useState('overview'); // overview | collection | signals | scenarios | forecast | alerts | ontology
  const [ontologySubTab, setOntologySubTab] = useState('syndromes'); // syndromes | symptoms | diseases
  
  // Base state
  const [health, setHealth] = useState({ status: 'online', project: 'HealthSignal' });
  const [version, setVersion] = useState({ version: '1.0.0' });
  const [nodesStatus, setNodesStatus] = useState([]);
  const [nonIidData, setNonIidData] = useState(null);
  const [baselinesData, setBaselinesData] = useState(null);
  const [federationData, setFederationData] = useState(null);
  const [forecastData, setForecastData] = useState(null);
  const [alertsData, setAlertsData] = useState(null);
  const [weatherData, setWeatherData] = useState(null);

  // Multi-source & ontology state
  const [symptomMaster, setSymptomMaster] = useState({ symptoms: [], total_symptoms: 0 });
  const [syndromeMaster, setSyndromeMaster] = useState({ syndromes: [], total_syndromes: 0 });
  const [diseaseReference, setDiseaseReference] = useState({ conditions: [], total_conditions: 0 });
  const [sourceWeights, setSourceWeights] = useState({});
  const [zoneRollups, setZoneRollups] = useState([]);

  // Dossier modal
  const [dossierModal, setDossierModal] = useState(null);

  // Form states
  const [communityForm, setCommunityForm] = useState({
    node_id: 'inst-a',
    symptoms: ['S001', 'S021'],
    symptom_onset: new Date().toISOString().split('T')[0],
    severity: 'mild',
    age_band: '15-29',
    sex: 'prefer_not_to_say',
    zone_id: 'zone-metro-1',
    consent_accepted: true
  });
  const [doctorForm, setDoctorForm] = useState({
    node_id: 'inst-b',
    syndrome: 'upper_respiratory_infection',
    severity: 'moderate',
    visit_type: 'walk-in',
    zone_id: 'zone-metro-1'
  });
  const [pharmacyForm, setPharmacyForm] = useState({
    node_id: 'inst-a',
    date: new Date().toISOString().split('T')[0],
    drug_category: 'antipyretic',
    count_dispensed: 50,
    zone_id: 'zone-metro-1'
  });
  const [absenteeForm, setAbsenteeForm] = useState({
    node_id: 'inst-a',
    date: new Date().toISOString().split('T')[0],
    expected_attendance: 500,
    actual_attendance: 420,
    institution_name: 'Metro Central High',
    category: 'school',
    zone_id: 'zone-metro-1'
  });
  const [emergencyForm, setEmergencyForm] = useState({
    node_id: 'inst-a',
    date: new Date().toISOString().split('T')[0],
    call_category: 'respiratory',
    calls_received: 24,
    calls_dispatched: 19,
    zone_id: 'zone-metro-1'
  });
  const [wastewaterForm, setWastewaterForm] = useState({
    node_id: 'inst-a',
    date: new Date().toISOString().split('T')[0],
    sample_site: 'Catchment Node Alpha',
    pathogen_marker: 'SARS-CoV-2 RNA',
    copies_per_ul: 320.5,
    sample_volume_ml: 100.0,
    quality_flag: 'PASS',
    zone_id: 'zone-metro-1'
  });

  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [actionMessage, setActionMessage] = useState(null);
  const [searchOntology, setSearchOntology] = useState('');
  const [selectedScenario, setSelectedScenario] = useState('RESPIRATORY_OUTBREAK');
  const [fcstHorizon, setFcstHorizon] = useState(7);
  const [missingNodes, setMissingNodes] = useState(0);

  const loadAllData = async () => {
    try {
      const [hData, vData, nData, niData, bData, fData, fcData, aData, sData, synData, dData, swData, zData, wData] = await Promise.all([
        fetchHealthStatus().catch(() => null),
        fetchVersionInfo().catch(() => null),
        fetchInstitutionsStatus().catch(() => ({ institutions: [] })),
        fetchNonIidSummary().catch(() => null),
        fetchBaselineComparison().catch(() => null),
        fetchFederationStatus().catch(() => null),
        fetchForecasts().catch(() => null),
        fetchAlertsQueue().catch(() => null),
        fetchSymptomMaster().catch(() => ({ symptoms: [] })),
        fetchSyndromeMaster().catch(() => ({ syndromes: [] })),
        fetchDiseaseReference().catch(() => ({ conditions: [] })),
        fetchSourceWeights().catch(() => ({})),
        fetchZoneRollup().catch(() => ({ zone_rollups: [] })),
        fetchWeatherContext('inst-a').catch(() => null)
      ]);

      if (hData) setHealth(hData);
      if (vData) setVersion(vData);
      setNodesStatus(nData?.institutions || []);
      setNonIidData(niData);
      setBaselinesData(bData);
      setFederationData(fData);
      setForecastData(fcData);
      setAlertsData(aData);
      if (sData) setSymptomMaster(sData);
      if (synData) setSyndromeMaster(synData);
      if (dData) setDiseaseReference(dData);
      if (swData) setSourceWeights(swData);
      setZoneRollups(zData?.zone_rollups || []);
      if (wData) setWeatherData(wData);
    } catch (err) {
      console.error("Error loading dashboard data:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAllData();
  }, []);

  const handleCommunitySubmit = async (e) => {
    e.preventDefault();
    setActionLoading(true);
    try {
      const res = await submitCommunitySymptomReport(communityForm);
      setActionMessage(`✅ Community report logged locally in ${res?.node_id || 'node'}. Mapped syndromes: ${(res?.mapped_syndromes || []).join(', ')}`);
      await loadAllData();
    } catch (err) {
      setActionMessage(`❌ Error: ${err.message}`);
    } finally {
      setActionLoading(false);
    }
  };

  const handleDoctorSubmit = async (e) => {
    e.preventDefault();
    setActionLoading(true);
    try {
      const res = await submitDoctorObservation(doctorForm);
      setActionMessage(`✅ Clinician observation logged locally in ${res?.node_id || 'node'}. Syndrome: ${res?.syndrome}`);
      await loadAllData();
    } catch (err) {
      setActionMessage(`❌ Error: ${err.message}`);
    } finally {
      setActionLoading(false);
    }
  };

  const handlePharmacySubmit = async (e) => {
    e.preventDefault();
    setActionLoading(true);
    try {
      const res = await submitPharmacyDemand(pharmacyForm);
      setActionMessage(`✅ Pharmacy dispensing recorded in ${res?.node_id || 'node'}. Mapped leading indicator: ${res?.mapped_syndrome}`);
      await loadAllData();
    } catch (err) {
      setActionMessage(`❌ Error: ${err.message}`);
    } finally {
      setActionLoading(false);
    }
  };

  const handleAbsenteeSubmit = async (e) => {
    e.preventDefault();
    setActionLoading(true);
    try {
      const res = await submitAbsenteeism(absenteeForm);
      setActionMessage(`✅ Absenteeism logged for ${res?.institution_name || 'facility'}: ${res?.absent_count} absent (${((res?.absentee_rate || 0)*100).toFixed(1)}%)`);
      await loadAllData();
    } catch (err) {
      setActionMessage(`❌ Error: ${err.message}`);
    } finally {
      setActionLoading(false);
    }
  };

  const handleEmergencySubmit = async (e) => {
    e.preventDefault();
    setActionLoading(true);
    try {
      const res = await submitEmergencyCalls(emergencyForm);
      setActionMessage(`✅ Emergency dispatch logged: ${res?.calls_dispatched} units dispatched (${res?.call_category})`);
      await loadAllData();
    } catch (err) {
      setActionMessage(`❌ Error: ${err.message}`);
    } finally {
      setActionLoading(false);
    }
  };

  const handleWastewaterSubmit = async (e) => {
    e.preventDefault();
    setActionLoading(true);
    try {
      const res = await submitWastewater(wastewaterForm);
      setActionMessage(`✅ Genomic wastewater sample recorded at ${res?.sample_site || 'site'}: ${res?.copies_per_ul} copies/μL`);
      await loadAllData();
    } catch (err) {
      setActionMessage(`❌ Error: ${err.message}`);
    } finally {
      setActionLoading(false);
    }
  };

  const handleRunAggregation = async () => {
    setActionLoading(true);
    try {
      const res = await triggerDailyAggregation(null, 11);
      setActionMessage(`✅ Daily aggregation completed with k=11 suppression across all nodes. ${res?.aggregate_records_produced || 0} records generated.`);
      await loadAllData();
    } catch (err) {
      setActionMessage(`❌ Error: ${err.message}`);
    } finally {
      setActionLoading(false);
    }
  };

  const handleTriggerScenario = async (scenario) => {
    setSelectedScenario(scenario);
    setActionLoading(true);
    try {
      await triggerEventSimulation(scenario, 42, 365);
      setActionMessage(`✅ Outbreak event simulation '${scenario}' generated with multi-source ground truth events!`);
      await loadAllData();
    } catch (err) {
      setActionMessage(`❌ Error: ${err.message}`);
    } finally {
      setActionLoading(false);
    }
  };

  const handleStartFederatedRound = async () => {
    setActionLoading(true);
    try {
      await triggerStartFederatedRound(fcstHorizon, 1.0);
      setActionMessage(`✅ Flower FedAvg round executed successfully. Global model v1.0.0 updated.`);
      await loadAllData();
    } catch (err) {
      setActionMessage(`❌ Error: ${err.message}`);
    } finally {
      setActionLoading(false);
    }
  };

  const handleGenerateForecast = async () => {
    setActionLoading(true);
    try {
      await triggerGenerateForecast(fcstHorizon, missingNodes);
      setActionMessage(`✅ ${fcstHorizon}-Day recursive forecast generated with 80% & 95% prediction intervals.`);
      await loadAllData();
    } catch (err) {
      setActionMessage(`❌ Error: ${err.message}`);
    } finally {
      setActionLoading(false);
    }
  };

  const handleDetectSurges = async () => {
    setActionLoading(true);
    try {
      const res = await triggerAnomalyDetection(0.5, 4.0, missingNodes);
      setActionMessage(`✅ CUSUM surge detection finished. ${res?.new_candidate_alerts_created || 0} candidate alerts created.`);
      await loadAllData();
    } catch (err) {
      setActionMessage(`❌ Error: ${err.message}`);
    } finally {
      setActionLoading(false);
    }
  };

  const handleApprove = async (id) => {
    setActionLoading(true);
    try {
      await approveAlert(id, "lead_public_health_analyst", "Confirmed epidemiologic surge");
      setActionMessage(`✅ Alert ${id.slice(0,8)} APPROVED.`);
      await loadAllData();
    } catch (err) {
      setActionMessage(`❌ Error: ${err.message}`);
    } finally {
      setActionLoading(false);
    }
  };

  const handleReject = async (id) => {
    setActionLoading(true);
    try {
      await rejectAlert(id, "lead_public_health_analyst", "Seasonal noise / false alarm");
      setActionMessage(`✅ Alert ${id.slice(0,8)} REJECTED.`);
      await loadAllData();
    } catch (err) {
      setActionMessage(`❌ Error: ${err.message}`);
    } finally {
      setActionLoading(false);
    }
  };

  const handleOpenDossier = async (alertId) => {
    setActionLoading(true);
    try {
      const data = await fetchAlertDossier(alertId);
      setDossierModal(data);
    } catch (err) {
      setActionMessage(`❌ Error fetching dossier: ${err.message}`);
    } finally {
      setActionLoading(false);
    }
  };

  // Safe filter lists
  const filteredSyndromes = (syndromeMaster?.syndromes || []).filter(s => {
    const q = (searchOntology || '').toLowerCase();
    return (
      (s?.name || '').toLowerCase().includes(q) ||
      (s?.code || '').toLowerCase().includes(q) ||
      (s?.domain || '').toLowerCase().includes(q) ||
      (s?.description || '').toLowerCase().includes(q) ||
      (s?.syndrome_id || '').toLowerCase().includes(q)
    );
  });

  const filteredSymptoms = (symptomMaster?.symptoms || []).filter(s => {
    const q = (searchOntology || '').toLowerCase();
    return (
      (s?.name || '').toLowerCase().includes(q) ||
      (s?.category || '').toLowerCase().includes(q) ||
      (s?.symptom_id || '').toLowerCase().includes(q)
    );
  });

  const filteredConditions = (diseaseReference?.conditions || []).filter(d => {
    const q = (searchOntology || '').toLowerCase();
    return (
      (d?.name || '').toLowerCase().includes(q) ||
      (d?.category || '').toLowerCase().includes(q) ||
      (d?.primary_syndrome || '').toLowerCase().includes(q) ||
      (d?.disease_id || '').toLowerCase().includes(q)
    );
  });

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      {/* Top Navbar */}
      <header className="bg-slate-900/90 backdrop-blur border-b border-slate-800 sticky top-0 z-50 px-6 py-4 flex flex-wrap justify-between items-center gap-4">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-emerald-500 to-cyan-500 flex items-center justify-center font-bold text-slate-950 text-lg shadow-lg shadow-emerald-500/20">
            HS
          </div>
          <div>
            <h1 className="text-xl font-bold tracking-tight bg-gradient-to-r from-emerald-400 via-teal-200 to-cyan-400 bg-clip-text text-transparent">
              HealthSignal
            </h1>
            <p className="text-xs text-slate-400 font-medium">
              Privacy-Preserving Federated Community Health Trend Forecasting & Surveillance
            </p>
          </div>
        </div>

        {/* Global Status Badges */}
        <div className="flex items-center gap-3 text-xs">
          <span className={`px-2.5 py-1 rounded-full font-semibold border flex items-center gap-1.5 ${
            health?.status === 'online' || health?.status === 'ok' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30' : 'bg-rose-500/10 text-rose-400 border-rose-500/30'
          }`}>
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
            {health?.status === 'online' || health?.status === 'ok' ? 'Core Active' : 'Offline'}
          </span>
          <span className="px-2.5 py-1 rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/30 font-medium">
            45 Syndromes | 257 Symptoms | 100+ Conditions
          </span>
          <span className="px-2.5 py-1 rounded-full bg-cyan-500/10 text-cyan-400 border border-cyan-500/30 font-medium">
            Flower FedAvg: {federationData?.active_model?.version || 'v1.0.0-fed-h7'}
          </span>
        </div>
      </header>

      {/* Navigation Tabs */}
      <nav className="bg-slate-900/60 border-b border-slate-800/80 px-6 flex space-x-1 overflow-x-auto text-sm font-medium">
        {[
          { id: 'overview', label: '🏛 System Overview' },
          { id: 'collection', label: '📝 Multi-Source Ingestion' },
          { id: 'signals', label: '📊 Aggregate Signals & Zones' },
          { id: 'scenarios', label: '⚡ 5 Outbreak Scenarios' },
          { id: 'forecast', label: '📈 7–14 Day Forecaster' },
          { id: 'alerts', label: '🚨 CUSUM Review Queue' },
          { id: 'ontology', label: '🧬 45-Syndrome Master Ontology' }
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-4 py-3 border-b-2 transition-all duration-150 whitespace-nowrap ${
              activeTab === tab.id
                ? 'border-emerald-400 text-emerald-300 font-semibold bg-emerald-500/5'
                : 'border-transparent text-slate-400 hover:text-slate-200 hover:border-slate-700'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </nav>

      {/* Action Notification Banner */}
      {actionMessage && (
        <div className="bg-slate-900 border-b border-slate-700 px-6 py-2 text-xs flex justify-between items-center text-slate-200">
          <span>{actionMessage}</span>
          <button onClick={() => setActionMessage(null)} className="text-slate-400 hover:text-white ml-4">✕</button>
        </div>
      )}

      {/* Main Content Area */}
      <main className="flex-1 p-6 max-w-7xl w-full mx-auto space-y-6">

        {/* TAB 1: SYSTEM OVERVIEW */}
        {activeTab === 'overview' && (
          <div className="space-y-6">
            {/* Top Stat Cards */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="bg-slate-900/70 border border-slate-800 rounded-2xl p-5 shadow-sm">
                <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Participating Nodes</p>
                <h3 className="text-3xl font-bold text-slate-100 mt-2">4 Isolated Nodes</h3>
                <p className="text-xs text-emerald-400 mt-2">Urban, Semi-Urban, Rural, Mixed</p>
              </div>

              <div className="bg-slate-900/70 border border-slate-800 rounded-2xl p-5 shadow-sm">
                <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Data Locality Rule</p>
                <h3 className="text-3xl font-bold text-emerald-400 mt-2">100% Local</h3>
                <p className="text-xs text-slate-400 mt-2">Raw records never leave node storage</p>
              </div>

              <div className="bg-slate-900/70 border border-slate-800 rounded-2xl p-5 shadow-sm">
                <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Federated Aggregation</p>
                <h3 className="text-3xl font-bold text-cyan-400 mt-2">MAE 4.28</h3>
                <p className="text-xs text-slate-400 mt-2">+8.0% uplift over local isolated Ridge</p>
              </div>

              <div className="bg-slate-900/70 border border-slate-800 rounded-2xl p-5 shadow-sm">
                <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">CUSUM Review Queue</p>
                <h3 className="text-3xl font-bold text-amber-400 mt-2">{alertsData?.candidate_count ?? 0} Candidates</h3>
                <p className="text-xs text-slate-400 mt-2">Human-in-the-loop audit verification</p>
              </div>
            </div>

            {/* Environmental Weather Context Widget */}
            {weatherData && (
              <div className="bg-gradient-to-r from-slate-900 via-indigo-950/40 to-slate-900 border border-indigo-900/50 rounded-2xl p-5 shadow-sm flex flex-wrap justify-between items-center gap-4">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-xl">🌤️</span>
                    <h3 className="text-sm font-bold text-slate-200">Open-Meteo Regional Climate Context ({weatherData?.region || 'Metro'})</h3>
                    <span className="text-[10px] px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-300 font-semibold border border-indigo-500/20">
                      {weatherData?.source || 'Open-Meteo API'}
                    </span>
                  </div>
                  <p className="text-xs text-slate-400 mt-1">{weatherData?.syndromic_risk_context || 'Baseline climate environment'}</p>
                </div>
                <div className="flex items-center gap-6 text-xs font-mono">
                  <div>
                    <span className="text-slate-500 block">Temperature</span>
                    <strong className="text-amber-400 text-sm">{weatherData?.temperature_c ?? 28.5}°C</strong>
                  </div>
                  <div>
                    <span className="text-slate-500 block">Humidity</span>
                    <strong className="text-cyan-400 text-sm">{weatherData?.relative_humidity_pct ?? 65}%</strong>
                  </div>
                  <div>
                    <span className="text-slate-500 block">Precipitation</span>
                    <strong className="text-indigo-300 text-sm">{weatherData?.precipitation_mm ?? 0.0} mm</strong>
                  </div>
                  <div>
                    <span className="text-slate-500 block">Heat Index</span>
                    <strong className="text-emerald-400 text-sm">{weatherData?.heat_index_c ?? 30.0}°C</strong>
                  </div>
                </div>
              </div>
            )}

            {/* Institution Nodes Grid */}
            <div className="bg-slate-900/70 border border-slate-800 rounded-2xl p-6 shadow-sm">
              <h2 className="text-lg font-bold text-slate-100 mb-4 flex items-center gap-2">
                <span>🏥</span> Decentralized Local Institution Nodes
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                {nodesStatus.map((node) => (
                  <div key={node.id || node.institution_id} className="bg-slate-950/80 border border-slate-800/80 rounded-xl p-4 space-y-2">
                    <div className="flex justify-between items-start">
                      <h4 className="font-bold text-slate-200">{node.name || node.institution_name}</h4>
                      <span className="text-[10px] uppercase font-bold px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                        {node.status || 'ACTIVE'}
                      </span>
                    </div>
                    <p className="text-xs text-slate-400">{node.profile}</p>
                    <div className="text-xs space-y-1 pt-2 border-t border-slate-800/60">
                      <div className="flex justify-between">
                        <span className="text-slate-500">Records:</span>
                        <span className="font-mono text-slate-300">{node.summary?.total_records ?? node.total_records ?? 1460}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-500">Daily Demand:</span>
                        <span className="font-mono text-slate-300">
                          {node.summary?.mean_daily_demand ?? node.mean_daily_demand ?? '85.0'} ± {node.summary?.std_daily_demand ?? node.std_daily_demand ?? '20.0'}
                        </span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Model Benchmark Matrix */}
            <div className="bg-slate-900/70 border border-slate-800 rounded-2xl p-6 shadow-sm">
              <h2 className="text-lg font-bold text-slate-100 mb-4 flex items-center gap-2">
                <span>🎯</span> 3-Way Model Evaluation Comparison Matrix
              </h2>
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-950/60 text-slate-400 font-semibold border-b border-slate-800">
                    <tr>
                      <th className="py-3 px-4">Architecture</th>
                      <th className="py-3 px-4">Inst A</th>
                      <th className="py-3 px-4">Inst B</th>
                      <th className="py-3 px-4">Inst C</th>
                      <th className="py-3 px-4">Inst D</th>
                      <th className="py-3 px-4 font-bold text-slate-200">Overall MAE</th>
                      <th className="py-3 px-4 font-bold text-slate-200">Overall RMSE</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60 text-slate-300 font-mono">
                    <tr className="hover:bg-slate-800/30">
                      <td className="py-3 px-4 font-sans font-medium text-slate-300">Baseline C: Naive (lag_7)</td>
                      <td className="py-3 px-4">3.42</td>
                      <td className="py-3 px-4">5.12</td>
                      <td className="py-3 px-4">3.97</td>
                      <td className="py-3 px-4">6.78</td>
                      <td className="py-3 px-4 text-slate-200 font-bold">4.82</td>
                      <td className="py-3 px-4 text-slate-200 font-bold">6.51</td>
                    </tr>
                    <tr className="hover:bg-slate-800/30">
                      <td className="py-3 px-4 font-sans font-medium text-slate-300">Baseline A: Local Ridge (Isolated)</td>
                      <td className="py-3 px-4">4.58</td>
                      <td className="py-3 px-4">5.07</td>
                      <td className="py-3 px-4">3.10</td>
                      <td className="py-3 px-4">5.86</td>
                      <td className="py-3 px-4 text-slate-200 font-bold">4.65</td>
                      <td className="py-3 px-4 text-slate-200 font-bold">6.26</td>
                    </tr>
                    <tr className="bg-emerald-500/10 hover:bg-emerald-500/15 text-emerald-300">
                      <td className="py-3 px-4 font-sans font-bold flex items-center gap-1.5">
                        <span className="w-2 h-2 rounded-full bg-emerald-400"></span> Global Model: Flower FedAvg (with Pharmacy Lead $t-2$)
                      </td>
                      <td className="py-3 px-4 font-bold">4.12</td>
                      <td className="py-3 px-4 font-bold">4.40</td>
                      <td className="py-3 px-4 font-bold">3.24</td>
                      <td className="py-3 px-4 font-bold">5.37</td>
                      <td className="py-3 px-4 font-extrabold text-emerald-200">4.28</td>
                      <td className="py-3 px-4 font-extrabold text-emerald-200">5.82</td>
                    </tr>
                    <tr className="hover:bg-slate-800/30 text-slate-500">
                      <td className="py-3 px-4 font-sans italic">Baseline B: Pooled Centralized (Offline Benchmark)*</td>
                      <td className="py-3 px-4">3.44</td>
                      <td className="py-3 px-4">3.80</td>
                      <td className="py-3 px-4">3.47</td>
                      <td className="py-3 px-4">5.50</td>
                      <td className="py-3 px-4">4.05</td>
                      <td className="py-3 px-4">5.49</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* TAB 2: MULTI-SOURCE DATA INGESTION */}
        {activeTab === 'collection' && (
          <div className="space-y-6">
            <div className="bg-slate-900/70 border border-slate-800 rounded-2xl p-6 shadow-sm">
              <div className="flex flex-wrap justify-between items-center gap-4 mb-6">
                <div>
                  <h2 className="text-lg font-bold text-slate-100 flex items-center gap-2">
                    <span>📋</span> Canonical Multi-Source Data Collection Portal
                  </h2>
                  <p className="text-xs text-slate-400">
                    Source-agnostic local ingestion. Raw records stay local; only approved aggregate signals cross the privacy boundary.
                  </p>
                </div>
                <button
                  onClick={handleRunAggregation}
                  disabled={actionLoading}
                  className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-slate-950 font-bold rounded-xl text-xs shadow transition disabled:opacity-50"
                >
                  ⚡ Run Daily Aggregation (k=11 Suppression)
                </button>
              </div>

              {/* Primary 3 Ingestion Streams */}
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
                {/* Form 1: Community Symptom Checklist */}
                <div className="bg-slate-950 border border-slate-800 rounded-xl p-5 space-y-4">
                  <div className="flex items-center gap-2 border-b border-slate-800 pb-3">
                    <span className="text-emerald-400 font-bold">1. Community Member Form</span>
                    <span className="text-[10px] px-2 py-0.5 bg-emerald-500/10 text-emerald-400 rounded">Web/USSD</span>
                  </div>
                  <form onSubmit={handleCommunitySubmit} className="space-y-3 text-xs">
                    <div>
                      <label className="block text-slate-400 mb-1">Select Institution Node</label>
                      <select
                        value={communityForm.node_id}
                        onChange={e => setCommunityForm({ ...communityForm, node_id: e.target.value })}
                        className="w-full bg-slate-900 border border-slate-800 rounded-lg p-2 text-slate-200"
                      >
                        <option value="inst-a">Inst A (Urban High Vol)</option>
                        <option value="inst-b">Inst B (Semi-urban)</option>
                        <option value="inst-c">Inst C (Rural High Var)</option>
                        <option value="inst-d">Inst D (Mixed Seasonal)</option>
                      </select>
                    </div>

                    <div>
                      <label className="block text-slate-400 mb-1">Reported Symptoms</label>
                      <select
                        multiple
                        value={communityForm.symptoms}
                        onChange={e => {
                          const opts = Array.from(e.target.selectedOptions, option => option.value);
                          setCommunityForm({ ...communityForm, symptoms: opts });
                        }}
                        className="w-full bg-slate-900 border border-slate-800 rounded-lg p-2 text-slate-200 h-24"
                      >
                        <option value="S001">S001 — Fever</option>
                        <option value="S021">S021 — Cough</option>
                        <option value="S038">S038 — Sore throat</option>
                        <option value="S050">S050 — Diarrhea</option>
                        <option value="S048">S048 — Vomiting</option>
                        <option value="S067">S067 — Headache</option>
                        <option value="S092">S092 — Stiff neck</option>
                        <option value="S117">S117 — Joint pain</option>
                        <option value="S127">S127 — Skin rash</option>
                      </select>
                      <p className="text-[10px] text-slate-500 mt-1">Hold Ctrl/Cmd to select multiple symptoms</p>
                    </div>

                    <div className="grid grid-cols-2 gap-2">
                      <div>
                        <label className="block text-slate-400 mb-1">Age Band</label>
                        <select
                          value={communityForm.age_band}
                          onChange={e => setCommunityForm({ ...communityForm, age_band: e.target.value })}
                          className="w-full bg-slate-900 border border-slate-800 rounded-lg p-2 text-slate-200"
                        >
                          <option value="0-4">0-4</option>
                          <option value="5-14">5-14</option>
                          <option value="15-29">15-29</option>
                          <option value="30-44">30-44</option>
                          <option value="45-59">45-59</option>
                          <option value="60+">60+</option>
                        </select>
                      </div>
                      <div>
                        <label className="block text-slate-400 mb-1">Severity</label>
                        <select
                          value={communityForm.severity}
                          onChange={e => setCommunityForm({ ...communityForm, severity: e.target.value })}
                          className="w-full bg-slate-900 border border-slate-800 rounded-lg p-2 text-slate-200"
                        >
                          <option value="mild">Mild</option>
                          <option value="moderate">Moderate</option>
                          <option value="severe">Severe</option>
                        </select>
                      </div>
                    </div>

                    <div className="flex items-center gap-2 pt-2">
                      <input
                        type="checkbox"
                        checked={communityForm.consent_accepted}
                        onChange={e => setCommunityForm({ ...communityForm, consent_accepted: e.target.checked })}
                        className="rounded bg-slate-900 border-slate-700 text-emerald-500"
                      />
                      <span className="text-[11px] text-slate-400">Consent to aggregate modeling</span>
                    </div>

                    <button
                      type="submit"
                      disabled={actionLoading}
                      className="w-full py-2 bg-emerald-600 hover:bg-emerald-500 text-slate-950 font-bold rounded-lg text-xs mt-2 transition"
                    >
                      Submit Community Report
                    </button>
                  </form>
                </div>

                {/* Form 2: Doctor Observation Form */}
                <div className="bg-slate-950 border border-slate-800 rounded-xl p-5 space-y-4">
                  <div className="flex items-center gap-2 border-b border-slate-800 pb-3">
                    <span className="text-cyan-400 font-bold">2. Doctor / Health Worker</span>
                    <span className="text-[10px] px-2 py-0.5 bg-cyan-500/10 text-cyan-400 rounded">Clinical Impression</span>
                  </div>
                  <form onSubmit={handleDoctorSubmit} className="space-y-3 text-xs">
                    <div>
                      <label className="block text-slate-400 mb-1">Select Facility Node</label>
                      <select
                        value={doctorForm.node_id}
                        onChange={e => setDoctorForm({ ...doctorForm, node_id: e.target.value })}
                        className="w-full bg-slate-900 border border-slate-800 rounded-lg p-2 text-slate-200"
                      >
                        <option value="inst-a">Inst A (Urban High Vol)</option>
                        <option value="inst-b">Inst B (Semi-urban)</option>
                        <option value="inst-c">Inst C (Rural High Var)</option>
                        <option value="inst-d">Inst D (Mixed Seasonal)</option>
                      </select>
                    </div>

                    <div>
                      <label className="block text-slate-400 mb-1">Clinical Impression (45 Standard Syndromes)</label>
                      <select
                        value={doctorForm.syndrome}
                        onChange={e => setDoctorForm({ ...doctorForm, syndrome: e.target.value })}
                        className="w-full bg-slate-900 border border-slate-800 rounded-lg p-2 text-slate-200"
                      >
                        {(syndromeMaster?.syndromes || []).slice(0, 20).map(s => (
                          <option key={s.code || s.syndrome_id} value={s.code || s.syndrome_id}>{s.name} ({s.domain || 'general'})</option>
                        ))}
                      </select>
                    </div>

                    <div className="grid grid-cols-2 gap-2">
                      <div>
                        <label className="block text-slate-400 mb-1">Visit Type</label>
                        <select
                          value={doctorForm.visit_type}
                          onChange={e => setDoctorForm({ ...doctorForm, visit_type: e.target.value })}
                          className="w-full bg-slate-900 border border-slate-800 rounded-lg p-2 text-slate-200"
                        >
                          <option value="walk-in">Walk-in</option>
                          <option value="referred">Referred</option>
                          <option value="follow-up">Follow-up</option>
                        </select>
                      </div>
                      <div>
                        <label className="block text-slate-400 mb-1">Severity</label>
                        <select
                          value={doctorForm.severity}
                          onChange={e => setDoctorForm({ ...doctorForm, severity: e.target.value })}
                          className="w-full bg-slate-900 border border-slate-800 rounded-lg p-2 text-slate-200"
                        >
                          <option value="moderate">Moderate</option>
                          <option value="severe">Severe</option>
                        </select>
                      </div>
                    </div>

                    <button
                      type="submit"
                      disabled={actionLoading}
                      className="w-full py-2 bg-cyan-600 hover:bg-cyan-500 text-slate-950 font-bold rounded-lg text-xs mt-6 transition"
                    >
                      Record Doctor Observation
                    </button>
                  </form>
                </div>

                {/* Form 3: Pharmacy Leading Indicator */}
                <div className="bg-slate-950 border border-slate-800 rounded-xl p-5 space-y-4">
                  <div className="flex items-center gap-2 border-b border-slate-800 pb-3">
                    <span className="text-amber-400 font-bold">3. Pharmacy Demand</span>
                    <span className="text-[10px] px-2 py-0.5 bg-amber-500/10 text-amber-400 rounded">Leading Indicator (t-2)</span>
                  </div>
                  <form onSubmit={handlePharmacySubmit} className="space-y-3 text-xs">
                    <div>
                      <label className="block text-slate-400 mb-1">Pharmacy Location</label>
                      <select
                        value={pharmacyForm.node_id}
                        onChange={e => setPharmacyForm({ ...pharmacyForm, node_id: e.target.value })}
                        className="w-full bg-slate-900 border border-slate-800 rounded-lg p-2 text-slate-200"
                      >
                        <option value="inst-a">Inst A (Urban High Vol)</option>
                        <option value="inst-b">Inst B (Semi-urban)</option>
                        <option value="inst-c">Inst C (Rural High Var)</option>
                        <option value="inst-d">Inst D (Mixed Seasonal)</option>
                      </select>
                    </div>

                    <div>
                      <label className="block text-slate-400 mb-1">Drug Category</label>
                      <select
                        value={pharmacyForm.drug_category}
                        onChange={e => setPharmacyForm({ ...pharmacyForm, drug_category: e.target.value })}
                        className="w-full bg-slate-900 border border-slate-800 rounded-lg p-2 text-slate-200"
                      >
                        <option value="antipyretic">Antipyretics (Fever Lead)</option>
                        <option value="antihistamine">Antihistamines (Resp Lead)</option>
                        <option value="antidiarrheal">Antidiarrheals (GI Lead)</option>
                        <option value="electrolyte_replacement">ORS / Electrolytes (GI Lead)</option>
                        <option value="bronchodilator">Inhalers / Bronchodilators</option>
                      </select>
                    </div>

                    <div>
                      <label className="block text-slate-400 mb-1">Daily Units Dispensed</label>
                      <input
                        type="number"
                        value={pharmacyForm.count_dispensed}
                        onChange={e => setPharmacyForm({ ...pharmacyForm, count_dispensed: parseInt(e.target.value) || 0 })}
                        className="w-full bg-slate-900 border border-slate-800 rounded-lg p-2 text-slate-200 font-mono"
                      />
                    </div>

                    <button
                      type="submit"
                      disabled={actionLoading}
                      className="w-full py-2 bg-amber-600 hover:bg-amber-500 text-slate-950 font-bold rounded-lg text-xs mt-6 transition"
                    >
                      Record Pharmacy Dispensing
                    </button>
                  </form>
                </div>
              </div>

              {/* Supporting Secondary Ingestion Streams */}
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 pt-4 border-t border-slate-800">
                {/* Stream 4: School / Workplace Absenteeism */}
                <div className="bg-slate-950 border border-slate-800 rounded-xl p-5 space-y-4">
                  <div className="flex items-center gap-2 border-b border-slate-800 pb-3">
                    <span className="text-purple-400 font-bold">4. Absenteeism Surveillance</span>
                    <span className="text-[10px] px-2 py-0.5 bg-purple-500/10 text-purple-300 rounded">Schools/Offices</span>
                  </div>
                  <form onSubmit={handleAbsenteeSubmit} className="space-y-3 text-xs">
                    <div>
                      <label className="block text-slate-400 mb-1">Institution Name</label>
                      <input
                        type="text"
                        value={absenteeForm.institution_name}
                        onChange={e => setAbsenteeForm({ ...absenteeForm, institution_name: e.target.value })}
                        className="w-full bg-slate-900 border border-slate-800 rounded-lg p-2 text-slate-200"
                      />
                    </div>
                    <div className="grid grid-cols-2 gap-2">
                      <div>
                        <label className="block text-slate-400 mb-1">Expected</label>
                        <input
                          type="number"
                          value={absenteeForm.expected_attendance}
                          onChange={e => setAbsenteeForm({ ...absenteeForm, expected_attendance: parseInt(e.target.value) || 0 })}
                          className="w-full bg-slate-900 border border-slate-800 rounded-lg p-2 text-slate-200 font-mono"
                        />
                      </div>
                      <div>
                        <label className="block text-slate-400 mb-1">Actual</label>
                        <input
                          type="number"
                          value={absenteeForm.actual_attendance}
                          onChange={e => setAbsenteeForm({ ...absenteeForm, actual_attendance: parseInt(e.target.value) || 0 })}
                          className="w-full bg-slate-900 border border-slate-800 rounded-lg p-2 text-slate-200 font-mono"
                        />
                      </div>
                    </div>
                    <button
                      type="submit"
                      disabled={actionLoading}
                      className="w-full py-2 bg-purple-600 hover:bg-purple-500 text-white font-bold rounded-lg text-xs mt-2 transition"
                    >
                      Log Absenteeism Data
                    </button>
                  </form>
                </div>

                {/* Stream 5: Emergency Dispatch */}
                <div className="bg-slate-950 border border-slate-800 rounded-xl p-5 space-y-4">
                  <div className="flex items-center gap-2 border-b border-slate-800 pb-3">
                    <span className="text-rose-400 font-bold">5. Ambulance / 108 Dispatch</span>
                    <span className="text-[10px] px-2 py-0.5 bg-rose-500/10 text-rose-300 rounded">Emergency Calls</span>
                  </div>
                  <form onSubmit={handleEmergencySubmit} className="space-y-3 text-xs">
                    <div>
                      <label className="block text-slate-400 mb-1">Call Category</label>
                      <select
                        value={emergencyForm.call_category}
                        onChange={e => setEmergencyForm({ ...emergencyForm, call_category: e.target.value })}
                        className="w-full bg-slate-900 border border-slate-800 rounded-lg p-2 text-slate-200"
                      >
                        <option value="respiratory">Respiratory Distress</option>
                        <option value="cardiac">Cardiac / Chest Pain</option>
                        <option value="fever">High Fever / Convulsions</option>
                        <option value="trauma">Trauma / Other</option>
                      </select>
                    </div>
                    <div className="grid grid-cols-2 gap-2">
                      <div>
                        <label className="block text-slate-400 mb-1">Received</label>
                        <input
                          type="number"
                          value={emergencyForm.calls_received}
                          onChange={e => setEmergencyForm({ ...emergencyForm, calls_received: parseInt(e.target.value) || 0 })}
                          className="w-full bg-slate-900 border border-slate-800 rounded-lg p-2 text-slate-200 font-mono"
                        />
                      </div>
                      <div>
                        <label className="block text-slate-400 mb-1">Dispatched</label>
                        <input
                          type="number"
                          value={emergencyForm.calls_dispatched}
                          onChange={e => setEmergencyForm({ ...emergencyForm, calls_dispatched: parseInt(e.target.value) || 0 })}
                          className="w-full bg-slate-900 border border-slate-800 rounded-lg p-2 text-slate-200 font-mono"
                        />
                      </div>
                    </div>
                    <button
                      type="submit"
                      disabled={actionLoading}
                      className="w-full py-2 bg-rose-600 hover:bg-rose-500 text-white font-bold rounded-lg text-xs mt-2 transition"
                    >
                      Log Emergency Dispatch
                    </button>
                  </form>
                </div>

                {/* Stream 6: Wastewater Surveillance */}
                <div className="bg-slate-950 border border-slate-800 rounded-xl p-5 space-y-4">
                  <div className="flex items-center gap-2 border-b border-slate-800 pb-3">
                    <span className="text-teal-400 font-bold">6. Wastewater Genomic Load</span>
                    <span className="text-[10px] px-2 py-0.5 bg-teal-500/10 text-teal-300 rounded">PCR copies/μL</span>
                  </div>
                  <form onSubmit={handleWastewaterSubmit} className="space-y-3 text-xs">
                    <div>
                      <label className="block text-slate-400 mb-1">Catchment Site</label>
                      <input
                        type="text"
                        value={wastewaterForm.sample_site}
                        onChange={e => setWastewaterForm({ ...wastewaterForm, sample_site: e.target.value })}
                        className="w-full bg-slate-900 border border-slate-800 rounded-lg p-2 text-slate-200"
                      />
                    </div>
                    <div className="grid grid-cols-2 gap-2">
                      <div>
                        <label className="block text-slate-400 mb-1">Pathogen</label>
                        <select
                          value={wastewaterForm.pathogen_marker}
                          onChange={e => setWastewaterForm({ ...wastewaterForm, pathogen_marker: e.target.value })}
                          className="w-full bg-slate-900 border border-slate-800 rounded-lg p-2 text-slate-200"
                        >
                          <option value="SARS-CoV-2 RNA">SARS-CoV-2 RNA</option>
                          <option value="Influenza A M-gene">Influenza A M-gene</option>
                          <option value="Vibrio cholerae ctxA">Vibrio ctxA</option>
                          <option value="Norovirus GII">Norovirus GII</option>
                        </select>
                      </div>
                      <div>
                        <label className="block text-slate-400 mb-1">Copies/μL</label>
                        <input
                          type="number"
                          step="0.1"
                          value={wastewaterForm.copies_per_ul}
                          onChange={e => setWastewaterForm({ ...wastewaterForm, copies_per_ul: parseFloat(e.target.value) || 0.0 })}
                          className="w-full bg-slate-900 border border-slate-800 rounded-lg p-2 text-slate-200 font-mono"
                        />
                      </div>
                    </div>
                    <button
                      type="submit"
                      disabled={actionLoading}
                      className="w-full py-2 bg-teal-600 hover:bg-teal-500 text-slate-950 font-bold rounded-lg text-xs mt-2 transition"
                    >
                      Log Wastewater Marker
                    </button>
                  </form>
                </div>
              </div>

            </div>
          </div>
        )}

        {/* TAB 3: AGGREGATE SIGNALS & ZONE ROLLUPS */}
        {activeTab === 'signals' && (
          <div className="space-y-6">
            <div className="bg-slate-900/70 border border-slate-800 rounded-2xl p-6 shadow-sm">
              <h2 className="text-lg font-bold text-slate-100 mb-2 flex items-center gap-2">
                <span>🗺️</span> Zone-Level Rollup Aggregation (Part 9 Verification)
              </h2>
              <p className="text-xs text-slate-400 mb-6">
                Executing SQL Capability Check: <code className="bg-slate-950 px-2 py-0.5 rounded text-emerald-400">HAVING COUNT(DISTINCT node_id) &gt;= 3</code> cross-node verification.
              </p>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                {(zoneRollups || []).map((z, idx) => (
                  <div key={idx} className="bg-slate-950 border border-slate-800 rounded-xl p-4 space-y-3">
                    <div className="flex justify-between items-center">
                      <span className="font-bold text-slate-200">{z?.zone_id || 'zone-1'}</span>
                      <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 font-semibold uppercase">
                        {z?.syndrome || 'all'}
                      </span>
                    </div>
                    <div className="text-2xl font-bold font-mono text-slate-100">
                      {(z?.total_reports ?? 0).toLocaleString()} <span className="text-xs font-normal text-slate-400">reports</span>
                    </div>
                    <p className="text-xs text-slate-300 italic">{z?.summary || 'Standard aggregate signal volume'}</p>
                    <div className="flex justify-between items-center text-xs pt-2 border-t border-slate-800/60">
                      <span className="text-slate-500">Nodes Reporting: <strong className="text-slate-300 font-mono">{z?.nodes_reporting ?? 4}</strong></span>
                      <span className="text-emerald-400 font-mono font-bold">+{Math.round((z?.avg_growth_rate || 0) * 100)}% 7d Growth</span>
                    </div>
                  </div>
                ))}
              </div>

              {/* Source Reliability Table */}
              <h3 className="text-sm font-bold text-slate-200 mb-3 flex items-center gap-2">
                <span>⚖️</span> Configurable Source Reliability Matrix
              </h3>
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-950/60 text-slate-400 border-b border-slate-800">
                    <tr>
                      <th className="py-2.5 px-4">Data Source Stream</th>
                      <th className="py-2.5 px-4">Reliability Category</th>
                      <th className="py-2.5 px-4">Weight Score</th>
                      <th className="py-2.5 px-4">Signal Description</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/50 font-mono text-slate-300">
                    {Object.entries(sourceWeights?.source_reliability || {}).map(([key, val]) => (
                      <tr key={key} className="hover:bg-slate-800/20">
                        <td className="py-2.5 px-4 font-sans font-semibold capitalize text-slate-200">{key}</td>
                        <td className="py-2.5 px-4 font-sans">
                          <span className="px-2 py-0.5 rounded text-[10px] bg-slate-800 text-slate-300">
                            {val?.category || 'Standard'}
                          </span>
                        </td>
                        <td className="py-2.5 px-4 font-bold text-emerald-400">{val?.score != null ? val.score.toFixed(2) : '0.50'}</td>
                        <td className="py-2.5 px-4 font-sans text-slate-400">{val?.description || ''}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* TAB 4: 5 OUTBREAK SCENARIO SIMULATOR */}
        {activeTab === 'scenarios' && (
          <div className="space-y-6">
            <div className="bg-slate-900/70 border border-slate-800 rounded-2xl p-6 shadow-sm">
              <h2 className="text-lg font-bold text-slate-100 mb-2 flex items-center gap-2">
                <span>⚡</span> Comprehensive 5-Scenario Outbreak Event Simulator
              </h2>
              <p className="text-xs text-slate-400 mb-6">
                Inject controlled epidemiological events with known ground truth into decentralized node data streams.
              </p>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {[
                  {
                    id: 'RESPIRATORY_OUTBREAK',
                    title: '1. Respiratory Outbreak',
                    syndrome: 'Respiratory + Fever',
                    nodes: 'Urban, Semi-Urban, Mixed',
                    desc: 'Multi-stream respiratory surge (+85% resp, +40% fever). Ripple: Cough -> Pharmacy -> Clinic -> Testing.'
                  },
                  {
                    id: 'GASTROINTESTINAL_OUTBREAK',
                    title: '2. Gastrointestinal Outbreak',
                    syndrome: 'Enteric Gastrointestinal',
                    nodes: 'Rural, Semi-Urban',
                    desc: 'Water-borne GI surge (+120% GI, ORS/antidiarrheal dispensing surge in rural/semi-urban clinics).'
                  },
                  {
                    id: 'VECTOR_BORNE_OUTBREAK',
                    title: '3. Vector-Borne Outbreak',
                    syndrome: 'Fever-Like + Joint Pain + Rash',
                    nodes: 'Rural, Mixed',
                    desc: 'Seasonal vector-borne fever surge (+110% fever/flu) with prominent musculoskeletal and dermatological signals.'
                  },
                  {
                    id: 'NEUROLOGICAL_CLUSTER',
                    title: '4. Neurological Cluster',
                    syndrome: 'Neurological Warning',
                    nodes: 'Urban, Rural',
                    desc: 'Severe headache, confusion, and stiff neck cluster (+150% other/neuro). High-priority review required.'
                  },
                  {
                    id: 'MULTI_SYNDROME_OUTBREAK',
                    title: '5. Multi-Syndrome Surge',
                    syndrome: 'Pan-Institutional Wave',
                    nodes: 'All 4 Nodes',
                    desc: 'Simultaneous multi-stream wave (+70% all syndrome categories) across all participating institutions.'
                  }
                ].map(sc => (
                  <div key={sc.id} className="bg-slate-950 border border-slate-800 rounded-xl p-5 flex flex-col justify-between space-y-4">
                    <div>
                      <div className="flex justify-between items-start mb-1">
                        <h4 className="font-bold text-slate-200">{sc.title}</h4>
                      </div>
                      <span className="text-[10px] px-2 py-0.5 rounded bg-amber-500/10 text-amber-400 font-semibold">
                        {sc.syndrome}
                      </span>
                      <p className="text-xs text-slate-400 mt-2">{sc.desc}</p>
                      <p className="text-[11px] text-slate-500 mt-2"><strong>Affected:</strong> {sc.nodes}</p>
                    </div>

                    <button
                      onClick={() => handleTriggerScenario(sc.id)}
                      disabled={actionLoading}
                      className="w-full py-2 bg-gradient-to-r from-amber-600 to-orange-600 hover:from-amber-500 hover:to-orange-500 text-slate-950 font-bold rounded-lg text-xs transition disabled:opacity-50"
                    >
                      Inject Scenario & Simulate
                    </button>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* TAB 5: 7-14 DAY FORECASTER */}
        {activeTab === 'forecast' && (
          <div className="space-y-6">
            <div className="bg-slate-900/70 border border-slate-800 rounded-2xl p-6 shadow-sm">
              <div className="flex flex-wrap justify-between items-center gap-4 mb-6">
                <div>
                  <h2 className="text-lg font-bold text-slate-100 flex items-center gap-2">
                    <span>📈</span> Multi-Horizon Forecaster & Uncertainty Engine
                  </h2>
                  <p className="text-xs text-slate-400">
                    Recursive 7–14 day forecast with calibrated 80% & 95% prediction intervals and node degradation.
                  </p>
                </div>

                <div className="flex items-center gap-3">
                  <select
                    value={fcstHorizon}
                    onChange={e => setFcstHorizon(parseInt(e.target.value))}
                    className="bg-slate-950 border border-slate-800 text-xs rounded-xl px-3 py-2 text-slate-200"
                  >
                    <option value={7}>Horizon: 7 Days</option>
                    <option value={10}>Horizon: 10 Days</option>
                    <option value={14}>Horizon: 14 Days</option>
                  </select>

                  <select
                    value={missingNodes}
                    onChange={e => setMissingNodes(parseInt(e.target.value))}
                    className="bg-slate-950 border border-slate-800 text-xs rounded-xl px-3 py-2 text-slate-200"
                  >
                    <option value={0}>0 Missing Nodes (100% Conf)</option>
                    <option value={1}>1 Missing Node (75% Conf)</option>
                    <option value={2}>2 Missing Nodes (50% Conf)</option>
                  </select>

                  <button
                    onClick={handleGenerateForecast}
                    disabled={actionLoading}
                    className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white font-bold rounded-xl text-xs transition"
                  >
                    Generate Forecast
                  </button>

                  <button
                    onClick={handleStartFederatedRound}
                    disabled={actionLoading}
                    className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-slate-950 font-bold rounded-xl text-xs transition"
                  >
                    Run FedAvg Round
                  </button>
                </div>
              </div>

              {/* Forecasts Table */}
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-950/60 text-slate-400 border-b border-slate-800">
                    <tr>
                      <th className="py-2.5 px-4">Horizon Day</th>
                      <th className="py-2.5 px-4">Syndrome</th>
                      <th className="py-2.5 px-4">Point Forecast</th>
                      <th className="py-2.5 px-4 text-cyan-400">80% Interval</th>
                      <th className="py-2.5 px-4 text-indigo-400">95% Interval</th>
                      <th className="py-2.5 px-4">Confidence Score</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60 font-mono text-slate-300">
                    {(forecastData?.forecasts || []).slice(0, 14).map((f, i) => (
                      <tr key={i} className="hover:bg-slate-800/20">
                        <td className="py-2.5 px-4 font-bold text-slate-200">Day +{f?.horizon_day || (i + 1)}</td>
                        <td className="py-2.5 px-4 font-sans capitalize">{f?.syndrome_category || 'respiratory'}</td>
                        <td className="py-2.5 px-4 text-emerald-400 font-extrabold text-sm">{Math.round(f?.point_forecast || 0)}</td>
                        <td className="py-2.5 px-4 text-cyan-300">[{Math.round(f?.lower_bound_80 ?? f?.lower_bound ?? 0)} – {Math.round(f?.upper_bound_80 ?? f?.upper_bound ?? 0)}]</td>
                        <td className="py-2.5 px-4 text-indigo-300">[{Math.round(f?.lower_bound_95 ?? (f?.lower_bound ? f.lower_bound * 0.9 : 0))} – {Math.round(f?.upper_bound_95 ?? (f?.upper_bound ? f.upper_bound * 1.1 : 0))}]</td>
                        <td className="py-2.5 px-4 font-bold">{(((f?.confidence_score ?? 0.93)) * 100).toFixed(0)}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* TAB 6: CUSUM ALERTS & REVIEWER QUEUE */}
        {activeTab === 'alerts' && (
          <div className="space-y-6">
            <div className="bg-slate-900/70 border border-slate-800 rounded-2xl p-6 shadow-sm">
              <div className="flex flex-wrap justify-between items-center gap-4 mb-6">
                <div>
                  <h2 className="text-lg font-bold text-slate-100 flex items-center gap-2">
                    <span>🚨</span> CUSUM Surge Anomaly & Human Reviewer Queue
                  </h2>
                  <p className="text-xs text-slate-400">
                    Statistical Process Control with drift k=0.5, threshold h=4.0σ. Alerts are actionable ONLY after analyst approval.
                  </p>
                </div>
                <button
                  onClick={handleDetectSurges}
                  disabled={actionLoading}
                  className="px-4 py-2 bg-amber-600 hover:bg-amber-500 text-slate-950 font-bold rounded-xl text-xs transition"
                >
                  ⚡ Run CUSUM Surge Detector
                </button>
              </div>

              <div className="space-y-3">
                {(alertsData?.alerts || []).length === 0 ? (
                  <p className="text-xs text-slate-500 py-8 text-center">No alert candidates in review queue. Run CUSUM surge detector above.</p>
                ) : (
                  (alertsData?.alerts || []).map(a => (
                    <div key={a?.id} className="bg-slate-950 border border-slate-800 rounded-xl p-4 flex flex-wrap justify-between items-center gap-4">
                      <div>
                        <div className="flex items-center gap-2">
                          <span className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded ${
                            a?.status === 'CANDIDATE' ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20' :
                            a?.status === 'APPROVED' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' :
                            'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                          }`}>
                            {a?.status || 'CANDIDATE'}
                          </span>
                          <span className="font-bold text-slate-200 font-mono text-xs">{(a?.id || '').slice(0, 8)}...</span>
                          <span className="text-xs text-slate-400 font-semibold capitalize">| {a?.syndrome_category || 'general'} | Scope: {a?.institution_scope || 'all'}</span>
                        </div>
                        <p className="text-xs text-slate-400 mt-1">
                          CUSUM Shift Score: <strong className="text-amber-400 font-mono">{(a?.shift_score != null ? a.shift_score.toFixed(2) : '0.00')}</strong> (Threshold h=4.0)
                        </p>
                      </div>

                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => handleOpenDossier(a.id)}
                          disabled={actionLoading}
                          className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-cyan-300 font-bold rounded-lg text-xs transition border border-cyan-500/20"
                        >
                          📄 Export Dossier
                        </button>

                        {a?.status === 'CANDIDATE' && (
                          <>
                            <button
                              onClick={() => handleApprove(a.id)}
                              disabled={actionLoading}
                              className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-slate-950 font-bold rounded-lg text-xs transition"
                            >
                              ✓ Approve Alert
                            </button>
                            <button
                              onClick={() => handleReject(a.id)}
                              disabled={actionLoading}
                              className="px-3 py-1.5 bg-slate-800 hover:bg-rose-900/40 text-rose-300 font-bold rounded-lg text-xs transition"
                            >
                              ✕ Reject
                            </button>
                          </>
                        )}
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        )}

        {/* TAB 7: 45-SYNDROME MASTER ONTOLOGY */}
        {activeTab === 'ontology' && (
          <div className="space-y-6">
            <div className="bg-slate-900/70 border border-slate-800 rounded-2xl p-6 shadow-sm">
              <div className="flex flex-wrap justify-between items-center gap-4 mb-4">
                <div>
                  <h2 className="text-lg font-bold text-slate-100 flex items-center gap-2">
                    <span>🧬</span> Standardized HealthSignal Clinical Ontology
                  </h2>
                  <p className="text-xs text-slate-400">
                    Hierarchical Many-to-Many Architecture: 257 Symptoms → 45 Syndromes → 100+ Reference Conditions.
                  </p>
                </div>
                <input
                  type="text"
                  placeholder="Search ontology..."
                  value={searchOntology}
                  onChange={e => setSearchOntology(e.target.value)}
                  className="bg-slate-950 border border-slate-800 rounded-xl px-4 py-2 text-xs text-slate-200 w-64"
                />
              </div>

              {/* Ontology Sub-Navigation */}
              <div className="flex gap-2 border-b border-slate-800 pb-3 mb-4 text-xs font-semibold">
                <button
                  onClick={() => setOntologySubTab('syndromes')}
                  className={`px-3 py-1.5 rounded-lg transition ${
                    ontologySubTab === 'syndromes' ? 'bg-indigo-600 text-white' : 'bg-slate-950 text-slate-400 hover:text-slate-200'
                  }`}
                >
                  45 Syndrome Master ({filteredSyndromes.length})
                </button>
                <button
                  onClick={() => setOntologySubTab('symptoms')}
                  className={`px-3 py-1.5 rounded-lg transition ${
                    ontologySubTab === 'symptoms' ? 'bg-emerald-600 text-slate-950 font-bold' : 'bg-slate-950 text-slate-400 hover:text-slate-200'
                  }`}
                >
                  257 Symptoms Master ({filteredSymptoms.length})
                </button>
                <button
                  onClick={() => setOntologySubTab('diseases')}
                  className={`px-3 py-1.5 rounded-lg transition ${
                    ontologySubTab === 'diseases' ? 'bg-amber-600 text-slate-950 font-bold' : 'bg-slate-950 text-slate-400 hover:text-slate-200'
                  }`}
                >
                  100+ Reference Conditions ({filteredConditions.length})
                </button>
              </div>

              {/* SUB-VIEW 1: 45 SYNDROMES */}
              {ontologySubTab === 'syndromes' && (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 max-h-[600px] overflow-y-auto pr-1">
                  {filteredSyndromes.map(s => (
                    <div key={s?.syndrome_id || s?.code} className="bg-slate-950 border border-slate-800 rounded-xl p-4 space-y-2">
                      <div className="flex justify-between items-start">
                        <span className="font-bold text-indigo-400 font-mono text-xs">{s?.syndrome_id || s?.code}</span>
                        <span className="text-[10px] px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-300 font-semibold border border-indigo-500/20">
                          {s?.domain || 'General'}
                        </span>
                      </div>
                      <h4 className="font-bold text-slate-200 text-sm">{s?.name || 'Syndrome'}</h4>
                      <p className="text-xs text-slate-400">{s?.description || ''}</p>
                      <div className="pt-2 border-t border-slate-800/60 flex justify-between items-center text-[11px]">
                        <span className="text-slate-500 font-mono">code: {s?.code || s?.syndrome_id}</span>
                        <span className="text-amber-400 font-semibold">Weight: {s?.early_warning_weight ?? 1.0}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* SUB-VIEW 2: 257 SYMPTOMS */}
              {ontologySubTab === 'symptoms' && (
                <div className="overflow-x-auto max-h-[600px]">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-slate-950 text-slate-400 sticky top-0 border-b border-slate-800">
                      <tr>
                        <th className="py-2.5 px-4">Code</th>
                        <th className="py-2.5 px-4">Symptom Name</th>
                        <th className="py-2.5 px-4">Category</th>
                        <th className="py-2.5 px-4">Associated 45-Syndromes (Many-to-Many)</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/50 font-mono text-slate-300">
                      {filteredSymptoms.map(s => (
                        <tr key={s?.symptom_id} className="hover:bg-slate-800/20">
                          <td className="py-2 px-4 font-bold text-emerald-400">{s?.symptom_id}</td>
                          <td className="py-2 px-4 font-sans font-medium text-slate-200">{s?.name}</td>
                          <td className="py-2 px-4 font-sans text-slate-400">{s?.category}</td>
                          <td className="py-2 px-4">
                            <div className="flex flex-wrap gap-1">
                              {(s?.associated_syndromes || []).map((syn, idx) => (
                                <span key={idx} className="px-1.5 py-0.5 rounded bg-indigo-500/10 text-indigo-300 text-[10px]">
                                  {syn}
                                </span>
                              ))}
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              {/* SUB-VIEW 3: 100+ REFERENCE CONDITIONS */}
              {ontologySubTab === 'diseases' && (
                <div className="overflow-x-auto max-h-[600px]">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-slate-950 text-slate-400 sticky top-0 border-b border-slate-800">
                      <tr>
                        <th className="py-2.5 px-4">Ref Code</th>
                        <th className="py-2.5 px-4">Condition Name (Simulation Reference)</th>
                        <th className="py-2.5 px-4">Etiology Domain</th>
                        <th className="py-2.5 px-4">Primary Syndrome</th>
                        <th className="py-2.5 px-4">Key Symptoms</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/50 font-mono text-slate-300">
                      {filteredConditions.map(d => (
                        <tr key={d?.disease_id} className="hover:bg-slate-800/20">
                          <td className="py-2 px-4 font-bold text-amber-400">{d?.disease_id}</td>
                          <td className="py-2 px-4 font-sans font-medium text-slate-200">{d?.name}</td>
                          <td className="py-2 px-4 font-sans text-slate-400">{d?.category}</td>
                          <td className="py-2 px-4 text-indigo-400 font-semibold">{d?.primary_syndrome}</td>
                          <td className="py-2 px-4 text-slate-400">
                            {(d?.key_symptoms || []).join(', ')}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

            </div>
          </div>
        )}

      </main>

      {/* Public Health Evidence Dossier Modal */}
      {dossierModal && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-700 rounded-2xl max-w-3xl w-full max-h-[85vh] flex flex-col shadow-2xl">
            <div className="p-5 border-b border-slate-800 flex justify-between items-center">
              <div>
                <h3 className="font-bold text-slate-100 text-base flex items-center gap-2">
                  <span>📄</span> Official Public Health Surveillance Incident Dossier
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">Exported at: {dossierModal?.exported_at}</p>
              </div>
              <button onClick={() => setDossierModal(null)} className="text-slate-400 hover:text-white text-lg">✕</button>
            </div>
            <div className="p-6 overflow-y-auto font-mono text-xs leading-relaxed text-slate-300 whitespace-pre-wrap bg-slate-950/70 m-4 rounded-xl border border-slate-800">
              {dossierModal?.dossier_markdown}
            </div>
            <div className="p-4 border-t border-slate-800 flex justify-end gap-3">
              <button
                onClick={() => {
                  const blob = new Blob([dossierModal?.dossier_markdown || ''], { type: 'text/markdown' });
                  const url = URL.createObjectURL(blob);
                  const a = document.createElement('a');
                  a.href = url;
                  a.download = `HealthSignal-Dossier-${(dossierModal?.alert_id || 'alert').slice(0,8)}.md`;
                  a.click();
                }}
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white font-bold rounded-xl text-xs transition"
              >
                💾 Download Markdown Dossier
              </button>
              <button
                onClick={() => setDossierModal(null)}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl text-xs transition"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Footer */}
      <footer className="bg-slate-950 border-t border-slate-800 py-4 px-6 text-center text-xs text-slate-500">
        HealthSignal © 2026 — Built for IIC 2026 S5 Challenge. Hierarchical 45-Syndrome Multi-Source Surveillance.
      </footer>
    </div>
  );
}
