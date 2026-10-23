from typing import List, Optional
from sqlalchemy import desc
from sqlalchemy.orm import Session

from .models import (
    Alert,
    CommunicationEvent,
    CommunicationMetric,
    CommunicationSession,
    DecisionRecord,
    Experiment,
    MonitoringSession,
    Prediction,
)




class ExperimentRepository:
    """Repository handling database operations for experiments."""

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, experiment_id: str) -> Optional[Experiment]:
        """Fetch a single experiment by ID."""
        return self.db.query(Experiment).filter(Experiment.id == experiment_id).first()

    def get_all(self, skip: int = 0, limit: int = 100) -> List[Experiment]:
        """Fetch all experiments ordered by creation time descending."""
        return (
            self.db.query(Experiment)
            .order_by(desc(Experiment.created_at))
            .offset(skip)
            .limit(limit)
            .all()
        )

    def create(self, experiment: Experiment) -> Experiment:
        """Persist a new experiment."""
        self.db.add(experiment)
        self.db.commit()
        self.db.refresh(experiment)
        return experiment

    def count(self) -> int:
        """Count total experiments."""
        return self.db.query(Experiment).count()


class MetricRepository:
    """Repository handling communication metrics queries."""

    def __init__(self, db: Session):
        self.db = db

    def get_latest(self, limit: int = 50) -> List[CommunicationMetric]:
        """Fetch latest communication metrics."""
        return (
            self.db.query(CommunicationMetric)
            .order_by(desc(CommunicationMetric.timestamp))
            .limit(limit)
            .all()
        )

    def create(self, metric: CommunicationMetric) -> CommunicationMetric:
        """Persist a new communication metric record."""
        self.db.add(metric)
        self.db.commit()
        self.db.refresh(metric)
        return metric


class AlertRepository:
    """Repository handling system alerts queries."""

    def __init__(self, db: Session):
        self.db = db

    def get_active(self, limit: int = 50) -> List[Alert]:
        """Fetch unresolved alerts."""
        return (
            self.db.query(Alert)
            .filter(Alert.resolved == False)
            .order_by(desc(Alert.timestamp))
            .limit(limit)
            .all()
        )

    def create(self, alert: Alert) -> Alert:
        """Persist a new alert."""
        self.db.add(alert)
        self.db.commit()
        self.db.refresh(alert)
        return alert

    def resolve_all_active(self) -> int:
        """Mark every unresolved alert as resolved.

        Called when the decision engine returns to a sustained healthy baseline,
        so the active-alert list reflects currently applicable conditions instead
        of accumulating stale entries indefinitely.
        """
        rows = self.db.query(Alert).filter(Alert.resolved == False).all()
        for alert in rows:
            alert.resolved = True
        self.db.commit()
        return len(rows)


class CommunicationSessionRepository:
    """Repository handling database operations for communication sessions."""

    def __init__(self, db: Session):
        self.db = db

    def get_by_session_id(self, session_id: str) -> Optional[CommunicationSession]:
        """Fetch a single communication session by session_id."""
        return (
            self.db.query(CommunicationSession)
            .filter(CommunicationSession.session_id == session_id)
            .first()
        )

    def get_all(self, skip: int = 0, limit: int = 50) -> List[CommunicationSession]:
        """Fetch all communication sessions ordered by creation time descending."""
        return (
            self.db.query(CommunicationSession)
            .order_by(desc(CommunicationSession.created_at))
            .offset(skip)
            .limit(limit)
            .all()
        )

    def create(self, session: CommunicationSession) -> CommunicationSession:
        """Persist a new communication session."""
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session

    def update(self, session: CommunicationSession) -> CommunicationSession:
        """Update an existing communication session record."""
        self.db.commit()
        self.db.refresh(session)
        return session

    def count(self) -> int:
        """Count total communication sessions."""
        return self.db.query(CommunicationSession).count()


class CommunicationEventRepository:
    """Repository handling communication events."""

    def __init__(self, db: Session):
        self.db = db

    def create(self, event: CommunicationEvent) -> CommunicationEvent:
        """Persist a new communication event."""
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        return event

    def get_by_session_id(self, session_id: str) -> List[CommunicationEvent]:
        """Fetch all events for a given session ordered by timestamp ascending."""
        return (
            self.db.query(CommunicationEvent)
            .filter(CommunicationEvent.session_id == session_id)
            .order_by(CommunicationEvent.timestamp.asc())
            .all()
        )


class DecisionRepository:
    """Repository handling database operations for unified decision records."""

    def __init__(self, db: Session):
        self.db = db

    def create(self, record: DecisionRecord) -> DecisionRecord:
        """Persist a new decision record."""
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def get_latest(self) -> Optional[DecisionRecord]:
        """Fetch the most recent decision record."""
        return (
            self.db.query(DecisionRecord)
            .order_by(desc(DecisionRecord.timestamp))
            .first()
        )

    def get_all(self, skip: int = 0, limit: int = 50) -> List[DecisionRecord]:
        """Fetch decision records ordered by timestamp descending."""
        return (
            self.db.query(DecisionRecord)
            .order_by(desc(DecisionRecord.timestamp))
            .offset(skip)
            .limit(limit)
            .all()
        )

    def count(self) -> int:
        """Count total decision records."""
        return self.db.query(DecisionRecord).count()


class MonitoringSessionRepository:
    """Repository handling database operations for unified monitoring sessions."""

    def __init__(self, db: Session):
        self.db = db

    def create(self, session: MonitoringSession) -> MonitoringSession:
        """Persist a new monitoring session."""
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session

    def get_by_id(self, monitoring_session_id: str) -> Optional[MonitoringSession]:
        """Fetch a single monitoring session by monitoring_session_id."""
        return (
            self.db.query(MonitoringSession)
            .filter(MonitoringSession.monitoring_session_id == monitoring_session_id)
            .first()
        )

    def get_all(self, skip: int = 0, limit: int = 50) -> List[MonitoringSession]:
        """Fetch monitoring sessions ordered by creation time descending."""
        return (
            self.db.query(MonitoringSession)
            .order_by(desc(MonitoringSession.created_at))
            .offset(skip)
            .limit(limit)
            .all()
        )

    def update(self, session: MonitoringSession) -> MonitoringSession:
        """Update an existing monitoring session record."""
        self.db.commit()
        self.db.refresh(session)
        return session

    def count(self) -> int:
        """Count total monitoring sessions."""
        return self.db.query(MonitoringSession).count()


