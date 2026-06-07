import streamlit as st

from services.monitoring_service import (
    get_cpu,
    get_memory,
    get_disk,
    get_ollama_process
)

from services.admin_service import (
    stop_ollama,
    start_ollama
)

st.title("Admin Dashboard")

cpu = get_cpu()
memory = get_memory()
disk = get_disk()

st.metric("CPU %", cpu)
st.metric("Memory %", memory)
st.metric("Disk %", disk)

process = get_ollama_process()

if process:

    st.subheader("Ollama Process")

    st.json(process)

if st.button("STOP OLLAMA"):

    stop_ollama()

    st.success(
        "Ollama Stopped"
    )

if st.button("START OLLAMA"):

    start_ollama()

    st.success(
        "Ollama Started"
    )

