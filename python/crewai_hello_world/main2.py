import asyncio
from crewai.flow.flow import Flow, listen, start
from python.crewai_hello_world.crews.outline_book_crew import outline_book_crew
from pydantic import BaseModel

from python.crewai_hello_world.model import Chapter, ChapterOutline


class BookState(BaseModel):
    id: str = "1"
    title: str = "The Current State of AI in September 2024"
    book: list[Chapter] = []
    book_outline: list[ChapterOutline] = []
    topic: str = (
        "Exploring the latest trends in AI across different industries as of September 2024"
    )
    goal: str = """
        The goal of this book is to provide a comprehensive overview of the current state of artificial intelligence in September 2024.
        It will delve into the latest trends impacting various industries, analyze significant advancements,
        and discuss potential future developments. The book aims to inform readers about cutting-edge AI technologies
        and prepare them for upcoming innovations in the field.
    """


class BookFlow(Flow[BookState]):
    initial_state = BookState

    @start()
    def generate_book_outline(self):
        print("Kickoff the Book Outline Crew")
        output = (
            outline_book_crew.OutlineCrew()
            .crew()
            .kickoff(inputs={"topic": self.state.topic, "goal": self.state.goal, "totle": self.state.title})
        )

        chapters = output["chapters"]
        print("Chapters:", chapters)

        self.state.book_outline = chapters
        return chapters

def kickoff() -> None:
    flow = BookFlow()
    flow.kickoff()


def plot() -> None:
    flow = BookFlow()
    flow.plot()


def main2() -> None:
    kickoff()

if __name__ == "__main__":
    main2()

