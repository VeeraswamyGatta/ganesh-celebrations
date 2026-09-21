"""
Google Drive utilities for syncing Ganesh Celebrations data
Handles authentication, folder creation, file upload, and cleanup
"""

import io
import os
import pickle
import json
from google.auth.transport.requests import Request
from google.oauth2.service_account import Credentials
from google.oauth2.credentials import Credentials as UserCredentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.exceptions import MissingTokenError
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseUpload
import streamlit as st
import pandas as pd

# Google Drive API scope
SCOPES = ['https://www.googleapis.com/auth/drive']

def get_drive_service():
    """
    Authenticate and return Google Drive service.
    Uses credentials from st.secrets['google_drive_credentials'] (JSON)
    """
    try:
        creds_json = st.secrets.get("google_drive_credentials")
        if not creds_json:
            st.error("❌ Google Drive credentials not found in st.secrets['google_drive_credentials']")
            return None
        
        # Parse the JSON credentials
        if isinstance(creds_json, str):
            creds_dict = json.loads(creds_json)
        else:
            creds_dict = creds_json
        
        # Create credentials from service account JSON
        credentials = Credentials.from_service_account_info(
            creds_dict,
            scopes=SCOPES
        )
        
        service = build('drive', 'v3', credentials=credentials)
        return service
    except Exception as e:
        st.error(f"❌ Failed to authenticate with Google Drive: {e}")
        return None


def create_folder_if_not_exists(service, folder_name, parent_id=None):
    """
    Create a folder in Google Drive if it doesn't exist.
    Returns folder ID.
    """
    try:
        query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        if parent_id:
            query += f" and '{parent_id}' in parents"
        
        results = service.files().list(
            q=query,
            spaces='drive',
            fields='files(id, name)',
            pageSize=1
        ).execute()
        
        items = results.get('files', [])
        if items:
            return items[0]['id']
        
        # Create new folder
        file_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        if parent_id:
            file_metadata['parents'] = [parent_id]
        
        folder = service.files().create(
            body=file_metadata,
            fields='id'
        ).execute()
        
        return folder.get('id')
    except Exception as e:
        st.error(f"❌ Failed to create folder: {e}")
        return None


def upload_file_to_drive(service, file_name, file_content, parent_id, mime_type='text/csv'):
    """
    Upload a file to Google Drive.
    file_content can be bytes or file-like object
    """
    try:
        file_metadata = {
            'name': file_name,
            'parents': [parent_id]
        }
        
        # Handle different file content types
        if isinstance(file_content, bytes):
            media = MediaIoBaseUpload(io.BytesIO(file_content), mimetype=mime_type, resumable=True)
        elif isinstance(file_content, str):
            media = MediaIoBaseUpload(io.BytesIO(file_content.encode()), mimetype=mime_type, resumable=True)
        else:
            media = MediaIoBaseUpload(file_content, mimetype=mime_type, resumable=True)
        
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, webViewLink'
        ).execute()
        
        return file.get('id'), file.get('webViewLink')
    except Exception as e:
        st.error(f"❌ Failed to upload file: {e}")
        return None, None


def delete_file_from_drive(service, file_id):
    """Delete a file or folder from Google Drive"""
    try:
        service.files().delete(fileId=file_id).execute()
        return True
    except Exception as e:
        st.error(f"❌ Failed to delete file: {e}")
        return False


def list_files_in_folder(service, folder_id):
    """List all files in a Google Drive folder"""
    try:
        results = service.files().list(
            q=f"'{folder_id}' in parents and trashed=false",
            spaces='drive',
            fields='files(id, name, mimeType, createdTime)',
            pageSize=100
        ).execute()
        
        return results.get('files', [])
    except Exception as e:
        st.error(f"❌ Failed to list files: {e}")
        return []


def delete_folder_contents(service, folder_id):
    """Delete all files in a folder (but not the folder itself)"""
    try:
        files = list_files_in_folder(service, folder_id)
        deleted_count = 0
        
        for file in files:
            if delete_file_from_drive(service, file['id']):
                deleted_count += 1
        
        return deleted_count
    except Exception as e:
        st.error(f"❌ Failed to delete folder contents: {e}")
        return 0


