import streamlit as st
import pandas as pd
import numpy as np
from pymongo import MongoClient

# MongoDB connection details
mongo_uri = "mongodb+srv://pratiksr:HWezyCHuVRH3H0Qg@zappresume.pcwoy.mongodb.net/?retryWrites=true&w=majority&appName=zappResume"
client = MongoClient(mongo_uri)

# Access database and collections
db = client["resumes_database"]
resume_collection = db["resumes"]
jd_collection = db["job_description"]

# Function to calculate cosine similarity
def calculate_cosine_similarity(vector1, vector2):
    vector1 = np.array(vector1)
    vector2 = np.array(vector2)
    dot_product = np.dot(vector1, vector2)
    norm_vector1 = np.linalg.norm(vector1)
    norm_vector2 = np.linalg.norm(vector2)
    if norm_vector1 == 0 or norm_vector2 == 0:
        return 0
    return dot_product / (norm_vector1 * norm_vector2)

# Function to find top matches
def find_top_matches(jd_embedding, num_candidates=10, top_matches=5):
    results = []
    resumes = resume_collection.find().limit(num_candidates)

    for resume in resumes:
        resume_embedding = resume.get("embedding")
        if not resume_embedding:
            continue

        # Calculate cosine similarity
        similarity_score = calculate_cosine_similarity(jd_embedding, resume_embedding)

        # Normalize to a score out of 10
        similarity_score = round(similarity_score * 10, 4)

        results.append({
            "Resume ID": resume.get("resumeId"),
            "Name": resume.get("name"),
            "Similarity Score": similarity_score
        })

    # Sort results by similarity score (descending)
    results = sorted(results, key=lambda x: x["Similarity Score"], reverse=True)
    return results[:top_matches]  # Return top matches

# Function to display detailed resume data
def display_resume_details(resume_id):
    resume = resume_collection.find_one({"resumeId": resume_id})
    if resume:
        # Convert resume data into a DataFrame for display
        detailed_data = [{"Key": key, "Value": value} for key, value in resume.items()]
        st.table(pd.DataFrame(detailed_data))
    else:
        st.warning("Resume details not found!")

# Main function to build Streamlit dashboard
def main():
    st.title("Resume and Job Description Matching Dashboard")

    # Metrics
    total_jds = jd_collection.count_documents({})
    total_resumes = resume_collection.count_documents({})
    st.header("Metrics")
    col1, col2 = st.columns(2)
    with col1:
        st.metric(label="Total Resumes", value=total_resumes)
    with col2:
        st.metric(label="Total Job Descriptions", value=total_jds)

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

        # Check if JD embedding is available
        jd_embedding = selected_jd.get("embedding")
        if not jd_embedding:
            st.error("Embedding not found for the selected JD.")
        else:
            # Find top matches
            matches = find_top_matches(jd_embedding, num_candidates=total_resumes, top_matches=5)

            # Display matches
            if matches:
                st.subheader("Top Matches")
                match_df = pd.DataFrame(matches)
                st.dataframe(match_df, height=300)

                # Allow user to click on a resume to see details
                selected_resume_id = st.selectbox("Select a Resume to View Details:", [match["Resume ID"] for match in matches])
                if selected_resume_id:
                    st.subheader("Resume Details")
                    display_resume_details(selected_resume_id)
            else:
                st.info("No matching resumes found.")

    # Resumes Table
    st.header("All Resumes")
    resumes = resume_collection.find()
    resumes_data = [{"Resume ID": resume.get("resumeId"), "Name": resume.get("name")} for resume in resumes]
    resumes_df = pd.DataFrame(resumes_data)
    st.dataframe(resumes_df, height=400)

    # Job Descriptions Table
    st.header("All Job Descriptions")
    jd_data = [{"JD ID": jd.get("jobDescriptionId"), "Query": jd.get("query", "N/A")} for jd in jds]
    jd_df = pd.DataFrame(jd_data)
    st.dataframe(jd_df, height=200)

if __name__ == "__main__":
    main()
