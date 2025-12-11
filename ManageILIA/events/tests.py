from django.test import TestCase
from .models import Event
from django.utils import timezone


class EventModelTest(TestCase):
    def test_create_event(self):
        start = timezone.now()
        end = start + timezone.timedelta(hours=1)
        e = Event.objects.create(title='Test', description='Desc', start=start, end=end)
        self.assertEqual(str(e), 'Test')
