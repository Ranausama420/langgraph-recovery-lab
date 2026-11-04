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

    def validate_task(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Task cannot be empty.")
        return value

    def validate_tool(self, value):
        value = value.strip()
        if value not in {"report", "unstable_email", "validation"}:
            raise serializers.ValidationError("Unsupported tool.")
        return value

    def validate_max_attempts(self, value):
        if not 1 <= value <= 10:
            raise serializers.ValidationError("max_attempts must be between 1 and 10.")
        return value

    def validate_idempotency_key(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("idempotency_key cannot be empty.")
        return value
