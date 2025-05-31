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
    #to list all models
    path('list_models/', views.list_downloaded_ollama_models),
    #to download a model
    path('api/download_model/', views.download_ollama_model),

    #to cancel the model download
    path('api/cancel_download/', views.cancel_download),

    #to delete a model
    path('api/delete_model/', views.delete_ollama_model),
    
    #to upload a file to Vector DB and store it in others folder
    path("upload_document/", views.upload_document),

    # path("query_user_doc/<str:conv_id>/", views.add_user_message_to_conversation),

    #to delete files in others folder
    path('delete_document/', views.delete_document_view),

    #to retrive the hyperparameters
    path('hyperparameters/', views.get_hyperparams_view),

    #to save the hyperparameters
    path('save_hyperparameters/', views.save_selected_hyper_params),

    #to restore the default hyperparameters
    path('restore_default_params/', views.restore_default_hyper_params),

    #to get the system info
    path('get_system_info/', views.get_system_info_view),

    #to swith the model
    path('switch_model/', views.switch_model_view),

    #to get the currently selected model
    path('current_model/', views.get_current_model_view),
    
    path('stop_model/', views.stop_ollama_model_view),

    path('ollama_chat/', views.ollama_chat_view),

    
]
    



    #testing
    
    
