import json
from datetime import datetime

from rest_framework.exceptions import ValidationError

from core.settings import CONV_JSON_FILE
from django.utils.dateparse import parse_datetime


# def sync_json_to_mysql():
#     # try:
#     #     with open(CONV_JSON_FILE, "r") as file:
#     #         conversations_json = json.load(file)
#     # except FileNotFoundError:
#     #     print("❌ Conversation JSON file not found.")
#     #     return

#     # for conv_data in conversations_json:
#     #     conv_id = conv_data.get("conv_id")
#     #     name = conv_data.get("Name")
#     #     date = conv_data.get("Date")

#     #     if not (conv_id and name and date):
#     #         print(f"❌ Skipping conversation due to missing fields: {conv_data}")
#     #         continue

#     #     # Create conversation if not exists
#     #     if not Conversation.objects.filter(conv_id=conv_id).exists():
#     #         conv_serializer = ConversationSerializer(data={
#     #             "conv_id": conv_id,
#     #             "Name": name,
#     #             "Date": date,
#     #         })

#     #         if conv_serializer.is_valid():
#     #             conv_serializer.save()
#     #             print(f"✅ Added conversation: {conv_id}")
#     #         else:
#     #             print(f"❌ Invalid conversation ({conv_id}): {conv_serializer.errors}")
#     #             continue

#     #     conversation_obj = Conversation.objects.get(conv_id=conv_id)

#     #     # Get already existing message IDs
#     #     existing_msg_ids = set(
#     #         Message.objects.filter(conversation=conversation_obj)
#     #         .values_list("message_id", flat=True)
#     #     )

#     #     for msg in conv_data.get("messages", []):
#     #         msg_id = msg.get("id")  # JSON uses "id" as the message ID
#     #         msg_text = msg.get("message")
#     #         msg_from = msg.get("from_field")  # Use "from_field"
#     #         msg_time = msg.get("time")

#     #         if None in [msg_id, msg_text, msg_from, msg_time]:
#     #             print(f"❌ Skipping message with missing fields: {msg}")
#     #             continue

#     #         if msg_id in existing_msg_ids:
#     #             continue  # Already synced

#     #         msg_serializer = MessageSerializer(data={
#     #             "message_id": msg_id,
#     #             "conversation": conversation_obj.pk,
#     #             "from_field": msg_from,
#     #             "message": msg_text,
#     #             "time": msg_time
#     #         })

#     #         if msg_serializer.is_valid():
#     #             msg_serializer.save()
#     #             print(f"✅ Added message: {msg_id}")
#     #         else:
#     #             print(f"❌ Invalid message ({msg_id}): {msg_serializer.errors}")
#     # Read data from the provided JSON file

#     from ..models import Conversation, Message
#     from ..serializers import ConversationSerializer, MessageSerializer

#     try:
#         with open(CONV_JSON_FILE, "r") as file:
#             data = json.load(file)
#     except FileNotFoundError:
#         print(f"⚠️ File {CONV_JSON_FILE} not found.")
#         return

#     # Get already existing conversation IDs from the database
#     existing_conv_ids = set(Conversation.objects.values_list("conv_id", flat=True))

#     for conv in data:
#         conv_id = conv["conv_id"]

#         # Handle Conversation
#         if conv_id not in existing_conv_ids:
#             # Create and validate new conversation
#             conversation_data = {
#                 "conv_id": conv["conv_id"],
#                 "Name": conv["Name"],
#                 "Date": parse_datetime(conv["Date"])
#             }
#             try:
#                 conversation_serializer = ConversationSerializer(data=conversation_data)
#                 if conversation_serializer.is_valid():
#                     # conversation_obj = conversation_serializer.save()  # Save new conversation
#                     # conversation_obj.save(using='azure')
#                     # Create an instance but do NOT save to DB yet
#                     conversation_obj = Conversation(**conversation_serializer.validated_data)

#                     # Save it explicitly to Azure DB
#                     conversation_obj.save(using='azure')
#                     # print(f"DB used: {conversation_obj._state.db}")  # Should print 'azure'
#                     print(f"✅ Added conversation: {conv_id}")
#                     print(f"DB used: {conversation_obj._state.db}")  # Should print 'azure'
#                 else:
#                     print(f"⚠️ Failed to validate conversation: {conversation_serializer.errors}")
#                     continue
#             except ValidationError as e:
#                 print(f"⚠️ Error while adding conversation: {e}")
#                 continue
#         else:
#             # If the conversation already exists, retrieve it
#             conversation_obj = Conversation.objects.get(conv_id=conv_id)
#             print(f"ℹ️ Conversation already exists: {conv_id}")

