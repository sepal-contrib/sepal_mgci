import asyncio
from types import SimpleNamespace

import pytest

from component.scripts.dashboard_data import (
    calculate_a_dashboard,
    calculate_b_dashboard,
    results_context,
)
from component.tile.dashboard_tile import DashView
from tests.setup_model import complete_model


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
        "component.scripts.dashboard_data.reduce_regions",
        lambda *args, **kwargs: "process",
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
    view.indicator = "sub_a"
    view.model = complete_model(results={})
    view.validate()


def test_a_dashboard_fetches_interpolation_sources_concurrently(monkeypatch):
    active = 0
    peak = 0

    class FakeGee:
        async def get_info_async(self, process):
            nonlocal active, peak
            active += 1
            peak = max(peak, active)
            await asyncio.sleep(0)
            active -= 1
            return {"sub_a": [{"biobelt": 1, "groups": [{"lc": 1, "sum": process}]}]}

    monkeypatch.setattr(
        "component.scripts.dashboard_data.reduce_regions",
        lambda *args, **kwargs: args[4][0]["year"],
    )
    model = SimpleNamespace(
        reporting_years_sub_a={
            2020: [{"asset": "old", "year": 2019}, {"asset": "new", "year": 2021}]
        },
        aoi_model=SimpleNamespace(feature_collection="aoi"),
        matrix_sub_a={},
        rsa=False,
        dem="dem",
        transition_matrix="matrix",
    )

    df = asyncio.run(calculate_a_dashboard(model, 2020, FakeGee()))

    assert peak == 2
    assert df["sum"].iloc[0] == pytest.approx(2020)


def test_b_dashboard_reduces_only_the_requested_transition(monkeypatch):
    requested = []

    def fake_reduce(*args, bands=None, **kwargs):
        requested.append(bands)
        return "process"

    class FakeGee:
        async def get_info_async(self, process):
            return {
                "baseline_transition": [
                    {"biobelt": 2, "groups": [{"lc": 201, "sum": 5.0}]}
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
        matrix_sub_b={},
        rsa=False,
        dem="dem",
        transition_matrix="matrix",
    )

    asyncio.run(calculate_b_dashboard(model, {"baseline": [2000, 2015]}, FakeGee()))

    assert requested == [["baseline_transition"]]


def test_reduce_regions_builds_only_requested_sub_b_bands(monkeypatch):
    import component.scripts.gee as gee

    class FakeTransition:
        def select(self, band):
            return band

    monkeypatch.setattr(gee, "get_transition", lambda *args: FakeTransition())
    monkeypatch.setattr(gee, "reduce_by_regions", lambda area, belt, band, aoi, scale: band)
    years = [{"asset": "a"}, {"asset": "b"}, {"asset": "c"}]

    process = gee.reduce_regions("aoi", {}, False, "dem", years, "matrix", 100)

    assert set(process.getInfo()) == {
        "baseline_degradation",
        "final_degradation",
        "baseline_transition",
        "report_transition",
    }

    process = gee.reduce_regions(
        "aoi", {}, False, "dem", years, "matrix", 100, bands=["report_transition"]
    )

    assert process.getInfo() == {"report_transition": "report_transition"}


class NoGee:
    async def get_info_async(self, process):
        raise AssertionError("stored results must not call Earth Engine")


def _sub_a_model():
    return SimpleNamespace(
        reporting_years_sub_a={2020: [{"asset": "lc/2020", "year": 2020}]},
        aoi_model=SimpleNamespace(feature_collection="aoi", name="Chile"),
        matrix_sub_a={"1": "1"},
        rsa=True,
        dem="dem",
        transition_matrix="matrix",
        results={"2020": {"sub_a": [{"biobelt": 1, "groups": [{"lc": 1, "sum": 7.0}]}]}},
    )


def _sub_b_model():
    return SimpleNamespace(
        sub_b_year={
            "baseline": {
                "base": {"asset": "base", "year": 2000},
                "report": {"asset": "reference", "year": 2015},
            },
            2: {"asset": "report", "year": 2021},
        },
        aoi_model=SimpleNamespace(feature_collection="aoi", name="Chile"),
        matrix_sub_b={1: 1},
        rsa=False,
        dem="dem",
        transition_matrix="matrix",
        results={
            "2000_2015_2021": {
                "report_transition": [
                    {"biobelt": 3, "groups": [{"lc": 102, "sum": 9.0}]}
                ]
            }
        },
    )


def test_a_dashboard_reads_stored_results_for_matching_inputs(monkeypatch):
    monkeypatch.setattr(
        "component.scripts.dashboard_data.reduce_regions",
        lambda *args, **kwargs: pytest.fail("stored results must not build a reduction"),
    )
    model = _sub_a_model()
    # The calculation step coerces the matrix to int while it runs.
    model.results_context = {"sub_a": results_context(model, 120, "sub_a")}
    model.matrix_sub_a = {1: 1}

    df = asyncio.run(calculate_a_dashboard(model, 2020, NoGee(), scale=120))

    assert df["sum"].iloc[0] == pytest.approx(7.0)


def test_a_dashboard_computes_live_when_inputs_changed(monkeypatch):
    live = []

    class LiveGee:
        async def get_info_async(self, process):
            live.append(process)
            return {"sub_a": [{"biobelt": 1, "groups": [{"lc": 1, "sum": 3.0}]}]}

    monkeypatch.setattr(
        "component.scripts.dashboard_data.reduce_regions",
        lambda *args, **kwargs: "process",
    )
    model = _sub_a_model()
    model.results_context = {"sub_a": results_context(model, 120, "sub_a")}

    asyncio.run(calculate_a_dashboard(model, 2020, LiveGee(), scale=250))
    model.matrix_sub_a = {1: 2}
    df = asyncio.run(calculate_a_dashboard(model, 2020, LiveGee(), scale=120))

    assert live == ["process", "process"]
    assert df["sum"].iloc[0] == pytest.approx(3.0)


def test_b_dashboard_reads_stored_transition_for_matching_inputs(monkeypatch):
    monkeypatch.setattr(
        "component.scripts.dashboard_data.reduce_regions",
        lambda *args, **kwargs: pytest.fail("stored results must not build a reduction"),
    )
    model = _sub_b_model()
    model.results_context = {"sub_b": results_context(model, None, "sub_b")}

    df = asyncio.run(
        calculate_b_dashboard(model, {"report": [2015, 2021]}, NoGee())
    )

    assert df[["belt_class", "from_lc", "to_lc", "sum"]].iloc[0].tolist() == [3, 1, 2, 9.0]


def test_b_dashboard_computes_live_when_period_was_not_stored(monkeypatch):
    class LiveGee:
        async def get_info_async(self, process):
            return {
                "baseline_transition": [
                    {"biobelt": 2, "groups": [{"lc": 201, "sum": 5.0}]}
                ]
            }

    monkeypatch.setattr(
        "component.scripts.dashboard_data.reduce_regions",
        lambda *args, **kwargs: "process",
    )
    model = _sub_b_model()
    model.results_context = {"sub_b": results_context(model, None, "sub_b")}

    df = asyncio.run(
        calculate_b_dashboard(model, {"baseline": [2000, 2015]}, LiveGee())
    )

    assert df[["from_lc", "to_lc", "sum"]].iloc[0].tolist() == [2, 1, 5.0]
