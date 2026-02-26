"""safety_tools — deterministic exercise safety filtering.

Corresponds to the 'injuries' entry in the K&T Registry.
"""

from __future__ import annotations

from fitness_agent.knowledge_base.models import ContraindicationTag, Exercise


def safety_guard(
    exercise_pool: list[Exercise],
    contraindication_tags: list[ContraindicationTag],
) -> list[Exercise]:
    """Filter exercises that have contraindications overlapping with the user's injuries.

    Parameters
    ----------
    exercise_pool:
        Full list of exercises to filter.
    contraindication_tags:
        The user's active contraindication tags (derived from injury descriptions).

    Returns
    -------
    list[Exercise]
        Exercises that are safe for the given contraindication profile.
    """
    if not contraindication_tags:
        return list(exercise_pool)

    contra_set = set(contraindication_tags)
    return [ex for ex in exercise_pool if not set(ex.contraindications) & contra_set]
