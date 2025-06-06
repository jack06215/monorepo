from crewai import Agent, Crew, Task, LLM
from crewai.project import CrewBase, agent, task, crew
from python.crewai_hello_world.model import BookOutline
from crewai.tools import tool

from python.crewai_hello_world.tools.ddg import MyCustomDuckDuckGoTool

@tool("Hello World Tool")
def hello_world_tool() -> str:
    """Say hello world tool."""
    return "Tool's result"

duckduckgo_search = MyCustomDuckDuckGoTool()

@CrewBase
class OutlineCrew:
    """Book outline crew"""

    agents_config = "config/agents.yml"
    tasks_config = "config/tasks.yml"
    llm = LLM(model="ollama/llama3.2", base_url="http://localhost:11434")

    @agent
    def researcher(self) -> Agent:
        """Researcher agent"""
        return Agent(
            config=self.agents_config["researcher"],  # type: ignore[index]
            tools=[hello_world_tool],
            llm=self.llm,
            verbose=True,
        )

    @agent
    def writer(self) -> Agent:
        """Book outliner agent"""
        return Agent(
            config=self.agents_config["writer"],  # type: ignore[index]
            llm=self.llm,
            verbose=True,
        )
    @task
    def research_chapter(self) -> Task:
        """Resaerch topic task"""
        return Task(
            config=self.tasks_config["research_chapter"],  # type: ignore[index]
        )
    
    @task
    def write_chapter(self) -> Task:
        """Generate outline task"""
        return Task(
            config=self.tasks_config["write_chapter"], # type: ignore[index]
            output_pydantic=BookOutline,
        )

    @crew
    def crew(self) -> Crew:
        """Creates the book outline crew"""
        return Crew(
            agents=self.agents, # type: ignore
            tasks=self.tasks,  # type: ignore
            
        )    


