import streamlit as st
import requests

import sys
import os

# add workspace root (parent of rag_project) to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

# API_URL = "http://fastapi:8000"
API_URL = "http://127.0.0.1:8000"


def get_headers():
    return {
        "Authorization": f"Bearer {st.session_state.access_token}"
    }


def logout():
    # st.session_state.clear()
    st.session_state.access_token = None
    st.session_state.username = None
    st.session_state.session_id = None
    st.session_state.sessions = []
    st.session_state.messages = []
    st.rerun()
    st.rerun()


def show_auth_page():
    st.title("🔐 Welcome to RAG Chat")

    login_tab, register_tab = st.tabs(["Login", "Register"])


    with login_tab:
        st.title("🔐 Login to RAG Chat")

        st.write("Please login to continue.")
    
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
    
        login_btn = st.button("Login", use_container_width=True)
    
        if login_btn:
    
            if username == "" or password == "":
                st.warning("Please enter username and password.")
                st.stop()
    
            with st.spinner("Logging in..."):
    
                response = requests.post(
                    f"{API_URL}/token",
                    data={
                        "username": username,
                        "password": password
                    }
                )
    
            if response.status_code == 200:
    
                token = response.json()["access_token"]
    
                st.session_state.access_token = token
                st.session_state.username = username
    
                st.success("Login successful!")
    
                st.rerun()
    
            else:
                st.error("Invalid username or password.")


    with register_tab:

        new_username = st.text_input("Username", key="register_username")
        email = st.text_input("Email", key="register_email")
        password = st.text_input("Password", type="password", key="register_password")

        if st.button("Create Account", use_container_width=True):

            response = requests.post(
                f"{API_URL}/register",
                data={
                    "username": new_username,
                    "email": email,
                    "password": password,
                },
            )

            if response.status_code == 200:
                st.success("Account created successfully. Please login.")
            else:
                try:
                    data = response.json()
                    st.error(data.get("detail", "Something went wrong"))
                except Exception:
                    st.error(response.text)


st.set_page_config(
    page_title="RAG Chat",
    layout="wide"
)

# if "session_id" not in st.session_state:
#     st.session_state.session_id = str(uuid.uuid4())

if "session_id" not in st.session_state:
    st.session_state.session_id = None

if "sessions" not in st.session_state:
    st.session_state.sessions = []

if "messages" not in st.session_state:
    st.session_state.messages = []

if "access_token" not in st.session_state:
    st.session_state.access_token = None

if "username" not in st.session_state:
    st.session_state.username = None


if st.session_state.access_token is None:
    show_auth_page()
    st.stop()

st.title("📚 RAG Chat App")
st.write("Upload a PDF Document and ask questions based on its content.")


def load_sessions():
    try:
        response = requests.get(
            f"{API_URL}/sessions",
            headers=get_headers()
        )
        # response = requests.get(f"{API_URL}/sessions")
        response.raise_for_status()
        st.session_state.sessions = response.json()
    except requests.RequestException:
        st.error("Unable to connect to backend.")

def load_chat(session_id):
    try:
        response = requests.get(f"{API_URL}/sessions/{session_id}", headers=get_headers())
        response.raise_for_status()
        # print(response.status_code)
        # print(response.json())
        st.session_state.messages = response.json()["messages"]
    except requests.RequestException:
        st.error("Unable to load chat.")

load_sessions()

if st.session_state.session_id is None:

    if st.session_state.sessions:

        # Select the most recent chat
        st.session_state.session_id = st.session_state.sessions[0]["session_id"]
        load_chat(st.session_state.session_id)

    else:

        response = requests.post(f"{API_URL}/sessions", headers=get_headers())

        if response.status_code == 200:

            session = response.json()

            st.session_state.session_id = session["session_id"]

            load_sessions()

            load_chat(session["session_id"])

# with st.sidebar:
#     st.header("Convertation History")

#     if not st.session_state.messages:
#         st.info("No conversation yet.")
#     else:
#         for msg in st.session_state.messages:
#             if msg["role"] == "user":
#                 st.markdown(f"**🧑 You:** {msg['content']}")
#             else:
#                 st.markdown(f"**🤖 AI:** {msg['content']}")

#             st.divider()

