import asyncio


ATTR_UNIT_OF_MEASUREMENT = "unit_of_measurement"
POWER_UNIT_WATTS = "W"
POWER_UNIT_KILOWATTS = "kW"


def convert_power_to_watts(value: float, unit: str | None) -> float:
    """Map state + unit_of_measurement to watts."""
    normalized = (unit or "").strip().casefold()
    if normalized in ("", "w", "watt", "watts"):
        return value
    if normalized in ("kw", "kilowatt"):
        return value * 1000.0
    return value


def watts_from_state(state) -> float:
    """Read power in watts from a sensor state."""
    if state is None:
        return 0.0
    try:
        raw = float(state.state)
    except (TypeError, ValueError):
        return 0.0
    unit = None
    if state.attributes:
        unit = state.attributes.get(ATTR_UNIT_OF_MEASUREMENT)
    return convert_power_to_watts(raw, unit)


def consumption_state_is_on(state, threshold_watts: float) -> bool:
    """Return whether consumption indicates the device is on."""
    return watts_from_state(state) > threshold_watts


def retry_delay_seconds(
    attempt_index: int,
    initial_delay_seconds: float,
    backoff_multiplier: float,
    max_delay_seconds: float,
) -> float:
    """Compute exponential retry delay for the given attempt index."""
    if attempt_index <= 0:
        return 0.0
    delay = initial_delay_seconds * (backoff_multiplier ** (attempt_index - 1))
    if max_delay_seconds > 0:
        return min(delay, max_delay_seconds)
    return delay


async def retry_with_feedback_backoff(
    *,
    retry_count: int,
    initial_delay_seconds: float,
    backoff_multiplier: float,
    max_delay_seconds: float,
    should_skip_retry,
    is_feedback_matching,
    resend_command,
) -> bool:
    """Retry sending a command until feedback matches or retries are exhausted."""
    if retry_count <= 0:
        return is_feedback_matching()
    if is_feedback_matching():
        return True

    for attempt in range(1, retry_count + 1):
        if should_skip_retry():
            return False
        delay = retry_delay_seconds(
            attempt, initial_delay_seconds, backoff_multiplier, max_delay_seconds
        )
        if delay > 0:
            await asyncio.sleep(delay)
        if should_skip_retry():
            return False
        if is_feedback_matching():
            return True
        await resend_command()
        if is_feedback_matching():
            return True

    return is_feedback_matching()
