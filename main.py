from fastapi import FastAPI, HTTPException, status
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import firebase_admin
from firebase_admin import credentials, firestore
import os
import json
import base64
from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()

app = FastAPI(title="GGHS Chak No 493 JB API")

# CORS middleware — allow frontend to communicate with this server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────────────────────────────────────
# Firebase Admin SDK Initialization
# Supports:
# 1. FIREBASE_CREDENTIALS_BASE64 (Base64 string - 100% reliable for Railway/Cloud)
# 2. FIREBASE_CREDENTIALS_JSON (Raw JSON string)
# 3. FIREBASE_CREDENTIALS_PATH or GOOGLE_APPLICATION_CREDENTIALS (File path)
# 4. Local serviceAccountKey.json file fallback
# ─────────────────────────────────────────────────────────────────────────────
def get_firebase_credentials():
    # 1. Check Base64 encoded string (recommended for cloud to avoid quote escaping issues)
    env_b64 = os.getenv("FIREBASE_CREDENTIALS_BASE64")
    if env_b64:
        try:
            decoded_json = base64.b64decode(env_b64.strip()).decode("utf-8")
            cred_dict = json.loads(decoded_json)
            return credentials.Certificate(cred_dict)
        except Exception as e:
            print(f"[Firebase Warning] Failed to parse FIREBASE_CREDENTIALS_BASE64: {e}")

    # 2. Check if raw JSON string is provided in env var
    env_json = os.getenv("FIREBASE_CREDENTIALS_JSON")
    if env_json:
        try:
            cred_dict = json.loads(env_json)
            return credentials.Certificate(cred_dict)
        except Exception as e:
            print(f"[Firebase Warning] Failed to parse FIREBASE_CREDENTIALS_JSON: {e}")

    # 3. Check if custom path is provided in env var
    env_path = os.getenv("FIREBASE_CREDENTIALS_PATH") or os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if env_path and os.path.exists(env_path):
        return credentials.Certificate(env_path)

    # 4. Fallback to local serviceAccountKey.json in the same directory
    local_file = os.path.join(os.path.dirname(__file__), "serviceAccountKey.json")
    if os.path.exists(local_file):
        return credentials.Certificate(local_file)

    raise RuntimeError(
        "Firebase credentials not found! Set FIREBASE_CREDENTIALS_BASE64 or FIREBASE_CREDENTIALS_JSON "
        "in environment variables, or place serviceAccountKey.json in the backend/ folder."
    )

if not firebase_admin._apps:
    cred = get_firebase_credentials()
    firebase_admin.initialize_app(cred)

db = firestore.client()

# Firestore collection / document references
SCHOOL_DOC_REF = db.collection("school_data").document("main")
CONFIG_DOC_REF  = db.collection("config").document("admin")

# ─────────────────────────────────────────────────────────────────────────────
# Default data — written to Firestore only if the document does not exist yet
# ─────────────────────────────────────────────────────────────────────────────
DEFAULT_SCHOOL_DATA = {
    "status": "Open",
    "principalName": "Dr. Noor",
    "principalPhone": "0301 7697996",
    "level": "High",
    "markaz": "SECONDARY-WING",
    "mauza": "BATIAN WALA",
    "uc": "CHAK 493/JB (No. 51)",
    "constituency": "PP: 128 | NA: 116",
    "illegalOccupation": "No",
    "monDate": "26-01-2026",
    "monTime": "10:25 AM - 11:34 AM",
    "monFormNo": "26012610331577",
    "monMeaName": "S-**** MU**** RA****",
    "monMeaPhone": "03****",
    "totalStaff": "13",
    "presentStaff": "13",
    "absentStaff": "0",
    "top1Name": "Ayesha Bibi",
    "top1Roll": "801",
    "top1Marks": "1050 / 1100",
    "top2Name": "Fatima Noor",
    "top2Roll": "802",
    "top2Marks": "1025 / 1100",
    "top3Name": "Zainab Ali",
    "top3Roll": "901",
    "top3Marks": "1000 / 1100",
    "electricity": "Wholly",
    "water": "Wholly",
    "toilet": "Wholly",
    "wall": "Wholly",
    "newSectionTitle": "",
    "newSectionIcon": "",
    "newSectionContent": "",
}

DEFAULT_ADMIN_CONFIG = {
    # Change this password via Firebase Console after first run:
    # Firestore → config (collection) → admin (document) → password (field)
    "password": "admin123"
}


def init_firestore():
    """Seed default data into Firestore if documents don't exist yet."""
    if not SCHOOL_DOC_REF.get().exists:
        SCHOOL_DOC_REF.set(DEFAULT_SCHOOL_DATA)
        print("[Firebase] school_data/main document created with default data.")
    else:
        print("[Firebase] school_data/main already exists. Skipping seed.")

    if not CONFIG_DOC_REF.get().exists:
        CONFIG_DOC_REF.set(DEFAULT_ADMIN_CONFIG)
        print("[Firebase] config/admin document created with default password.")
    else:
        print("[Firebase] config/admin already exists. Skipping seed.")


init_firestore()


# ─────────────────────────────────────────────────────────────────────────────
# Pydantic Models
# ─────────────────────────────────────────────────────────────────────────────
class SchoolDataModel(BaseModel):
    status: str
    principalName: str
    principalPhone: str
    level: str
    markaz: str
    mauza: str
    uc: str
    constituency: str
    illegalOccupation: str
    monDate: str
    monTime: str
    monFormNo: str
    monMeaName: str
    monMeaPhone: str
    totalStaff: str
    presentStaff: str
    absentStaff: str
    top1Name: str
    top1Roll: str
    top1Marks: str
    top2Name: str
    top2Roll: str
    top2Marks: str
    top3Name: str
    top3Roll: str
    top3Marks: str
    electricity: str
    water: str
    toilet: str
    wall: str
    newSectionTitle: str
    newSectionIcon: str
    newSectionContent: str


class LoginModel(BaseModel):
    password: str


# ─────────────────────────────────────────────────────────────────────────────
# API Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/api/login")
def admin_login(login: LoginModel):
    """
    Validate admin password against the value stored in Firestore.
    To change the password: Firebase Console → config/admin → edit 'password' field.
    """
    config_doc = CONFIG_DOC_REF.get()
    if not config_doc.exists:
        raise HTTPException(status_code=500, detail="Admin config not found in Firestore.")

    stored_password = config_doc.to_dict().get("password", "")

    if login.password == stored_password:
        return {"success": True, "message": "Login successful"}

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Ghalat Password! Dobara koshish karein."
    )


@app.get("/api/data")
def get_school_data():
    """Fetch school data from Firestore."""
    doc = SCHOOL_DOC_REF.get()
    if doc.exists:
        return doc.to_dict()
    raise HTTPException(status_code=404, detail="School data not found in Firestore.")


@app.post("/api/data")
def update_school_data(data: SchoolDataModel):
    """Update school data in Firestore."""
    SCHOOL_DOC_REF.set(data.model_dump())
    return {"message": "Data successfully saved to Firebase Firestore."}


@app.get("/", response_class=HTMLResponse)
def root():
    return """
    <html>
        <head><title>GGHS 493 JB Backend</title></head>
        <body style="font-family: Arial; text-align: center; padding-top: 50px;">
            <h1 style="color: green;">GGHS Chak No 493 JB — FastAPI + Firebase Backend is Running!</h1>
            <p>Database: <b>Firebase Firestore</b> (SQLite removed)</p>
            <p>Use <b>/api/data</b> (GET/POST) to fetch or update records.</p>
            <p>Use <b>/api/login</b> (POST) to authenticate.</p>
        </body>
    </html>
    """