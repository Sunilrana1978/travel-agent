"""
Shared type definitions for the Travel Agent app.
"""
from typing import TypedDict


class Feedback(TypedDict, total=False):
    """
    User feedback payload for Agent Engine evaluation.

    Attributes:
        run_id: The unique ID of the agent run being rated.
        score: 1.0 = thumbs up (good), 0.0 = thumbs down (bad).
        comment: Optional free-text comment from the user.
    """
    run_id: str
    score: float
    comment: str
