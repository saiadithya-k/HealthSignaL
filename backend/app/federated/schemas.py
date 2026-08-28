from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class FederatedRoundStatus(BaseModel):
    round_id: str
    global_model_version: str
    status: str  # IN_PROGRESS, COMPLETED, INCOMPLETE, FAILED
    expected_clients: int = 4
    participating_clients: List[str] = Field(default_factory=list)
    successful_clients: int = 0
    failed_clients: int = 0
    aggregation_method: str = "FedAvg"
    started_at: str
    completed_at: Optional[str] = None
    overall_mae: Optional[float] = None
    overall_rmse: Optional[float] = None

class ClientUpdatePayload(BaseModel):
    institution_id: str
    n_samples: int
    coef: List[float]
    intercept: float
    features: List[str]
