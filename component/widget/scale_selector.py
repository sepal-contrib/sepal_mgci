import ipyvuetify as v
from traitlets import Bool, Int

from component.message import cm
from component.scripts.setup_check import SetupError

NATIVE = 0
"""Toggle value of the land cover's own resolution."""

SCALE_PRESETS = (100, 300, 500, 1000)
"""Process scales in meters offered as buttons."""

MIN_SCALE, MAX_SCALE = 10, 1500
"""Limits of a custom scale in meters.

The bioclimatic belt asset is averaged in its coarser pyramid levels, which
gives fractional belt classes from about 1,800 m.
"""


class ScaleSelector(v.Html):
    """Choose the process scale: the land cover's own resolution, a preset or a
    custom value."""

    scale = Int(None, allow_none=True)
    "The selected scale in meters, or None for the land cover's own resolution."

    valid = Bool(True)
    "False while the custom field holds a value that cannot be used."

    def __init__(self, **kwargs):
        super().__init__(tag="div", **kwargs)

        self.buttons = {
            NATIVE: self._button(NATIVE, cm.dashboard.label.native_scale),
            **{scale: self._button(scale, str(scale)) for scale in SCALE_PRESETS},
        }
        self.toggle = v.BtnToggle(
            v_model=NATIVE,
            dense=True,
            color="secondary",
            style_="background: transparent; flex-wrap: wrap;",
            children=list(self.buttons.values()),
        )
        self.custom = v.TextField(
            v_model="",
            type="number",
            suffix="m",
            dense=True,
            hide_details="auto",
            placeholder=cm.dashboard.label.custom_scale,
            style_="max-width: 128px;",
        )
        self.children = [
            v.Html(tag="div", class_="text-subtitle-2 mb-1", children=[cm.dashboard.label.scale]),
            v.Html(
                tag="div",
                class_="d-flex align-center",
                style_="gap: 12px;",
                children=[self.toggle, self.custom],
            ),
        ]

        self.toggle.observe(self._on_toggle, "v_model")
        self.custom.observe(self._on_custom, "v_model")
        self._paint()

    @staticmethod
    def _button(value, label):
        return v.Btn(value=value, small=True, depressed=True, class_="text-none", children=[label])

    def checked_scale(self):
        """The selected scale; raise SetupError while the custom value is not valid."""
        if not self.valid:
            raise SetupError(
                cm.setup.scale_range.format(
                    min=MIN_SCALE, max=MAX_SCALE, step=cm.app.drawer_item.calculation
                )
            )
        return self.scale

    def _button_key(self):
        """The button of the current scale, or None for a custom or invalid scale."""
        if not self.valid:
            return None
        if self.scale is None:
            return NATIVE
        return self.scale if self.scale in SCALE_PRESETS else None

    def _on_toggle(self, change):
        if change["new"] is None:
            # A click on the selected button unselects it; keep it selected.
            self.toggle.v_model = self._button_key()
            return
        self.scale = None if change["new"] == NATIVE else change["new"]
        self.valid = True
        self.custom.error_messages = []
        self.custom.v_model = "" if self.scale is None else str(self.scale)
        self._paint()

    def _on_custom(self, change):
        text = (change["new"] or "").strip()
        if not text:
            self.scale = None
        else:
            try:
                value = int(float(text))
            except ValueError:
                value = None
            if value is None or not MIN_SCALE <= value <= MAX_SCALE:
                # Keep no scale: a partial value such as "200" on the way to
                # "2000" must not be used.
                self.valid = False
                self.custom.error_messages = [
                    cm.error.scale_range.format(MIN_SCALE, MAX_SCALE)
                ]
                self.toggle.v_model = None
                self._paint()
                return
            self.scale = value
        self.valid = True
        self.custom.error_messages = []
        self.toggle.v_model = self._button_key()
        self._paint()

    def _paint(self):
        """Fill the selected button, as the export dialog of pysepal does."""
        for key, button in self.buttons.items():
            selected = key == self.toggle.v_model
            button.color = "secondary" if selected else None
            button.class_ = "text-none white--text" if selected else "text-none"
