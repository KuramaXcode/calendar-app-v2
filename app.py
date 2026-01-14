import os, json, shutil, zipfile
from io import BytesIO
from datetime import datetime

import streamlit as st
import pandas as pd
import requests
from PIL import Image

from engine.calendar_generator import (
    generate_calendar_with_templates,
    regenerate_single_month
)
from engine.drive_uploader import upload_final_folder_to_drive
from engine.drive_reader import drive_partner_exists


# =================================================
# PAGE CONFIG
# =================================================
st.set_page_config(page_title="Partner Calendar Generator", layout="wide")
st.title("Partner Calendar Generator")
st.info("⏳ Generation may take 2–5 minutes per partner. Please do not refresh.")


# =================================================
# CONSTANTS
# =================================================
GOOGLE_SHEET_CSV_URL = (
    "https://docs.google.com/spreadsheets/d/e/"
    "2PACX-1vQvfwcOfqApQ0YkBjPtLJcCLQO1V67xVQXBirYPuHyKP8PWiHpSDsqbzb0R08Qcdutkv06LRGYNN1kN"
    "/pub?gid=802117755&output=csv"
)

PARTNER_NAME_COL = "Partner Name"
FILE_ID_COL = "File ID"

OUTPUT_ROOT = "calendar_outputs"
QUEUE_FILE = os.path.join(OUTPUT_ROOT, "_queue.json")
os.makedirs(OUTPUT_ROOT, exist_ok=True)

MONTHS = [
    "January","February","March","April","May","June",
    "July","August","September","October","November","December"
]


# =================================================
# HELPERS
# =================================================
def safe(name):
    return name.replace(" ", "_")


def load_image_from_drive(file_id):
    url = f"https://drive.google.com/uc?id={file_id}"
    r = requests.get(url)
    r.raise_for_status()
    return Image.open(BytesIO(r.content)).convert("RGB")


def paths(partner):
    base = os.path.join(OUTPUT_ROOT, safe(partner))
    return {
        "base": base,
        "draft": os.path.join(base, "draft"),
        "final": os.path.join(base, "final"),
        "status": os.path.join(base, "status.json"),
    }


def init_state(partner):
    p = paths(partner)
    os.makedirs(p["draft"], exist_ok=True)
    if not os.path.exists(p["status"]):
        with open(p["status"], "w") as f:
            json.dump({
                "partner": partner,
                "state": "draft",
                "finalized_at": None
            }, f, indent=2)


def load_status(partner):
    with open(paths(partner)["status"]) as f:
        return json.load(f)


def save_status(partner, status):
    with open(paths(partner)["status"], "w") as f:
        json.dump(status, f, indent=2)


def is_finalized(partner):
    status_file = paths(partner)["status"]
    if not os.path.exists(status_file):
        return False
    with open(status_file) as f:
        return json.load(f).get("state") == "final"


def has_draft(partner):
    p = paths(partner)
    return os.path.exists(p["draft"]) and len(os.listdir(p["draft"])) > 0


