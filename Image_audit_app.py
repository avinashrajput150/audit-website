import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import io

# --- CONFIGURATION ---
ADMIN_PASSWORD = "admin123" # Aapka Admin Password
DB_NAME = "realtime_audit.db"

# --- DATABASE LOGIC ---
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # Main Table: Yahan 2 lakh rows easily handle hongi
    c.execute('''CREATE TABLE IF NOT EXISTS audit_base 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  store_id TEXT, store_name TEXT, image_link TEXT, 
                  assigned_user TEXT, status TEXT DEFAULT 'Pending', 
                  window_exit TEXT, shelves TEXT, planogram TEXT,
                  audit_date TEXT, audit_time TEXT)''')
    conn.commit()
    conn.close()

init_db()

def run_query(query, params=()):
    with sqlite3.connect(DB_NAME) as conn:
        return pd.read_sql_query(query, conn, params=params)

def execute_db(query, params=()):
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute(query, params)
        conn.commit()

# --- UI DESIGN ---
st.set_page_config(page_title="Retail Audit Website", layout="wide")

# Sidebar for Navigation
st.sidebar.title("🔐 Login Portal")
app_mode = st.sidebar.selectbox("Choose Mode", ["Auditor Login", "Admin Dashboard"])

# --- 1. ADMIN DASHBOARD (Data Upload & Management) ---
if app_mode == "Admin Dashboard":
    st.title("👨‍💼 Admin Control Panel")
    pwd = st.sidebar.text_input("Enter Admin Password", type="password")
    
    if pwd == ADMIN_PASSWORD:
        tab1, tab2, tab3 = st.tabs(["Upload Data", "Live Tracking", "Download Reports"])
        
        with tab1:
            st.subheader("Upload 2 Lakh+ Row Base")
            uploaded_file = st.file_uploader("Upload Excel/CSV", type=["csv", "xlsx"])
            if uploaded_file:
                if st.button("Push Data to Website"):
                    df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
                    # Mapping columns
                    df['status'] = 'Pending'
                    conn = sqlite3.connect(DB_NAME)
                    df.to_sql('audit_base', conn, if_exists='append', index=False)
                    st.success(f"Successfully uploaded {len(df)} rows!")

        with tab2:
            st.subheader("Real-Time Auditor Performance")
            stats_df = run_query("SELECT status, assigned_user FROM audit_base")
            if not stats_df.empty:
                col1, col2, col3 = st.columns(3)
                col1.metric("Total Base", len(stats_df))
                col2.metric("Audited", len(stats_df[stats_df['status'] == 'Audited']))
                col3.metric("Pending", len(stats_df[stats_df['status'] == 'Pending']))
                
                # Bar chart for users
                user_perf = stats_df[stats_df['status'] == 'Audited'].groupby('assigned_user').size().reset_index(name='Done')
                st.bar_chart(user_perf.set_index('assigned_user'))

        with tab3:
            st.subheader("Filter & Download Reports")
            col_a, col_b = st.columns(2)
            with col_a:
                d_filter = st.date_input("Select Audit Date")
            with col_b:
                u_filter = st.text_input("Filter by User ID")

            query = "SELECT * FROM audit_base WHERE 1=1"
            if u_filter: query += f" AND assigned_user = '{u_filter}'"
            
            report_df = run_query(query)
            st.dataframe(report_df)
            
            # Export to Excel
            towrite = io.BytesIO()
            report_df.to_excel(towrite, index=False, header=True)
            st.download_button(label="Download Excel Report", data=towrite.getvalue(), file_name="audit_report.xlsx")

    elif pwd != "":
        st.error("Incorrect Admin Password")

# --- 2. AUDITOR PORTAL (Work Interface) ---
else:
    st.title("📸 Image Audit Portal")
    user_id = st.sidebar.text_input("Enter Your User ID")
    
    if user_id:
        # Fetch 1 image at a time that is Pending and assigned to this user
        data = run_query("SELECT * FROM audit_base WHERE assigned_user=? AND status='Pending' LIMIT 1", (user_id,))
        
        if not data.empty:
            row = data.iloc[0]
            st.warning(f"Auditing Store: {row['store_id']} | {row['store_name']}")
            
            c1, c2 = st.columns([1.8, 1])
            with c1:
                st.image(row['image_link'], caption="Current Store Image", use_container_width=True)
            
            with c2:
                st.info("Fill Audit Details")
                w_exit = st.selectbox("Window Exit", ["Select", "Yes", "No", "Not Clear"])
                sh = st.selectbox("No. of Shelves", ["1", "2", "3", "4", "5+"])
                pl = st.selectbox("Planogram Match", ["Match", "Mismatch", "Empty"])
                
                if st.button("Submit & Next Image"):
                    now = datetime.now()
                    date_str = now.strftime("%Y-%m-%d")
                    time_str = now.strftime("%H:%M:%S")
                    
                    execute_db('''UPDATE audit_base SET 
                                  status='Audited', window_exit=?, shelves=?, 
                                  planogram=?, audit_date=?, audit_time=? 
                                  WHERE id=?''', 
                               (w_exit, sh, pl, date_str, time_str, row['id']))
                    
                    st.success("Audit Recorded Successfully!")
                    st.rerun()
        else:
            st.balloons()
            st.success("No pending images assigned to you! Contact Admin.")
    else:
        st.info("Please enter your User ID in the sidebar to start.")
