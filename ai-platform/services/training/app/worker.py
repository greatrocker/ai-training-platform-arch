from celery import Celery

from .config import settings

celery_app = Celery("training", broker=settings.celery_broker_url, backend=settings.celery_broker_url)


@celery_app.task(name="training.run_job")
def run_job(job_id: str) -> dict:
    from .train_job import run_training_job

    return run_training_job(job_id)


@celery_app.task(name="training.bootstrap_label", bind=True)
def bootstrap_label(self, dataset_id: str, conf_threshold: float | None = None) -> dict:
    from .bootstrap import run_bootstrap_label

    try:
        return run_bootstrap_label(dataset_id, conf_threshold=conf_threshold, task=self)
    except Exception as exc:
        return {"status": "failed", "reason": str(exc)}
