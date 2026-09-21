from fastapi import APIRouter

from ..worker import bootstrap_label

router = APIRouter(prefix="/api/training", tags=["bootstrap-label"])


@router.post("/bootstrap-label/{dataset_id}")
def trigger_bootstrap_label(dataset_id: str, conf_threshold: float | None = None):
    task = bootstrap_label.delay(dataset_id, conf_threshold)
    return {"task_id": task.id, "status": "queued"}


@router.get("/bootstrap-label/tasks/{task_id}")
def get_bootstrap_task(task_id: str):
    result = bootstrap_label.AsyncResult(task_id)
    progress = result.info if result.state == "PROGRESS" and isinstance(result.info, dict) else None
    return {
        "task_id": task_id,
        "state": result.state,
        "progress": progress,
        "result": result.result if result.ready() else None,
    }
