from google.oauth2 import service_account
from googleapiclient.discovery import build
import os

SERVICE_ACCOUNT_FILE = "notion-sync-483309-02a27dfe1d63.json"
SCOPES = ["https://www.googleapis.com/auth/drive"]

try:
    print(f"Loading credentials from {SERVICE_ACCOUNT_FILE}...")
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES
    )
    service = build("drive", "v3", credentials=creds)

    print("Querying drive usage...")
    about_req = service.about().get(fields="storageQuota,user")
    about = about_req.execute()
    
    quota = about.get("storageQuota", {})
    usage = int(quota.get("usage", 0))
    limit = int(quota.get("limit", -1))
    
    print(f"Raw Quota JSON: {quota}")
    with open("quota_info.txt", "w") as f:
        f.write(str(about))
    print("Quota info saved to quota_info.txt")
    print("-" * 30)

    # Test Upload
    folder_id = "121kLj2-TAksaVIfP4j-4zeAOQktHTtL5"
    print(f"Attempting test upload to folder {folder_id}...")
    
    file_metadata = {
        "name": "quota_test_file.txt",
        "parents": [folder_id]
    }
    from googleapiclient.http import MediaIoBaseUpload
    import io
    
    media = MediaIoBaseUpload(io.BytesIO(b"Hello World"), mimetype="text/plain")
    
    file = service.files().create(body=file_metadata, media_body=media, fields="id").execute()
    print(f"Test upload successful! File ID: {file.get('id')}")
    
    # Clean up test file
    service.files().delete(fileId=file.get('id')).execute()
    print("Test file deleted.")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
