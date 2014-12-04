# encoding_workflow #

The project is composed from various celery tasks in the adaptation python package. One should only call high level task encoding_workflow in the commons.py module.

## Context ##

The context object is the only object that is passed from task task. It has various helper functions that help computing eg. resources path.


## A Task Scenario ##

* A task is given the context by *args,
* Some named arguments that are retrieve by **kwargs. 
* All named argument should be added to the context. 
* The context fields should be used in the task business. 
* The context should be returned by the task to be used by the next task.


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
