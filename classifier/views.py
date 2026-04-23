import json
import uuid
import requests
from django.http import JsonResponse
from .models import Profile


# ======================
# CORS HELPER
# ======================
def cors_response(data, status=200):
    response = JsonResponse(data, status=status)
    response["Access-Control-Allow-Origin"] = "*"
    return response


# ======================
# AGE GROUP LOGIC
# ======================
def get_age_group(age):
    if age <= 12:
        return "child"
    elif age <= 19:
        return "teenager"
    elif age <= 59:
        return "adult"
    else:
        return "senior"


# ======================
# CREATE PROFILE (POST)
# ======================
def create_profile(request):
    if request.method != "POST":
        return cors_response({"status": "error", "message": "Method not allowed"}, 405)

    try:
        body = json.loads(request.body)
        name = body.get("name")

        if not name:
            return cors_response({"status": "error", "message": "Missing name"}, 400)

    except:
        return cors_response({"status": "error", "message": "Invalid JSON"}, 422)

    # Check duplicate
    existing = Profile.objects.filter(name__iexact=name).first()
    if existing:
        return cors_response({
            "status": "success",
            "message": "Profile already exists",
            "data": serialize_profile(existing)
        }, 200)

    # External APIs
    gender_res = requests.get(f"https://api.genderize.io?name={name}").json()
    age_res = requests.get(f"https://api.agify.io?name={name}").json()
    nation_res = requests.get(f"https://api.nationalize.io?name={name}").json()

    # Edge cases
    if gender_res.get("gender") is None or gender_res.get("count") == 0:
        return cors_response({"status": "error", "message": "Genderize returned an invalid response"}, 502)

    if age_res.get("age") is None:
        return cors_response({"status": "error", "message": "Agify returned an invalid response"}, 502)

    countries = nation_res.get("country")
    if not countries:
        return cors_response({"status": "error", "message": "Nationalize returned an invalid response"}, 502)

    top_country = max(countries, key=lambda x: x["probability"])

    profile = Profile.objects.create(
        id=uuid.uuid4(),
        name=name.lower(),
        gender=gender_res["gender"],
        gender_probability=gender_res["probability"],
        age=age_res["age"],
        age_group=get_age_group(age_res["age"]),
        country_id=top_country["country_id"],
        country_name=top_country["country_id"],  # simple for now
        country_probability=top_country["probability"]
    )

    return cors_response({
        "status": "success",
        "data": serialize_profile(profile)
    }, 201)


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
# GET ALL (FILTER + SORT + PAGINATION)
# ======================
def get_all_profiles(request):
    if request.method != "GET":
        return cors_response({"status": "error", "message": "Method not allowed"}, 405)

    profiles = Profile.objects.all()

    try:
        # Filters
        gender = request.GET.get("gender")
        age_group = request.GET.get("age_group")
        country_id = request.GET.get("country_id")

        min_age = request.GET.get("min_age")
        max_age = request.GET.get("max_age")
        min_gender_prob = request.GET.get("min_gender_probability")
        min_country_prob = request.GET.get("min_country_probability")

        if gender:
            profiles = profiles.filter(gender__iexact=gender)

        if age_group:
            profiles = profiles.filter(age_group__iexact=age_group)

        if country_id:
            profiles = profiles.filter(country_id__iexact=country_id)

        if min_age:
            profiles = profiles.filter(age__gte=int(min_age))

        if max_age:
            profiles = profiles.filter(age__lte=int(max_age))

        if min_gender_prob:
            profiles = profiles.filter(gender_probability__gte=float(min_gender_prob))

        if min_country_prob:
            profiles = profiles.filter(country_probability__gte=float(min_country_prob))

        # Sorting
        sort_by = request.GET.get("sort_by")
        order = request.GET.get("order", "asc")

        if sort_by in ["age", "created_at", "gender_probability"]:
            if order == "desc":
                sort_by = f"-{sort_by}"
            profiles = profiles.order_by(sort_by)

        # Pagination
        page = int(request.GET.get("page", 1))
        limit = min(int(request.GET.get("limit", 10)), 50)

        start = (page - 1) * limit
        end = start + limit

        total = profiles.count()
        profiles = profiles[start:end]

    except:
        return cors_response({"status": "error", "message": "Invalid query parameters"}, 422)

    data = [serialize_profile(p) for p in profiles]

    return cors_response({
        "status": "success",
        "page": page,
        "limit": limit,
        "total": total,
        "data": data
    })

def profiles_handler(request):
    if request.method == "POST":
        return create_profile(request)

    elif request.method == "GET":
        return get_all_profiles(request)

    return cors_response({
        "status": "error",
        "message": "Method not allowed"
    }, 405)


# ======================
# GET SINGLE
# ======================
def get_profile(request, id):
    if request.method != "GET":
        return cors_response({"status": "error", "message": "Method not allowed"}, 405)

    try:
        profile = Profile.objects.get(id=id)
    except Profile.DoesNotExist:
        return cors_response({"status": "error", "message": "Profile not found"}, 404)

    return cors_response({
        "status": "success",
        "data": serialize_profile(profile)
    })


# ======================
# DELETE
# ======================
def delete_profile(request, id):
    if request.method != "DELETE":
        return cors_response({"status": "error", "message": "Method not allowed"}, 405)

    try:
        profile = Profile.objects.get(id=id)
        profile.delete()
        return cors_response({}, 204)
    except Profile.DoesNotExist:
        return cors_response({"status": "error", "message": "Profile not found"}, 404)

def search_profiles(request):
    if request.method != "GET":
        return cors_response({"status": "error", "message": "Method not allowed"}, 405)

    query = request.GET.get("q")

    if not query:
        return cors_response({"status": "error", "message": "Missing query"}, 400)

    query = query.lower()

    profiles = Profile.objects.all()

    try:
        # ======================
        # GENDER
        # ======================
        if "male" in query:
            profiles = profiles.filter(gender="male")

        if "female" in query:
            profiles = profiles.filter(gender="female")

        # ======================
        # AGE KEYWORDS
        # ======================
        if "young" in query:
            profiles = profiles.filter(age__gte=16, age__lte=24)

        if "adult" in query:
            profiles = profiles.filter(age_group="adult")

        if "teenager" in query:
            profiles = profiles.filter(age_group="teenager")

        if "child" in query:
            profiles = profiles.filter(age_group="child")

        if "senior" in query:
            profiles = profiles.filter(age_group="senior")

        # ======================
        # AGE NUMBERS (above X)
        # ======================
        if "above" in query:
            parts = query.split()
            for i, word in enumerate(parts):
                if word == "above":
                    age = int(parts[i + 1])
                    profiles = profiles.filter(age__gte=age)

        # ======================
        # COUNTRY (simple mapping)
        # ======================
        country_map = {
            "nigeria": "NG",
            "kenya": "KE",
            "ghana": "GH",
            "angola": "AO",
            "usa": "US"
        }

        for country_name, code in country_map.items():
            if country_name in query:
                profiles = profiles.filter(country_id=code)

    except:
        return cors_response({
            "status": "error",
            "message": "Unable to interpret query"
        }, 400)

    # Pagination (same as before)
    page = int(request.GET.get("page", 1))
    limit = min(int(request.GET.get("limit", 10)), 50)

    start = (page - 1) * limit
    end = start + limit

    total = profiles.count()
    profiles = profiles[start:end]

    data = [serialize_profile(p) for p in profiles]

    return cors_response({
        "status": "success",
        "page": page,
        "limit": limit,
        "total": total,
        "data": data
    })