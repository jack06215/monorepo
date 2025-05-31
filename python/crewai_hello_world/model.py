from pydantic import BaseModel


class ChapterOutline(BaseModel):
    title: str
    description: str


class BookOutline(BaseModel):
    chapters: list[ChapterOutline]


class Chapter(BaseModel):
    title: str
    content: str
