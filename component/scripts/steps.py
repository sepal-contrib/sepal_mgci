"""Footer buttons of the step windows of the app shell."""

from component.message import cm


def _opens_window(step):
    """True when activating ``step`` opens a window: a dialog step with content."""
    content = step.get("content")
    has_content = content is not None and not (
        isinstance(content, list) and not content
    )
    return step.get("display") == "dialog" and has_content


def opens_panel_only(step):
    """True when ``step`` has no window and opens a panel, as "4. Results" does."""
    return not _opens_window(step) and bool(step.get("right_panel_action"))


def add_step_actions(steps):
    """Give each step window a "Close" button, and a "Next" button to the next step.

    "Next" to a step that opens only a panel closes this window first, and
    ``MgciMapApp`` then opens the panel instead of an empty window.
    """
    close = {"label": cm.app.step_action.close, "close": True, "cancel": True}
    result = []
    for index, step in enumerate(steps):
        step = dict(step)
        if _opens_window(step):
            actions = [close]
            following = steps[index + 1] if index + 1 < len(steps) else None
            if following is not None:
                next_step = {"label": cm.app.step_action.next, "next": following["id"]}
                if _opens_window(following):
                    actions.append(next_step)
                elif opens_panel_only(following):
                    actions.append({**next_step, "close": True})
            step["actions"] = actions
        result.append(step)
    return result
