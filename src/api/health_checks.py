from fastapi import BackgroundTasks

from src.infrastructure.performance.performance_monitor_singleton import (
    get_performance_monitor,
)


async def get_health_status(background_tasks: BackgroundTasks):
    """
    Endpoint to get the health status of the application.
    """
    performance_monitor = get_performance_monitor()
    background_tasks.add_task(performance_monitor.generate_report)
    return {"status": "ok", "message": "Health report generation started."}
