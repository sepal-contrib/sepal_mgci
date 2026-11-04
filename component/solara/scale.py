"""Controlled scale input with the established preset and field layout."""

import reacton.ipyvuetify as rv
import solara

from mgci.domain.configuration import ScalePolicy
from component.message import cm
from .messages import msg


@solara.component
def ScaleField(value: ScalePolicy, on_value):
    raw = solara.use_reactive('' if value.metres is None else str(value.metres))
    valid = value.mode == 'native' or (type(value.metres) is int and 10 <= value.metres <= 1500)
    selected = 0 if value.mode == 'native' else value.metres if valid and value.metres in (100, 300, 500, 1000) else None

    def choose(preset):
        if preset is None:
            return
        raw.set('' if preset == 0 else str(preset))
        on_value(ScalePolicy() if preset == 0 else ScalePolicy('custom', preset))

    def custom(text):
        raw.set(str(text or ''))
        try:
            metres = int(float(text))
        except (ValueError, TypeError, OverflowError):
            metres = None
        on_value(ScalePolicy('custom', metres))

    with rv.Html(tag='div'):
        rv.Html(tag='div', class_='text-subtitle-2 mb-1', children=[cm.dashboard.label.scale])
        with rv.Html(tag='div', class_='d-flex align-center', style_='gap: 12px;'):
            with rv.BtnToggle(v_model=selected, on_v_model=choose, dense=True,
                              color='secondary', style_='background: transparent; flex-wrap: wrap;'):
                for preset in (0, 100, 300, 500, 1000):
                    rv.Btn(value=preset, small=True, depressed=True,
                           class_='text-none white--text' if preset == selected else 'text-none',
                           color='secondary' if preset == selected else None,
                           children=[msg('scale.native') if preset == 0 else str(preset)])
            rv.TextField(v_model=raw.value, on_v_model=custom, type='number', suffix='m',
                         dense=True, hide_details=False, placeholder=cm.dashboard.label.custom_scale,
                         style_='max-width: 128px;', error_messages=[] if valid else [msg('scale.error', min=10, max=1500)])
