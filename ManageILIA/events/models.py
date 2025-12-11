from django.db import models


class Event(models.Model):
    id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    start = models.DateTimeField()
    end = models.DateTimeField()

    organiser = models.ForeignKey('ILIA.Personne', on_delete=models.SET_NULL, null=True, blank=True)
    co_organisers = models.ManyToManyField('ILIA.Personne', related_name='co_events', blank=True)

    def __str__(self):
        return self.title


class Participant(models.Model):
    class Status(models.IntegerChoices):
        INVITED = 0, 'En attente'
        ACCEPTED = 1, 'Accepté'
        DECLINED = 2, 'Refusé'

    id = models.AutoField(primary_key=True)
    event = models.ForeignKey(Event, related_name='participants', on_delete=models.CASCADE)
    person = models.ForeignKey('ILIA.Personne', on_delete=models.CASCADE)
    status = models.IntegerField(choices=Status.choices, default=Status.INVITED)

    def __str__(self):
        return f"{self.person} - {self.get_status_display()}"
