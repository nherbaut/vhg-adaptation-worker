BROKER_URL = 'amqp://guest:guest@192.168.2.122'
CELERY_RESULT_BACKEND = 'amqp://guest:guest@192.168.2.122'
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
config = {"folder_out": "/var/www",
          "bitrates_size_tuple_list": [(10, 10, "low"), (20, 20, "medium"), (30, 30, "high")]}
#CELERY_ACCEPT_CONTENT = ['json']