with st.sidebar:

    st.success(f"👋 Welcome {st.session_state.username}")

    if st.button("🚪 Logout", use_container_width=True):
        logout()

    st.divider()

    st.title("💬 Chats")

    if st.button("+ New Chat", use_container_width=True):

        response = requests.post(f"{API_URL}/sessions", headers=get_headers())

        if response.status_code == 200:

            session = response.json()

            st.session_state.session_id = session["session_id"]

            # st.session_state.messages = []

            load_sessions()

            load_chat(session["session_id"])

            st.rerun()

    st.divider()

    for chat in st.session_state.sessions:

        col1, col2 = st.columns([5, 1])

        title = chat["title"]

        if len(title) > 28:
            title = title[:28] + "..."

        if chat["session_id"] == st.session_state.session_id:
            title = "🟢 " + title

        with col1:

            if st.button(
                title,
                key=chat["session_id"],
                use_container_width=True,
            ):

                st.session_state.session_id = chat["session_id"]

                load_chat(chat["session_id"])

                st.rerun()

        with col2:

            if st.button(
                "🗑️",
                key=f"delete_{chat['session_id']}",
            ):

                delete_response = requests.delete(
                    f"{API_URL}/sessions/{chat['session_id']}",
                    headers=get_headers()
                )

                if delete_response.status_code == 200:
                    load_sessions()

                    if st.session_state.session_id == chat["session_id"]:
                        if st.session_state.sessions:

                            st.session_state.session_id = (
                                st.session_state.sessions[0]["session_id"]
                            )

                            load_chat(st.session_state.session_id)

                        else:

                            response = requests.post(f"{API_URL}/sessions", headers=get_headers())

                            if response.status_code == 200:
                                session = response.json()

                                st.session_state.session_id = session["session_id"]

                                # st.session_state.messages = []

                                load_sessions()

                                load_chat(session["session_id"])
                    st.rerun()

    st.divider()

    with st.expander("📄 Documents", expanded=False):

        ##################################################
        # Upload PDF
        ##################################################

        st.subheader("Upload PDF")

        uploaded_file = st.file_uploader(
            "Choose a PDF",
            type="pdf"
        )

        if uploaded_file is not None:
            os.makedirs("fastapi_uploads", exist_ok=True)
            with open(f"fastapi_uploads/{uploaded_file.name}", "wb") as f:
                f.write(uploaded_file.getbuffer())
            st.success(f"File '{uploaded_file.name}' stored locally successfully!")

            if st.button("Upload & Ingest"):
                
                files = {
                    "file": (
                        uploaded_file.name,
                        uploaded_file.getvalue(),
                        "application/pdf"
                    )
                }

                with st.spinner("Uploading..."):

                    response = requests.post(
                        f"{API_URL}/upload",
                        files=files,
                        headers=get_headers()
                    )

                if response.status_code == 200:
                    st.success(response.json()["message"])
                else:
                    st.error(response.text)

        st.divider()



        ##################################################
        # Delete PDFs
        ##################################################

        st.subheader("Uploaded Files")

        response = requests.get(f"{API_URL}/files", headers=get_headers())

        uploaded_files = response.json()["files"]

        if uploaded_files:

            selected_file = st.selectbox(
                "Select a file",
                uploaded_files
            )

            if st.button("Delete Selected File"):

                response = requests.delete(
                    f"{API_URL}/files/{selected_file}",
                    headers=get_headers()
                )

                if response.status_code == 200:

                    st.success("Deleted successfully")

                    st.rerun()

                else:

                    st.error(response.text)

        else:

            st.info("No uploaded files.")

        st.divider()




##################################################
# Chat
##################################################

st.header("Ask Questions")

##################################################
# Chat History
##################################################

# st.write(st.session_state.messages)
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

query = st.chat_input("Ask a question...")

# if st.button("Get Answer"):
if query:
    # st.session_state.messages.append(
    #     {
    #         "role": "user",
    #         "content": query
    #     }
    # )

    with st.chat_message("user"):
        st.markdown(query)

    with st.spinner("Thinking..."):

        response = requests.post(
            f"{API_URL}/chat",
            json={
                "query": query,
                "session_id": st.session_state.session_id
            },
            headers=get_headers()
        )

    if response.status_code == 200:

        # answer = response.json()["answer"]

        load_chat(st.session_state.session_id)

        load_sessions()

        # st.session_state.messages.append(
        #     {"role": "user", "content": query}
        # )

        # st.session_state.messages.append(
        #     {"role": "assistant", "content": answer}
        # )

        # load_sessions()
        
        st.rerun()  # Refresh the page to show the new messages
        # st.markdown("### Answer")

        # st.write(answer)

    else:
        # Remove the temporary message
        st.session_state.messages.pop()
        st.error(response.text)


