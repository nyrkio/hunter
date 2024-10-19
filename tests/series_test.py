import time
from random import random
import pytest

from hunter.series import AnalysisOptions, Metric, Series, compare


def test_change_point_detection():
    series_1 = [1.02, 0.95, 0.99, 1.00, 1.12, 0.90, 0.50, 0.51, 0.48, 0.48, 0.55]
    series_2 = [2.02, 2.03, 2.01, 2.04, 1.82, 1.85, 1.79, 1.81, 1.80, 1.76, 1.78]
    time = list(range(len(series_1)))
    test = Series(
        "test",
        branch=None,
        time=time,
        metrics={"series1": Metric(1, 1.0), "series2": Metric(1, 1.0)},
        data={"series1": series_1, "series2": series_2},
        attributes={},
    )

    change_points = test.analyze().change_points_by_time
    assert len(change_points) == 2
    assert change_points[0].index == 4
    assert change_points[0].changes[0].metric == "series2"
    assert change_points[1].index == 6
    assert change_points[1].changes[0].metric == "series1"


def test_change_point_min_magnitude():
    series_1 = [1.02, 0.95, 0.99, 1.00, 1.12, 0.90, 0.50, 0.51, 0.48, 0.48, 0.55]
    series_2 = [2.02, 2.03, 2.01, 2.04, 1.82, 1.85, 1.79, 1.81, 1.80, 1.76, 1.78]
    time = list(range(len(series_1)))
    test = Series(
        "test",
        branch=None,
        time=time,
        metrics={"series1": Metric(1, 1.0), "series2": Metric(1, 1.0)},
        data={"series1": series_1, "series2": series_2},
        attributes={},
    )

    options = AnalysisOptions()
    options.min_magnitude = 0.2
    change_points = test.analyze(options).change_points_by_time
    assert len(change_points) == 1
    assert change_points[0].index == 6
    assert change_points[0].changes[0].metric == "series1"

    for change_point in change_points:
        for change in change_point.changes:
            assert (
                change.magnitude() >= options.min_magnitude
            ), f"All change points must have magnitude greater than {options.min_magnitude}"

# Divide by zero is only a RuntimeWarning, but for testing we want to make sure it's a failure
@pytest.mark.filterwarnings("error")
def test_div_by_zero():
    series_1 = [0.0, 0.0, 0.0, 1.00, 1.12, 0.90, 0.50, 0.51, 0.48, 0.48, 0.55]
    time = list(range(len(series_1)))
    test = Series(
        "test",
        branch=None,
        time=time,
        metrics={"series1": Metric(1, 1.0)},
        data={"series1": series_1},
        attributes={},
    )

    analyzed_series = test.analyze()
    change_points = analyzed_series.change_points_by_time
    cpjson = analyzed_series.to_json()
    assert len(change_points) == 2
    assert change_points[0].index == 3

def test_change_point_detection_performance():
    timestamps = range(0, 90)  # 3 months of data
    series = [random() for x in timestamps]

    start_time = time.process_time()
    for run in range(0, 10):  # 10 series
        test = Series(
            "test",
            branch=None,
            time=list(timestamps),
            metrics={"series": Metric(1, 1.0)},
            data={"series": series},
            attributes={},
        )
        test.analyze()
    end_time = time.process_time()
    assert (end_time - start_time) < 0.5


def test_get_stable_range():
    series_1 = [1.02, 0.95, 0.99, 1.00, 1.12, 0.90, 0.50, 0.51, 0.48, 0.48, 0.55]
    series_2 = [2.02, 2.03, 2.01, 2.04, 1.82, 1.85, 1.79, 1.81, 1.80, 1.76, 1.78]
    time = list(range(len(series_1)))
    test = Series(
        "test",
        branch=None,
        time=time,
        metrics={"series1": Metric(1, 1.0), "series2": Metric(1, 1.0)},
        data={"series1": series_1, "series2": series_2},
        attributes={},
    ).analyze()

    assert test.get_stable_range("series1", 0) == (0, 6)
    assert test.get_stable_range("series1", 1) == (0, 6)
    assert test.get_stable_range("series1", 5) == (0, 6)
    assert test.get_stable_range("series1", 6) == (6, len(series_1))
    assert test.get_stable_range("series1", 7) == (6, len(series_1))
    assert test.get_stable_range("series1", 10) == (6, len(series_1))

    assert test.get_stable_range("series2", 0) == (0, 4)
    assert test.get_stable_range("series2", 1) == (0, 4)
    assert test.get_stable_range("series2", 3) == (0, 4)


