import json
import uuid
import requests
import jwt
import csv

from datetime import datetime, timedelta
from time import time

from django.http import JsonResponse, HttpResponse
from django.shortcuts import redirect
from django.conf import settings

from .models import Profile, User


SECRET_KEY = settings.SECRET_KEY
REQUEST_LOG = {}


# ======================
# CORS HELPER
# ======================
def cors_response(data, status=200):
    response = JsonResponse(data, status=status)
    response["Access-Control-Allow-Origin"] = "*"
    return response


# ======================
# TOKEN GENERATION
# ======================
def generate_access_token(user):
    payload = {
        "user_id": str(user.id),
        "role": user.role,
        "exp": datetime.utcnow() + timedelta(minutes=15),
        "type": "access"
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")


def generate_refresh_token(user):
    payload = {
        "user_id": str(user.id),
        "exp": datetime.utcnow() + timedelta(days=1),
        "type": "refresh"
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")


# ======================
# AUTH HELPER
# ======================
def get_authenticated_user(request):
    auth_header = request.headers.get("Authorization")

    if not auth_header:
        return None, "Authorization header missing"

    try:
        token = auth_header.split(" ")[1]
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])

        if payload.get("type") != "access":
            return None, "Invalid token type"

        user = User.objects.get(id=payload["user_id"])

        if not user.is_active:
            return None, "User inactive"

        return user, None

    except jwt.ExpiredSignatureError:
        return None, "Token expired"
    except:
        return None, "Invalid token"


# ======================
# ROLE CHECK
# ======================
def require_admin(user):
    return user.role == "admin"


# ======================
# API VERSION
# ======================
def check_api_version(request):
    return request.headers.get("X-API-Version") == "v1"


# ======================
# AGE GROUP
# ======================
def get_age_group(age):
    if age <= 12:
        return "child"
    elif age <= 19:
        return "teenager"
    elif age <= 59:
        return "adult"
    return "senior"


# ======================
# GITHUB LOGIN (RATE LIMITED)
# ======================
def github_login(request):
    ip = request.META.get("REMOTE_ADDR")
    now = time()

    if ip not in REQUEST_LOG:
        REQUEST_LOG[ip] = []

    REQUEST_LOG[ip] = [t for t in REQUEST_LOG[ip] if now - t < 60]

    if len(REQUEST_LOG[ip]) >= 10:
        return cors_response({"status": "error", "message": "Too many requests"}, 429)

    REQUEST_LOG[ip].append(now)

    url = (
        "https://github.com/login/oauth/authorize"
        f"?client_id={settings.GITHUB_CLIENT_ID}"
        "&scope=read:user"
    )
    return redirect(url)


# ======================
# GITHUB CALLBACK
# ======================
def github_callback(request):
    code = request.GET.get("code")

    if not code:
        return cors_response({"error": "No code provided"}, 400)

    # ======================
    # TEST MODE
    # ======================
    if code == "test_code":
        admin_user, _ = User.objects.get_or_create(
            github_id="test_admin_id",
            defaults={
                "username": "admin_test",
                "role": "admin",
                "is_active": True
            }
        )

        # create analyst user
        User.objects.get_or_create(
            github_id="test_analyst_id",
            defaults={
                "username": "analyst_test",
                "role": "analyst",
                "is_active": True
            }
        )

        return cors_response({
            "access_token": generate_access_token(admin_user),
            "refresh_token": generate_refresh_token(admin_user)
        })

    # ======================
    # NORMAL GITHUB FLOW
    # ======================
    token_response = requests.post(
        "https://github.com/login/oauth/access_token",
        headers={"Accept": "application/json"},
        data={
            "client_id": settings.GITHUB_CLIENT_ID,
            "client_secret": settings.GITHUB_CLIENT_SECRET,
            "code": code,
        }
    ).json()

    github_access_token = token_response.get("access_token")

    if not github_access_token:
        return cors_response({"error": "Failed to get GitHub token"}, 400)

    user_response = requests.get(
        "https://api.github.com/user",
        headers={"Authorization": f"Bearer {github_access_token}"}
    ).json()

    github_id = str(user_response.get("id"))
    username = user_response.get("login")

    if not github_id or not username:
        return cors_response({"error": "Failed to fetch user"}, 400)

    # ✅ FIXED: use github_id
    user, _ = User.objects.get_or_create(
        github_id=github_id,
        defaults={
            "username": username,
            "role": "analyst",
            "is_active": True
        }
    )

    return cors_response({
        "access_token": generate_access_token(user),
        "refresh_token": generate_refresh_token(user)
    })


# ======================
# REFRESH TOKEN
# ======================
def refresh_token_view(request):
    if request.method != "POST":
        return cors_response({"error": "Method not allowed"}, 405)

    try:
        body = json.loads(request.body.decode("utf-8"))
        refresh = body.get("refresh_token")

        payload = jwt.decode(refresh, SECRET_KEY, algorithms=["HS256"])

        if payload.get("type") != "refresh":
            return cors_response({"error": "Invalid token"}, 401)

        user = User.objects.get(id=payload["user_id"])

        return cors_response({
            "access_token": generate_access_token(user)
        })

    except jwt.ExpiredSignatureError:
        return cors_response({"error": "Refresh expired"}, 401)
    except:
        return cors_response({"error": "Invalid token"}, 401)


