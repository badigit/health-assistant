from pydantic import BaseModel, Field, model_validator
from typing import Optional, List
from datetime import datetime
from uuid import UUID


class TelemetryDataPoint(BaseModel):
    """A single long-format telemetry measurement.

    One point = one ``(timestamp, slug, value)`` triple. A mobile client
    syncing N metrics at one timestamp sends N points (not one point with N
    fields). The integration SDK already produces one Observation per metric,
    so the mapping is 1:1.
    """

    source_id: Optional[str] = Field(
        None, pattern=r"^[a-f0-9]{64}$",
        description="SHA-256 identity of the complete source sample for retry-safe delivery",
    )
    start_timestamp: Optional[datetime] = None
    source_name: Optional[str] = Field(None, max_length=255)
    timestamp: datetime = Field(
        ..., description="ISO 8601 timestamp of the measurement"
    )
    slug: str = Field(
        ...,
        description="Biomarker slug (e.g. 'heart-rate', 'steps', 'spo2')",
    )
    value: float = Field(..., description="Numeric measurement value")
    unit: Optional[str] = Field(
        None, description="Optional unit symbol (e.g. 'bpm', 'count', '%')"
    )
    patient_id: Optional[UUID] = Field(
        None,
        description=(
            "Optional patient attribution. When omitted, the row is "
            "attributed later via the device_id → UserIntegration chain."
        ),
    )

    @model_validator(mode='after')
    def validate_interval(self):
        if self.start_timestamp is not None:
            if self.start_timestamp.utcoffset() is None or self.timestamp.utcoffset() is None:
                raise ValueError('Interval timestamps must include a timezone')
            if self.start_timestamp > self.timestamp:
                raise ValueError('Interval start must not follow its end')
        return self


class TelemetrySyncPayload(BaseModel):
    device_id: str = Field(
        ..., description="Unique identifier for the mobile device or watch"
    )
    points: List[TelemetryDataPoint] = Field(
        ..., description="Array of long-format telemetry points to sync"
    )
