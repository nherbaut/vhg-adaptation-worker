config = {"folder_out": "/var/www",
          "bitrates_size_tuple_list": [(10, 10, "low"), (20, 20, "medium"), (30, 30, "high")],
          "broker_host": "192.168.2.122",
          "broker_user": "guest",
          "broker_pwd": "guest"}

BROKER_URL = 'amqp://' + config["broker_user"] + ':' + config["broker_pwd"] + '@' + config["broker_host"]
CELERY_RESULT_BACKEND = BROKER_URL
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
# CELERY_ACCEPT_CONTENT = ['json']
