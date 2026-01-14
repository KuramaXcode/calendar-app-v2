import os
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import streamlit as st
from io import BytesIO

DRIVE_SCOPE = ["https://www.googleapis.com/auth/drive.readonly"]
ROOT_FOLDER_NAME = "AI_Calendar_Final"


def _get_drive_service():
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=DRIVE_SCOPE
    )
    return build("drive", "v3", credentials=creds)


def _get_folder_id(service, name, parent_id=None):
    query = (
        f"name='{name}' and mimeType='application/vnd.google-apps.folder' "
        f"and trashed=false"
    )
    if parent_id:
        query += f" and '{parent_id}' in parents"

    res = service.files().list(q=query, fields="files(id, name)").execute()
    files = res.get("files", [])
    return files[0]["id"] if files else None


def drive_partner_exists(partner_name: str) -> bool:
    service = _get_drive_service()
    root_id = _get_folder_id(service, ROOT_FOLDER_NAME)
    if not root_id:
        return False

    partner_id = _get_folder_id(service, partner_name, root_id)
    return partner_id is not None


def hydrate_partner_final_from_drive(partner_name: str, local_final_path: str):
    """
    Read-only hydration:
    Downloads partner calendar images from Drive into local final folder
    Used only for UI rendering
    """
    service = _get_drive_service()

    root_id = _get_folder_id(service, ROOT_FOLDER_NAME)
    if not root_id:
        return False

    partner_id = _get_folder_id(service, partner_name, root_id)
    if not partner_id:
        return False

    os.makedirs(local_final_path, exist_ok=True)

    results = service.files().list(
        q=f"'{partner_id}' in parents and trashed=false",
        fields="files(id, name)"
    ).execute()

    for f in results.get("files", []):
        file_path = os.path.join(local_final_path, f["name"])
        if os.path.exists(file_path):
            continue  # do not overwrite

        request = service.files().get_media(fileId=f["id"])
        fh = BytesIO()
        downloader = MediaIoBaseDownload(fh, request)

        done = False
        while not done:
            _, done = downloader.next_chunk()

        with open(file_path, "wb") as out:
            out.write(fh.getvalue())

    return True
