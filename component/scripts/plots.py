import pandas as pd
from plotly import graph_objects as go

# Define a function that receives a dataframe and returns a sankey diagram


def create_sankey(df):
    # Define a dummy dataframe that shows Land cover transitions from 2000 to 2010

    df = pd.DataFrame(
        {
            "label": [
                "A1",
                "A2",
                "A2",
                "B1",
                "B1",
                "B1",
                "B2",
                "B2",
                "B2",
                "C1",
                "C1",
                "C1",
                "C2",
                "C2",
                "C2",
                "C3",
                "C3",
                "C3",
            ],
            "source": [0, 1, 1, 2, 2, 2, 3, 3, 3, 4, 4, 4, 5, 5, 5, 6, 6, 6],
            "target": [1, 2, 2, 3, 3, 3, 4, 4, 4, 5, 5, 5, 6, 6, 6, 7, 7, 7],
            # define a value for each link
            "value": [8, 2, 4, 8, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4],
        }
    )

    fig = go.Figure(
        data=[
            go.Sankey(
                node=dict(
                    pad=15,
                    thickness=20,
                    line=dict(color="black", width=0.5),
                    label=df["label"],
                ),
                link=dict(
                    source=df[
                        "source"
                    ],  # indices correspond to labels, eg A1, A2, A2, B1, ...
                    target=df["target"],
                    value=df["value"],
                ),
            )
        ]
    )

    fig.update_layout(title_text="Transition Land Cover", font_size=10)

    return fig
