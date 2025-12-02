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
    try:
        response = requests.get(url, stream=True)
        if response.status_code == 200:
            with open(os.path.join(folder, file_name), "wb") as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)
        else:
            print(f"Failed to download: {url}")
    except Exception as e:
        print(f"Error downloading {url}: {e}")

# ------------------------------
# STREAMLIT UI
# ------------------------------
st.set_page_config(page_title="Finance File Downloader", page_icon="📁")

st.title("📁 Finance File Downloader Dashboard (CSV → Files → ZIP)")

st.write("""
Upload a CSV file containing columns like:
- RESTAURANT_ID  
- INVOICE_URL  
- PAYMENT_ADVICE_URL  
- ANNEXURE_URL  
- DT  

The system will:
1. Download all URLs  
2. Arrange into folders  
3. Create a ZIP file (splits into parts if >23 MB)  
4. Allow you to download it  
""")

uploaded_file = st.file_uploader("Upload the CSV file", type=["csv"])

if st.button("Start Processing"):

    if uploaded_file is None:
        st.error("Please upload a CSV file.")
        st.stop()

    # Read CSV and convert headers to lowercase
    df = pd.read_csv(uploaded_file)
    df.columns = df.columns.str.lower()

    required_cols = ["restaurant_id", "invoice_url", "payment_advice_url", "annexure_url", "dt"]
    for col in required_cols:
        if col not in df.columns:
            st.error(f"CSV is missing required column: {col} (case-insensitive)")
            st.stop()

    temp_dir = tempfile.mkdtemp()
    progress = st.progress(0)
    total = len(df)

    for idx, row in df.iterrows():

        rid = str(row["restaurant_id"])
        invoice_url = row["invoice_url"]
        pa_url = row["payment_advice_url"]
        ann_url = row["annexure_url"]
        dt = pd.to_datetime(row["dt"])

        rid_folder = os.path.join(temp_dir, f"RID_{rid}")
        year_folder = os.path.join(rid_folder, str(dt.year))
        inv_folder = os.path.join(year_folder, "Invoices")
        pa_folder = os.path.join(year_folder, "Payment_Advices")
        ann_folder = os.path.join(year_folder, "Annexures")

        for f in [inv_folder, pa_folder, ann_folder]:
            os.makedirs(f, exist_ok=True)

        date_str = dt.strftime("%Y_%m_%d")

        if pd.notna(invoice_url):
            download_file(invoice_url, inv_folder, f"Invoice_{date_str}.pdf")

        if pd.notna(pa_url):
            download_file(pa_url, pa_folder, f"Payment_Advice_{date_str}.pdf")

        if pd.notna(ann_url):
            download_file(ann_url, ann_folder, f"Annexure_{date_str}.xlsx")

        progress.progress((idx + 1) / total)

    # ------------------------------
    # Create ZIP (split if >23 MB)
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
        # Single ZIP
        with open(zip_path, "rb") as f:
            st.download_button("Download ZIP File", f, file_name="finance_output.zip")
    else:
        # Split into multiple parts
        st.info(f"The total ZIP size is {zip_size / (1024*1024):.2f} MB. Splitting into multiple parts...")
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
