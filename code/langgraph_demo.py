from langgraph.graph import StateGraph,END 
from typing  import TypedDict,Annotated
import operator
from langchain_ollama import OllamaLLM

#LLM
MODEL_NAME = 'gemma:2b'
llm = OllamaLLM(model=MODEL_NAME, keep_alive=0)


#Define the State that flows through our Graph
''' 
StateGraph: The main class from LangGraph that defines our agent's workflow.
AgentState: A TypedDict that defines what information our agent tracks.
messages: Uses operator.add to accumulate all thoughts, actions, and observations.
next_action: Tells the graph which node to execute next.
iterations: Counts how many reasoning cycles we've completed.

TypedDict: This is for Type Hinting. It tells Python exactly which keys are allowed in your state dictionary 
(e.g., "The state must have a 'messages' key and it must be a list").

Annotated: This allows you to attach metadata to a type. 
In LangGraph, we use it to tell the graph how to update a specific key.

operator.add: This is the "how." By default, if a node returns a value for a key, LangGraph overwrites the old value. 
Using Annotated[list, operator.add] tells LangGraph: "Don't overwrite the list; append the new messages to the existing ones."
'''
class AgentState(TypedDict):
    # 'messages' is a list. 
    # The 'operator.add' tells LangGraph: "Append new items to this list" 
    # instead of replacing the whole list.
    messages: Annotated[list, operator.add]
    next_action:str # This has no annotation, so it will be OVERWRITTEN if changed.
    iterations:int

#Creating a Mock Tool
'''
In a real ReAct agent, tools are functions that perform actions in the world — like searching the web, 
querying databases, or calling APIs. For this example, we'll use a simple mock search tool.
'''
def search_tool(query: str) -> str:
    q = query.lower().strip()
    responses = {
        "weather bangalore": "30°C, partly cloudy",
        "population karnataka": "Approximately 68 million",
        "bangalore": "The capital of Karnataka, known as the Silicon Valley of India.",
        "karnataka": "A state in southwest India with a rich heritage."
    }
    # Check if any keyword exists in the query
    for key in responses:
        if key in q:
            return responses[key]
    return f"No results found for {query}. Try searching for 'weather bangalore' or 'population karnataka'."


# The Reasoning Node — The “Brain” of ReAct, This is where the agent thinks about what to do next.
'''
How it works:

The reasoning node examines the current state and decides:
Should we gather more information? (return "action")
Do we have enough to answer? (return "end")
Notice how each return value updates the state:

Adds a “Thought” message explaining the decision.
Sets next_action to route to the next node.
Increments the iteration counter.

'''
# Small models get confused by long "History" strings. We need to tell the model that if it sees the word "Observation", it should stop searching.
# force Gemma to be a "Robot" during the reasoning phase so it doesn't waste its energy writing the essay yet.
def reasoning_node(state: AgentState):
    history = state["messages"]
    # We tell Gemma: JUST give me a command, don't write the story yet!
    prompt = f"""Review the history: {history}
    
    If you see an 'Observation', write: FINISH
    If you see NO 'Observation', write: SEARCH: bangalore
    
    Response:"""
    
    response = llm.invoke(prompt).strip()
    
    if "FINISH" in response or state.get("iterations", 0) >= 2:
        return {"next_action": "end"} # We just signal it's time to end the loop
    else:
        return {
            "messages": [f"AI Thought: SEARCH: bangalore"], 
            "next_action": "action", 
            "iterations": state.get("iterations", 0) + 1
        }

#The Action Node — Taking Action
# Once the reasoning node decides to act, this node executes the chosen action and observes the results.

'''
The ReAct Cycle in Action:

Action: Calls the search_tool with a query.
Observation: Records what the tool returned.
Routing: Sets next_action back to “reasoning” to continue the loop.
The router function is a simple helper that reads the next_action value and tells LangGraph where to go next.
'''

# 4. Dynamic Action Node
def action_node(state: AgentState):
    last_msg = state["messages"][-1]
    # This splits the string by "SEARCH:" and takes whatever is on the right side
    if "SEARCH:" in last_msg:
        query = last_msg.split("SEARCH:")[-1].strip()
    else:
        query = last_msg # fallback

    print(f"--- Searching for: {query} ---")
    result = search_tool(query)
    return {
        "messages": [f"Observation: {result}"],
        "next_action": "reasoning"
    }

# Gemma will finally stop repeating itself and give you that long-form guide you're looking fo 
def final_summary_node(state: AgentState):
    history = state["messages"]
    # Now we ask for the 500-word essay
    prompt = f"""Based on these facts: {history}
    Write a detailed, 500-word travel guide about Bangalore and Karnataka. 
    Include history, culture, and the 'Silicon Valley' aspect.
    Final Answer:"""
    
    response = llm.invoke(prompt)
    return {"messages": [f"Final Detailed Report:\n{response}"]}

# Router - decides next step
def route(state: AgentState):
    print(f"--- ROUTING to: {state['next_action']} ---")
    return state["next_action"]

# Building and Executing the Graph
# Now we assemble all the pieces into a LangGraph workflow. This is where the magic happens!
'''
Understanding the Graph Structure:

1. Add Nodes: We register our reasoning and action functions as nodes.
2. Set Entry Point: The graph always starts at the reasoning node.
3. Add Conditional Edges: Based on the reasoning node's decision:
    If next_action == "action" → go to the action node.
    If next_action == "end" → stop execution.
4. Add Fixed Edge: After action completes, always return to reasoning.

The app.invoke() call kicks off this entire process.

'''

workflow = StateGraph(AgentState)
workflow.add_node("reasoning",reasoning_node)
workflow.add_node("action",action_node)
workflow.add_node("summarize", final_summary_node) # Add the new node

# Define edges
workflow.set_entry_point("reasoning")
workflow.add_conditional_edges("reasoning", route, {
    "action": "action",
    "end": "summarize"
})
workflow.add_edge("action", "reasoning")
workflow.add_edge("summarize", END) # The summary is the final stop

#Compile and run

app =workflow.compile()

#Execute
print("\n--- Starting Agent ---")
# We add a config dictionary to limit the steps to 10
result = app.invoke(
    {"messages": ["User: Tell me about Bangalore and Karnataka"], "iterations": 0},
    config={"recursion_limit": 10}
)
# Print the conversation flow
print("\n=== ReAct Loop Output ===")
for msg in result["messages"]:
    print(msg)