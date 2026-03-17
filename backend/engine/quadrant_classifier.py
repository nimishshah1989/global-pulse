"""Quadrant Classifier — Stage 7 RRG Framework.

Classifies instruments into one of four quadrants based on their
adjusted RS score and RS momentum. Directly maps to the Relative
Rotation Graph (RRG) visualization.
"""

from decimal import Decimal


def classify_quadrant(adjusted_rs_score: Decimal, rs_momentum: Decimal) -> str:
    """Classify instrument into RRG quadrant.

    Quadrant determination (2D plane, x=score centered at 50, y=momentum centered at 0):
        LEADING    = score > 50 AND momentum > 0
        WEAKENING  = score > 50 AND momentum <= 0
        LAGGING    = score <= 50 AND momentum <= 0
        IMPROVING  = score <= 50 AND momentum > 0

    Args:
        adjusted_rs_score: Volume-adjusted RS score (0-100 range).
        rs_momentum: RS momentum (-50 to +50 range).

    Returns:
        One of 'LEADING', 'WEAKENING', 'LAGGING', 'IMPROVING'.
    """
    above_50 = adjusted_rs_score > Decimal("50")
    positive_momentum = rs_momentum > Decimal("0")

    if above_50 and positive_momentum:
        return "LEADING"
    elif above_50 and not positive_momentum:
        return "WEAKENING"
    elif not above_50 and positive_momentum:
        return "IMPROVING"
    else:
        return "LAGGING"
