import streamlit as st
import pandas as pd
import requests
import os
import zipfile
import tempfile
from datetime import datetime

# ------------------------------
# Download file from URL
# ------------------------------
def download_file(url, folder, file_name):
    """
    Downloads a file from an internal URL into the specified folder.
    Works only inside the internal network where URLs are accessible.
    """
    try:
        response = requests.get(url, stream=True)
        if response.status_code == 200:
            file_path = os.path.join(folder, file_name)
            with open(file_path, "wb") as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)
            return True
        else:
            st.warning(f"Failed to download {file_name} - Status {response.status_code}")
            return False
    except Exception as e:
        st.warning(f"Error downloading {file_name}: {e}")
        return False

# ------------------------------
# STREAMLIT UI
# ------------------------------
st.set_page_config(page_title="Finance File Downloader", page_icon="📁")
st.title("📁 Finance File Downloader Dashboard (Internal Use)")

st.write("""
Upload a CSV file with these columns:
- RESTAURANT_ID  
- INVOICE_URL  
- PAYMENT_ADVICE_URL  
- ANNEXURE_URL  
- DT  

The system will:
1. Download all files from internal URLs  
2. Organize by Restaurant ID → Year → File Type  
3. Create ZIP file(s) (splits if >23 MB)  
4. Allow download directly from the dashboard  
""")

uploaded_file = st.file_uploader("Upload CSV file", type=["csv"])

if st.button("Start Processing"):

    if uploaded_file is None:
        st.error("Please upload a CSV file.")
        st.stop()

    # Read CSV and normalize headers
    df = pd.read_csv(uploaded_file)
    df.columns = df.columns.str.lower()

    required_cols = ["restaurant_id", "invoice_url", "payment_advice_url", "annexure_url", "dt"]
    for col in required_cols:
        if col not in df.columns:
            st.error(f"CSV missing required column: {col}")
            st.stop()

    temp_dir = tempfile.mkdtemp()
    progress = st.progress(0)
    total = len(df)

    for idx, row in df.iterrows():
        rid = str(row["restaurant_id"])
        dt = pd.to_datetime(row["dt"])
        date_str = dt.strftime("%Y_%m_%d")

        # Create folder structure
        rid_folder = os.path.join(temp_dir, f"RID_{rid}", str(dt.year))
        folders = {
            "Invoices": os.path.join(rid_folder, "Invoices"),
            "Payment_Advices": os.path.join(rid_folder, "Payment_Advices"),
            "Annexures": os.path.join(rid_folder, "Annexures")
        }
        for f in folders.values():
            os.makedirs(f, exist_ok=True)

        # Download files
        if pd.notna(row["invoice_url"]):
            download_file(row["invoice_url"], folders["Invoices"], f"Invoice_{date_str}.pdf")
        if pd.notna(row["payment_advice_url"]):
            download_file(row["payment_advice_url"], folders["Payment_Advices"], f"Payment_Advice_{date_str}.pdf")
        if pd.notna(row["annexure_url"]):
            download_file(row["annexure_url"], folders["Annexures"], f"Annexure_{date_str}.xlsx")

        progress.progress((idx + 1) / total)

    # ------------------------------
    # Create ZIP(s)
    # ------------------------------
    MAX_SIZE_MB = 23
    MAX_SIZE = MAX_SIZE_MB * 1024 * 1024  # bytes
    zip_path = os.path.join(temp_dir, "output.zip")

    with zipfile.ZipFile(zip_path, "w") as zipf:
        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                file_path = os.path.join(root, file)
                if os.path.isfile(file_path):
                    zipf.write(file_path, arcname=os.path.relpath(file_path, temp_dir))

    zip_size = os.path.getsize(zip_path)

    st.success("Processing Completed!")

    if zip_size <= MAX_SIZE:
        with open(zip_path, "rb") as f:
            st.download_button("Download ZIP File", f, file_name="finance_output.zip")
    else:
        st.info(f"ZIP size is {zip_size / (1024*1024):.2f} MB. Splitting into multiple parts...")
        part_num = 1
        with open(zip_path, "rb") as f:
            while True:
                chunk = f.read(MAX_SIZE)
                if not chunk:
                    break
                part_path = os.path.join(temp_dir, f"finance_output_part{part_num}.zip")
                with open(part_path, "wb") as pf:
                    pf.write(chunk)
                with open(part_path, "rb") as pf:
                    st.download_button(f"Download ZIP Part {part_num}", pf, file_name=f"finance_output_part{part_num}.zip")
                part_num += 1
