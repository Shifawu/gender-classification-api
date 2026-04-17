import json
import requests
from datetime import datetime
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Profile


# ---------------------------
# Helper: CORS Response
# ---------------------------
def cors_response(data, status=200):
    response = JsonResponse(data, status=status, safe=False)
    response["Access-Control-Allow-Origin"] = "*"
    return response


# ---------------------------
# STAGE 0 — GET /api/classify
# ---------------------------
def classify_name(request):
    name = request.GET.get('name')

    if not name:
        return cors_response({
            "status": "error",
            "message": "Name parameter is required"
        }, status=400)

    try:
        response = requests.get(
            f"https://api.genderize.io?name={name}",
            timeout=5
        )

        if response.status_code != 200:
            return cors_response({
                "status": "error",
                "message": "Upstream service error"
            }, status=502)

        data = response.json()

        gender = data.get("gender")
        probability = data.get("probability")
        count = data.get("count")

        if gender is None or count == 0:
            return cors_response({
                "status": "error",
                "message": "No prediction available for the provided name"
            }, status=422)

        sample_size = count
        is_confident = probability >= 0.7 and sample_size >= 100
        processed_at = datetime.utcnow().isoformat() + "Z"

        return cors_response({
            "status": "success",
            "data": {
                "name": name,
                "gender": gender,
                "probability": probability,
                "sample_size": sample_size,
                "is_confident": is_confident,
                "processed_at": processed_at
            }
        })

    except requests.exceptions.RequestException:
        return cors_response({
            "status": "error",
            "message": "Failed to reach external service"
        }, status=502)


# ---------------------------
# STAGE 1 — PROFILES (GET + POST)
# ---------------------------
@csrf_exempt
def profiles(request):

    # ======================
    # POST → CREATE PROFILE
    # ======================
    if request.method == "POST":
        try:
            body = json.loads(request.body)
            name = body.get("name")
        except:
            return cors_response({
                "status": "error",
                "message": "Invalid JSON"
            }, status=400)

        if not name:
            return cors_response({
                "status": "error",
                "message": "Name is required"
            }, status=400)

        name = name.lower()

        # Check duplicate
        existing = Profile.objects.filter(name=name).first()
        if existing:
            return cors_response({
                "status": "success",
                "message": "Profile already exists",
                "data": {
                    "id": str(existing.id),
                    "name": existing.name,
                    "gender": existing.gender,
                    "gender_probability": existing.gender_probability,
                    "sample_size": existing.sample_size,
                    "age": existing.age,
                    "age_group": existing.age_group,
                    "country_id": existing.country_id,
                    "country_probability": existing.country_probability,
                    "created_at": existing.created_at.isoformat() + "Z"
                }
            })

        try:
            gender_res = requests.get(f"https://api.genderize.io?name={name}").json()
            age_res = requests.get(f"https://api.agify.io?name={name}").json()
            nation_res = requests.get(f"https://api.nationalize.io?name={name}").json()

            # Edge cases
            if gender_res.get("gender") is None or gender_res.get("count") == 0:
                return cors_response({
                    "status": "error",
                    "message": "Genderize returned an invalid response"
                }, status=502)

            if age_res.get("age") is None:
                return cors_response({
                    "status": "error",
                    "message": "Agify returned an invalid response"
                }, status=502)

            countries = nation_res.get("country")
            if not countries:
                return cors_response({
                    "status": "error",
                    "message": "Nationalize returned an invalid response"
                }, status=502)

            # Process data
            age = age_res["age"]

            if age <= 12:
                age_group = "child"
            elif age <= 19:
                age_group = "teenager"
            elif age <= 59:
                age_group = "adult"
            else:
                age_group = "senior"

            top_country = max(countries, key=lambda x: x["probability"])

            profile = Profile.objects.create(
                name=name,
                gender=gender_res["gender"],
                gender_probability=gender_res["probability"],
                sample_size=gender_res["count"],
                age=age,
                age_group=age_group,
                country_id=top_country["country_id"],
                country_probability=top_country["probability"]
            )

            return cors_response({
                "status": "success",
                "data": {
                    "id": str(profile.id),
                    "name": profile.name,
                    "gender": profile.gender,
                    "gender_probability": profile.gender_probability,
                    "sample_size": profile.sample_size,
                    "age": profile.age,
                    "age_group": profile.age_group,
                    "country_id": profile.country_id,
                    "country_probability": profile.country_probability,
                    "created_at": profile.created_at.isoformat() + "Z"
                }
            }, status=201)

        except:
            return cors_response({
                "status": "error",
                "message": "External API request failed"
            }, status=502)

    # ======================
    # GET → LIST + FILTER
    # ======================
    elif request.method == "GET":
        profiles = Profile.objects.all()

        gender = request.GET.get("gender")
        country_id = request.GET.get("country_id")
        age_group = request.GET.get("age_group")

        if gender:
            profiles = profiles.filter(gender__iexact=gender)

        if country_id:
            profiles = profiles.filter(country_id__iexact=country_id)

        if age_group:
            profiles = profiles.filter(age_group__iexact=age_group)

        data = [
            {
                "id": str(p.id),
                "name": p.name,
                "gender": p.gender,
                "age": p.age,
                "age_group": p.age_group,
                "country_id": p.country_id
            }
            for p in profiles
        ]

        return cors_response({
            "status": "success",
            "count": len(data),
            "data": data
        })

    return cors_response({
        "status": "error",
        "message": "Method not allowed"
    }, status=405)


# ---------------------------
# STAGE 1 — SINGLE (GET + DELETE)
# ---------------------------
@csrf_exempt
def profile_detail(request, id):
    try:
        profile = Profile.objects.get(id=id)

        if request.method == "GET":
            return cors_response({
                "status": "success",
                "data": {
                    "id": str(profile.id),
                    "name": profile.name,
                    "gender": profile.gender,
                    "gender_probability": profile.gender_probability,
                    "sample_size": profile.sample_size,
                    "age": profile.age,
                    "age_group": profile.age_group,
                    "country_id": profile.country_id,
                    "country_probability": profile.country_probability,
                    "created_at": profile.created_at.isoformat() + "Z"
                }
            })

        elif request.method == "DELETE":
            profile.delete()
            return cors_response({}, status=204)

        else:
            return cors_response({
                "status": "error",
                "message": "Method not allowed"
            }, status=405)

    except Profile.DoesNotExist:
        return cors_response({
            "status": "error",
            "message": "Profile not found"
        }, status=404)