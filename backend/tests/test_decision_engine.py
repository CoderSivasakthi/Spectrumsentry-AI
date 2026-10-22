"""Unit and integration tests for Phase 6 DecisionEngine class and database persistence."""

import pytest
from backend.app.database.database import SessionLocal, init_db
from backend.app.database.models import Alert, DecisionRecord
from backend.app.decision.engine import DecisionEngine
from backend.app.schemas.decision import (
    CommunicationEvidence,
    DecisionInput,
    OverallStatus,
    SignalEvidence,
)


@pytest.fixture(scope="module", autouse=True)
def setup_db():
    init_db()


@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class TestDecisionEngine:
    """Test suite for DecisionEngine class."""

    def test_evaluate_normal_scenario(self, db_session):
        engine = DecisionEngine()
        inp = DecisionInput(
            signal_evidence=SignalEvidence(
                predicted_modulation="BPSK",
                confidence=0.999,
                measured_snr_db=16.0,
            ),
            communication_evidence=CommunicationEvidence(
                status="CONNECTED",
                health_score=100.0,
                packet_loss_percent=0.0,
                avg_latency_ms=8.5,
            ),
        )
        res = engine.evaluate(inp, db=db_session, persist=True)

        assert res.overall_status == OverallStatus.NORMAL
        assert res.decision_confidence >= 0.90
        assert res.id is not None
        assert len(res.contributing_factors) >= 1

        # Verify DB record exists
        record = db_session.query(DecisionRecord).filter(DecisionRecord.id == res.id).first()
        assert record is not None
        assert record.overall_status == "NORMAL"

    def test_evaluate_interrupted_creates_alert(self, db_session):
        engine = DecisionEngine()
        inp = DecisionInput(
            communication_evidence=CommunicationEvidence(
                status="INTERRUPTED",
                is_interrupted=True,
                interruption_count=1,
            ),
        )
        res = engine.evaluate(inp, db=db_session, persist=True)

        assert res.overall_status == OverallStatus.INTERRUPTED

        # Verify alert created
        alert = (
            db_session.query(Alert)
            .filter(Alert.severity == "CRITICAL", Alert.source == "DecisionEngine")
            .order_by(Alert.timestamp.desc())
            .first()
        )
        assert alert is not None
        assert "INTERRUPTED" in alert.message

    def test_evaluate_conflicting_evidence(self, db_session):
        engine = DecisionEngine()
        inp = DecisionInput(
            signal_evidence=SignalEvidence(
                predicted_modulation="16-QAM",
                confidence=0.999,
                measured_snr_db=18.0,
            ),
            communication_evidence=CommunicationEvidence(
                status="DEGRADED",
                health_score=40.0,
                packet_loss_percent=30.0,
            ),
        )
        res = engine.evaluate(inp, db=db_session, persist=True)

        assert res.overall_status == OverallStatus.REVIEW
        assert res.consistency.value == "CONFLICTING"
        assert res.decision_confidence == 0.65

    def test_evaluate_from_latest(self, db_session):
        engine = DecisionEngine()
        res = engine.evaluate_from_latest(db=db_session, persist=False)
        assert res.overall_status in OverallStatus
        assert res.decision_confidence > 0.0

    def test_get_active_rules(self):
        engine = DecisionEngine()
        rules = engine.get_active_rules()
        assert len(rules) >= 7
