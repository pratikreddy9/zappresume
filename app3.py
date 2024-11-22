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

# Main function to build Streamlit dashboard
def main():
    # Page title
    st.title("Resume and Job Description Dashboard")

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

    # Fetch and display resumes in table format
    st.header("Resumes Data (Scrollable Table)")
    resumes = resumes_collection.find()
    resumes_data = [flatten_resume(resume) for resume in resumes]
    resumes_df = pd.DataFrame(resumes_data)
    st.dataframe(resumes_df, height=400)

    # Fetch and display job descriptions in table format
    st.header("Sample Job Descriptions Data (Table)")
    jds = jd_collection.find().limit(10)
    jd_data = [{"JD ID": jd.get("jobDescriptionId", "N/A"), "Query": jd.get("query", "N/A")} for jd in jds]
    jd_df = pd.DataFrame(jd_data)
    st.dataframe(jd_df, height=200)

if __name__ == "__main__":
    main()
