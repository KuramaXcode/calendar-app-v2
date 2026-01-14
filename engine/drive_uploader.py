import os
import json
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import streamlit as st


DRIVE_SCOPE = ["https://www.googleapis.com/auth/drive"]
ROOT_FOLDER_NAME = "AI_Calendar_Final"


def _get_drive_service():
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=DRIVE_SCOPE
    )
    return build("drive", "v3", credentials=creds)


def _get_or_create_folder(service, name, parent_id=None):
    query = f"name='{name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    if parent_id:
        query += f" and '{parent_id}' in parents"

    res = service.files().list(q=query, fields="files(id, name)").execute()
    files = res.get("files", [])

    if files:
        return files[0]["id"]

    metadata = {
        "name": name,
        "mimeType": "application/vnd.google-apps.folder",
    }
    if parent_id:
        metadata["parents"] = [parent_id]

    folder = service.files().create(body=metadata, fields="id").execute()
    return folder["id"]


def upload_final_folder_to_drive(partner_name: str, local_final_path: str):
    service = _get_drive_service()

    root_id = _get_or_create_folder(service, ROOT_FOLDER_NAME)
    partner_id = _get_or_create_folder(service, partner_name, root_id)

    # Upload / overwrite files
    for fname in os.listdir(local_final_path):
        fpath = os.path.join(local_final_path, fname)

        if not os.path.isfile(fpath):
            continue

        # Check if file exists
        query = f"name='{fname}' and '{partner_id}' in parents and trashed=false"
        res = service.files().list(q=query, fields="files(id)").execute()
        existing = res.get("files", [])

        import os
import json
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import streamlit as st


DRIVE_SCOPE = ["https://www.googleapis.com/auth/drive"]
ROOT_FOLDER_NAME = "AI_Calendar_Final"


def _get_drive_service():
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=DRIVE_SCOPE
    )
    return build("drive", "v3", credentials=creds)


def _get_or_create_folder(service, name, parent_id=None):
    query = f"name='{name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    if parent_id:
        query += f" and '{parent_id}' in parents"

    res = service.files().list(q=query, fields="files(id, name)").execute()
    files = res.get("files", [])

    if files:
        return files[0]["id"]

    metadata = {
        "name": name,
        "mimeType": "application/vnd.google-apps.folder",
    }
    if parent_id:
        metadata["parents"] = [parent_id]

    folder = service.files().create(body=metadata, fields="id").execute()
    return folder["id"]


def upload_final_folder_to_drive(partner_name: str, local_final_path: str):
    service = _get_drive_service()

    if not os.path.exists(local_final_path):
        raise RuntimeError(f"Final path does not exist: {local_final_path}")

    files = [
        f for f in os.listdir(local_final_path)
        if os.path.isfile(os.path.join(local_final_path, f))
    ]

    if not files:
        raise RuntimeError(
            f"No files found in final folder for upload: {local_final_path}"
        )

    root_id = _get_or_create_folder(service, ROOT_FOLDER_NAME)
    partner_id = _get_or_create_folder(service, partner_name, root_id)

    for fname in files:
        fpath = os.path.join(local_final_path, fname)

        query = f"name='{fname}' and '{partner_id}' in parents and trashed=false"
        res = service.files().list(q=query, fields="files(id)").execute()
        existing = res.get("files", [])

        media = MediaFileUpload(
            fpath,
            mimetype="image/jpeg",
            resumable=True
        )

        if existing:
            service.files().update(
                fileId=existing[0]["id"],
                media_body=media
            ).execute()
        else:
            service.files().create(
                body={"name": fname, "parents": [partner_id]},
                media_body=media
            ).execute()

        if existing:
            service.files().update(
                fileId=existing[0]["id"],
                media_body=media
            ).execute()
        else:
            service.files().create(
                body={"name": fname, "parents": [partner_id]},
                media_body=media
            ).execute()