def sync_data_to_drive(conn, year):
    """
    Main sync function - exports all data and uploads to Google Drive
    Structure: ganesh_celebrations/[YEAR]/[data_types]
    """
    try:
        service = get_drive_service()
        if not service:
            return False
        
        cursor = conn.cursor()
        
        # Create folder structure
        root_folder_id = create_folder_if_not_exists(service, "ganesh_celebrations")
        if not root_folder_id:
            return False
        
        year_folder_id = create_folder_if_not_exists(service, str(year), parent_id=root_folder_id)
        if not year_folder_id:
            return False
        
        # Delete existing files in year folder to avoid duplicates
        st.info(f"Cleaning up existing files for {year}...")
        deleted = delete_folder_contents(service, year_folder_id)
        if deleted > 0:
            st.info(f"Deleted {deleted} existing file(s)")
        
        # Data exports
        data_to_export = {}
        
        # 1. Sponsors
        try:
            sponsors_df = pd.read_sql("SELECT * FROM sponsors ORDER BY name", conn)
            sponsors_csv = sponsors_df.to_csv(index=False).encode()
            data_to_export['sponsors'] = {
                'name': f"sponsors_{year}.csv",
                'content': sponsors_csv,
                'mime': 'text/csv'
            }
        except Exception as e:
            st.warning(f"⚠️ Failed to export sponsors: {e}")
        
        # 2. Sponsorship Items
        try:
            items_df = pd.read_sql(
                "SELECT id, category, item, amount FROM sponsorship_items ORDER BY category, item",
                conn
            )
            items_csv = items_df.to_csv(index=False).encode()
            data_to_export['sponsorship_items'] = {
                'name': f"sponsorship_items_{year}.csv",
                'content': items_csv,
                'mime': 'text/csv'
            }
        except Exception as e:
            st.warning(f"⚠️ Failed to export sponsorship items: {e}")
        
        # 3. Expenses
        try:
            expenses_df = pd.read_sql(
                "SELECT * FROM expenses ORDER BY expense_date DESC",
                conn
            )
            # Don't include blob columns in CSV
            if 'receipt_blob' in expenses_df.columns:
                expenses_df = expenses_df.drop(columns=['receipt_blob'])
            expenses_csv = expenses_df.to_csv(index=False).encode()
            data_to_export['expenses'] = {
                'name': f"expenses_{year}.csv",
                'content': expenses_csv,
                'mime': 'text/csv'
            }
        except Exception as e:
            st.warning(f"⚠️ Failed to export expenses: {e}")
        
        # 4. Settlements
        try:
            settlements_df = pd.read_sql(
                "SELECT * FROM settlements ORDER BY settlement_date DESC",
                conn
            )
            settlements_csv = settlements_df.to_csv(index=False).encode()
            data_to_export['settlements'] = {
                'name': f"settlements_{year}.csv",
                'content': settlements_csv,
                'mime': 'text/csv'
            }
        except Exception as e:
            st.warning(f"⚠️ Failed to export settlements: {e}")
        
        # 5. Committee Members
        try:
            members_df = pd.read_sql(
                "SELECT * FROM committee_members ORDER BY name",
                conn
            )
            members_csv = members_df.to_csv(index=False).encode()
            data_to_export['committee_members'] = {
                'name': f"committee_members_{year}.csv",
                'content': members_csv,
                'mime': 'text/csv'
            }
        except Exception as e:
            st.warning(f"⚠️ Failed to export committee members: {e}")
        
        # 6. Payments (if table exists)
        try:
            payments_df = pd.read_sql(
                "SELECT * FROM payments ORDER BY payment_date DESC",
                conn
            )
            payments_csv = payments_df.to_csv(index=False).encode()
            data_to_export['payments'] = {
                'name': f"payments_{year}.csv",
                'content': payments_csv,
                'mime': 'text/csv'
            }
        except Exception as e:
            st.info(f"Note: Payments table not found or empty")
        
        # Upload all files
        uploaded_files = []
        failed_files = []
        
        for data_type, file_info in data_to_export.items():
            file_id, file_link = upload_file_to_drive(
                service,
                file_info['name'],
                file_info['content'],
                year_folder_id,
                file_info['mime']
            )
            if file_id:
                uploaded_files.append(file_info['name'])
            else:
                failed_files.append(file_info['name'])
        
        # Upload receipts as a subfolder
        try:
            cursor.execute(
                "SELECT id, expense_id, spent_by, amount, receipt_filename, receipt_blob FROM expenses WHERE receipt_blob IS NOT NULL"
            )
            receipts = cursor.fetchall()
            
            if receipts:
                receipts_folder_id = create_folder_if_not_exists(service, "receipts", parent_id=year_folder_id)
                
                for receipt_id, expense_id, spent_by, amount, receipt_filename, receipt_blob in receipts:
                    if receipt_blob:
                        # Convert blob to bytes
                        if isinstance(receipt_blob, memoryview):
                            receipt_bytes = receipt_blob.tobytes()
                        elif isinstance(receipt_blob, bytearray):
                            receipt_bytes = bytes(receipt_blob)
                        else:
                            receipt_bytes = receipt_blob
                        
                        # Create filename
                        file_ext = receipt_filename.split('.')[-1] if receipt_filename else 'pdf'
                        receipt_name = f"EXP_{expense_id:03d}_{spent_by.replace(' ', '_')}_{amount:.2f}.{file_ext}"
                        
                        file_id, _ = upload_file_to_drive(
                            service,
                            receipt_name,
                            receipt_bytes,
                            receipts_folder_id,
                            'application/octet-stream'
                        )
                        if file_id:
                            uploaded_files.append(receipt_name)
                        else:
                            failed_files.append(receipt_name)
        except Exception as e:
            st.warning(f"⚠️ Note on receipts: {e}")
        
        # Summary
        st.success(f"✅ Synced {len(uploaded_files)} files to Google Drive!")
        if uploaded_files:
            st.write("**Uploaded:**")
            for fname in uploaded_files:
                st.write(f"  • {fname}")
        
        if failed_files:
            st.warning(f"⚠️ Failed to upload {len(failed_files)} file(s)")
            for fname in failed_files:
                st.write(f"  • {fname}")
        
        return True
        
    except Exception as e:
        st.error(f"❌ Sync failed: {e}")
        return False
