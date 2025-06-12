# 🚀 GDriveUploader

A lightweight command-line tool for uploading files to **Google Drive** using **Rclone** and **Service Accounts**. Supports load-balancing across multiple service accounts for seamless, automated uploading at scale.

Made with ❤️ From Ionicboy

---
## ⚙️ Features

- 🌀 **Load-balanced uploading** with multiple service accounts
- 💾 Supports `rclone` and standard service account JSON files
- 🔐 Secure: excludes sensitive files from Git
- ✅ Easy setup for batch uploading to your GDrive
---

## Install Requirements
```bash 
pip install -r requirements.txt
```

### 1. Clone this repository

```bash
git clone https://github.com/yourusername/GdriveUploader.git
cd GdriveUploader

```
## 📁 Project Structure

```bash
GdriveUploader/
├── accounts/                # Folder with multiple service accounts (excluded from Git)
│   ├── 1.json
│   └── ...
├── Uploader.py              # Main upload script
├── rclone.exe               # Rclone binary (Windows)
├── tokenSA.pickle           # Cached token (excluded from Git)
├── requirements.txt         # Python dependencies
└── README.md                # Project documentation
```

---

## ⚙️ Requirements

- Python 3.8+
- [Rclone](https://rclone.org/downloads/) (must be accessible from the script)
- Google Service Account credentials
---

## 🧪 How to Use

1. **Add your service accounts** in the `accounts/` folder.
2. **Run the Start.bat....**
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

![image](https://github.com/user-attachments/assets/397012b6-2aac-4c09-8933-25800d49af7a)
![image](https://github.com/user-attachments/assets/aa83c4e9-b96d-42dd-a7df-55bbfd4773ad)
![image](https://github.com/user-attachments/assets/22e9cd3a-7365-4116-b0e3-ef3b277943a3)

---

## 📜 License

MIT License. Feel free to fork and improve.

---

## 🤝 Contribution

Pull requests are welcome. For major changes, open an issue first to discuss what you would like to change.

---
🛑 Make sure you do NOT upload any confidential files like JSON service accounts or tokenSA.pickle.
