#!/bin/bash
celery -A adaptation.commons worker --loglevel=info --concurrency=1
