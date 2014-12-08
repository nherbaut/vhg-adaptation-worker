# encoding_workflow #

The project is composed from various celery tasks in the adaptation python package. One should only call high level task encoding_workflow in the commons.py module.

## Context ##

The context diict is the only arg that is passed from task task. It has various helper functions that help computing eg. resources path.

## installation ##

### Celery on Debian ###

sudo apt-get install python-pip mediainfo ffmpeg gpac
sudo pip install celery pymediainfo

### Celery As a Daemon ###

follow instructions given at http://celery.readthedocs.org/en/latest/tutorials/daemonizing.html#generic-init-scripts

### Configuration ###

configuration options are in the settings.py file. You can configure the broker url and default output dir

```python
    BROKER_URL = 'amqp://guest:guest@172.16.1.1' #connection to the message broker
    CELERY_RESULT_BACKEND = 'amqp://guest:guest@172.16.1.1' #that's to connect to result backend
    config = {"folder_out": "/home/nicolas/output", #where the files should be writt en
        "bitrates_size_dict": {100: 100, 200:200}} # what king of transcoding should be done
```

if your worker is called worker 1, logs are located in 

    /var/log/celery/worker1.log

## A Task Scenario ##

* A task is given the context by *args
* Some named arguments that are retrieved by **kwargs. 
* All named arguments should be added to the context dict. 
* Context fields should be used in the task business. 
* Context should be returned by the task to be used by the next task.


## Workflow ##
here's a description on how the encoding workflow tasks work. Some long stating task run un parallel on different workers thanks to a celery chord

    _________________   _______________   ____________________
    | DOWNLOAD FILE |___|GET VIDEO SIZE|__|ADD PLAYLIST HEADER|__     
    |_______________|   |______________|  |___________________|  |
                                                                 |
                                                                 |
                                                _________________|________________
                                                | For each couple heigh/bitrate  |\
                                                |    _____________________       | \
                                                |    |COMPUTE TARGET SIZE |      | |\
                                                |    |____________________|      | | \
                                                |              |                 | | |
                                                |    __________|___________      | | |
                                                |    |TRANSCODE            |     | | |
                                                |    |_____________________|     | | |
                                                |              |                 | | |
                                                |              |                 | | |
                                                |     _________|____________     | | |
                                                |     | CHUNK HLS          |     | | |
                                                |     |____________________|     | | |
                                                |              |                 | | |
                                                |      ________|____________     | | |
                                                |      |ADD PLAYLIST INFO  |     | | |
                                                |      |___________________|     | | |
                                                |              |                 | | |
                                                |      ________|____________     | | |
                                                |      |NOTIFY STATUS      |     | | |
                                                |      |___________________|     | | |
                                                |________________________________| | |
                                                  \____________|__________________\| |
                                                    \__________|___________________\_|
                                                       ________|___________
                                                       |ADD PLAYLIST FOOTER|
                                                       |___________________|
                                                               |
                                                        _______|___________
                                                        | CHUNK DASH       |
                                                        |__________________|
                                                        _______|___________
                                                        | NOTIFY STATUS    |
                                                        |__________________|


## Notifications ##

A notification task, which is passed the highest level task_id, is called when required and update the status, which triggers a json message sent to the result backend. A consumer should listen to the queue named after the task_id given at creation time
