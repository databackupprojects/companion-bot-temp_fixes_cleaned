# backend/tasks/celery.py - Celery Configuration
from celery import Celery
import os

# Create Celery instance
celery_app = Celery(
    'companion_bot',
    broker=os.getenv('REDIS_URL', 'redis://localhost:6379/0'),
    backend=os.getenv('REDIS_URL', 'redis://localhost:6379/0'),
    include=['tasks.jobs']
)

# Configure Celery
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_routes={
        'tasks.jobs.*': {'queue': 'jobs'},
    },
    beat_schedule={
        'daily-reset': {
            'task': 'tasks.jobs.run_daily_reset',
            'schedule': 300.0,  # Every 5 minutes
        },
        'memory-summarization': {
            'task': 'tasks.jobs.run_memory_summarization',
            'schedule': 21600.0,  # Every 6 hours
        },
        'data-cleanup': {
            'task': 'tasks.jobs.run_data_cleanup',
            'schedule': 3600.0,  # Every hour
        },
        'proactive-messages': {
            'task': 'tasks.jobs.run_proactive_scheduler',
            'schedule': 900.0,  # Every 15 minutes
        },
    }
)