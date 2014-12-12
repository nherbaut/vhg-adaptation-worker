config = {"folder_out": "/var/www/html",
          "bitrates_size_tuple_list": [(100, 100, "low"), (200, 200, "medium"), (500, 300, "high")],
          "broker_host": "frontal",
          "broker_user": "guest",
          "broker_pwd": "guest"}

BROKER_URL = 'amqp://' + config["broker_user"] + ':' + config["broker_pwd"] + '@' + config["broker_host"]
CELERY_RESULT_BACKEND = BROKER_URL
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
# CELERY_ACCEPT_CONTENT = ['json']
