BROKER_URL = 'amqp://guest:guest@172.16.1.1'
CELERY_RESULT_BACKEND = 'amqp://guest:guest@172.16.1.1'
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
#CELERY_ACCEPT_CONTENT = ['json']
config = {"folder_out": "/home/nicolas/output", "bitrates_size_dict": {100: 100, 200:200}}
