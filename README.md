# Gender Classification API

## Endpoint
GET /api/classify?name={name}

## Example
/api/classify?name=shifawu

## Live Response
{
    "status": "success",
    "data": {
        "name": "shifawu",
        "gender": "female",
        "probability": 0.99,
        "sample_size": 1234,
        "is_confident": true,
        "processed_at": "2026-04-14T12:00:00Z"
    }
}

## Stack
- Django
- Python
- Requests