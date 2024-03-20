from collections import OrderedDict, defaultdict
from enum import Enum, unique
from typing import List, Tuple

from tabulate import tabulate

from hunter.analysis import ComparativeStats
from hunter.series import ChangePointGroup, Series
from hunter.util import format_timestamp, insert_multiple, remove_common_prefix


@unique
class ReportType(Enum):
    LOG = "log"
    JSON = "json"

    def __str__(self):
        return self.value


class ChangePointReport:
    __series: Series
    __change_points: List[ChangePointGroup]

    def __init__(self, series: Series, change_points: List[ChangePointGroup]):
        self.__series = series
        self.__change_points = change_points

    @staticmethod
    def __column_widths(log: List[str]) -> List[int]:
        return [len(c) for c in log[1].split(None)]

    def produce_report(self, test_name: str, report_type: ReportType):
        if report_type == ReportType.LOG:
            return self.__format_log_annotated(test_name)
        elif report_type == ReportType.JSON:
            return self.__format_json(test_name)
        else:
            from hunter.main import HunterError

            raise HunterError(f"Unknown report type: {report_type}")

    def __format_log(self) -> str:
        time_column = [format_timestamp(ts) for ts in self.__series.time]
        table = {"time": time_column, **self.__series.attributes, **self.__series.data}
        metrics = list(self.__series.data.keys())
        headers = list(
            OrderedDict.fromkeys(
                ["time", *self.__series.attributes, *remove_common_prefix(metrics)]
            )
        )
        return tabulate(table, headers=headers)

    def __format_log_annotated(self, test_name: str) -> str:
        """Returns test log with change points marked as horizontal lines"""
        lines = self.__format_log().split("\n")
        col_widths = self.__column_widths(lines)
        indexes = [cp.index for cp in self.__change_points]
        separators = []
        columns = list(
            OrderedDict.fromkeys(["time", *self.__series.attributes, *self.__series.data])
        )
        for cp in self.__change_points:
            separator = ""
            info = ""
            for col_index, col_name in enumerate(columns):
                col_width = col_widths[col_index]
                change = [c for c in cp.changes if c.metric == col_name]
                if change:
                    change = change[0]
                    change_percent = change.forward_change_percent()
                    separator += "·" * col_width + "  "
                    info += f"{change_percent:+.1f}%".rjust(col_width) + "  "
                else:
                    separator += " " * (col_width + 2)
                    info += " " * (col_width + 2)

            separators.append(f"{separator}\n{info}\n{separator}")

        lines = lines[:2] + insert_multiple(lines[2:], separators, indexes)
        return "\n".join(lines)

    def __format_json(self, test_name: str) -> str:
        import json

        return json.dumps({test_name: [cpg.to_json() for cpg in self.__change_points]})


class RegressionsReport:
    def __init__(self, regressions: List[Tuple[str, ComparativeStats]]):
        self.__regressions = regressions

    def produce_report(self, test_name: str, report_type: ReportType):
        if report_type == ReportType.LOG:
            return self.__format_log(test_name)
        elif report_type == ReportType.JSON:
            return self.__format_json(test_name)
        else:
            from hunter.main import HunterError

            raise HunterError(f"Unknown report type: {report_type}")

    def __format_log(self, test_name: str) -> str:
        if not self.__regressions:
            return f"{test_name}: OK"

        output = f"{test_name}:"
        for metric_name, stats in self.__regressions:
            m1 = stats.mean_1
            m2 = stats.mean_2
            change_percent = stats.forward_change_percent()
            output += "\n    {:16}: {:#8.3g} --> {:#8.3g} ({:+6.1f}%)".format(
                metric_name, m1, m2, change_percent
            )
        return output

    def __format_json(self, test_name: str) -> str:
        import json

        if not self.__regressions:
            return json.dumps({test_name: []})

        output = defaultdict(list)
        for metric_name, stats in self.__regressions:
            obj = {"metric": metric_name}
            obj.update(stats.to_json())
            output[test_name].append(obj)

        return json.dumps(output)