def zip_final(partner):
    p = paths(partner)
    zip_path = os.path.join(OUTPUT_ROOT, f"{safe(partner)}_calendar.zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for f in os.listdir(p["final"]):
            z.write(os.path.join(p["final"], f), arcname=f)
    return zip_path


# ---------------- QUEUE HELPERS ----------------
def load_queue():
    if not os.path.exists(QUEUE_FILE):
        return {"state": "stopped", "current_index": 0, "items": []}
    with open(QUEUE_FILE) as f:
        return json.load(f)


def save_queue(queue):
    with open(QUEUE_FILE, "w") as f:
        json.dump(queue, f, indent=2)


@st.cache_data
def load_sheet():
    return pd.read_csv(GOOGLE_SHEET_CSV_URL)


# =================================================
# LOAD SHEET (MUST COME FIRST)
# =================================================
st.subheader("1️⃣ Load Partner Data")
if st.button("Load partners"):
    st.session_state.df = load_sheet()

if "df" not in st.session_state:
    st.stop()

df = st.session_state.df

# =================================================
# PARTNER LIST
# =================================================
def finalized_partners():
    done = set()
    for d in os.listdir(OUTPUT_ROOT):
        status_file = os.path.join(OUTPUT_ROOT, d, "status.json")
        if os.path.exists(status_file):
            with open(status_file) as f:
                s = json.load(f)
                if s.get("state") == "final":
                    done.add(s.get("partner"))
    return done


finalized = finalized_partners()

def highlight(row):
    if row[PARTNER_NAME_COL] in finalized:
        return ["background-color: #8fd19e"] * len(row)
    return [""] * len(row)

st.subheader("Partner List (Finalized in green)")
st.dataframe(df.style.apply(highlight, axis=1), use_container_width=True)


# =================================================
# QUEUE SELECTION
# =================================================
st.subheader("2️⃣ Select up to 10 partners for queue")

selected = st.multiselect(
    "Choose partners",
    df[PARTNER_NAME_COL].dropna().tolist(),
    max_selections=10
)

queue = load_queue()

if st.button("➕ Add to Queue"):
    for name in selected:
        if is_finalized(name):
            continue
        if name not in [i["partner"] for i in queue["items"]]:
            row = df[df[PARTNER_NAME_COL] == name].iloc[0]
            queue["items"].append({
                "partner": name,
                "file_id": row[FILE_ID_COL],
                "status": "pending"
            })
    save_queue(queue)
    st.success("Added to queue")
    st.rerun()


# =================================================
# QUEUE CONTROLS
# =================================================
st.subheader("3️⃣ Processing Queue")
st.table(queue["items"])

c1, c2, c3, c4 = st.columns(4)

if c1.button("▶️ Start Queue"):
    queue["state"] = "running"
    save_queue(queue)
    st.rerun()

if c2.button("⏸ Pause Queue"):
    queue["state"] = "paused"
    save_queue(queue)

if c3.button("⏹ Stop Queue"):
    queue["state"] = "stopped"
    queue["current_index"] = 0
    save_queue(queue)

if c4.button("🧹 Clear Queue"):
    save_queue({"state": "stopped", "current_index": 0, "items": []})
    st.rerun()


# =================================================
# AUTO PROCESS QUEUE
# =================================================
queue = load_queue()

if queue["state"] == "running":
    idx = queue["current_index"]

    if idx >= len(queue["items"]):
        queue["state"] = "stopped"
        save_queue(queue)
        st.success("Queue completed 🎉")
        st.rerun()

    item = queue["items"][idx]
    partner = item["partner"]
    file_id = item["file_id"]

    st.info(f"Processing {partner} ({idx+1}/{len(queue['items'])})")

    init_state(partner)

    if is_finalized(partner) or has_draft(partner):
        queue["current_index"] += 1
        save_queue(queue)
        st.rerun()

    img = load_image_from_drive(file_id)
    results = generate_calendar_with_templates(img)

    for m, im in results.items():
        im.save(os.path.join(paths(partner)["draft"], f"{m}.jpg"), quality=95)

    queue["current_index"] += 1
    save_queue(queue)
    st.rerun()

# =================================================
# REVIEW / REDO / FINALIZE  ✅ NOW SAFE
# =================================================
st.subheader("4️⃣ Review / Redo / Finalize")

partner = st.selectbox(
    "Select partner",
    df[PARTNER_NAME_COL].dropna().tolist()
)

partner_folder = safe(partner)

if drive_partner_exists(partner_folder):
    st.info("📂 Existing calendar found in Google Drive")
else:
    st.warning("📭 No calendar found in Google Drive")

init_state(partner)
status = load_status(partner)
p = paths(partner)

img_dir = None
allow_redo = False

if status["state"] == "draft" and has_draft(partner):
    img_dir = p["draft"]
    allow_redo = True
    st.info("📝 Draft mode — review and redo individual months")

elif status["state"] == "final" and os.path.exists(p["final"]):
    img_dir = p["final"]
    st.success("✅ Finalized calendar")

if img_dir:
    cols = st.columns(4)
    for i, m in enumerate(MONTHS):
        img_path = os.path.join(img_dir, f"{m}.jpg")
        if not os.path.exists(img_path):
            continue
        with cols[i % 4]:
            st.image(img_path, caption=m, use_container_width=True)
            if allow_redo:
                if st.button(f"🔁 Redo {m}", key=f"redo_{partner}_{m}"):
                    img = load_image_from_drive(
                        df[df[PARTNER_NAME_COL] == partner].iloc[0][FILE_ID_COL]
                    )
                    new = regenerate_single_month(img, m)
                    new.save(img_path, quality=95)
                    st.rerun()

if status["state"] == "draft" and has_draft(partner):
    if st.button("✅ Finalize Calendar"):
        os.makedirs(p["final"], exist_ok=True)
        for f in os.listdir(p["draft"]):
            shutil.copy(os.path.join(p["draft"], f), os.path.join(p["final"], f))

        status["state"] = "final"
        status["finalized_at"] = datetime.utcnow().isoformat()
        save_status(partner, status)

        try:
            upload_final_folder_to_drive(safe(partner), p["final"])
            st.success("✅ Calendar finalized and backed up to Google Drive")
        except Exception as e:
            st.warning("⚠️ Calendar finalized, but Drive upload failed")
            st.exception(e)

        st.rerun()

if status["state"] == "final":
    zip_path = zip_final(partner)
    with open(zip_path, "rb") as f:
        st.download_button(
            "⬇️ Download Final Calendar (ZIP)",
            f,
            file_name=os.path.basename(zip_path),
            mime="application/zip"
        )
