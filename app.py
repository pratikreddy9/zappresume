import streamlit as st
from pymongo import MongoClient

# MongoDB connection details
mongo_uri = "mongodb+srv://pratiksr:HWezyCHuVRH3H0Qg@zappresume.pcwoy.mongodb.net/?retryWrites=true&w=majority&appName=zappResume"

# Connect to MongoDB
def get_mongo_client():
    return MongoClient(mongo_uri)

# Function to recursively display nested JSON
def display_json(json_data, level=0):
    if isinstance(json_data, dict):
        for key, value in json_data.items():
            st.write(f"{' ' * level * 2}**{key}:**")
            display_json(value, level + 1)
    elif isinstance(json_data, list):
        for index, item in enumerate(json_data):
            st.write(f"{' ' * level * 2}- Item {index + 1}:")
            display_json(item, level + 1)
    else:
        st.write(f"{' ' * level * 2}{json_data}")

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

    # Display resumes data
    st.header("Resumes Data")
    resumes = resumes_collection.find()

    for resume in resumes:
        with st.expander(f"Resume ID: {resume.get('resumeId', 'N/A')} - {resume.get('name', 'Unnamed')}"):
            display_json(resume)

    # Display job descriptions data
    st.header("Sample Job Descriptions Data")
    jds = jd_collection.find().limit(10)
    jd_data = [{"JD ID": jd.get("jobDescriptionId", "N/A"), "Query": jd.get("query", "N/A")} for jd in jds]
    st.table(jd_data)

if __name__ == "__main__":
    main()
