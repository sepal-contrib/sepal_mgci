import ipyvuetify as v
import sepal_ui.sepalwidgets as sw
from ipywidgets import Output
from matplotlib import pyplot as plt

import component.parameter.module_parameter as param
import component.scripts as cs
from component.message import cm
from component.scripts.sub_a import get_mgci


class StatisticCard(sw.Card):
    def __init__(self, df, belt_class, model, *args, **kwargs):
        """
        Creates a full layout view with a circular MGC index followed by
        horizontal bars of land cover area per kapos classes.

        Args:
            krange (int): kapos range number (1,2,3,4,5,6); empty for overall.
            area_per_class (dictionary): Dictionary of lu/lc areas
        """

        self.df = df
        self.belt_class = belt_class
        self.model = model

        super().__init__(*args, **kwargs)

        self._metadata = {"name": "statistics"}
        self.class_ = "ma-4"
        self.row = True

        self.output_chart = Output()

        # Create title and description based on the inputs
        title = cm.dashboard.global_.title
        desc = sw.Alert(
            children=[cm.dashboard.global_.desc.format(param.UNITS["sqkm"][1])],
            dense=True,
        ).show()

        if belt_class != "Total":
            title = cm.dashboard.individual.title.format(belt_class)
            desc = eval(f"cm.dashboard.individual.desc.belt_{int(belt_class)}")

        self.children = [
            v.CardTitle(children=[title]),
            v.CardText(children=[desc]),
            v.Row(
                children=[
                    v.Col(
                        sm=4,
                        class_="d-flex justify-center",
                        children=[
                            cs.create_avatar(self.get_mgci(belt_class=self.belt_class))
                        ],
                    ),
                    v.Col(
                        children=[
                            v.Flex(xs12=True, children=[self.output_chart]),
                        ]
                    ),
                ]
            ),
        ]

        self.get_chart(self.belt_class)

    def get_mgci(self, belt_class):
        """from the model.results, parse the result and return the requested model"""

        return round(
            get_mgci(self.df)
            .loc[get_mgci(self.df).belt_class == belt_class, "mgci"]
            .iloc[0],
            2,
        )

    def get_chart(self, belt_class):
        values = (
            self.df.groupby(["lc_class"], as_index=False).sum()
            if belt_class == "Total"
            else self.df[self.df.belt_class == belt_class]
        )

        total_area = values["sum"].sum()

        norm_values = [row["sum"] / total_area * 100 for idx, row in values.iterrows()]
        human_values = [cs.human_format(row["sum"]) for idx, row in values.iterrows()]

        # We are doing this assumming that the dict will create the labels in the
        # same order
        labels, colors = zip(
            *[
                (
                    self.model.lulc_classes[str(int(class_))][0],
                    self.model.lulc_classes[str(int(class_))][1],
                )
                for class_ in values["lc_class"]
            ]
        )

        with self.output_chart:
            self.output_chart.clear_output()
            plt.style.use("dark_background")

            # create the chart
            fig, ax = plt.subplots(
                figsize=[25, len(values) * 2], facecolor=((0, 0, 0, 0))
            )

            ax.barh(labels, norm_values, color=colors)

            for i, (norm, name, val, color) in enumerate(
                zip(norm_values, labels, human_values, colors)
            ):
                ax.text(norm + 2, i, val, fontsize=40, color=color)
            # cosmetic tuning

            ax.set_xlim(0, 110)
            ax.tick_params(axis="y", which="major", pad=30, labelsize=40, left=False)
            ax.tick_params(axis="x", bottom=False, labelbottom=False)
            ax.set_frame_on(False)
            plt.show()
