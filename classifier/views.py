import json
import uuid
import requests
import jwt
from datetime import datetime, timedelta

from django.http import JsonResponse
from django.conf import settings
from django.shortcuts import redirect

from .models import Profile, User


# ======================
# CORS HELPER
# ======================
def cors_response(data, status=200):
    response = JsonResponse(data, status=status)
    response["Access-Control-Allow-Origin"] = "*"
    return response


# ======================
# JWT CONFIG
# ======================
SECRET_KEY = settings.SECRET_KEY


def generate_access_token(user):
    payload = {
        "user_id": str(user.id),
        "role": user.role,
        "exp": datetime.utcnow() + timedelta(hours=1),
        "type": "access"
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")


def decode_token(token):
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    except:
        return None


def get_authenticated_user(request):
    auth_header = request.headers.get("Authorization")

    if not auth_header or not auth_header.startswith("Bearer "):
        return None, "Unauthorized"

    try:
        token = auth_header.split(" ")[1]
        payload = decode_token(token)

        if not payload or payload.get("type") != "access":
            return None, "Invalid token"

        user = User.objects.get(id=payload["user_id"])
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
# OAUTH (GITHUB)
# ======================
def github_login(request):
    url = (
        "https://github.com/login/oauth/authorize"
        f"?client_id={settings.GITHUB_CLIENT_ID}&scope=read:user"
    )
    return redirect(url)


def github_callback(request):
    code = request.GET.get("code")

    if not code:
        return cors_response({"status": "error", "message": "No code provided"}, 400)

    token_res = requests.post(
        "https://github.com/login/oauth/access_token",
        headers={"Accept": "application/json"},
        data={
            "client_id": settings.GITHUB_CLIENT_ID,
            "client_secret": settings.GITHUB_CLIENT_SECRET,
            "code": code,
        }
    ).json()

    access_token = token_res.get("access_token")

    if not access_token:
        return cors_response({"status": "error", "message": "Failed to get access token"}, 400)

    user_res = requests.get(
        "https://api.github.com/user",
        headers={"Authorization": f"Bearer {access_token}"}
    ).json()

    username = user_res.get("login")

    if not username:
        return cors_response({"status": "error", "message": "Failed to fetch user"}, 400)

    user, _ = User.objects.get_or_create(
        username=username,
        defaults={"role": "analyst"}
    )

    return cors_response({
        "status": "success",
        "access_token": generate_access_token(user)
    })


# ======================
# TEST LOGIN
# ======================
def test_login(request):
    if request.method != "POST":
        return cors_response({"status": "error", "message": "Method not allowed"}, 405)

    try:
        body = json.loads(request.body)
        username = body.get("username")
    except:
        return cors_response({"status": "error", "message": "Invalid JSON"}, 422)

    user = User.objects.filter(username=username).first()

    if not user:
        return cors_response({"status": "error", "message": "User not found"}, 404)

    return cors_response({
        "status": "success",
        "access_token": generate_access_token(user)
    })


# ======================
# CREATE PROFILE
# ======================
def create_profile(request):
    user, error = get_authenticated_user(request)
    if error:
        return cors_response({"status": "error", "message": error}, 401)

    if not require_admin(user):
        return cors_response({"status": "error", "message": "Forbidden"}, 403)

    if request.method != "POST":
        return cors_response({"status": "error", "message": "Method not allowed"}, 405)

    try:
        body = json.loads(request.body)
        name = body.get("name")

        if not name:
            return cors_response({"status": "error", "message": "Missing name"}, 400)
    except:
        return cors_response({"status": "error", "message": "Invalid JSON"}, 422)

    existing = Profile.objects.filter(name__iexact=name).first()
    if existing:
        return cors_response({
            "status": "success",
            "message": "Profile already exists",
            "data": serialize_profile(existing)
        })

    g = requests.get(f"https://api.genderize.io?name={name}").json()
    a = requests.get(f"https://api.agify.io?name={name}").json()
    n = requests.get(f"https://api.nationalize.io?name={name}").json()

    if g.get("gender") is None or g.get("count") == 0:
        return cors_response({"status": "error", "message": "Genderize returned an invalid response"}, 502)

    if a.get("age") is None:
        return cors_response({"status": "error", "message": "Agify returned an invalid response"}, 502)

    if not n.get("country"):
        return cors_response({"status": "error", "message": "Nationalize returned an invalid response"}, 502)

    top = max(n["country"], key=lambda x: x["probability"])

    profile = Profile.objects.create(
        id=uuid.uuid4(),
        name=name.lower(),
        gender=g["gender"],
        gender_probability=g["probability"],
        age=a["age"],
        age_group=get_age_group(a["age"]),
        country_id=top["country_id"],
        country_name=top["country_id"],
        country_probability=top["probability"]
    )

    return cors_response({"status": "success", "data": serialize_profile(profile)}, 201)


# ======================
# GET ALL (FILTER + SORT + PAGINATION)
# ======================
def get_all_profiles(request):
    user, error = get_authenticated_user(request)
    if error:
        return cors_response({"status": "error", "message": error}, 401)

    if request.method != "GET":
        return cors_response({"status": "error", "message": "Method not allowed"}, 405)

    profiles = Profile.objects.all()

    try:
        # FILTERS
        if request.GET.get("gender"):
            profiles = profiles.filter(gender__iexact=request.GET["gender"])

        if request.GET.get("age_group"):
            profiles = profiles.filter(age_group__iexact=request.GET["age_group"])

        if request.GET.get("country_id"):
            profiles = profiles.filter(country_id__iexact=request.GET["country_id"])

        if request.GET.get("min_age"):
            profiles = profiles.filter(age__gte=int(request.GET["min_age"]))

        if request.GET.get("max_age"):
            profiles = profiles.filter(age__lte=int(request.GET["max_age"]))

        if request.GET.get("min_gender_probability"):
            profiles = profiles.filter(gender_probability__gte=float(request.GET["min_gender_probability"]))

        if request.GET.get("min_country_probability"):
            profiles = profiles.filter(country_probability__gte=float(request.GET["min_country_probability"]))

        # SORT
        sort_by = request.GET.get("sort_by")
        order = request.GET.get("order", "asc")

        allowed = ["age", "created_at", "gender_probability"]

        if sort_by:
            if sort_by not in allowed:
                return cors_response({"status": "error", "message": "Invalid query parameters"}, 422)

            if order == "desc":
                sort_by = f"-{sort_by}"

            profiles = profiles.order_by(sort_by)

        # PAGINATION
        page = int(request.GET.get("page", 1))
        limit = min(int(request.GET.get("limit", 10)), 50)

        start = (page - 1) * limit
        end = start + limit

        total = profiles.count()
        profiles = profiles[start:end]

    except:
        return cors_response({"status": "error", "message": "Invalid query parameters"}, 422)

    return cors_response({
        "status": "success",
        "page": page,
        "limit": limit,
        "total": total,
        "data": [serialize_profile(p) for p in profiles]
    })


# ======================
# GET SINGLE
# ======================
def get_profile(request, id):
    user, error = get_authenticated_user(request)
    if error:
        return cors_response({"status": "error", "message": error}, 401)

    try:
        profile = Profile.objects.get(id=id)
    except Profile.DoesNotExist:
        return cors_response({"status": "error", "message": "Profile not found"}, 404)

    return cors_response({"status": "success", "data": serialize_profile(profile)})


# ======================
# DELETE
# ======================
def delete_profile(request, id):
    user, error = get_authenticated_user(request)
    if error:
        return cors_response({"status": "error", "message": error}, 401)

    if not require_admin(user):
        return cors_response({"status": "error", "message": "Forbidden"}, 403)

    if request.method != "DELETE":
        return cors_response({"status": "error", "message": "Method not allowed"}, 405)

    try:
        profile = Profile.objects.get(id=id)
        profile.delete()
        return cors_response({}, 204)
    except Profile.DoesNotExist:
        return cors_response({"status": "error", "message": "Profile not found"}, 404)


# ======================
# SEARCH (FIXED)
# ======================
def search_profiles(request):
    user, error = get_authenticated_user(request)
    if error:
        return cors_response({"status": "error", "message": error}, 401)

    query = request.GET.get("q")

    if not query:
        return cors_response({"status": "error", "message": "Missing query"}, 400)

    query = query.lower()
    profiles = Profile.objects.all()
    applied = False

    try:
        if "male" in query:
            profiles = profiles.filter(gender="male")
            applied = True

        if "female" in query:
            profiles = profiles.filter(gender="female")
            applied = True

        if "young" in query:
            profiles = profiles.filter(age__gte=16, age__lte=24)
            applied = True

        if "adult" in query:
            profiles = profiles.filter(age_group="adult")
            applied = True

    except:
        return cors_response({"status": "error", "message": "Unable to interpret query"}, 422)

    if not applied:
        return cors_response({"status": "error", "message": "Unable to interpret query"}, 422)

    return cors_response({
        "status": "success",
        "page": 1,
        "limit": profiles.count(),
        "total": profiles.count(),
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