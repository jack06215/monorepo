import argparse
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Self

from common.execute import run_command
from meetingbar.model import MeetingBarDType


def format_human_time_jp(start: datetime, end: datetime) -> str:
    today = date.today()

    if start.date() == today:
        day = "今日"
    elif start.date() == today.fromordinal(today.toordinal() + 1):
        day = "明日"
    else:
        day = start.strftime("%m/%d")

    return f"{day} {start:%H:%M}〜{end:%H:%M}"


@dataclass
class Args:
    json_path: Path


@dataclass
class Notification:
    title: str
    subtitle: str
    sound: str
    message: str
    url: str | None = None

    @classmethod
    def from_meetingbar(cls, data: MeetingBarDType) -> Self:
        return cls(
            title="MeetingBar Notofication",
            subtitle=data.title,
            sound="Glass",
            url=cls.normalize_str(data.meeting_url),
            message=format_human_time_jp(start=data.start, end=data.end),
        )

    @staticmethod
    def normalize_str(value: str | None) -> str | None:
        if value is None or value == "EMPTY":
            return None
        return value


def main(args: Args) -> None:
    meetingbar_info = MeetingBarDType.from_meetingbar_json(file=args.json_path)
    print(meetingbar_info)
    notification = Notification.from_meetingbar(meetingbar_info)
    cmd_args = [
        "/opt/homebrew/bin/terminal-notifier",
        "-message",
        notification.message,
        "-title",
        notification.title,
        "-subtitle",
        notification.subtitle,
        "-sound",
        notification.sound,
    ]
    if notification.url is not None:
        cmd_args.extend(
            [
                "-open",
                notification.url,
            ]
        )
    return_val = run_command(args=cmd_args)


if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("--json_path", required=True, type=Path)
    args = Args(**vars(arg_parser.parse_args()))
    main(args)
