import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, Float, DateTime, ForeignKey, Text, JSON, Boolean
)
from sqlalchemy.orm import relationship
from app.db.database import Base

def generate_uuid():
    return str(uuid.uuid4())

class Institution(Base):
    __tablename__ = "institutions"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False, unique=True)
    profile = Column(String, nullable=False)  # Urban, Semi-urban, Rural, Mixed
    status = Column(String, nullable=False, default="ACTIVE")  # ACTIVE, DISCONNECTED, DEGRADED
    model_version = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    participants = relationship("RoundParticipant", back_populates="institution")
    forecasts = relationship("Forecast", back_populates="institution")


class FederatedRound(Base):
    __tablename__ = "federated_rounds"

    round_id = Column(String, primary_key=True, default=generate_uuid)
    global_model_version = Column(String, nullable=False)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    status = Column(String, nullable=False, default="IN_PROGRESS")  # IN_PROGRESS, COMPLETED, INCOMPLETE, FAILED
    expected_clients = Column(Integer, default=4)
    successful_clients = Column(Integer, default=0)
    failed_clients = Column(Integer, default=0)

    participants = relationship("RoundParticipant", back_populates="round")


class RoundParticipant(Base):
    __tablename__ = "round_participants"

    id = Column(String, primary_key=True, default=generate_uuid)
    round_id = Column(String, ForeignKey("federated_rounds.round_id"), nullable=False)
    institution_id = Column(String, ForeignKey("institutions.id"), nullable=False)
    status = Column(String, nullable=False, default="INVITED")  # INVITED, SUBMITTED, FAILED, TIMEOUT
    update_status = Column(String, nullable=True)  # VALIDATED, REJECTED
    failure_reason = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

    round = relationship("FederatedRound", back_populates="participants")
    institution = relationship("Institution", back_populates="participants")


class ModelVersion(Base):
    __tablename__ = "model_versions"

    id = Column(String, primary_key=True, default=generate_uuid)
    version = Column(String, nullable=False, unique=True)
    parent_version = Column(String, nullable=True)
    algorithm = Column(String, nullable=False, default="Ridge Regression (FedAvg)")
    metrics = Column(JSON, nullable=True)  # e.g., {"mae": 3.42, "wape": 0.08}
    created_at = Column(DateTime, default=datetime.utcnow)
    artifact_reference = Column(String, nullable=True)


class Forecast(Base):
    __tablename__ = "forecasts"

    id = Column(String, primary_key=True, default=generate_uuid)
    model_version = Column(String, nullable=False)
    institution_id = Column(String, ForeignKey("institutions.id"), nullable=True)  # NULL for regional aggregate
    syndrome_category = Column(String, nullable=False)
    forecast_date = Column(DateTime, nullable=False)
    horizon_day = Column(Integer, nullable=False)  # 1 to 14
    point_forecast = Column(Float, nullable=False)
    lower_bound = Column(Float, nullable=False)
    upper_bound = Column(Float, nullable=False)
    uncertainty_score = Column(Float, nullable=False)
    generated_at = Column(DateTime, default=datetime.utcnow)

    institution = relationship("Institution", back_populates="forecasts")


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(String, primary_key=True, default=generate_uuid)
    institution_scope = Column(String, nullable=False)  # Institution ID or 'REGIONAL'
    syndrome_category = Column(String, nullable=False)
    detected_at = Column(DateTime, default=datetime.utcnow)
    shift_score = Column(Float, nullable=False)
    status = Column(String, nullable=False, default="CANDIDATE")  # CANDIDATE, UNDER_REVIEW, APPROVED, REJECTED
    evidence_data = Column(JSON, nullable=True)
    forecast_reference = Column(String, nullable=True)

    decisions = relationship("ReviewerDecision", back_populates="alert")


class ReviewerDecision(Base):
    __tablename__ = "reviewer_decisions"

    id = Column(String, primary_key=True, default=generate_uuid)
    alert_id = Column(String, ForeignKey("alerts.id"), nullable=False)
    reviewer_id = Column(String, nullable=False)
    decision = Column(String, nullable=False)  # APPROVED, REJECTED, REQUEST_MORE_EVIDENCE
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    alert = relationship("Alert", back_populates="decisions")


class PrivacyEvent(Base):
    __tablename__ = "privacy_events"

    id = Column(String, primary_key=True, default=generate_uuid)
    institution_id = Column(String, nullable=True)
    event_type = Column(String, nullable=False)  # REJECTED_TRANSMISSION, SUPPRESSION_TRIGGERED, LEAKAGE_TEST
    severity = Column(String, nullable=False, default="HIGH")
    description = Column(Text, nullable=False)
    details = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String, primary_key=True, default=generate_uuid)
    actor_type = Column(String, nullable=False)  # SYSTEM, FSA, REVIEWER, AUDITOR, NODE
    actor_id = Column(String, nullable=False)
    event_type = Column(String, nullable=False)
    entity_type = Column(String, nullable=True)
    entity_id = Column(String, nullable=True)
    metadata_json = Column(JSON, nullable=True)
    prev_hash = Column(String, nullable=True)
    current_hash = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
