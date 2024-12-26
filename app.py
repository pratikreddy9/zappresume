import streamlit as st
import pandas as pd
from pymongo import MongoClient
import requests
import re
from rapidfuzz import fuzz
import os
from multiprocessing import Pool, cpu_count
from functools import partial
import numpy as np

# Disable Streamlit's file watcher to avoid inotify limit issues
os.environ["STREAMLIT_SERVER_FILE_WATCHER_TYPE"] = "none"

# MongoDB connection details
mongo_uri = st.secrets["mongo"]["uri"]
client = MongoClient(mongo_uri)

# Accessing the database and collections
db = client["resumes_database"]
resume_collection = db["resumes"]
jd_collection = db["job_description"]

# Lambda function URL for processing job descriptions
lambda_url = "https://ljlj3twvuk.execute-api.ap-south-1.amazonaws.com/default/getJobDescriptionVector"

# Set Streamlit page configuration
st.set_page_config(layout="wide")

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
        </style>
        """,
        unsafe_allow_html=True,
    )

def preprocess_keyword(keyword):
    """Preprocess a keyword by normalizing its format."""
    keyword = keyword.casefold().strip()
    keyword = re.sub(r'[^\w\s]', '', keyword)
    return ' '.join(sorted(keyword.split()))

def fuzzy_match(keyword, target_keywords, threshold=80):
    """Perform fuzzy matching with a similarity threshold."""
    return any(fuzz.ratio(keyword, tk) >= threshold for tk in target_keywords)

def calculate_vector_similarity(resume_embedding, jd_embedding):
    """Calculate cosine similarity between two vectors."""
    if not resume_embedding or not jd_embedding:
        return 0
    
    dot_product = np.dot(resume_embedding, jd_embedding)
    magnitude_resume = np.linalg.norm(resume_embedding)
    magnitude_jd = np.linalg.norm(jd_embedding)
    
    if magnitude_resume == 0 or magnitude_jd == 0:
        return 0
        
    return dot_product / (magnitude_resume * magnitude_jd)

def process_resume_batch(args):
    """Process a batch of resumes with both keyword and vector matching."""
    batch, jd_keywords, jd_embedding = args
    results = []
    
    jd_keywords_normalized = [preprocess_keyword(keyword) for keyword in jd_keywords]
    
    for resume in batch:
        # Skip if no keywords or embedding
        if not resume.get("keywords") or not resume.get("embedding"):
            continue
            
        # Calculate keyword match
        resume_keywords_normalized = [preprocess_keyword(keyword) for keyword in resume.get("keywords", [])]
        matching_keywords = [
            keyword for keyword in jd_keywords_normalized
            if any(preprocess_keyword(keyword) == rk or fuzzy_match(keyword, [rk]) for rk in resume_keywords_normalized)
        ]
        
        keyword_match_percentage = round((len(matching_keywords) / len(jd_keywords_normalized) * 100), 2) if jd_keywords_normalized else 0
        
        # Calculate vector similarity
        vector_similarity = calculate_vector_similarity(resume.get("embedding"), jd_embedding)
        vector_match_percentage = round(vector_similarity * 100, 2)
        
        # Combined score (weighted average)
        combined_score = (keyword_match_percentage * 0.4) + (vector_match_percentage * 0.6)
        
        # Prepare result data
        skills = ", ".join(resume.get("keywords") or [])
        job_experiences = [
            f"{job.get('title', 'N/A')} at {job.get('companyName', 'N/A')}" 
            for job in resume.get("jobExperiences") or []
        ]
        educational_qualifications = [
            f"{edu.get('degree', 'N/A')} in {edu.get('field', 'N/A')}" 
            for edu in resume.get("educationalQualifications") or []
        ]
        
        results.append({
            "Resume ID": resume.get("resumeId"),
            "Name": resume.get("name", "N/A"),
            "Keyword Match %": keyword_match_percentage,
            "Vector Match %": vector_match_percentage,
            "Combined Score": combined_score,
            "Matching Keywords": matching_keywords,
            "Skills": skills,
            "Job Experiences": "; ".join(job_experiences),
            "Educational Qualifications": "; ".join(educational_qualifications),
        })
    
    return results

def find_matches(jd_keywords, jd_embedding, num_candidates=15000):
    """Find matches using parallel processing for both keyword and vector matching."""
    # Get all resumes
    resumes = list(resume_collection.find().limit(num_candidates * 2))
    
    # Remove duplicates based on email and phone
    seen_keys = set()
    unique_resumes = []
    for resume in resumes:
        key = f"{resume.get('email')}_{resume.get('contactNo')}"
        if key not in seen_keys:
            seen_keys.add(key)
            unique_resumes.append(resume)
            if len(unique_resumes) >= num_candidates:
                break
    
    # Split resumes into batches for parallel processing
    num_processes = cpu_count()
    batch_size = max(1, len(unique_resumes) // num_processes)
    batches = [unique_resumes[i:i + batch_size] for i in range(0, len(unique_resumes), batch_size)]
    
    # Prepare arguments for parallel processing
    process_args = [(batch, jd_keywords, jd_embedding) for batch in batches]
    
    # Process batches in parallel
    with Pool(processes=num_processes) as pool:
        results = pool.map(process_resume_batch, process_args)
    
    # Combine and sort results
    all_results = [item for sublist in results for item in sublist]
    return sorted(all_results, key=lambda x: x["Combined Score"], reverse=True)

def main():
    st.markdown("<div class='metrics-container'>", unsafe_allow_html=True)

    total_resumes = resume_collection.count_documents({})
    total_jds = jd_collection.count_documents({})
    col1, col2 = st.columns(2)

    with col1:
        st.metric(label="Total Resumes", value=total_resumes)
    with col2:
        st.metric(label="Total Job Descriptions", value=total_jds)

    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='section-heading'>Select Job Description for Matching</div>", unsafe_allow_html=True)
    jds = list(jd_collection.find())
    jd_mapping = {jd.get("jobDescription", "N/A"): jd.get("jobId", "N/A") for jd in jds}
    selected_jd_description = st.selectbox("Select a Job Description:", list(jd_mapping.keys()))

    if selected_jd_description:
        selected_jd_id = jd_mapping[selected_jd_description]
        selected_jd = next(jd for jd in jds if jd.get("jobId") == selected_jd_id)
        jd_keywords = selected_jd.get("structured_query", {}).get("keywords", [])
        jd_embedding = selected_jd.get("embedding")

        if not jd_embedding:
            st.error("Embedding not found for the selected JD.")
            return

        st.write(f"**Job Description ID:** {selected_jd_id}")
        st.write(f"**Job Description:** {selected_jd_description}")

        # Find matches using combined approach
        matches = find_matches(jd_keywords, jd_embedding)
        
        if matches:
            st.subheader("Top Matches (Combined Scoring)")
            matches_df = pd.DataFrame(matches).astype(str)
            st.dataframe(matches_df, use_container_width=True, height=500)
        else:
            st.info("No matching resumes found.")

if __name__ == "__main__":
    load_css()
    main()
