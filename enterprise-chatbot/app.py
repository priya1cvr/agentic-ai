import streamlit as st

from services.auth_service import (
    is_allowed_user,
    is_admin
)

from services.ollama_service import (
    get_models,
    ask_model
)

from services.database_service import (
    create_tables,
    save_chat
)

create_tables()

st.set_page_config(
    page_title="Enterprise ChatBot",
    layout="wide"
)

st.title("Enterprise ChatBot")

username = st.text_input(
    "User ID"
)

if not username:
    st.stop()

if not is_allowed_user(username):

    st.error("Access Denied")

    st.stop()

st.success(f"Welcome {username}")

models = get_models()

selected_model = st.selectbox(
    "Choose Model",
    models
)

# Conversation memory
if "messages" not in st.session_state:

    st.session_state.messages = []

# Display previous messages
for message in st.session_state.messages:

    with st.chat_message(message["role"]):

        st.markdown(
            message["content"]
        )

prompt = st.chat_input(
    "Ask something..."
)

if prompt:

    st.session_state.messages.append(
        {
            "role": "user",
            "content": prompt
        }
    )

    with st.chat_message("user"):

        st.markdown(prompt)

    with st.spinner("Thinking..."):

        answer = ask_model(
            selected_model,
            st.session_state.messages
        )

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": answer
        }
    )

    with st.chat_message("assistant"):

        st.markdown(answer)

    save_chat(
        username,
        prompt,
        answer
    )

if is_admin(username):

    st.sidebar.success(
        "Admin Access Enabled"
    )

    st.sidebar.page_link(
        "pages/Admin.py",
        label="Admin Dashboard"
    )
