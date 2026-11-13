"""Episodes of the deciding agent on stored reports, scored exactly like every other run."""

from __future__ import annotations

from typing import Callable

from ..agent.episode import Episode, _State, generate_many
from ..data.schema import View
from ..data.views import load_image
from .arbiter import arbiter_messages


def arbiter_episodes(policy, cfg: dict, reports: dict[str, dict], drop: frozenset) -> Callable[[list[View]], list[Episode]]:
    """views -> episodes: one turn of the arbiter per view (no tools), parsed and scored as an agent episode."""
    def run(views: list[View]) -> list[Episode]:
        missing = [v.view_id for v in views if v.view_id not in reports]
        if missing:
            raise SystemExit(f"{len(missing)} views have no stored reports (first: {missing[0]}); compute them first")
        states = []
        for v in views:
            img = load_image(v.image_path)
            st = _State(v, img, budget=0)
            st.messages = arbiter_messages(img, v.question, reports[v.view_id], drop)
            st.n_prefix = len(st.messages) - 1
            states.append(st)
        for st, g in zip(states, generate_many(policy, [st.messages for st in states], sample=False)):
            st.step(g)
        return [st.finish(cfg) for st in states]
    return run
