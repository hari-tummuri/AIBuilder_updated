from django.core.management.base import BaseCommand
from itassist.utils.sync_utils import sync_json_to_mysql  # Import your sync function

class Command(BaseCommand):
    help = 'Sync conversations from SQLite to Azure MySQL'

    def handle(self, *args, **kwargs):
        # Call your existing sync function to sync data
        sync_json_to_mysql()

