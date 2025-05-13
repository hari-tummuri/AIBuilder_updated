from django.db import models

# Create your models here.
class Conversation(models.Model):
    conv_id = models.CharField(max_length=100, primary_key=True)
    Name = models.CharField(max_length=255)
    Date = models.DateTimeField()

    def __str__(self):
        return self.conv_id


class Message(models.Model):
    message_id = models.CharField(max_length=150, primary_key=True)  # Unique message ID (conv_id + number)
    conversation = models.ForeignKey(Conversation, related_name="messages", on_delete=models.CASCADE)
    from_field = models.CharField(max_length=50)  # "User" or "System"
    message = models.TextField()
    time = models.DateTimeField()

    def __str__(self):
        return f"{self.conversation.conv_id} - {self.message_id}: {self.from_field}"
    

class SharedBlob(models.Model):
    sender_email = models.EmailField()
    receiver_email = models.EmailField()
    file_name = models.CharField(max_length=255)
    blob_url = models.URLField()
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.file_name} from {self.sender_email} to {self.receiver_email}"