#         # Handle Messages
#         existing_msg_ids = set(
#             Message.objects.filter(conversation=conversation_obj)
#             .values_list("message_id", flat=True)
#         )

#         for msg in conv.get("messages", []):
#             msg_id = msg.get("id")
#             if msg_id in existing_msg_ids:
#                 print(f"🔁 Skipped existing message: {msg_id}")
#                 continue

#             # Prepare data for the message
#             msg_data = {
#                 "message_id": msg["id"],
#                 "from_field": msg["from_field"],
#                 "message": msg["message"],
#                 "time": parse_datetime(msg["time"]),
#                 "conversation": conversation_obj
#             }
#             print(f"conversation id is {msg_data['conversation']}")
#             try:
#                 # Try to get the conversation from Azure
#                 try:
#                     conv = Conversation.objects.using('azure').get(conv_id=msg_data['conversation'])
#                 except Conversation.DoesNotExist:
#                     print(f"❌ Conversation {msg_data['conversation']} does not exist in Azure DB.")
#                     continue  # Skip this message

#                 # Attach and save the message
#                 msg_data['conversation'] = conv.conv_id  # or conv.pk

#                 message_serializer = MessageSerializer(data=msg_data)
#                 if message_serializer.is_valid():
#                     # message_obj = message_serializer.save()  # Save new message
#                     # message_obj.save(using='azure')
#                     message_obj = Message(**message_serializer.validated_data)

#                     # Save it explicitly to Azure DB
#                     message_obj.save(using='azure')
#                     print(f"✅ Added message: {msg_id}")
#                 else:
#                     print(f"⚠️ Failed to validate message: {message_serializer.errors}")
#                     continue
#             except ValidationError as e:
#                 print(f"⚠️ Error while adding message: {e}")
#                 continue

def sync_json_to_mysql():
    from ..models import Conversation, Message
    from ..serializers import ConversationSerializer, MessageSerializer

    try:
        with open(CONV_JSON_FILE, "r") as file:
            data = json.load(file)
    except FileNotFoundError:
        print(f"⚠️ File {CONV_JSON_FILE} not found.")
        return
    
    existing_conv_ids = set(Conversation.objects.using('azure').values_list("conv_id", flat=True))

    for conv in data:
        conv_id = conv["conv_id"]

        if conv_id not in existing_conv_ids:
            conversation_data = {
                "conv_id": conv["conv_id"],
                "Name": conv["Name"],
                "Date": parse_datetime(conv["Date"])
            }

            try:
                serializer = ConversationSerializer(data=conversation_data)
                if serializer.is_valid():
                    conversation_obj = Conversation(**serializer.validated_data)
                    conversation_obj.save(using='azure')
                    print(f"✅ Added conversation: {conv_id}")

                    # Conversation just created, no messages exist yet
                    conversation_obj = Conversation.objects.using('azure').get(conv_id=conv_id)
                    existing_msg_ids = set()
                else:
                    print(f"⚠️ Invalid conversation: {serializer.errors}")
                    continue
            except ValidationError as e:
                print(f"⚠️ Error while adding conversation: {e}")
                continue
        else:
            conversation_obj = Conversation.objects.using('azure').get(conv_id=conv_id)
            print(f"ℹ️ Conversation already exists: {conv_id}")

            # Get existing message IDs for this conversation
            existing_msg_ids = set(
                Message.objects.using('azure')
                .filter(conversation=conversation_obj)
                .values_list('message_id', flat=True)
            )

        # Now process messages
        for msg in conv.get("messages", []):
            msg_id = msg.get("id")
            if msg_id in existing_msg_ids:
                print(f"🔁 Skipped existing message: {msg_id}")
                continue

            try:
                msg_data = {
                    "message_id": msg["id"],
                    "from_field": msg["from_field"],
                    "message": msg["message"],
                    "time": parse_datetime(msg["time"]),
                    "conversation": conversation_obj.pk  # Always use the pk of Azure conversation
                }

                serializer = MessageSerializer(data=msg_data)
                if serializer.is_valid():
                    message_obj = Message(**serializer.validated_data)
                    message_obj.save(using='azure')
                    print(f"✅ Added message: {msg_id}")
                else:
                    print(f"⚠️ Invalid message: {serializer.errors}")

            except Conversation.DoesNotExist:
                print(f"❌ Conversation {conv_id} not found in Azure DB for message {msg_id}")
            except ValidationError as e:
                print(f"⚠️ Error while adding message: {e}")