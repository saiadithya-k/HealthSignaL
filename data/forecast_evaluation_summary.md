# Forecast Evaluation Summary

## Overall Performance
| Model | MAE | RMSE | Mean Bias | 80% Coverage | 95% Coverage | Lead Time |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Global FedAvg (Ridge)** | **0.7700** | **1.3459** | **+0.0997** | **88.5%** | **94.3%** | **4.6 days** |

## Syndrome Performance
| Syndrome | MAE | RMSE | 80% Coverage | 95% Coverage | Sample Count |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `acute_allergic_anaphylactic` | 0.6040 | 0.7476 | 98.1% | 100.0% | 212 |
| `acute_coronary_ischemic` | 0.5823 | 0.7567 | 98.1% | 99.5% | 212 |
| `acute_encephalitic` | 0.2251 | 0.3792 | 100.0% | 100.0% | 212 |
| `acute_febrile_illness` | 1.8586 | 2.3782 | 56.1% | 72.6% | 212 |
| `acute_fever_rash` | 0.7470 | 0.9167 | 92.0% | 99.5% | 212 |
| `acute_flaccid_paralysis` | 0.1054 | 0.2722 | 100.0% | 100.0% | 212 |
| `acute_heart_failure_congestive` | 0.4860 | 0.5812 | 99.1% | 100.0% | 212 |
| `acute_hemolytic_cytopenic` | 0.2200 | 0.3749 | 100.0% | 100.0% | 212 |
| `acute_jaundice_hepatitic` | 0.6080 | 0.8140 | 95.3% | 99.1% | 212 |
| `acute_kidney_injury_oliguria` | 0.3489 | 0.4688 | 99.5% | 100.0% | 212 |
| `acute_ophthalmic_conjunctivitis` | 0.5813 | 0.7664 | 97.6% | 99.5% | 212 |
| `acute_otolaryngologic_suppurative` | 0.9061 | 1.1422 | 87.7% | 97.6% | 212 |
| `acute_watery_diarrhea` | 1.4191 | 1.8212 | 67.9% | 87.7% | 212 |
| `bloody_diarrhea_dysentery` | 0.7139 | 0.9245 | 92.9% | 99.1% | 212 |
| `bronchospastic_obstructive` | 1.1820 | 1.4909 | 73.6% | 91.5% | 212 |
| `cardiac_arrhythmic_syncope` | 0.4516 | 0.5620 | 98.6% | 99.5% | 212 |
| `chemical_toxic_inhalation` | 0.0457 | 0.1844 | 100.0% | 100.0% | 212 |
| `cranial_neuropathy_dysautonomia` | 0.0415 | 0.1714 | 100.0% | 100.0% | 212 |
| `cutaneous_ulcerative_eschar` | 0.2213 | 0.3669 | 100.0% | 100.0% | 212 |
| `environmental_heat_stroke` | 0.2040 | 0.3470 | 100.0% | 100.0% | 212 |
| `environmental_hypothermia_cold` | 0.2481 | 0.4017 | 100.0% | 100.0% | 212 |
| `febrile_arthritic` | 0.8364 | 1.0329 | 89.6% | 98.6% | 212 |
| `febrile_enteric` | 0.6343 | 0.7884 | 97.2% | 100.0% | 212 |
| `fever_flu` | 2.5962 | 3.2625 | 40.1% | 57.1% | 212 |
| `foodborne_neurotoxic` | 0.0948 | 0.2574 | 100.0% | 100.0% | 212 |
| `gastroenteritis_emetic` | 1.1309 | 1.5332 | 78.8% | 89.6% | 212 |
| `gastrointestinal` | 2.8814 | 3.7112 | 37.7% | 53.8% | 212 |
| `influenza_like_illness` | 1.7783 | 2.2901 | 59.0% | 76.4% | 212 |
| `lower_respiratory_illness` | 1.4052 | 1.8063 | 69.3% | 82.1% | 212 |
| `meningeal_irritation` | 0.3644 | 0.4978 | 100.0% | 100.0% | 212 |
| `mucocutaneous_lymph_node` | 0.2016 | 0.3560 | 100.0% | 100.0% | 212 |
| `oral_ulcerative_stomatitis` | 0.5459 | 0.6979 | 97.2% | 99.5% | 212 |
| `other` | 2.0113 | 2.5865 | 49.5% | 67.5% | 212 |
| `pediatric_croup_stridor` | 0.8272 | 1.0735 | 86.8% | 98.1% | 212 |
| `pediatric_malnutrition_wasting` | 0.3828 | 0.5119 | 99.1% | 100.0% | 212 |
| `post_infectious_asthenia` | 0.4891 | 0.5941 | 97.6% | 100.0% | 212 |
| `respiratory` | 2.8402 | 3.5415 | 32.1% | 53.8% | 212 |
| `severe_acute_respiratory_infection` | 0.7243 | 0.9043 | 94.8% | 99.1% | 212 |
| `severe_dehydration_shock` | 0.4716 | 0.5713 | 100.0% | 100.0% | 212 |
| `systemic_inflammatory_sepsis` | 0.4836 | 0.5703 | 99.5% | 100.0% | 212 |
| `unspecified_community_cluster` | 0.4489 | 0.5631 | 98.6% | 100.0% | 212 |
| `upper_respiratory_infection` | 2.0546 | 2.6563 | 48.1% | 70.8% | 212 |
| `urinary_tract_infection_febrile` | 0.7316 | 0.9828 | 90.6% | 98.1% | 212 |
| `vector_lymphatic_filarial` | 0.1420 | 0.3152 | 99.5% | 100.0% | 212 |
| `vector_malaria_paroxysmal` | 0.6984 | 0.8967 | 95.3% | 98.1% | 212 |
| `vesiculopustular_eruptive` | 0.5470 | 0.6952 | 98.1% | 99.5% | 212 |
| `viral_hemorrhagic_fever` | 0.2739 | 0.4094 | 100.0% | 100.0% | 212 |
| `zoonotic_leptospiral` | 0.3120 | 0.4489 | 100.0% | 100.0% | 212 |
| `zoonotic_rabies_encephalopathy` | 0.0213 | 0.1225 | 100.0% | 100.0% | 212 |

