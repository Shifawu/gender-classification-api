# 🧠 Profile Intelligence System

A full-stack system that generates, stores, and queries demographic profiles using external APIs, JWT authentication, role-based access control, and natural language parsing.

---

## 🚀 Live Links

* **Backend API:** https://gender-classification-api-production.up.railway.app/
* **Web Portal:** https://web-portal-ashy-psi.vercel.app/
* **CLI Repository:** https://github.com/Shifawu/profile-cli.git
* **Backend Repository:** https://github.com/Shifawu/gender-classification-api.git
* **Web Portal Repository:** https://github.com/Shifawu/web-portal.git

---

## 🏗️ System Architecture

The system is composed of three main components:

### 1. Backend (Django API)

* Handles authentication (JWT + OAuth)
* Processes external API data
* Stores profiles in database
* Exposes REST endpoints

### 2. CLI Tool (Python)

* Allows terminal interaction with the API
* Supports fetching and creating profiles

### 3. Web Portal (HTML + JS)

* Simple UI to interact with backend
* Performs login, create, and fetch operations

---

### 🔄 Data Flow

User → (CLI / Web) → Backend API → External APIs → Database → Response

External APIs used:

* Genderize API
* Agify API
* Nationalize API

---

## 🔐 Authentication Flow

### JWT Authentication

1. User logs in via `/api/auth/test-login/`
2. Backend generates JWT access token
3. Token is stored on client (CLI or browser)
4. Token is sent in request headers:

```
Authorization: Bearer <access_token>
```

5. Backend validates token before granting access

---

## 🔑 Token Handling Approach

* JWT tokens are generated using PyJWT

* Token payload includes:

  * `user_id`
  * `role` (admin / analyst)
  * `exp` (expiration time)

* Access token expires after **1 hour**

* Token validation is handled in every protected endpoint

---

## 👮 Role Enforcement Logic

The system supports two roles:

### Admin

* Can create profiles
* Can delete profiles
* Full access to system

### Analyst

* Can view profiles
* Can search profiles
* Cannot create or delete

### Enforcement

Role checks are done in backend:

```python
if not require_admin(user):
    return error
```

---

## 🧠 Natural Language Parsing Approach

The search endpoint supports simple rule-based parsing.

### Example Queries:

| Query               | Interpretation                |
| ------------------- | ----------------------------- |
| young males         | gender=male + age 16–24       |
| females above 30    | gender=female + min_age=30    |
| people from nigeria | country_id=NG                 |
| adult males         | gender=male + age_group=adult |

### Rules:

* Keyword-based parsing (no AI used)
* Case-insensitive matching
* Multiple filters can be combined

### Error Handling:

If query cannot be interpreted:

```json
{
  "status": "error",
  "message": "Unable to interpret query"
}
```

---

## 📡 API Endpoints

### Profiles

* `GET /api/profiles/` → List profiles (filter + pagination)
* `POST /api/profiles` → Create profile (admin only)
* `GET /api/profiles/{id}/` → Get single profile
* `DELETE /api/profiles/{id}` → Delete profile (admin only)

### Search

* `GET /api/profiles/search/?q=...`

### Auth

* `POST /api/auth/test-login/`
* `GET /api/auth/github/`
* `GET /api/auth/github/callback/`

---

## 💻 CLI Usage

### Setup

```bash
pip install -r requirements.txt
```

### Run CLI

```bash
python main.py
```

### Features

* Fetch profiles
* Create profiles
* Uses JWT token for authentication

---

## 🌐 Web Portal Usage

1. Open the deployed Netlify URL
2. Enter username and login
3. Create profiles
4. Fetch profiles

---

## 🧪 Error Handling

All errors follow this structure:

```json
{
  "status": "error",
  "message": "error description"
}
```

---

## ⚙️ Tech Stack

* Django (Backend)
* PostgreSQL (Database)
* PyJWT (Authentication)
* GitHub OAuth
* HTML + JavaScript (Frontend)
* Python CLI (Requests)
* Railway (Backend hosting)
* Netlify (Frontend hosting)

---

## 📌 Notes

* All timestamps are in UTC (ISO 8601 format)
* UUID used for profile IDs
* CORS enabled for all origins
* System designed to prevent duplicate profiles
