from rest_framework import serializers
from .models import Attempt, Job, WorkflowEvent
class AttemptSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attempt
        fields = "__all__"
class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkflowEvent
        fields = "__all__"
class JobSerializer(serializers.ModelSerializer):
    attempts = AttemptSerializer(many=True, read_only=True)
    events = EventSerializer(many=True, read_only=True)
    class Meta:
        model = Job
        fields = "__all__"
        read_only_fields = ["status","current_attempt","result","error"]
class JobCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Job
        fields = ["task","tool","max_attempts","idempotency_key"]
