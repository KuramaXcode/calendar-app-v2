import streamlit as st
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

DRIVE_SCOPE = ["https://www.googleapis.com/auth/drive"]
ROOT_FOLDER_NAME = "AI_Calendar_Final"


def get_drive_service():
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=DRIVE_SCOPE
    )
    return build("drive", "v3", credentials=creds)

def drive_partner_exists(partner_folder_name: str) -> bool:
    service = get_drive_service()

    # Find root folder
    root_query = (
        f"name='{ROOT_FOLDER_NAME}' and "
        f"mimeType='application/vnd.google-apps.folder' and trashed=false"
    )
    root_res = service.files().list(
        q=root_query,
        fields="files(id)"
    ).execute()

    roots = root_res.get("files", [])
    if not roots:
        return False

    root_id = roots[0]["id"]

    # Find partner folder inside root
    partner_query = (
        f"name='{partner_folder_name}' and "
        f"mimeType='application/vnd.google-apps.folder' and "
        f"'{root_id}' in parents and trashed=false"
    )

    partner_res = service.files().list(
        q=partner_query,
        fields="files(id)"
    ).execute()

    return len(partner_res.get("files", [])) > 0
