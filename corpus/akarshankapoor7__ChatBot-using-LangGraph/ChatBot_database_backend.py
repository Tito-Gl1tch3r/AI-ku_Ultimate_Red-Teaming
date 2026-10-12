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
from langgraph.checkpoint.sqlite import SqliteSaver # for persistent storage
import sqlite3
from langgraph.graph.message import add_messages

class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]



def chat_node(state:ChatState):
    messages = state['messages'] 
    resp = llm.invoke(messages)
    return {'messages': [resp]}

# creating a SQLite connection
conn = sqlite3.connect(database='chatbot_memory.db', check_same_thread=False)

# checkpointer
checkpoint = SqliteSaver(conn)

# Define the graph structure
graph = StateGraph(ChatState)

# add nodes
graph.add_node('chat_node', chat_node)

# add edges
graph.add_edge(START,'chat_node')
graph.add_edge('chat_node',END)

# compile the graph
chatbot =graph.compile(checkpointer=checkpoint)

def retrieve_all_threads():
    all_threads = set()
    for cp in checkpoint.list(None):
        all_threads.add(cp.config['configurable']['thread_id'])

    return list(all_threads)