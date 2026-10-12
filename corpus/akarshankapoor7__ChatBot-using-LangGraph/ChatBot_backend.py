import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Access the key
groq_api_key = os.getenv("GROQ_API_KEY")

from langchain_groq import ChatGroq

llm = ChatGroq(
    groq_api_key=groq_api_key,
    model="gemma2-9b-it"   
)

from langgraph.graph import StateGraph,START,END
from typing import TypedDict, Annotated
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_groq import ChatGroq
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph.message import add_messages

class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]



def chat_node(state:ChatState):
    messages = state['messages'] 
    resp = llm.invoke(messages)
    return {'messages': [resp]}



# Define the graph structure

checkpoint = MemorySaver()

graph = StateGraph(ChatState)

# add nodes
graph.add_node('chat_node', chat_node)

# add edges
graph.add_edge(START,'chat_node')
graph.add_edge('chat_node',END)

# compile the graph
chatbot =graph.compile(checkpointer=checkpoint)
