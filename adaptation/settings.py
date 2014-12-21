BROKER_URL = 'amqp://guest:guest@localhost'
CELERY_RESULT_BACKEND = 'amqp://guest:guest@localhost'
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
#CELERY_ACCEPT_CONTENT = ['json']
config = {"folder_out": "/var/www/html", "bitrates_size_dict": {240:20, 480:1500, 720:3000}}
