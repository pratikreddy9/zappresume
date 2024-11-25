import streamlit as st
import pandas as pd
from pymongo import MongoClient
import requests

# MongoDB connection details
# This connects to your MongoDB instance using credentials stored in Streamlit secrets.
mongo_uri = st.secrets["mongo"]["uri"]
client = MongoClient(mongo_uri)

# Accessing the database and collections
db = client["resumes_database"]
resume_collection = db["resumes"]  # Collection for resumes
jd_collection = db["job_description"]  # Collection for job descriptions

# Lambda function URL for processing job descriptions
# This Lambda function expects both jobId and jobDescription as input.
lambda_url = "https://ljlj3twvuk.execute-api.ap-south-1.amazonaws.com/default/getJobDescriptionVector"

# Set Streamlit page configuration for a wider layout
st.set_page_config(layout="wide")

# Load custom CSS for consistent styling
def load_css():
    st.markdown(
        """
        <style>
        .metrics-container {
            border: 2px solid #4CAF50;
            padding: 10px;
            margin-bottom: 20px;
            border-radius: 10px;
            background-color: #f9f9f9;
        }
        .section-heading {
            border-left: 5px solid #4CAF50;
            padding-left: 10px;
            margin-top: 20px;
            margin-bottom: 10px;
        }
        .tile {
            border: 1px solid #ddd;
            border-radius: 8px;
            padding: 15px;
            margin: 10px;
            background-color: #f9f9f9;
            box-shadow: 0px 2px 5px rgba(0, 0, 0, 0.1);
        }
        .tile:hover {
            box-shadow: 0px 4px 10px rgba(0, 0, 0, 0.2);
        }
        .tile-heading {
            font-size: 18px;
            font-weight: bold;
            margin-bottom: 10px;
            color: #333;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

# Function to find top matches for a given JD embedding
# Matches are calculated using cosine similarity
def find_top_matches(jd_embedding, num_candidates=10):
    results = []
    resumes = resume_collection.find().limit(num_candidates)

    for resume in resumes:
        resume_embedding = resume.get("embedding")
        if not resume_embedding:  # Skip if embedding is missing
            continue

        # Cosine similarity calculation
        similarity_score = sum(
            a * b for a, b in zip(jd_embedding, resume_embedding)
        ) / (sum(a * a for a in jd_embedding) ** 0.5 * sum(b * b for b in resume_embedding) ** 0.5)
        similarity_score = round(similarity_score * 10, 4)  # Scale and round the score

        results.append({
            "Resume ID": resume.get("resumeId"),
            "Name": resume.get("name"),
            "Similarity Score": similarity_score
        })

    # Return sorted results by similarity score in descending order
    return sorted(results, key=lambda x: x["Similarity Score"], reverse=True)

# Function to display detailed resume information
def display_resume_details(resume_id):
    resume = resume_collection.find_one({"resumeId": resume_id})
    if not resume:
        st.warning("Resume details not found!")
        return

    # Personal Information
    st.markdown("<div class='section-heading'>Personal Information</div>", unsafe_allow_html=True)
    st.write(f"**Name:** {resume.get('name', 'N/A')}")
    st.write(f"**Email:** {resume.get('email', 'N/A')}")
    st.write(f"**Contact No:** {resume.get('contactNo', 'N/A')}")
    st.write(f"**Address:** {resume.get('address', 'N/A')}")
    st.markdown("---")

    # Educational Qualifications
    edu_qual = [
        f"{eq.get('degree', 'N/A')} in {eq.get('field', 'N/A')} ({eq.get('graduationYear', 'N/A')})"
        for eq in resume.get("educationalQualifications", [])
    ]

    # Job Experiences
    job_exp = [
        f"{je.get('title', 'N/A')} at {je.get('company', 'N/A')} ({je.get('duration', 'N/A')} years)"
        for je in resume.get("jobExperiences", [])
    ]

    # Skills
    skills = [skill.get("skillName", "N/A") for skill in resume.get("skills", [])]

    # Keywords
    keywords = resume.get("keywords", [])

    # Create a 2x2 grid for displaying data
    col1, col2 = st.columns(2)

    # Tile for Educational Qualifications
    with col1:
        st.markdown("<div class='tile'><div class='tile-heading'>Educational Qualifications</div>", unsafe_allow_html=True)
        if edu_qual:
            for edu in edu_qual:
                st.write(f"- {edu}")
        else:
            st.write("No educational qualifications available.")
        st.markdown("</div>", unsafe_allow_html=True)

    # Tile for Job Experiences
    with col2:
        st.markdown("<div class='tile'><div class='tile-heading'>Job Experiences</div>", unsafe_allow_html=True)
        if job_exp:
            for job in job_exp:
                st.write(f"- {job}")
        else:
            st.write("No job experiences available.")
        st.markdown("</div>", unsafe_allow_html=True)

    # Tile for Skills
    with col1:
        st.markdown("<div class='tile'><div class='tile-heading'>Skills</div>", unsafe_allow_html=True)
        if skills:
            st.write(", ".join(skills))
        else:
            st.write("No skills available.")
        st.markdown("</div>", unsafe_allow_html=True)

    # Tile for Keywords
    with col2:
        st.markdown("<div class='tile'><div class='tile-heading'>Keywords</div>", unsafe_allow_html=True)
        if keywords:
            st.write(", ".join(keywords))
        else:
            st.write("No keywords available.")
        st.markdown("</div>", unsafe_allow_html=True)

# Updated Feature: Add Job Description with Job ID
def natural_language_jd_addition():
    # Heading for this section
    st.markdown("<div class='section-heading'>Add a Job Description</div>", unsafe_allow_html=True)

    # Input for Job ID
    jd_id_input = st.text_input("Enter Job ID", placeholder="e.g., 1234abcd-5678-efgh-9101-ijklmnopqrs")

    # Input for Job Description
    jd_input = st.text_area("Paste a Job Description (JD) in natural language:")

    # Button to store the JD
    if st.button("Store Job Description"):
        # Validate inputs
        if not jd_id_input.strip():
            st.error("Please provide a valid Job ID.")
            return
        if not jd_input.strip():
            st.error("Please provide a valid Job Description.")
            return

        # Prepare payload for Lambda function
        payload = {
            "jobId": jd_id_input.strip(),
            "jobDescription": jd_input.strip()
        }

        try:
            # Send POST request to Lambda function
            response = requests.post(lambda_url, json=payload)
            if response.status_code == 200:
                lambda_response = response.json()
                st.success(f"Job Description stored successfully! Job ID: {jd_id_input}")
            else:
                st.error(f"Lambda error: {response.json()}")
        except Exception as e:
            st.error(f"Error: {e}")

# Main application logic
def main():
    # Display metrics at the top of the app
    st.markdown("<div class='metrics-container'>", unsafe_allow_html=True)
    total_resumes = resume_collection.count_documents({})
    total_jds = jd_collection.count_documents({})
    col1, col2 = st.columns(2)
    with col1:
        st.metric(label="Total Resumes", value=total_resumes)
    with col2:
        st.metric(label="Total Job Descriptions", value=total_jds)
    st.markdown("</div>", unsafe_allow_html=True)

    # Add a new Job Description
    natural_language_jd_addition()

    # Section for selecting and processing a Job Description
    st.markdown("<div class='section-heading'>Selected Job Description</div>", unsafe_allow_html=True)
    col1, col2 = st.columns([1, 2])
    with col1:
        num_resumes_to_fetch = st.number_input(
            "Enter the Number of Resumes to Fetch", min_value=1, max_value=total_resumes, value=10, step=1
        )
    with col2:
        jds = list(jd_collection.find())
        jd_options = {jd.get("jobId", "N/A"): jd for jd in jds}  # Use jobId for selection
        selected_jd_id = st.selectbox("Select a Job Description:", list(jd_options.keys()))

    if jd_options and selected_jd_id:
        selected_jd = jd_options[selected_jd_id]
        st.write(f"**Job Description ID:** {selected_jd_id}")
        st.write(f"**Job Description:** {selected_jd.get('jobDescription', 'N/A')}")

        jd_embedding = selected_jd.get("embedding")
        if jd_embedding:
            st.subheader("Top Matches")
            matches = find_top_matches(jd_embedding, num_candidates=num_resumes_to_fetch)
            if matches:
                match_df = pd.DataFrame(matches[:num_resumes_to_fetch])
                st.dataframe(match_df, use_container_width=True, height=300)
                names_to_ids = {match["Name"]: match["Resume ID"] for match in matches[:num_resumes_to_fetch]}
                selected_name = st.selectbox("Select a Resume to View Details:", list(names_to_ids.keys()))
                if selected_name:
                    st.subheader("Resume Details")
                    display_resume_details(names_to_ids[selected_name])
            else:
                st.info("No matching resumes found.")
        else:
            st.error("Embedding not found for the selected JD.")

    # Display all resumes (Previously commented section restored)
    st.header("All Resumes")
    resumes = resume_collection.find()
    resumes_data = [{"Resume ID": resume.get("resumeId"), "Name": resume.get("name", "N/A")} for resume in resumes]
    resumes_df = pd.DataFrame(resumes_data)
    st.dataframe(resumes_df, use_container_width=True, height=400)

    # Display all Job Descriptions
    st.header("All Job Descriptions")
    jd_data = [
        {"JD ID": jd.get("jobId"), "Job Description": jd.get("jobDescription", "N/A")}  # Updated to use jobDescription
        for jd in jds
    ]
    jd_df = pd.DataFrame(jd_data)
    st.dataframe(jd_df, use_container_width=True, height=200)

if __name__ == "__main__":
    load_css()
    main()
