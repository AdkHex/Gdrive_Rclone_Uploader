<p align="center">
  <img src="https://img.shields.io/badge/Python-3.8+-blue?logo=python&logoColor=white" />
  
  <img src="https://img.shields.io/badge/Rclone-Supported-success?logo=google-drive&logoColor=white&color=brightgreen" />
  
  <img src="https://img.shields.io/badge/Google%20Drive-API%20Enabled-informational?logo=google-drive&logoColor=white" />
  
  <img src="https://img.shields.io/badge/License-MIT-yellow.svg" />
</p>


# GdriveUploader

GdriveUploader is a lightweight Python utility to upload files to Google Drive using Rclone and Google Service Accounts. It's optimized for bulk and automated uploads using service account rotation to bypass daily upload limits.

---

## 🚀 Features

- ✅ Upload using Rclone with Google Drive
- 🔄 Automatic service account rotation
- 🛡️ Secure handling (tokens and credentials ignored via `.gitignore`)
- 🧠 Simple, readable code structure

---
## 📁 Project Structure

```
GdriveUploader/
├── accounts/                # Folder with multiple service accounts (excluded from Git)
│   ├── 1.json
│   └── ...
├── gdrive_uploader.py       # Main upload script
├── rclone.exe               # Rclone binary (Windows)
├── tokenSA.pickle           # Cached token (excluded from Git)
├── requirements.txt         # Python dependencies
├── StartUploader.bat        # Batch File to Directly Run the Program        
└── README.md                # Project documentation
```

---

## ⚙️ Requirements

- ![Python](https://img.shields.io/badge/python-3.8%2B-blue) Python 3.8+
- <img src="https://img.shields.io/badge/Rclone-Supported-success?logo=google-drive&logoColor=white&color=brightgreen" />  [Rclone](https://rclone.org/downloads/) (must be accessible from the script)
- <img src="https://img.shields.io/badge/Google%20Drive-API%20Enabled-informational?logo=google-drive&logoColor=white" />  Google Service Account credentials

Install Python dependencies:
```bash
pip install -r requirements.txt
```

---

## 🧪 How to Use

1. **Add your service accounts** in the `accounts/` folder.
2. **Put the file you want to upload** (default: `sample.txt`) in the project root or modify `SOURCE_FILE` in `Uploader.py`.
3. **Run the script**:

```bash
python Uploader.py
```

The script will rotate service accounts randomly and upload the file to your Google Drive.

---

## 📌 Notes

- Change `UPLOAD_FOLDER_ID` to your desired Google Drive folder ID.
- Rclone must be authorized once with your first service account (you can automate this).
- Windows users: Make sure `rclone.exe` is placed in the same directory.

---

## 📸 Screenshot

![Screenshot1](https://github.com/user-attachments/assets/e8916776-8e0b-4db4-b841-1bcfaf1cb1d3)
![Screenshot](https://github.com/user-attachments/assets/d9fb620a-0cb5-4559-9dd2-4ea4a162fa78)

---

##   <img src="https://img.shields.io/badge/License-MIT-yellow.svg" />

MIT License. Feel free to fork and improve.

---

## 🤝 Contribution

Pull requests are welcome. For major changes, open an issue first to discuss what you would like to change.

```
🛑 Make sure you do NOT upload any confidential files like JSON service accounts or tokenSA.pickle.
