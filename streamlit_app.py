import streamlit as st
import pandas as pd
import numpy as np
import os
from typing import List
import gspread
from google.oauth2.service_account import Credentials

# === CONFIG ===
SYMPTOMS: List[str] = [
    'Atelectasis','Cardiomegaly','Consolidation','Edema',
    'Enlarged Cardiomediastinum','Fracture','Lung Lesion',
    'Lung Opacity','No Finding','Pleural Effusion','Pleural Other',
    'Pneumonia','Pneumothorax','Support Devices'
]

# === Google Sheets setup ===
SHEET_URL = st.secrets["gsheet"]["url"]

@st.cache_resource
def connect_gsheet():
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
    )
    client = gspread.authorize(creds)
    return client.open_by_url(SHEET_URL)

def append_to_gsheet(worksheet_name, row_dict):
    sh = connect_gsheet()
    ws = sh.worksheet(worksheet_name)
    headers = ws.row_values(1)
    if not headers:
        headers = list(row_dict.keys())
        ws.append_row(headers)
    
    def clean_value(v):
        return "" if pd.isna(v) else str(v)

    values = [clean_value(row_dict.get(h, "")) for h in headers]
    ws.append_row(values)

@st.cache_data(ttl=2)
def load_all_from_gsheet(worksheet_name):
    sh = connect_gsheet()
    ws = sh.worksheet(worksheet_name)
    data = ws.get_all_records()
    return pd.DataFrame(data) if data else pd.DataFrame()

def get_progress_from_gsheet(user):
    quant_done = set()
    df_quant = load_all_from_gsheet("Annotations")
    if not df_quant.empty:
        user_quant = df_quant[df_quant["annotator"] == user]
        quant_done = set(
            user_quant["study_id"].astype(str) + "__" + user_quant["source_label"]
        )
    return quant_done

# === Credentials ===
USERS = st.secrets["credentials"]

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

# === Login ===
def login():
    st.title("🔐 Login Required")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        if username in USERS and USERS[username] == password:
            st.session_state.logged_in = True
            st.session_state.username = username
            st.rerun()
        else:
            st.error("❌ Invalid username or password")

if not st.session_state.logged_in:
    login()
    st.stop()

# === Load and Prepare Data ===
df1 = pd.read_csv("selected_samples_new.csv")
df1["source_file"], df1["source_label"] = "slog.csv", "slog"

df2 = pd.read_csv("selected_samples_00_new.csv")
df2["source_file"], df2["source_label"] = "lam0.csv", "lam0"

QUANT_TARGET_REPORTS = df1.shape[0] + df2.shape[0]

if "prepared" not in st.session_state:
    user_seed = abs(hash(st.session_state.username)) % (2**32)
    pool_df = pd.concat([df1, df2], ignore_index=True)
    pool_df["uid"] = pool_df["study_id"].astype(str) + "__" + pool_df["source_label"]
    # Shuffle for the specific user
    st.session_state.quant_df = pool_df.sample(frac=1, random_state=user_seed).reset_index(drop=True)
    st.session_state.prepared = True

# === Progress Tracking ===
user = st.session_state.username
quant_done = get_progress_from_gsheet(user)

# Filter out what's already done
available_df = st.session_state.quant_df[
    ~st.session_state.quant_df["uid"].isin(quant_done)
].reset_index(drop=True)

# === Sidebar ===
st.sidebar.success(f"Logged in as {st.session_state.username}")
pages = ["Annotate"]
if st.session_state.username == "admin":
    pages.append("Review Results")

st.sidebar.markdown("### 📊 Progress")
st.sidebar.write(f"**Completed:** {len(quant_done)} / {QUANT_TARGET_REPORTS}")

page = st.sidebar.radio("📂 Navigation", pages)

# === Annotation Page ===
if page == "Annotate":
    if available_df.empty:
        st.balloons()
        st.header("✅ All Done!")
        st.success("You have completed all assigned annotations.")
    else:
        # Always take the first row from the filtered 'available' dataframe
        row = available_df.iloc[0]
        study_id = row["study_id"]
        report_text = row["reports_preds"]

        st.header(f"Report {len(quant_done) + 1} of {QUANT_TARGET_REPORTS}")
        st.caption(f"Study ID: {study_id} | Source: {row['source_label']}")
        
        st.text_area("Report Text", report_text, height=300, disabled=True)
        
        st.subheader("Symptom Evaluation")
        st.info("Select the presence of each symptom based on the text above.")

        # Organize inputs into a cleaner grid or list
        scores = {}
        for symptom in SYMPTOMS:
            scores[symptom] = st.radio(
                label=f"**{symptom}**",
                options=['Yes', 'No', 'May be'],
                horizontal=True,
                key=f"q_{study_id}_{symptom}"
            )

        if st.button("Submit Annotation", use_container_width=True):
            result = {
                "phase": "quant",
                "study_id": study_id,
                "report_text": report_text,
                "source_file": row["source_file"],
                "source_label": row["source_label"],
                "annotator": user,
                **{f"symptom_scores.{k}": v for k, v in scores.items()}
            }
            
            with st.spinner("Saving to Google Sheets..."):
                append_to_gsheet("Annotations", result)
                st.cache_data.clear() # Force refresh progress
                st.rerun()

elif page == "Review Results" and st.session_state.username == "admin":
    st.header("Admin Review")
    all_data = load_all_from_gsheet("Annotations")
    st.dataframe(all_data)