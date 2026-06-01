from shared.shared.exceptions.handlers import BusinessError

# Transições válidas: current_status → set[next_status_allowed]
_VALID_TRANSITIONS: dict[str, set[str]] = {
    "open": {"in_progress", "cancelled"},
    "in_progress": {"completed", "cancelled"},
    "completed": set(),
    "cancelled": set(),
}


def validate_status_transition(current: str, next: str) -> None:
    allowed = _VALID_TRANSITIONS.get(current, set())
    if next not in allowed:
        raise BusinessError(
            "INVALID_STATUS_TRANSITION",
            400,
            f"Transição de '{current}' para '{next}' não é permitida",
        )
