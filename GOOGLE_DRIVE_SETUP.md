# Google Drive Integration Setup Guide

## Overview
The Ganesh Celebrations app now includes Google Drive sync capability to automatically backup and organize all data:
- Sponsors
- Sponsorship Items
- Expenses
- Settlements
- Committee Members
- Payments
- Receipt Attachments

## Folder Structure on Google Drive
```
ganesh_celebrations/
├── 2024/
│   ├── sponsors_2024.csv
│   ├── expenses_2024.csv
│   ├── settlements_2024.csv
│   ├── committee_members_2024.csv
│   ├── sponsorship_items_2024.csv
│   ├── payments_2024.csv
│   └── receipts/
│       ├── EXP_001_John_Doe_500.00.pdf
│       ├── EXP_002_Jane_Smith_1000.00.jpg
│       └── ...
├── 2025/
│   ├── sponsors_2025.csv
│   └── ...
```

## Setup Steps

### Step 1: Create Google Service Account

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project:
   - Click "Select a Project" → "New Project"
   - Name it "Ganesh Celebrations"
   - Click "Create"

3. Enable Google Drive API:
   - In the search bar, search for "Google Drive API"
   - Click on it
   - Click "Enable"

4. Create a Service Account:
   - Go to "APIs & Services" → "Credentials"
   - Click "Create Credentials" → "Service Account"
   - Fill in the details:
     - Service account name: "Ganesh App"
     - Service account ID: (auto-filled)
     - Click "Create and Continue"
   - Grant it basic access (click "Continue" on the permission screens)
   - Click "Done"

5. Create JSON Key:
   - In the "Service Accounts" list, click on the service account you just created
   - Go to the "Keys" tab
   - Click "Add Key" → "Create new key"
   - Choose "JSON"
   - Click "Create" - this will download a JSON file
   - Save this file securely

### Step 2: Add Credentials to Streamlit Secrets

1. Open `.streamlit/secrets.toml` in your project
2. Open the downloaded JSON key file with a text editor
3. Copy the **entire JSON content**
4. Add to `secrets.toml`:

```toml
google_drive_credentials = '''
{
  "type": "service_account",
  "project_id": "your-project-id-here",
  "private_key_id": "...",
  "private_key": "...",
  "client_email": "ganesh-app@your-project.iam.gserviceaccount.com",
  "client_id": "...",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/..."
}
'''
```

**Important:** Include the triple quotes around the JSON as shown above.

### Step 3: (Optional) Share Drive Folder with Your Account

If you want to access the files from your personal Google account:

1. After the first sync, go to [Google Drive](https://drive.google.com/)
2. Look for the "ganesh_celebrations" folder
3. Right-click → Share
4. Add your Gmail address
5. Click "Share"

Now you can view and download the files from your personal Google Drive account.

### Step 4: Verify Setup

1. Open the Ganesh Celebrations app
2. Go to **Admin** → **Sync with Drive**
3. Click "ℹ️ Verify Credentials"
4. You should see "✅ Connected as: [service-account-email]"

If you see an error, check:
- The JSON credentials are properly formatted
- The credentials are in `secrets.toml`
- The Google Drive API is enabled in Google Cloud Console

## Using Sync with Drive

### First Time Sync
1. Go to **Admin** → **Sync with Drive**
2. Select the year (defaults to current year)
3. Click "☁️ Sync to Google Drive"
4. Wait for the process to complete
5. You'll see a success message and list of uploaded files

### Subsequent Syncs
When you sync the same year again:
1. All existing files for that year are **automatically deleted**
2. Fresh exports are created and uploaded
3. This ensures you always have the latest data

**Why?** Receipt filenames are auto-generated based on data, so having duplicates from multiple sync runs would create confusion.

## What Gets Synced

### CSV Files (with all columns)
- **sponsors_YYYY.csv** - All sponsor records with donations, sponsorships, and contact info
- **expenses_YYYY.csv** - All expenses excluding binary receipt data
- **settlements_YYYY.csv** - All settlement records
- **committee_members_YYYY.csv** - All committee members with email addresses
- **sponsorship_items_YYYY.csv** - Available sponsorship items and categories
- **payments_YYYY.csv** - All payment records (if payments table exists)

### Receipts Folder
- **receipts/** subfolder contains all uploaded receipt files
- Files are named: `EXP_{ID:03d}_{PERSON}_{AMOUNT}.{EXT}`
- Example: `EXP_001_John_Doe_500.00.pdf`

## Advanced Features

### Error Handling
- If a receipt file can't be uploaded, you'll see a warning but syncing continues
- All successfully uploaded files are listed with checkmarks
- Failed files are listed separately for manual upload

### Large Files
- The sync process uses resumable uploads
- Even if interrupted, uploads resume from where they left off
- Files can be up to 5TB in size (Google Drive limit)

### Rate Limiting
- Google Drive API has rate limits
- For most use cases (syncing once per day), you won't hit limits
- If you do see rate limit errors, wait a few minutes and retry

## Troubleshooting

### "Failed to authenticate with Google Drive"
**Solution:** Check that `google_drive_credentials` is properly added to `secrets.toml`

### "Google Drive credentials not found"
**Solution:** Ensure the key is named `google_drive_credentials` (exact spelling)

### "Failed to create folder"
**Solution:** 
- Verify service account has Drive API access
- Check that the service account email has permissions in Google Cloud

### Receipt files not uploading
**Solution:**
- Some binary formats might not upload properly
- Check file size (should be under 100MB for most receipts)
- Try manual upload to diagnose

### Files already exist error
**Solution:**
- The app auto-deletes files before syncing to prevent duplicates
- If you see this, it means the deletion didn't work
- Delete the year folder manually from Google Drive and retry

## Security Notes

1. **Service Account Email:** Keep the service account email secure
   - Don't share `secrets.toml` with untrusted users
   - The JSON contains a private key

2. **Shared Access:** When sharing the drive folder:
   - Only share with trusted committee members
   - Use "Viewer" role to prevent accidental deletion
   - Consider "Editor" only for admins

3. **Backup:** Google Drive sync is a backup tool, not the source of truth
   - Always maintain your PostgreSQL database backups
   - Google Drive is for accessibility and archival

## Common Questions

**Q: Can I sync multiple years?**
A: Yes! Select different years and click sync. Each year gets its own folder.

**Q: What if I delete a file from Google Drive?**
A: Just sync again - it will be re-uploaded. The app always has the source data.

**Q: Can I schedule automatic syncs?**
A: Not yet, but you can sync manually via the Admin panel. Consider setting a reminder.

**Q: What about privacy?**
A: Your data is stored on Google's servers encrypted. Google complies with SOC 2, ISO 27001.

**Q: Can non-admins sync?**
A: Currently only admins can access the "Sync with Drive" menu.

## Support

For issues with Google Cloud setup, see:
- [Google Cloud Console Help](https://cloud.google.com/docs)
- [Google Drive API Docs](https://developers.google.com/drive)

For app-specific issues:
- Check the error message in the Streamlit app
- Verify all credentials in `secrets.toml`
- Try the "Verify Credentials" button first
