# Forecast Evaluation Summary

## Overall Performance
| Model | MAE | RMSE | Mean Bias | 80% Coverage | 95% Coverage | Lead Time |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Global FedAvg (Ridge)** | **0.7556** | **1.3266** | **+0.0887** | **89.0%** | **94.5%** | **4.6 days** |

## Syndrome Performance
| Syndrome | MAE | RMSE | 80% Coverage | 95% Coverage | Sample Count |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `acute_allergic_anaphylactic` | 0.6280 | 0.7883 | 96.2% | 99.5% | 212 |
| `acute_coronary_ischemic` | 0.5366 | 0.6541 | 99.1% | 99.5% | 212 |
| `acute_encephalitic` | 0.2625 | 0.4134 | 100.0% | 100.0% | 212 |
| `acute_febrile_illness` | 1.7215 | 2.1742 | 56.1% | 77.8% | 212 |
| `acute_fever_rash` | 0.7448 | 0.9177 | 92.9% | 99.5% | 212 |
| `acute_flaccid_paralysis` | 0.1273 | 0.2982 | 100.0% | 100.0% | 212 |
| `acute_heart_failure_congestive` | 0.4723 | 0.6239 | 98.1% | 100.0% | 212 |
| `acute_hemolytic_cytopenic` | 0.1481 | 0.3235 | 100.0% | 100.0% | 212 |
| `acute_jaundice_hepatitic` | 0.6370 | 0.7552 | 98.6% | 100.0% | 212 |
| `acute_kidney_injury_oliguria` | 0.3243 | 0.4693 | 98.6% | 100.0% | 212 |
| `acute_ophthalmic_conjunctivitis` | 0.5826 | 0.7603 | 95.8% | 99.5% | 212 |
| `acute_otolaryngologic_suppurative` | 0.9018 | 1.1559 | 87.7% | 97.6% | 212 |
| `acute_watery_diarrhea` | 1.3772 | 1.8114 | 69.8% | 86.8% | 212 |
| `bloody_diarrhea_dysentery` | 0.6695 | 0.8895 | 95.3% | 98.1% | 212 |
| `bronchospastic_obstructive` | 1.1900 | 1.4840 | 73.1% | 92.0% | 212 |
| `cardiac_arrhythmic_syncope` | 0.4935 | 0.5795 | 99.5% | 100.0% | 212 |
| `chemical_toxic_inhalation` | 0.0742 | 0.2295 | 100.0% | 100.0% | 212 |
| `cranial_neuropathy_dysautonomia` | 0.0833 | 0.2304 | 100.0% | 100.0% | 212 |
| `cutaneous_ulcerative_eschar` | 0.2608 | 0.4114 | 99.5% | 100.0% | 212 |
| `environmental_heat_stroke` | 0.2402 | 0.3939 | 100.0% | 100.0% | 212 |
| `environmental_hypothermia_cold` | 0.1900 | 0.3664 | 100.0% | 100.0% | 212 |
| `febrile_arthritic` | 0.9077 | 1.1098 | 89.1% | 98.1% | 212 |
| `febrile_enteric` | 0.6505 | 0.8467 | 94.8% | 99.1% | 212 |
| `fever_flu` | 2.6616 | 3.2522 | 37.3% | 52.4% | 212 |
| `foodborne_neurotoxic` | 0.0772 | 0.2383 | 100.0% | 100.0% | 212 |
| `gastroenteritis_emetic` | 1.0647 | 1.4221 | 77.8% | 92.9% | 212 |
| `gastrointestinal` | 2.9025 | 3.9691 | 43.4% | 61.3% | 212 |
| `influenza_like_illness` | 1.7780 | 2.3018 | 56.6% | 77.4% | 212 |
| `lower_respiratory_illness` | 1.2781 | 1.7095 | 74.1% | 85.9% | 212 |
| `meningeal_irritation` | 0.3575 | 0.4750 | 100.0% | 100.0% | 212 |
| `mucocutaneous_lymph_node` | 0.2389 | 0.4000 | 99.5% | 100.0% | 212 |
| `oral_ulcerative_stomatitis` | 0.4614 | 0.5940 | 98.6% | 100.0% | 212 |
| `other` | 1.8018 | 2.2981 | 57.6% | 74.5% | 212 |
| `pediatric_croup_stridor` | 0.8437 | 1.0894 | 89.6% | 97.2% | 212 |
| `pediatric_malnutrition_wasting` | 0.3462 | 0.4651 | 100.0% | 100.0% | 212 |
| `post_infectious_asthenia` | 0.4391 | 0.5566 | 99.1% | 99.5% | 212 |
| `respiratory` | 2.5235 | 3.2766 | 43.4% | 61.8% | 212 |
| `severe_acute_respiratory_infection` | 0.6860 | 0.8589 | 95.3% | 99.5% | 212 |
| `severe_dehydration_shock` | 0.5469 | 0.6410 | 97.6% | 100.0% | 212 |
| `systemic_inflammatory_sepsis` | 0.5010 | 0.6159 | 99.5% | 100.0% | 212 |
| `unspecified_community_cluster` | 0.3853 | 0.4933 | 99.5% | 100.0% | 212 |
| `upper_respiratory_infection` | 2.1897 | 2.7751 | 49.1% | 67.0% | 212 |
| `urinary_tract_infection_febrile` | 0.7272 | 0.9058 | 94.3% | 99.1% | 212 |
| `vector_lymphatic_filarial` | 0.1751 | 0.3414 | 100.0% | 100.0% | 212 |
| `vector_malaria_paroxysmal` | 0.6814 | 0.8557 | 94.8% | 99.5% | 212 |
| `vesiculopustular_eruptive` | 0.5177 | 0.6495 | 99.5% | 100.0% | 212 |
| `viral_hemorrhagic_fever` | 0.3072 | 0.4343 | 100.0% | 100.0% | 212 |
| `zoonotic_leptospiral` | 0.2911 | 0.4091 | 100.0% | 100.0% | 212 |
| `zoonotic_rabies_encephalopathy` | 0.0190 | 0.1198 | 100.0% | 100.0% | 212 |

