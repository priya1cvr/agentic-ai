from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated
import operator
import os
from openai import OpenAI

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

class AgentStateLLM(TypedDict):
    messages: Annotated[list, operator.add]
    next_action: str
    iteration_count: int

# Instead of a mock search, we’ll let the LLM answer queries using its own knowledge. This demonstrates how you can turn an LLM into a tool!
def llm_tool(query: str) -> str:
    """Let the LLM answer the query directly using its knowledge"""
    response = client.chat.completions.create(
        model="gpt-4o",
        max_tokens=150,
        messages=[{"role": "user", "content": f"Answer this query briefly: {query}"}]
    )
    return response.choices[0].message.content.strip()

# LLM-Powered Reasoning — The Core Innovation
def reasoning_node_llm(state: AgentStateLLM):
    iteration_count = state.get("iteration_count", 0)
    if iteration_count >= 3:
        return {"messages": ["Thought: I have gathered enough information"], 
                "next_action": "end", "iteration_count": iteration_count}
    
    history = "\n".join(state["messages"])
    prompt = f"""You are an AI agent answering: "Tell me about Tokyo and Japan"

Conversation so far:
{history}

Queries completed: {iteration_count}/3

You MUST make exactly 3 queries to gather information. 
Respond ONLY with: QUERY: <your specific question>

Do NOT be conversational. Do NOT thank the user. ONLY output: QUERY: <question>"""
    
    decision = client.chat.completions.create(
        model="gpt-4o", max_tokens=100,
        messages=[{"role": "user", "content": prompt}]
    ).choices[0].message.content.strip()
    
    if decision.startswith("QUERY:"):
        return {"messages": [f"Thought: {decision}"], "next_action": "action", 
                "iteration_count": iteration_count}
    return {"messages": [f"Thought: {decision}"], "next_action": "end", 
            "iteration_count": iteration_count}

'''
Context Building: We include the conversation history so the LLM knows what’s already been gathered.
Structured Prompting: We give clear instructions to output in a specific format (QUERY: <question>).
Iteration Control: We enforce a maximum of 3 queries to prevent infinite loops.
Decision Parsing: We check if the LLM wants to take action or finish.
'''

#Executing the Action
def action_node_llm(state: AgentStateLLM):
    last_thought = state["messages"][-1]
    query = last_thought.replace("Thought: QUERY:", "").strip()
    result = llm_tool(query)
    return {"messages": [f"Action: query('{query}')", f"Observation: {result}"], 
            "next_action": "reasoning", 
            "iteration_count": state.get("iteration_count", 0) + 1}

# Building the LLM-Powered Graph
workflow_llm = StateGraph(AgentStateLLM)
workflow_llm.add_node("reasoning", reasoning_node_llm)
workflow_llm.add_node("action", action_node_llm)
workflow_llm.set_entry_point("reasoning")
workflow_llm.add_conditional_edges("reasoning", lambda s: s["next_action"], 
                                   {"action": "action", "end": END})
workflow_llm.add_edge("action", "reasoning")

app_llm = workflow_llm.compile()
result_llm = app_llm.invoke({
    "messages": ["User: Tell me about Tokyo and Japan"], 
    "next_action": "", 
    "iteration_count": 0
})

print("\n=== LLM-Powered ReAct (No Mock Data) ===")
for msg in result_llm["messages"]:
    print(msg)            