from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from .models import Branch, Subject


class BranchSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Branch
        fields = ("id", "name", "city")


class SubjectSerializer(serializers.ModelSerializer):
    branch = BranchSummarySerializer(read_only=True)
    branch_id = serializers.PrimaryKeyRelatedField(source="branch", queryset=Branch.objects.all(), write_only=True)

    class Meta:
        model = Subject
        fields = ("id", "name", "branch", "branch_id", "status")
        read_only_fields = ("id", "branch")

    def validate(self, attrs):
        branch = attrs.get("branch") or getattr(self.instance, "branch", None)
        name = attrs.get("name") or getattr(self.instance, "name", None)

        if branch is not None and name:
            queryset = Subject.objects.filter(branch=branch, name__iexact=name)
            if self.instance is not None:
                queryset = queryset.exclude(pk=self.instance.pk)
            if queryset.exists():
                raise ValidationError({"name": "A subject with this name already exists in this branch."})

        if self.instance is not None and "branch" in attrs and branch is not None and branch.id != self.instance.branch_id:
            raise ValidationError({"branch_id": "Subject branch cannot be changed here."})

        return attrs