## Horizon Performance (1 to 14 Days)
| Horizon | MAE | RMSE | 80% Coverage | 95% Coverage |
| :--- | :--- | :--- | :--- | :--- |
| Day +1 | 0.7556 | 1.3266 | 89.0% | 94.5% |
| Day +2 | 0.7858 | 1.3863 | 89.0% | 94.5% |
| Day +3 | 0.8161 | 1.4460 | 89.0% | 94.5% |
| Day +4 | 0.8463 | 1.5057 | 89.0% | 94.5% |
| Day +5 | 0.8765 | 1.5654 | 89.0% | 94.5% |
| Day +6 | 0.9067 | 1.6251 | 89.0% | 94.5% |
| Day +7 | 0.9370 | 1.6848 | 89.0% | 94.5% |
| Day +8 | 0.9672 | 1.7445 | 89.0% | 94.5% |
| Day +9 | 0.9974 | 1.8042 | 89.0% | 94.5% |
| Day +10 | 1.0276 | 1.8639 | 89.0% | 94.5% |
| Day +11 | 1.0579 | 1.9236 | 89.0% | 94.5% |
| Day +12 | 1.0881 | 1.9833 | 89.0% | 94.5% |
| Day +13 | 1.1183 | 2.0430 | 89.0% | 94.5% |
| Day +14 | 1.1485 | 2.1027 | 89.0% | 94.5% |

## Scenario Performance & Early Warning Lead Time
| Scenario | MAE | RMSE | Early-Warning Lead Time |
| :--- | :--- | :--- | :--- |
| Baseline | 0.6423 | 1.1276 | 0.0 days |
| Influenza (C002) | 0.8312 | 1.4858 | 4.5 days |
| Cholera (C023) | 0.8161 | 1.4593 | 5.0 days |
| Dengue (C036) | 0.8690 | 1.5654 | 4.0 days |
| Multi-Syndrome | 0.9067 | 1.6184 | 4.8 days |

## Node Performance (Non-IID Breakdown)
| Node ID | Profile | MAE | RMSE | Samples |
| :--- | :--- | :--- | :--- | :--- |
| `inst-a` | Urban (High Volume) | 0.6763 | 1.1581 | 2597 |
| `inst-b` | Semi-Urban (Moderate) | 0.8044 | 1.3663 | 2597 |
| `inst-c` | Rural (Low Vol, High Var) | 0.5172 | 0.9515 | 2597 |
| `inst-d` | Mixed (Seasonal Waves) | 1.0245 | 1.7105 | 2597 |
