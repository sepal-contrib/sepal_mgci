"""Footer buttons of the step windows of the app shell."""

from component.message import cm


def _opens_window(step):
    """True when activating ``step`` opens a window: a dialog step with content."""
    content = step.get("content")
    has_content = content is not None and not (
        isinstance(content, list) and not content
    )
    return step.get("display") == "dialog" and has_content


def add_step_actions(steps):
    """Give each step window a "Close" button, and a "Next" button to the next step.

    "Next" is added only when the next step opens a window too: a step that only
    opens the results panel would show an empty window.
    """
    close = {"label": cm.app.step_action.close, "close": True, "cancel": True}
    result = []
    for index, step in enumerate(steps):
        step = dict(step)
        if _opens_window(step):
            actions = [close]
            following = steps[index + 1] if index + 1 < len(steps) else None
            if following is not None and _opens_window(following):
                next_step = {"label": cm.app.step_action.next, "next": following["id"]}
                actions.append(next_step)
            step["actions"] = actions
        result.append(step)
    return result
