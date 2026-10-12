import streamlit as st
from ChatBot_backend import chatbot
from langchain_core.messages import HumanMessage, AIMessage
import uuid

# 🌟 Chatbot App with Memory, Streaming & Persistent Sessions
st.set_page_config(page_title="LangGraph Chatbot", layout="wide")
st.title("🤖 LangGraph Chatbot")
st.caption("A multi-session conversational AI with memory persistence and real-time streaming responses.")
# **************************************** Utility Functions *************************

def generate_thread_id():
    """Generate unique ID for a new chat session."""
    return str(uuid.uuid4())[:8]

def reset_chat():
    """Start a fresh chat."""
    thread_id = generate_thread_id()
    st.session_state['thread_id'] = thread_id
    add_thread(thread_id)
    st.session_state['message_history'] = []

def add_thread(thread_id):
    """Track threads in session and assign session names."""
    if thread_id not in st.session_state['chat_threads']:
        st.session_state['chat_threads'].append(thread_id)

        # Assign session number and store in mapping
        session_number = len(st.session_state["chat_threads"])
        st.session_state["thread_name_map"][thread_id] = f"session-{session_number}"

def load_conversation(thread_id):
    """Retrieve previous conversation for a thread from backend."""
    state = chatbot.get_state(config={'configurable': {'thread_id': thread_id}})
    return state.values.get('messages', [])


# **************************************** Session Setup ******************************

if 'message_history' not in st.session_state:
    st.session_state['message_history'] = []

if 'thread_id' not in st.session_state:
    st.session_state['thread_id'] = generate_thread_id()

if 'chat_threads' not in st.session_state:
    st.session_state['chat_threads'] = []

# 🔹 New mapping for thread_id → session-n
if "thread_name_map" not in st.session_state:
    st.session_state["thread_name_map"] = {}

add_thread(st.session_state['thread_id'])


# **************************************** Sidebar UI *********************************

st.sidebar.title("🤖 LangGraph Chatbot")

if st.sidebar.button("➕ New Chat", use_container_width=True):
    reset_chat()

st.sidebar.header("🗂️ My Conversations")

# Show sessions in reverse order (latest first)
for thread_id in st.session_state['chat_threads'][::-1]:
    display_name = st.session_state["thread_name_map"].get(thread_id, str(thread_id))
    if st.sidebar.button(display_name, use_container_width=True, key=f"thread-{thread_id}"):
        st.session_state['thread_id'] = thread_id
        messages = load_conversation(thread_id)

        temp_messages = []
        for msg in messages:
            role = "user" if isinstance(msg, HumanMessage) else "assistant"
            temp_messages.append({'role': role, 'content': msg.content})

        st.session_state['message_history'] = temp_messages


# **************************************** Main UI ************************************

# Show existing conversation
for message in st.session_state['message_history']:
    with st.chat_message(message['role']):
        st.markdown(message['content'])

# Chat input
user_input = st.chat_input("Type your message...")

if user_input:
    # Add user message
    st.session_state['message_history'].append({'role': 'user', 'content': user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    CONFIG = {'configurable': {'thread_id': st.session_state['thread_id']}}

    # Assistant reply
    with st.chat_message("assistant"):
        def ai_only_stream():
            for message_chunk, metadata in chatbot.stream(
                {"messages": [HumanMessage(content=user_input)]},
                config=CONFIG,
                stream_mode="messages"
            ):
                if isinstance(message_chunk, AIMessage):
                    yield message_chunk.content  # only assistant tokens

        ai_message = st.write_stream(ai_only_stream())

    # Save assistant response
    st.session_state['message_history'].append({'role': 'assistant', 'content': ai_message})
