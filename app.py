import streamlit as st
import pandas as pd
from pymongo import MongoClient

# MongoDB connection details
mongo_uri = "mongodb+srv://pratiksr:HWezyCHuVRH3H0Qg@zappresume.pcwoy.mongodb.net/?retryWrites=true&w=majority&appName=zappResume"

# Connect to MongoDB
def get_mongo_client():
    return MongoClient(mongo_uri)

# Flatten nested resume data for table display
def flatten_resume(resume):
    educational_qualifications = "; ".join(
        [
            f"{eq.get('degree', 'N/A')} in {eq.get('field', 'N/A')} ({eq.get('graduationYear', 'N/A')})"
            for eq in resume.get("educationalQualifications", [])
        ]
    )
    job_experiences = "; ".join(
        [
            f"{je.get('title', 'N/A')} at {je.get('company', 'N/A')} ({je.get('duration', 'N/A')} years)"
            for je in resume.get("jobExperiences", [])
        ]
    )
    skills = "; ".join([skill.get("skillName", "N/A") for skill in resume.get("skills", [])])
    keywords = "; ".join(resume.get("keywords", []))
    return {
        "Resume ID": resume.get("resumeId", "N/A"),
        "Name": resume.get("name", "N/A"),
        "Email": resume.get("email", "N/A"),
        "Contact No": resume.get("contactNo", "N/A"),
        "Address": resume.get("address", "N/A"),
        "Education": educational_qualifications,
        "Job Experience": job_experiences,
        "Skills": skills,
        "Keywords": keywords,
    }

# Match resumes with the selected JD
def match_resumes_with_jd(jd, resumes_collection):
    matched_resumes = []
    jd_keywords = jd.get("query", "").split()  # Assuming JD's query is a string of keywords
    for resume in resumes_collection.find():
        resume_keywords = resume.get("keywords", [])
        if any(keyword in jd_keywords for keyword in resume_keywords):
            matched_resumes.append(flatten_resume(resume))
    return matched_resumes

# Main function to build Streamlit dashboard
def main():
    # Page title
    st.title("Resume and Job Description Matching Dashboard")

    # Connect to MongoDB
    client = get_mongo_client()
    db = client["resumes_database"]

    # Collections
    resumes_collection = db["resumes"]
    jd_collection = db["job_description"]

    # Metrics
    num_resumes = resumes_collection.count_documents({})
    num_jds = jd_collection.count_documents({})

    # Display metrics
    st.header("Metrics")
    col1, col2 = st.columns(2)
    with col1:
        st.metric(label="Total Resumes", value=num_resumes)
    with col2:
        st.metric(label="Total Job Descriptions", value=num_jds)

    # Matching Section
    st.header("Matching System")
    jds = list(jd_collection.find())
    jd_options = {jd.get("jobDescriptionId", "N/A"): jd for jd in jds}

    if jd_options:
        selected_jd_id = st.selectbox("Select a Job Description:", list(jd_options.keys()))
        selected_jd = jd_options[selected_jd_id]

        st.subheader("Selected Job Description")
        st.write(f"**Job Description ID:** {selected_jd_id}")
        st.write(f"**Query:** {selected_jd.get('query', 'N/A')}")

        # Match resumes
        matched_resumes = match_resumes_with_jd(selected_jd, resumes_collection)

        # Display matched resumes
        if matched_resumes:
            st.subheader("Matched Resumes")
            matched_df = pd.DataFrame(matched_resumes)
            st.dataframe(matched_df, height=400)
        else:
            st.info("No matching resumes found.")

    # Resumes Table
    st.header("All Resumes")
    resumes = resumes_collection.find()
    resumes_data = [flatten_resume(resume) for resume in resumes]
    resumes_df = pd.DataFrame(resumes_data)
    st.dataframe(resumes_df, height=400)

    # Job Descriptions Table
    st.header("All Job Descriptions")
    jd_data = [{"JD ID": jd.get("jobDescriptionId", "N/A"), "Query": jd.get("query", "N/A")} for jd in jds]
    jd_df = pd.DataFrame(jd_data)
    st.dataframe(jd_df, height=200)

if __name__ == "__main__":
    main()
