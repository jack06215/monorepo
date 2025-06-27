# hello.py


from crewai import LLM, Agent, Crew, Process, Task
from crewai.tools import BaseTool
from dotenv import load_dotenv

# ——— 0. Load environment variables ———
# Load environment variables from a .env file if it exists
load_dotenv()

llm = LLM(model="ollama/llama3.2", base_url="http://localhost:11434")


# ——— 2. Define a HelloTool ———
class HelloTool(BaseTool):
    name: str = "hello_tool"
    description: str = "Returns the classic greeting."

    def _run(self) -> str:
        return "Hello, world!"


# ——— 3. Build your Crew ———
class HelloWorldCrew:
    def greeter(self) -> Agent:
        return Agent(
            role="Greeter",
            goal="Greet the world with a classic phrase.",
            backstory="An agent whose sole mission is to say hello.",
            llm=llm,
            verbose=True,
        )

    def greet_task(self) -> Task:
        return Task(
            description="Say hello to the world!",
            expected_output="Hello, world!",
            tools=[HelloTool()],
            agent=self.greeter(),
        )

    def crew(self) -> Crew:
        return Crew(
            agents=[self.greeter()],
            tasks=[self.greet_task()],
            process=Process.sequential,
            verbose=True,
        )


# ——— 4. Run it! ———
if __name__ == "__main__":
    HelloWorldCrew().crew().kickoff()
