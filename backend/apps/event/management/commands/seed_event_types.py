from django.core.management.base import BaseCommand
from apps.event.models.event_type import EventType

class Command(BaseCommand):
    help = 'Seeds initial popular event types'

    def handle(self, *args, **options):
        event_types = [
            {'name': 'Birthday', 'slug': 'birthday', 'description': 'Celebrate another year of life.'},
            {'name': 'Memorial', 'slug': 'memorial', 'description': 'Honor and remember a loved one.'},
            {'name': 'Anniversary', 'slug': 'anniversary', 'description': 'Celebrate years of love and commitment.'},
            {'name': 'Wedding', 'slug': 'wedding', 'description': 'Celebrate the union of two people.'},
            {'name': 'Graduation', 'slug': 'graduation', 'description': 'Celebrate academic achievements.'},
            {'name': 'Retirement', 'slug': 'retirement', 'description': 'Celebrate a career and new beginnings.'},
        ]

        for et_data in event_types:
            obj, created = EventType.objects.get_or_create(
                slug=et_data['slug'],
                defaults={'name': et_data['name'], 'description': et_data['description']}
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"Created event type: {obj.name}"))
            else:
                self.stdout.write(self.style.WARNING(f"Event type already exists: {obj.name}"))
        
        self.stdout.write(self.style.SUCCESS("Event types seeding complete!"))
