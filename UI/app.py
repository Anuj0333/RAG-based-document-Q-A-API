"""Streamlit UI for RAG application."""

import sys
import os

# add workspace root (parent of rag_project) to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from rag_project.backend.index import ingest_pdf
from rag_agent import retrieve_answer
from rag_project.backend.file_deletion import delete_from_qdrant
import streamlit as st

# import logging


st.set_page_config(page_title="RAG Chat App", layout="wide")


st.title("📚 RAG Chat with Your PDFs")
st.write("Upload a PDF and ask questions based on its content.")

# --- Upload Section ---
uploaded_file = st.file_uploader("Upload a PDF", type="pdf")

if uploaded_file is not None:
    os.makedirs("uploads", exist_ok=True)
    with open(f"uploads/{uploaded_file.name}", "wb") as f:
        f.write(uploaded_file.getbuffer())
    st.success(f"File '{uploaded_file.name}' stored locally successfully!")

    if st.button("Ingest Documents"):
        # # if file is already ingested ignore it  
        # if os.path.exists(f"uploads/{uploaded_file.name}"):
        #     st.warning(f"File '{uploaded_file.name}' already exists. Skipping ingestion.")
        # else:

        with st.spinner("Processing and indexing..."):
            success = ingest_pdf(f"uploads/{uploaded_file.name}")
            if success:
                st.success("Document indexed successfully!")
            else:
                st.error("Failed to ingest PDF. Check logs for details.")

st.divider()

# --- Chat Section ---
st.subheader("Ask Questions")

query = st.text_input("Enter your question")

if st.button("Get Answer"):
    if query:
        with st.spinner("Thinking..."):
            answer = retrieve_answer(query)
            st.markdown("### Answer:")
            st.write(answer)
    else:
        st.warning("Please enter a question.")

# #--- Delete uploaded files on app exit ---
# if st.button("Clear Uploaded Files"):
#     # ask user give dropdown to delete specifice file or all files
    
#     for file in os.listdir("uploads"):
#         file_path = os.path.join("uploads", file)
#         try:
#             os.remove(file_path)
#             st.info(f"Deleted '{file}'")
#         except Exception as e:
#             st.error(f"Error deleting '{file}': {str(e)}")

# --- Delete uploaded files on app exit ---
if "show_delete_section" not in st.session_state:
    st.session_state.show_delete_section = False


if st.button("Clear Uploaded Files"):
    st.session_state.show_delete_section = True


if st.session_state.show_delete_section:

    uploaded_files = os.listdir("uploads")

    if uploaded_files:
        selected_file = st.selectbox(
            "Select file to delete",
            uploaded_files,
            key="file_selector"
        )

        if st.button("Delete Selected File"):
            try:
                delete_from_qdrant(selected_file)
                file_path = os.path.join("uploads", selected_file)
                os.remove(file_path)
                st.success(f"{selected_file} deleted successfully.")
                st.rerun()   # refresh list
            except Exception as e:
                st.error(f"Error deleting: {str(e)}")

    else:
        st.warning("No uploaded files to delete.")