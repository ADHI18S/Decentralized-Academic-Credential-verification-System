# Decentralized Academic Credential Verification System

A secure, commercial-grade platform built to completely eliminate academic fraud using zero-trust architecture and cryptographic verification. Developed as a **Final Year Project**.

![System Overview](https://img.shields.io/badge/Status-Active-success.svg)
![Python Version](https://img.shields.io/badge/Python-3.10%2B-blue.svg)
![Flask](https://img.shields.io/badge/Framework-Flask-black.svg)
![Database](https://img.shields.io/badge/Database-SQLite3-cfd0d1.svg)

---

## 📖 Project Overview

Academic certificate forgery is a rapidly increasing global issue. Traditional methods of verifying student records are often slow, require manual human intervention, and are highly susceptible to document tampering.

The **Decentralized Academic Credential Verification System (ACVS)** is designed to permanently resolve this. By generating an immutable **SHA-256 footprint** for every official academic document upon issuance, employers can mathematically verify a candidate's legitimacy in milliseconds without ever contacting the university directly.

---

## ✨ Enterprise-Grade Features

### 1. 🛡️ Tamper-Proof Cryptographic Hashing (SHA-256)
When an authorized University uploads a certificate, the centralized system maps the bytes of that document into an irreversible SHA-256 hash. If passing a modified certificate to the verifier—even if a single pixel is altered—the resulting mathematical difference guarantees instant rejection.

### 2. 📱 Built-In Camera QR Scanner Engine
Universities automatically generate custom QR codes during student issuance containing dynamic System IDs. Employers can seamlessly launch their mobile or laptop webcam directly from the dashboard to securely ingest and verify the code using `Html5Qrcode`.

### 3. 💼 Three-Tier Role Isolation
* **Master System Admin**: Controls the centralized ledger and has sole permission to grant access keys/accounts to authorized Universities globally.
* **Authorized University Portal**: A highly-polished SaaS interface where departments can securely issue hashes into the database, generate unique Certificate IDs, view all past records, and generate/download direct QR codes.
* **Open Employer Portal**: A public verification endpoint where any company can drag-and-drop a PDF or scan a QR code to verify candidate authenticity instantaneously.

### 4. 🎨 Commercial Product UI/UX Architecture
Designed beyond the scope of traditional "Student Projects", the platform features premium UI paradigms including soft gradient transitions, glassmorphism navbars, intelligent hover states, contextual animated loading indicators, and dedicated responsive Grid/Flex layouts ensuring a mobile-first experience.

---

## 🛠️ Technology Stack

**Backend System:**
*   **Python**: Core execution and mathematical processing.
*   **Flask**: Lightweight web framework governing API routes, HTTP handling, and protected sessions.
*   **SQLite3**: Persistent, serverless database mapping hashes, users, and department ledgers.
*   **Werkzeug Security**: Advanced password and key hashing.

**Frontend Interface:**
*   **HTML5 / Vanilla CSS3**: Highly optimized rendering leveraging custom variables, Flexbox layouts, animations, and shadows.
*   **Jinja2**: Secure template rendering engine avoiding client-side state manipulation.
*   **JavaScript (ES6+)**: Powers asynchronous loading animations and interactive features.
*   **Html5Qrcode**: Implements client-side, privacy-first camera control and data extraction.

---

## 🚀 Quick Start & Installation

To run this repository locally without an externally managed environment constraint:

### 1. Clone the project and setup the directory
```bash
git clone https://github.com/ADHI18S/Decentralized-Academic-Credential-verification-System.git
cd Decentralized-Academic-Credential-verification-System
```

### 2. Create and activate a Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows, use: venv\Scripts\activate
```

### 3. Install required logic extensions
```bash
pip install Flask werkzeug Pillow "qrcode[pil]"
```
*(Note: If you are forcing a global system installation on Linux, you may append `--break-system-packages`)*

### 4. Launch the application
```bash
flask run
```
The system will dynamically construct `database.db` and open safely on **`http://127.0.0.1:5000/`**.

---

## 🧭 Application Workflows & Security
* **Accessing Admin**: You must specifically navigate to `/admin/login` or `/admin` to bypass public restrictions.
* **Privacy Controls**: Because QR codes are publicly visible, the system strictly assigns a mapped `Certificate ID` internally rather than exposing the student's Register Number or Department visually in the data trace. The query resolves *privately* on the backend and displays explicitly formatted UI blocks based exclusively on the result index.

---
**Developed explicitly for Final Year Academic Research by ADHI18S.**
