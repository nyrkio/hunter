import argparse
import logging
import os
from pathlib import Path
from typing import Optional

import pystache

from hunter import config
from hunter.config import ConfigError
from hunter.fallout import Fallout, FalloutError
from hunter.graphite import Graphite, GraphiteError
from hunter.importer import FalloutImporter, DataImportError
from hunter.report import Report


def setup():
    fallout_user = input("Fallout user name (email): ")
    fallout_token = input("Fallout token: ")
    conf_template = (Path(__file__).parent / "resources" / "conf.yaml.template").read_text()
    conf_yaml = pystache.render(conf_template, {
        'fallout_token': fallout_token,
        'fallout_user': fallout_user
    })
    hunter_conf_dir = (Path.home() / ".hunter")
    if not hunter_conf_dir.exists():
        hunter_conf_dir.mkdir()
    os.umask(0o600) # Don't share credentials with other users
    (Path.home() / ".hunter" / "conf.yaml").write_text(conf_yaml)
    exit(0)


def list_tests(fallout: Fallout, user: Optional[str]):
    for test_name in fallout.list_tests(user):
        print(test_name)
    exit(0)


def analyze_runs(
        fallout: Fallout,
        graphite: Graphite,
        test: str,
        user: Optional[str],
        selector: Optional[str]):
    results = FalloutImporter(fallout, graphite).fetch(test, user, selector)
    results.find_change_points()

    report = Report(results)
    print(report.format_log_annotated())
    exit(0)


def main():
    logging.basicConfig(format='%(levelname)s: %(message)s', level=logging.INFO)

    parser = argparse.ArgumentParser(
        description="Hunts performance regressions in Fallout results")
    parser.add_argument("--user", help="user-name in Fallout")

    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("setup", help="run interactive setup")
    subparsers.add_parser("list", help="list available tests")
    analyze_parser = subparsers.add_parser(
        "analyze",
        help="analyze performance test results")
    analyze_parser.add_argument("test", help="name of the test in Fallout")
    analyze_parser.add_argument(
        "--metrics",
        dest="metrics",
        help="metrics selector, passed to graphite")

    try:
        args = parser.parse_args()
        user = args.user

        if args.command == "setup":
            setup()

        conf = config.load_config()
        fallout = Fallout(conf.fallout)
        graphite = Graphite(conf.graphite)

        if args.command == "list":
            list_tests(fallout, user)
        if args.command == "analyze":
            analyze_runs(fallout, graphite, args.test, user, args.metrics)
        if args.command is None:
            parser.print_usage()

    except ConfigError as err:
        logging.error(err.message)
        exit(1)
    except FalloutError as err:
        logging.error(err.message)
        exit(1)
    except GraphiteError as err:
        logging.error(err.message)
        exit(1)
    except DataImportError as err:
        logging.error(err.message)
        exit(1)


if __name__ == "__main__":
    main()