def test_compare():
    series_1 = [1.02, 0.95, 0.99, 1.00, 1.04, 1.02, 0.50, 0.51, 0.48, 0.48, 0.53]
    series_2 = [2.02, 2.03, 2.01, 2.04, 0.51, 0.49, 0.51, 0.49, 0.48, 0.52, 0.50]
    time = list(range(len(series_1)))
    test_1 = Series("test_1", None, time, {"data": Metric()}, {"data": series_1}, {}).analyze()
    test_2 = Series("test_2", None, time, {"data": Metric()}, {"data": series_2}, {}).analyze()

    stats = compare(test_1, None, test_2, None).stats["data"]
    assert stats.pvalue > 0.5  # tails are almost the same
    assert 0.48 < stats.mean_1 < 0.52
    assert 0.48 < stats.mean_2 < 0.52

    stats = compare(test_1, 0, test_2, 0).stats["data"]
    assert stats.pvalue < 0.01  # beginnings are different
    assert 0.98 < stats.mean_1 < 1.02
    assert 2.00 < stats.mean_2 < 2.03

    stats = compare(test_1, 5, test_2, 10).stats["data"]
    assert stats.pvalue < 0.01
    assert 0.98 < stats.mean_1 < 1.02
    assert 0.49 < stats.mean_2 < 0.51


def test_compare_single_point():
    series_1 = [1.02, 0.95, 0.99, 1.00, 1.04, 1.02, 0.50, 0.51, 0.48, 0.48, 0.53]
    series_2 = [0.51]
    series_3 = [0.99]

    test_1 = Series(
        "test_1", None, list(range(len(series_1))), {"data": Metric()}, {"data": series_1}, {}
    ).analyze()
    test_2 = Series("test_2", None, [1], {"data": Metric()}, {"data": series_2}, {}).analyze()
    test_3 = Series("test_3", None, [1], {"data": Metric()}, {"data": series_3}, {}).analyze()

    stats = compare(test_1, None, test_2, None).stats["data"]
    assert stats.pvalue > 0.5

    stats = compare(test_1, 5, test_3, None).stats["data"]
    assert stats.pvalue > 0.5

    stats = compare(test_1, None, test_3, None).stats["data"]
    assert stats.pvalue < 0.01


def test_compare_metrics_order():
    test = Series(
        "test",
        branch=None,
        time=list(range(3)),
        metrics={"m1": Metric(), "m2": Metric(), "m3": Metric(), "m4": Metric(), "m5": Metric()},
        data={"m1": [0, 0, 0], "m2": [0, 0, 0], "m3": [0, 0, 0], "m4": [0, 0, 0], "m5": [0, 0, 0]},
        attributes={},
    ).analyze()
    cmp = compare(test, None, test, None)
    assert list(cmp.stats.keys()) == ["m1", "m2", "m3", "m4", "m5"]


def test_incremental_hunter():
    series_1 = [1.02, 0.95, 0.99, 1.00, 1.12, 0.90, 0.50, 0.51, 0.48, 0.48, 0.55]
    series_2 = [2.02, 2.03, 2.01, 2.04, 1.82, 1.85, 1.79, 1.81, 1.80, 1.76, 1.78]
    time = list(range(len(series_1)))
    test = Series(
        "test",
        branch=None,
        time=time,
        metrics={"series1": Metric(1, 1.0), "series2": Metric(1, 1.0)},
        data={"series1": series_1, "series2": series_2},
        attributes={},
    )

    analyzed_series = test.analyze()
    analyzed_series.append(time=[len(time)], new_data={"series1":[0.5], "series2":[1.97]}, attributes= {})
    change_points = analyzed_series.change_points
    assert [c.index for c in change_points["series1"]] == [6]
    assert [c.index for c in change_points["series2"]] == [4]

    analyzed_series.append(time=[len(time)], new_data={"series1":[0.51]}, attributes= {})
    change_points = analyzed_series.change_points
    assert [c.index for c in change_points["series1"]] == [6]
    assert [c.index for c in change_points["series2"]] == [4]

    analyzed_series.append(time=[len(time)], new_data={"series2":[33.33, 46.46]}, attributes= {})
    change_points = analyzed_series.change_points
    assert [c.index for c in change_points["series1"]] == [6]
    assert [c.index for c in change_points["series2"]] == [4,12]

