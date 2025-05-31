from python.crewai_hello_world.crews.outline_book_crew import outline_book_crew

def main2() -> None:
    # Instantiate the crew
    crew_instance = outline_book_crew.OutlineCrew()
    
    # Kick off the crew's tasks
    result = crew_instance.crew().kickoff()
    
    # Print the result
    print(result)

if __name__ == "__main__":
    main2()

