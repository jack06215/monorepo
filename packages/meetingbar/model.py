import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Self


@dataclass(slots=True, frozen=True)
class MeetingBarDType:
    event_id: str
    title: str
    all_day: bool
    start: datetime
    end: datetime
    location: str
    repeating: bool
    attendees: int
    meeting_url: str
    meeting_service: str
    notes: str

    @classmethod
    def from_meetingbar_json(cls, file: Path) -> Self:
        meetingbar_dt_format = "%A, %B %d, %Y at %H:%M:%S"
        data = json.loads(file.read_bytes())
        return cls(
            event_id=data["eventId"],
            title=data["title"],
            all_day=data["allday"].lower() == "true",
            start=datetime.strptime(data["start"], meetingbar_dt_format),
            end=datetime.strptime(data["end"], meetingbar_dt_format),
            location=data["location"],
            repeating=data["repeating"].lower() == "true",
            attendees=int(data["attendees"]),
            meeting_url=data.get("meetingUrl"),
            meeting_service=data.get("meetingService"),
            notes=data.get("notes"),
        )
