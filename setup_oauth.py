import os
import json
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

# Define scopes
SCOPES = ['https://www.googleapis.com/auth/drive']

def setup_oauth():
    print("=== Google Drive User Login Setup ===")
    
    # Check for client_secret.json
    if not os.path.exists('client_secret.json'):
        print("❌ Error: 'client_secret.json' not found.")
        print("Please download your OAuth 2.0 Client ID JSON from Google Cloud Console.")
        print("Rename it to 'client_secret.json' and place it in this folder.")
        return

    creds = None
    # The file token.json stores the user's access and refresh tokens
    if os.path.exists('token.json'):
        try:
            creds = Credentials.from_authorized_user_file('token.json', SCOPES)
            print("✅ Found existing token.json.")
        except Exception:
            print("⚠️ Existing token.json is invalid.")

    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("🔄 Refreshing expired token...")
            try:
                creds.refresh(Request())
            except Exception as e:
                print(f"⚠️ Refresh failed: {e}")
                creds = None

        if not creds:
            print("🌐 Launching browser for login...")
            try:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'client_secret.json', SCOPES)
                creds = flow.run_local_server(port=0)
            except Exception as e:
                print(f"❌ Login failed: {e}")
                return

        # Save the credentials for the next run
        print("💾 Saving new token.json...")
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
            
    print("\n✅ Success! 'token.json' has been generated.")
    print("You can now use this token for GitHub Actions (GOOGLE_TOKEN_JSON) or local scripts.")

if __name__ == "__main__":
    setup_oauth()
