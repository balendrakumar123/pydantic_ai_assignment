
# import logfire
# from pydantic import BaseModel, Field
# from pydantic_ai import Agent, RunContext
# from ddgs import DDGS
# import os
# import dotenv
# dotenv.load_dotenv()


# GOOGLE_API_KEY =os.getenv("GOOGLE_API_KEY")

# logfire.configure()
# logfire.instrument_pydantic_ai()

# class ResearchOutput(BaseModel):
#     summary: str = Field(description="A concise summary of the research findings")
#     key_facts: list[str] = Field(description="A list of 3-5 key facts extracted from the research")
#     sources: list[str] = Field(description="List of source URLs or references used")

# research_agent = Agent(
#     'google-gla:gemini-2.5-flash',
#     output_type=ResearchOutput,
#     instructions=(
#         "You are a research agent specialized in gathering and summarizing information. "
#         "Use the web_search tool to fetch relevant data from the internet. "
#         "Always cite sources and structure your output according to the schema."
#     ),
# )

# @research_agent.tool
# def web_search(ctx: RunContext, query: str) -> str:
#     """Perform a web search for the given query and return a string with the top results."""
#     with DDGS() as ddgs:
#         results = ddgs.text(query, max_results=5) 
#         formatted_results = []
#         for r in results:
#             formatted_results.append(f"Title: {r['title']}\nSnippet: {r['body']}\nURL: {r['href']}\n")
#     return "\n".join(formatted_results)

# if __name__ == "__main__":
#     print("Research Agent (type 'exit' to quit)")
#     while True:
#         query = input("Enter your research query: ")
#         if query.strip().lower() == 'exit':
#             print("Exiting.")
#             break
#         print(f"Running research agent for query: {query}")
#         result = research_agent.run_sync(query)
#         print("Research Output:")
#         print(result.output)
"""
Research Assistant - PydanticAI + Logfire  
Author: Balendra Paraste  
Description:
    This script implements an intelligent research assistant using 
    Google Gemini (via pydantic-ai) with Logfire instrumentation.
    It performs web searches through a custom tool, summarizes the findings,
    and returns structured research output.
"""

import os
import dotenv
import logfire
from ddgs import DDGS
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext

# --- Load environment variables -------------------------------------------------
dotenv.load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# --- Logfire configuration ------------------------------------------------------
# Cloud instrumentation (project already configured using CLI)
logfire.configure()
logfire.instrument_pydantic_ai()

# --- Pydantic output schema -----------------------------------------------------
class ResearchOutput(BaseModel):
    summary: str = Field(description="Short, clear summary of the research findings.")
    key_facts: list[str] = Field(description="3–5 key insights pulled from the sources.")
    sources: list[str] = Field(description="List of URLs used to generate the answer.")

# --- Create the research agent --------------------------------------------------
researchAssistant = Agent(
    model="google-gla:gemini-2.5-flash",
    output_type=ResearchOutput,
    instructions=(
        "You are an AI research assistant. "
        "Use the 'perform_web_search' tool when you need real-world information. "
        "Return a structured response containing a summary, key facts, and source URLs."
    ),
)

# --- Define tool: Web search ----------------------------------------------------
@researchAssistant.tool
def perform_web_search(ctx: RunContext, query: str) -> str:
    """Search the web and return formatted text results."""
    
    with logfire.span("web_search_tool"):
        with DDGS() as ddgs:
            results = ddgs.text(query, max_results=5)
            
            formatted = []
            for r in results:
                formatted.append(
                    f"Title: {r['title']}\n"
                    f"Snippet: {r['body']}\n"
                    f"URL: {r['href']}\n"
                )
        return "\n".join(formatted)

# --- CLI runner -----------------------------------------------------------------
if __name__ == "__main__":
    print("🔍 Research Assistant (type 'exit' to quit)\n")

    while True:
        user_query = input("Enter your research query: ").strip()

        if user_query.lower() == 'exit':
            print("Exiting Research Assistant.")
            break

        try:
            with logfire.span("agent_run"):
                response = researchAssistant.run_sync(user_query)
                print("\n--- Research Output ------------------------------------")
                print(response.output)
                print("---------------------------------------------------------\n")

        except Exception as e:
            logfire.error("Error while running agent", error=str(e))
            print("\n⚠️ Something went wrong. Check your logs for details.\n")
