from rest_framework import serializers
from .models import Conversation, Message, SharedBlob
from django.utils.timezone import localtime

class ConversationSerializer(serializers.ModelSerializer): 
    class Meta:
        model = Conversation
        fields = ['conv_id', 'Name', 'Date']

class MessageSerializer(serializers.ModelSerializer):
    conversation = serializers.SlugRelatedField(
        queryset=Conversation.objects.using('azure').all(),
        slug_field='conv_id'
    )
    class Meta:
        model = Message
        fields = ['message_id', 'conversation', 'from_field', 'message', 'time']

class SharedBlobSerializer(serializers.ModelSerializer):
    uploaded_at = serializers.SerializerMethodField()

    class Meta:
        model = SharedBlob
        fields = ['sender_email', 'receiver_email', 'file_name', 'blob_url', 'uploaded_at']

    def get_uploaded_at(self, obj):
        return localtime(obj.uploaded_at).strftime('%Y-%m-%d %H:%M:%S')
    
    def create(self, validated_data):
        using = self.context.get('using', None)
        if using:
            return SharedBlob.objects.using(using).create(**validated_data)
        return SharedBlob.objects.create(**validated_data)