import ipyvuetify as v

from component.message import cm

SCALE_PRESETS = (100, 300, 500, 1000)
"""Process scales in meters offered besides the land cover's own resolution.

Keep them at 1,500 m or below: the bioclimatic belt asset is averaged in its
coarser pyramid levels, which gives fractional belt classes.
"""


class ScaleSelector(v.Flex):
    """Choose the process scale: the land cover's own resolution or a preset."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.class_ = "d-flex align-center flex-wrap mt-2"

        native = v.Btn(
            value=0, small=True, class_="text-none", children=[cm.dashboard.label.native_scale]
        )
        presets = [
            v.Btn(value=scale, small=True, class_="text-none", children=[f"{scale} m"])
            for scale in SCALE_PRESETS
        ]
        self.toggle = v.BtnToggle(
            v_model=0,
            mandatory=True,
            dense=True,
            color="primary",
            children=[native, *presets],
        )
        self.children = [
            v.Html(tag="span", class_="mr-3", children=[cm.dashboard.label.scale]),
            self.toggle,
        ]

    @property
    def scale(self):
        """The selected scale in meters, or None for the land cover's own."""
        return self.toggle.v_model or None
