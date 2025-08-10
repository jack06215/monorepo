"""Workspace Definition."""

import datetime
import pathlib
from collections.abc import Sequence

import dagster

PROJECT_ROOT = pathlib.Path(__file__).parent

partition_definition_everyday_midnight = dagster.TimeWindowPartitionsDefinition(
    start=datetime.datetime(2025, 1, 1),
    timezone="Asia/Tokyo",
    cron_schedule="0 15 * * *",
    fmt="%Y-%m-%d",
    end_offset=1,
)


def define_asset_key(key: Sequence[str]) -> dagster.AssetKey:
    return dagster.AssetKey(key)
