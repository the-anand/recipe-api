'''
Command to wait for database to be available
'''

import time
from psycopg2 import OperationalError as Psycopg2Error
from django.db.utils import OperationalError
from django.core.management.base import BaseCommand

class Command(BaseCommand):

    def handle(self, *args, **options):
        self.stdout.write('Waiting for database to be connected...')

        db_up= False

        while db_up is False:
            try:
                self.check(databases=['default'])
                db_up= True
            except (Psycopg2Error, OperationalError):
                self.stdout.write('Database offline waiting to reconnect in 1 sec')
                time.sleep(1)
        
        self.stdout.write(self.style.SUCCESS('Database online'))