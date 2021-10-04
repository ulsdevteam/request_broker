from rest_framework import serializers

class LinkResolverSerializer(serializers.Serializer):
  ref_id = serializers.CharField()