def test_validate():
    series_1 = [1.02, 0.95, 0.99, 1.00, 1.12, 0.90, 0.50, 0.51, 0.48, 0.48, 0.55]
    series_2 = [2.02, 2.03, 2.01, 2.04, 1.82, 1.85, 1.79, 1.81, 1.80, 1.76, 1.78]
    time = list(range(len(series_1)))
    test = Series(
        "test",
        branch=None,
        time=time,
        metrics={"series1": Metric(1, 1.0), "series2": Metric(1, 1.0)},
        data={"series1": series_1, "series2": series_2},
        attributes={},
    )
    test_fail = Series(
        "test",
        branch=None,
        time=time,
        metrics={"series1": Metric(1, 1.0), "series2": Metric(1, 1.0)},
        data={"series1": series_1, "series2": series_2},
        attributes={},
    )

    analyzed_series_fail = test_fail.analyze()
    analyzed_series_fail.change_points = None
    err = analyzed_series_fail._validate_append(time=[len(time)], new_data={"series1":[0.51]}, attributes= {})
    assert isinstance(err, RuntimeError)

    analyzed_series = test.analyze()
    analyzed_series.append(time=[len(time)], new_data={"series1":[0.5], "series2":[1.97]}, attributes= {})
    change_points = analyzed_series.change_points

    err = analyzed_series._validate_append(time=[len(time)], new_data={"series1":[0.51]}, attributes= {})
    assert err is None

    err = analyzed_series._validate_append(time=[5], new_data={"series1":[0.51]}, attributes= {})
    assert isinstance(err, ValueError)

    err = analyzed_series._validate_append(time=[len(time)], new_data={}, attributes= {})
    assert isinstance(err, ValueError)

def test_can_append():
    series_1 = [1.02, 0.95, 0.99, 1.00, 1.12, 0.90, 0.50, 0.51, 0.48, 0.48, 0.55]
    series_2 = [2.02, 2.03, 2.01, 2.04, 1.82, 1.85, 1.79, 1.81, 1.80, 1.76, 1.78]
    time = list(range(len(series_1)))
    test = Series(
        "test",
        branch=None,
        time=time,
        metrics={"series1": Metric(1, 1.0), "series2": Metric(1, 1.0)},
        data={"series1": series_1, "series2": series_2},
        attributes={},
    )

    analyzed_series = test.analyze()
    analyzed_series.append(time=[len(time)], new_data={"series1":[0.5], "series2":[1.97]}, attributes= {})
    change_points = analyzed_series.change_points

    can = analyzed_series.can_append(time=[len(time)], new_data={"series1":[0.51]}, attributes= {})
    assert can == True

    can = analyzed_series.can_append(time=[5], new_data={"series1":[0.51]}, attributes= {})
    assert can == False

def test_orig_edivisive():
    series_1 = [1.02, 0.95, 0.99, 1.00, 1.12, 0.90, 0.50, 0.51, 0.48, 0.48, 0.55]
    series_2 = [2.02, 2.03, 2.01, 2.04, 1.82, 1.85, 1.79, 1.81, 1.80, 1.76, 1.78]
    time = list(range(len(series_1)))
    test = Series(
        "test",
        branch=None,
        time=time,
        metrics={"series1": Metric(1, 1.0), "series2": Metric(1, 1.0)},
        data={"series1": series_1, "series2": series_2},
        attributes={},
    )

    options = AnalysisOptions()
    options.orig_edivisive = True
    options.max_pvalue = 0.01

    change_points = test.analyze(options=options).change_points_by_time
    assert len(change_points) == 2
    assert change_points[0].index == 4
    assert change_points[1].index == 6
