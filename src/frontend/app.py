import streamlit as st
import requests

st.set_page_config(page_title="CV Nexus AI", page_icon="🤖", layout="centered")

st.title("CV Nexus: Dual-Engine AI Profiler")
st.markdown("Upload your resume (PDF) and choose how our AI analyzes your career path.")

# --- THE DUAL PATH SELECTOR ---
analysis_mode = st.radio(
    "Select AI Analysis Mode:",
    options=[
        "ATS Matcher (Find best fit in our internal Job Database)",
        "Open Market Profiler (Pure AI Career Consultant)"
    ]
)

st.divider()

uploaded_file = st.file_uploader("Upload your CV (PDF format only)", type=["pdf"])

if uploaded_file is not None:
    if st.button("Analyze My CV", type="primary", use_container_width=True):
        
        with st.spinner("Llama 3 is crunching the data... Please wait."):
            files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "application/pdf")}
            
            # The Magic Switch: Direct the traffic based on user selection
            if "ATS Matcher" in analysis_mode:
                backend_url = "http://localhost:8000/api/v1/match-cv"
            else:
                backend_url = "http://localhost:8000/api/v1/profile-cv"
            
            try:
                response = requests.post(backend_url, files=files)
                
                if response.status_code == 200:
                    data = response.json()
                    st.success(f"✅ Analysis Complete! (Mode: {analysis_mode.split(' ')[0]})")
                    st.subheader("🎯 AI Results")
                    st.info(data["recommendation_result"])
                else:
                    st.error(f"Backend Error: {response.json().get('detail', 'Unknown error')}")
                    
            except requests.exceptions.ConnectionError:
                st.error("🚨 Connection Failed! Make sure your FastAPI backend is running.")