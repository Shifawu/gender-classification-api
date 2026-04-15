# Gender Classification API

A simple backend API built with Django that classifies a given name by gender using the Genderize.io API and returns a processed, structured response.

---

## Live Endpoint

GET /api/classify?name={name}

### Example:

```
/api/classify?name=john
```

---

## Response Format

### Success Response (200 OK)

```json
{
  "status": "success",
  "data": {
    "name": "john",
    "gender": "male",
    "probability": 0.99,
    "sample_size": 1234,
    "is_confident": true,
    "processed_at": "2026-04-14T12:00:00Z"
  }
}
```

---

## Error Responses

### 400 Bad Request

* Missing or empty name parameter

```json
{
  "status": "error",
  "message": "Name parameter is required"
}
```

---

### 422 Unprocessable Entity

* No prediction available (gender is null or sample size is 0)
* Name is not a valid string

```json
{
  "status": "error",
  "message": "No prediction available for the provided name"
}
```

---

### 502 Bad Gateway

* External API failure

```json
{
  "status": "error",
  "message": "Failed to reach external service"
}
```

---

## Processing Logic

* Extracts:

  * `gender`
  * `probability`
  * `count` → renamed to `sample_size`

* Computes:

  * `is_confident` = true if:

    * probability ≥ 0.7 AND
    * sample_size ≥ 100

* Generates:

  * `processed_at` → current UTC time in ISO 8601 format

---

##  Tech Stack

* Python
* Django
* Requests library

---

## External API

* Genderize.io

---

## Setup Instructions (Local Development)

1. Clone the repository:

```
git clone https://github.com/YOUR_USERNAME/gender-classification-api.git
cd gender-classification-api
```

2. Create a virtual environment:

```
python -m venv venv
source venv/bin/activate   # On Windows: venv\Scripts\activate
```

3. Install dependencies:

```
pip install -r requirements.txt
```

4. Run the server:

```
python manage.py runserver
```

5. Test the API:

```
http://127.0.0.1:8000/api/classify?name=john
```



## Notes

* CORS is enabled to allow external access
* Handles multiple requests efficiently
* Includes proper error handling and validation



## Author

Shifawu Bello

