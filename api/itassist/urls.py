from django.urls import path
from itassist import views

urlpatterns = [
    #to create a new conversation
    path('new_conv/', views.create_conversation),
    #to delete a conversation and its messages
    path('delete_conv/<str:conv_id>/', views.delete_conversation),
    #to get all conversations with their messages
    path('get_all_conv/', views.get_all_conversations),
    #to upadate a conversation
    path("update_conv/<str:conv_id>/", views.update_conversation),
    #to ask question to the system
    path("add_message/<str:conv_id>/", views.add_user_message_to_conversation),
    #to get full details of a conversation
    path("conversation/<str:conv_id>/", views.get_conversation_detail_view),
    #testing purpose
    path("sync/", views.sync_data_sql_server),
    path("download_file/", views.download_file),
    #path for list_files view
    path("list_files/", views.list_files),
    #to share the document with other users
    path("share_document/", views.share_document),
    #to fetch notifications for a user by email
    path("notify/<str:email>/", views.list_noti_by_email),
    #to download shared file to local and delete it from azure and delete the db entry for shared blob(notification table)
    path('download/', views.download_blob_to_local),
]