# ======================
# LOGOUT
# ======================
def logout_view(request):
    if request.method != "POST":
        return cors_response({"error": "Method not allowed"}, 405)

    return cors_response({
        "status": "success",
        "message": "Logged out"
    })


# ======================
# CURRENT USER
# ======================
def get_current_user(request):
    if not check_api_version(request):
        return cors_response({"error": "Invalid API version"}, 400)

    user, error = get_authenticated_user(request)
    if error:
        return cors_response({"error": error}, 401)

    return cors_response({
        "id": str(user.id),
        "username": user.username,
        "role": user.role
    })


# ======================
# SERIALIZER
# ======================
def serialize_profile(p):
    return {
        "id": str(p.id),
        "name": p.name,
        "gender": p.gender,
        "gender_probability": p.gender_probability,
        "age": p.age,
        "age_group": p.age_group,
        "country_id": p.country_id,
        "country_name": p.country_name,
        "country_probability": p.country_probability,
        "created_at": p.created_at.isoformat() + "Z"
    }


# ======================
# CREATE PROFILE
# ======================
def create_profile(request):
    if not check_api_version(request):
        return cors_response({"error": "Invalid API version"}, 400)

    user, error = get_authenticated_user(request)
    if error:
        return cors_response({"error": error}, 401)

    if not require_admin(user):
        return cors_response({"error": "Admins only"}, 403)

    if request.method != "POST":
        return cors_response({"error": "Method not allowed"}, 405)

    try:
        body = json.loads(request.body.decode("utf-8"))
        name = body.get("name")

        if not name:
            return cors_response({"error": "Missing name"}, 400)

    except:
        return cors_response({"error": "Invalid JSON"}, 422)

    existing = Profile.objects.filter(name__iexact=name).first()
    if existing:
        return cors_response(serialize_profile(existing))

    gender = requests.get(f"https://api.genderize.io?name={name}").json()
    age = requests.get(f"https://api.agify.io?name={name}").json()
    nation = requests.get(f"https://api.nationalize.io?name={name}").json()

    country = max(nation.get("country", []), key=lambda x: x["probability"])

    profile = Profile.objects.create(
        id=uuid.uuid4(),
        name=name.lower(),
        gender=gender["gender"],
        gender_probability=gender["probability"],
        age=age["age"],
        age_group=get_age_group(age["age"]),
        country_id=country["country_id"],
        country_name=country["country_id"],
        country_probability=country["probability"]
    )

    return cors_response(serialize_profile(profile), 201)


# ======================
# GET ALL PROFILES
# ======================
def get_all_profiles(request):
    if request.method == "POST":
        return create_profile(request)
    
    if not check_api_version(request):
        return cors_response({"error": "Invalid API version"}, 400)

    user, error = get_authenticated_user(request)
    if error:
        return cors_response({"error": error}, 401)

    profiles = Profile.objects.all()

    page = int(request.GET.get("page", 1))
    limit = min(int(request.GET.get("limit", 10)), 50)

    start = (page - 1) * limit
    end = start + limit

    total = profiles.count()
    profiles = profiles[start:end]

    if request.GET.get("format") == "csv":
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = "attachment; filename=profiles.csv"

        writer = csv.writer(response)
        writer.writerow(["id", "name", "gender", "age"])

        for p in profiles:
            writer.writerow([p.id, p.name, p.gender, p.age])

        return response

    return cors_response({
        "page": page,
        "limit": limit,
        "total": total,
        "data": [serialize_profile(p) for p in profiles]
    })

# ======================
# GET SINGLE
# ======================
def get_profile(request, id):
    if not check_api_version(request):
        return cors_response({"error": "Invalid API version"}, 400)

    user, error = get_authenticated_user(request)
    if error:
        return cors_response({"status": "error", "message": error}, 401)

    try:
        p = Profile.objects.get(id=id)
        return cors_response({"status": "success", "data": serialize_profile(p)})
    except:
        return cors_response({"status": "error", "message": "Not found"}, 404)

# ======================
# DELETE
# ======================
def delete_profile(request, id):
    if not check_api_version(request):
        return cors_response({"error": "Invalid API version"}, 400)

    user, error = get_authenticated_user(request)
    if error:
        return cors_response({"status": "error", "message": error}, 401)

    if not require_admin(user):
        return cors_response({"status": "error", "message": "Admins only"}, 403)

    try:
        Profile.objects.get(id=id).delete()
        return cors_response({}, 204)
    except:
        return cors_response({"status": "error", "message": "Not found"}, 404)

# ======================
# SEARCH
# ======================
def search_profiles(request):
    if not check_api_version(request):
        return cors_response({"error": "Invalid API version"}, 400)

    user, error = get_authenticated_user(request)
    if error:
        return cors_response({"status": "error", "message": error}, 401)

    query = request.GET.get("q", "").lower()
    profiles = Profile.objects.all()

    if "male" in query:
        profiles = profiles.filter(gender="male")

    if "female" in query:
        profiles = profiles.filter(gender="female")

    return cors_response({
        "status": "success",
        "data": [serialize_profile(p) for p in profiles]
    })

# ======================
# HANDLER
# ======================
# def profiles_handler(request):
#     if request.method == "POST":
#         return create_profile(request)
#     elif request.method == "GET":
#         return get_all_profiles(request)

#     return cors_response({"status": "error", "message": "Method not allowed"}, 405)

from django.core.management import call_command

def trigger_seed(request):
    call_command("seed_profiles")
    return cors_response({
        "status": "success",
        "message": "Seeding done"
    })