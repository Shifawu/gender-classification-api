import json
from django.core.management.base import BaseCommand
from classifier.models import Profile

class Command(BaseCommand):
    help = "Seed database with profiles"

    def handle(self, *args, **kwargs):
        with open("seed_profiles.json") as f:
            data = json.load(f) ["profiles"]

        count = 0

        for item in data:
            name = item["name"].lower()

            if Profile.objects.filter(name=name).exists():
                continue  # prevent duplicates

            Profile.objects.create(
                name=name,
                gender=item["gender"],
                gender_probability=item["gender_probability"],
                age=item["age"],
                age_group=item["age_group"],
                country_id=item["country_id"],
                country_name=item["country_name"],
                country_probability=item["country_probability"]
            )

            count += 1

        self.stdout.write(self.style.SUCCESS(f"Seeded {count} profiles"))