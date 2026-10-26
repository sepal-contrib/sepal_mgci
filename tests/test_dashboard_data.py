import asyncio
from types import SimpleNamespace

import pytest

from component.scripts.dashboard_data import calculate_a_dashboard, calculate_b_dashboard
from component.tile.dashboard_tile import DashView


def test_a_dashboard_fetches_new_source_years_without_stored_results(monkeypatch):
    calls = []

    def fake_reduce(*args, **kwargs):
        calls.append(args[4])
        assert args[1] == {1: 1}
        assert args[6] == 120
        return args[4][0]["year"]

    class FakeGee:
        async def get_info_async(self, process):
            return {"sub_a": [{"biobelt": 1, "groups": [{"lc": 1, "sum": process}]}]}

    monkeypatch.setattr("component.scripts.dashboard_data.reduce_regions", fake_reduce)
    model = SimpleNamespace(
        reporting_years_sub_a={
            2020: [
                {"asset": "old", "year": 2019},
                {"asset": "new", "year": 2021},
            ]
        },
        aoi_model=SimpleNamespace(feature_collection="aoi"),
        matrix_sub_a={"1": "1"},
        rsa=False,
        dem="dem",
        transition_matrix="matrix",
    )

    df = asyncio.run(calculate_a_dashboard(model, 2020, FakeGee(), scale=120))

    assert [row[0]["asset"] for row in calls] == ["old", "new"]
    assert set(df["belt_class"]) == {1}
    assert df["sum"].iloc[0] == pytest.approx(2020)


def test_b_dashboard_fetches_selected_reporting_period_without_stored_results(monkeypatch):
    captured = []

    def fake_reduce(*args, **kwargs):
        captured.append(args[4])
        assert args[1] == {1: 1}
        assert args[6] == 120
        return "process"

    class FakeGee:
        async def get_info_async(self, process):
            return {
                "report_transition": [
                    {"biobelt": 1, "groups": [{"lc": 102, "sum": 10.0}]}
                ]
            }

    monkeypatch.setattr("component.scripts.dashboard_data.reduce_regions", fake_reduce)
    model = SimpleNamespace(
        sub_b_year={
            "baseline": {
                "base": {"asset": "base", "year": 2000},
                "report": {"asset": "reference", "year": 2015},
            },
            2: {"asset": "report", "year": 2021},
        },
        aoi_model=SimpleNamespace(feature_collection="aoi"),
        matrix_sub_b={"1": "1"},
        rsa=False,
        dem="dem",
        transition_matrix="matrix",
    )

    df = asyncio.run(
        calculate_b_dashboard(model, {"report": [2015, 2021]}, FakeGee(), scale=120)
    )

    assert [item["asset"] for item in captured[0]] == ["base", "reference", "report"]
    assert df[["from_lc", "to_lc", "sum"]].iloc[0].tolist() == [1, 2, 10.0]


def test_b_dashboard_uses_baseline_transitions(monkeypatch):
    class FakeGee:
        async def get_info_async(self, process):
            return {
                "baseline_transition": [
                    {"biobelt": 2, "groups": [{"lc": 201, "sum": 5.0}]}
                ]
            }

    monkeypatch.setattr(
        "component.scripts.dashboard_data.reduce_regions", lambda *args: "process"
    )
    model = SimpleNamespace(
        sub_b_year={
            "baseline": {
                "base": {"asset": "base", "year": 2000},
                "report": {"asset": "reference", "year": 2015},
            },
            2: {"asset": "report", "year": 2021},
        },
        aoi_model=SimpleNamespace(feature_collection="aoi"),
        matrix_sub_b={},
        rsa=False,
        dem="dem",
        transition_matrix="matrix",
    )

    df = asyncio.run(calculate_b_dashboard(model, {"baseline": [2000, 2015]}, FakeGee()))

    assert df[["from_lc", "to_lc", "sum"]].iloc[0].tolist() == [2, 1, 5.0]


def test_dashboard_allows_chart_request_before_full_statistics_run():
    view = DashView.__new__(DashView)
    view.model = SimpleNamespace(
        aoi_model=SimpleNamespace(feature_collection="aoi"), results={}
    )
    view.render_dashboard()
