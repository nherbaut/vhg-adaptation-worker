BROKER_URL = 'amqp://guest:guest@172.16.1.1'
CELERY_RESULT_BACKEND = 'amqp://guest:guest@172.16.1.1'
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
# CELERY_ACCEPT_CONTENT = ['json']
config = {"folder_out": "/home/nicolas/output",
          "bitrates_size_tuple_list": [(10, 10, "low"), (20, 20, "medium"), (30, 30, "high")]}
