import requests 
from django.http import JsonResponse
from datetime import datetime

def cors_response(data, status=200):
    response = JsonResponse(data, status=status)
    response["Access-Control-Allow-Origin"] = "*"

    return response

def classify_name(request):
    name = request.GET.get('name')

    #400 - missing name
    if not name:
        return cors_response({
            "status": "error",
            "message": "Name parameter is required"
        }, status=400)
    
    #422 - invalid type
    if not isinstance(name, str):
        return cors_response({
            "status": "error",
            "message": "Name must be a string"
        }, status=422)
    
    try:
        response = requests.get(f"https://api.genderize.io?name={name}", timeout=5)

        # 502 - upstream error
        if response.status_code != 200:
            return cors_response({
                "status": "error",
                "message": "Upstream service error"
            }, status=502)
        
        data = response.json()

        gender = data.get("gender")
        probability = data.get("probability")
        count = data.get("count")

        # 422 - no prediction
        if gender is None or count == 0:
            return cors_response({
                "status": "error",
                "message": "No prediction abailable for the provided name"
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