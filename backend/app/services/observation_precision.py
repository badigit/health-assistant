"""Preserve censored measurements without treating their bounds as samples."""

from math import isfinite

from app.services.observation_value_validator import InvalidObservationValue


def validate_quantity(quantity):
    """Validate the supported FHIR quantity and comparator contract."""
    if quantity is None:
        return
    if not isinstance(quantity, dict):
        raise InvalidObservationValue("value_quantity must be an object")
    value = quantity.get("value")
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value):
        raise InvalidObservationValue("Quantity value must be a finite number")
    if quantity.get("comparator") not in (None, "<", "<=", ">", ">="):
        raise InvalidObservationValue("Unsupported quantity comparator")


def is_censored(observation):
    """Return whether a quantity describes a bound rather than an exact sample."""
    quantity = observation.value_quantity
    return isinstance(quantity, dict) and bool(quantity.get("comparator"))


def quantity_display(observation):
    """Return a literal censored quantity or the observation's original value."""
    if is_censored(observation):
        q = observation.value_quantity
        return f"{q['comparator']}{q['value']:g}"
    return observation.value_string