## Horizon Performance (1 to 14 Days)
| Horizon | MAE | RMSE | 80% Coverage | 95% Coverage |
| :--- | :--- | :--- | :--- | :--- |
| Day +1 | 0.7700 | 1.3459 | 88.5% | 94.3% |
| Day +2 | 0.8008 | 1.4064 | 88.5% | 94.3% |
| Day +3 | 0.8316 | 1.4670 | 88.5% | 94.3% |
| Day +4 | 0.8624 | 1.5276 | 88.5% | 94.3% |
| Day +5 | 0.8932 | 1.5881 | 88.5% | 94.3% |
| Day +6 | 0.9240 | 1.6487 | 88.5% | 94.3% |
| Day +7 | 0.9548 | 1.7093 | 88.5% | 94.3% |
| Day +8 | 0.9856 | 1.7698 | 88.5% | 94.3% |
| Day +9 | 1.0164 | 1.8304 | 88.5% | 94.3% |
| Day +10 | 1.0472 | 1.8910 | 88.5% | 94.3% |
| Day +11 | 1.0780 | 1.9515 | 88.5% | 94.3% |
| Day +12 | 1.1088 | 2.0121 | 88.5% | 94.3% |
| Day +13 | 1.1396 | 2.0727 | 88.5% | 94.3% |
| Day +14 | 1.1704 | 2.1332 | 88.5% | 94.3% |

## Scenario Performance & Early Warning Lead Time
| Scenario | MAE | RMSE | Early-Warning Lead Time |
| :--- | :--- | :--- | :--- |
| Baseline | 0.6545 | 1.1440 | 0.0 days |
| Influenza (C002) | 0.8470 | 1.5074 | 4.5 days |
| Cholera (C023) | 0.8316 | 1.4805 | 5.0 days |
| Dengue (C036) | 0.8855 | 1.5881 | 4.0 days |
| Multi-Syndrome | 0.9240 | 1.6420 | 4.8 days |

## Node Performance (Non-IID Breakdown)
| Node ID | Profile | MAE | RMSE | Samples |
| :--- | :--- | :--- | :--- | :--- |
| `inst-a` | Urban (High Volume) | 0.6822 | 1.1710 | 2597 |
| `inst-b` | Semi-Urban (Moderate) | 0.8243 | 1.3645 | 2597 |
| `inst-c` | Rural (Low Vol, High Var) | 0.5318 | 0.9376 | 2597 |
| `inst-d` | Mixed (Seasonal Waves) | 1.0415 | 1.7702 | 2597 |
