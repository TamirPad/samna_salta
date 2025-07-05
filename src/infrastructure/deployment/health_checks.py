"""
Health Check System for Deployment Monitoring

Provides comprehensive health checks for database, cache, external services,
and overall system health monitoring.
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

import httpx
import psutil
from sqlalchemy import text

from src.infrastructure.cache.cache_manager import CacheManager
from src.infrastructure.database.operations import get_engine
from src.infrastructure.logging.error_handler import get_error_statistics
from src.infrastructure.logging.logger_config import get_performance_metrics


class HealthStatus(Enum):
    """Health check status levels"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    CRITICAL = "critical"


@dataclass
class HealthCheckResult:
    """Result of a health check"""
    service: str
    status: HealthStatus
    message: str
    response_time: float
    timestamp: datetime
    metadata: dict[str, Any]


class SystemHealthMonitor:
    """Comprehensive system health monitoring"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.start_time = datetime.now()
        self.health_checks = []
        self.alert_thresholds = {
            'cpu_usage': 80.0,
            'memory_usage': 85.0,
            'disk_usage': 90.0,
            'response_time': 2.0,
            'error_rate': 5.0
        }
    
    async def perform_all_health_checks(self) -> dict[str, Any]:
        """Perform all health checks and return comprehensive status"""
        start_time = time.time()
        
        health_checks = await asyncio.gather(
            self.check_database_health(),
            self._check_cache_health(),
            self._check_system_resources(),
            self._check_application_health(),
            self._check_external_services(),
            return_exceptions=True
        )
        
        total_time = time.time() - start_time
        
        # Process results
        results = {}
        overall_status = HealthStatus.HEALTHY
        
        for check in health_checks:
            if isinstance(check, Exception):
                results[f"error_{len(results)}"] = HealthCheckResult(
                    service="error",
                    status=HealthStatus.CRITICAL,
                    message=str(check),
                    response_time=0.0,
                    timestamp=datetime.now(),
                    metadata={}
                )
                overall_status = HealthStatus.CRITICAL
            else:
                results[check.service] = check
                if check.status.value in ['critical', 'unhealthy']:
                    overall_status = HealthStatus.CRITICAL
                elif check.status.value == 'degraded' and overall_status == HealthStatus.HEALTHY:
                    overall_status = HealthStatus.DEGRADED
        
        return {
            "status": overall_status.value,
            "timestamp": datetime.now().isoformat(),
            "uptime": str(datetime.now() - self.start_time),
            "total_check_time": round(total_time, 3),
            "checks": {k: self.serialize_health_check(v) for k, v in results.items()},
            "summary": self._generate_health_summary(results)
        }
    
    async def check_database_health(self) -> HealthCheckResult:
        """Check database connectivity and performance"""
        start_time = time.time()
        
        try:
            # Try to get database connection manager
            engine = get_engine()
            with engine.connect() as conn:
                # Test basic connectivity
                result = conn.execute(text("SELECT 1"))
                result.fetchone()
                
                # Test response time
                response_time = time.time() - start_time
                
                # Get connection pool info
                pool = engine.pool
                pool_status = {
                    "pool_size": pool.size(),
                    "checked_in": pool.checkedin(),
                    "checked_out": pool.checkedout(),
                    "overflow": pool.overflow(),
                }
                
                # Determine health based on response time and pool status
                if response_time > 2.0:
                    status = HealthStatus.DEGRADED
                    message = f"Database responding slowly ({response_time:.2f}s)"
                elif pool_status["checked_out"] > pool_status["pool_size"] * 0.8:
                    status = HealthStatus.DEGRADED
                    message = "Database connection pool near capacity"
                else:
                    status = HealthStatus.HEALTHY
                    message = "Database is healthy"
                
                return HealthCheckResult(
                    service="database",
                    status=status,
                    message=message,
                    response_time=response_time,
                    timestamp=datetime.now(),
                    metadata=pool_status
                )
                
        except (IOError, OSError) as e:
            return HealthCheckResult(
                service="database",
                status=HealthStatus.CRITICAL,
                message=f"Database connection failed: {str(e)}",
                response_time=time.time() - start_time,
                timestamp=datetime.now(),
                metadata={"error": str(e)}
            )
    
    async def _check_cache_health(self) -> HealthCheckResult:
        """Check cache system health"""
        start_time = time.time()
        
        try:
            cache_manager = CacheManager()
            
            # Test cache operations
            test_key = "health_check_test"
            test_value = "test_value"
            
            cache_manager.general_cache.set(test_key, test_value, ttl=60)
            retrieved_value = cache_manager.general_cache.get(test_key)
            
            if retrieved_value != test_value:
                raise RuntimeError("Cache set/get test failed")
            
            # Clean up test data
            cache_manager.general_cache.delete(test_key)
            
            # Get cache statistics
            stats = cache_manager.general_cache.get_stats()
            response_time = time.time() - start_time
            
            # Determine health based on hit rate
            hit_rate = stats.get('hit_rate', 0)
            if hit_rate < 0.5:
                status = HealthStatus.DEGRADED
                message = f"Cache hit rate low ({hit_rate:.2%})"
            else:
                status = HealthStatus.HEALTHY
                message = "Cache is healthy"
            
            return HealthCheckResult(
                service="cache",
                status=status,
                message=message,
                response_time=response_time,
                timestamp=datetime.now(),
                metadata=stats
            )
            
        except (IOError, OSError) as e:
            return HealthCheckResult(
                service="cache",
                status=HealthStatus.CRITICAL,
                message=f"Cache health check failed: {str(e)}",
                response_time=time.time() - start_time,
                timestamp=datetime.now(),
                metadata={"error": str(e)}
            )
    
    async def _check_system_resources(self) -> HealthCheckResult:
        """Check system resource usage"""
        start_time = time.time()
        
        try:
            # Get system metrics
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            system_metrics = {
                "cpu_usage": cpu_percent,
                "memory_usage": memory.percent,
                "disk_usage": disk.percent,
                "memory_available": memory.available,
                "disk_free": disk.free,
                "load_average": psutil.getloadavg() if hasattr(psutil, 'getloadavg') else None
            }
            
            # Determine health based on thresholds
            issues = []
            if cpu_percent > self.alert_thresholds['cpu_usage']:
                issues.append(f"High CPU usage: {cpu_percent:.1f}%")
            if memory.percent > self.alert_thresholds['memory_usage']:
                issues.append(f"High memory usage: {memory.percent:.1f}%")
            if disk.percent > self.alert_thresholds['disk_usage']:
                issues.append(f"High disk usage: {disk.percent:.1f}%")
            
            if issues:
                status = HealthStatus.DEGRADED if len(issues) < 3 else HealthStatus.UNHEALTHY
                message = "; ".join(issues)
            else:
                status = HealthStatus.HEALTHY
                message = "System resources are healthy"
            
            return HealthCheckResult(
                service="system",
                status=status,
                message=message,
                response_time=time.time() - start_time,
                timestamp=datetime.now(),
                metadata=system_metrics
            )
            
        except (IOError, OSError) as e:
            return HealthCheckResult(
                service="system",
                status=HealthStatus.CRITICAL,
                message=f"System resource check failed: {str(e)}",
                response_time=time.time() - start_time,
                timestamp=datetime.now(),
                metadata={"error": str(e)}
            )
    
    async def _check_application_health(self) -> HealthCheckResult:
        """Check application-level health (errors, performance)"""
        start_time = time.time()
        
        try:
            # Check error rates
            error_stats = get_error_statistics()
            total_errors = sum(error_stats.values())
            # Assuming a way to get total requests, placeholder here
            total_requests = get_performance_metrics().get("total_requests", 1)
            error_rate = (total_errors / total_requests * 100) if total_requests > 0 else 0

            # Check performance metrics
            perf_metrics = get_performance_metrics()
            avg_response_time = perf_metrics.get("average_response_time", 0)

            # Determine health
            issues = []
            if error_rate > self.alert_thresholds['error_rate']:
                issues.append(f"High error rate: {error_rate:.2f}%")
            if avg_response_time > self.alert_thresholds['response_time']:
                issues.append(f"Slow response time: {avg_response_time:.2f}s")

            if issues:
                status = HealthStatus.DEGRADED
                message = "; ".join(issues)
            else:
                status = HealthStatus.HEALTHY
                message = "Application is healthy"

            return HealthCheckResult(
                service="application",
                status=status,
                message=message,
                response_time=time.time() - start_time,
                timestamp=datetime.now(),
                metadata={
                    "error_stats": error_stats,
                    "performance_metrics": perf_metrics
                }
            )

        except (IOError, OSError) as e:
            return HealthCheckResult(
                service="application",
                status=HealthStatus.CRITICAL,
                message=f"Application health check failed: {str(e)}",
                response_time=time.time() - start_time,
                timestamp=datetime.now(),
                metadata={"error": str(e)}
            )
    
    async def _check_external_services(self) -> HealthCheckResult:
        """Check connectivity to external services"""
        start_time = time.time()
        telegram_api_url = "https://api.telegram.org"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(telegram_api_url, timeout=10)
                response.raise_for_status()

            return HealthCheckResult(
                service="external_services",
                status=HealthStatus.HEALTHY,
                message="Telegram API is reachable",
                response_time=time.time() - start_time,
                timestamp=datetime.now(),
                metadata={"telegram_api_status": "ok"}
            )
        except httpx.RequestError as e:
            return HealthCheckResult(
                service="external_services",
                status=HealthStatus.UNHEALTHY,
                message=f"Telegram API unreachable: {e}",
                response_time=time.time() - start_time,
                timestamp=datetime.now(),
                metadata={"telegram_api_status": "unreachable"}
            )
            
    def serialize_health_check(self, result: HealthCheckResult) -> dict[str, Any]:
        """Serialize HealthCheckResult to a dictionary"""
        return {
            "service": result.service,
            "status": result.status.value,
            "message": result.message,
            "response_time": round(result.response_time, 3),
            "timestamp": result.timestamp.isoformat(),
            "metadata": result.metadata
        }

    def _generate_health_summary(self, results: dict[str, HealthCheckResult]) -> dict[str, Any]:
        """Generate a summary of all health checks"""
        summary = {
            "healthy_services": [],
            "degraded_services": [],
            "unhealthy_services": [],
            "critical_services": [],
        }
        
        for result in results.values():
            if result.status == HealthStatus.HEALTHY:
                summary["healthy_services"].append(result.service)
            elif result.status == HealthStatus.DEGRADED:
                summary["degraded_services"].append(result.service)
            elif result.status == HealthStatus.UNHEALTHY:
                summary["unhealthy_services"].append(result.service)
            else:
                summary["critical_services"].append(result.service)
                
        return summary


# Global health monitor instance
health_monitor = SystemHealthMonitor()


async def get_health_status() -> dict[str, Any]:
    """Get overall health status of the application"""
    monitor = SystemHealthMonitor()
    return await monitor.perform_all_health_checks()


async def get_liveness_check() -> dict[str, Any]:
    """Basic check to see if the application is running"""
    return {
        "status": "alive",
        "timestamp": datetime.now().isoformat(),
    }


async def get_readiness_check() -> dict[str, Any]:
    """Check if the application is ready to handle requests"""
    try:
        # Check database connection
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))

        # Check other critical services if needed
        return {
            "status": "ready",
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logging.getLogger(__name__).error(
            "Readiness check failed: %s", e, exc_info=True
        )
        return {
            "status": "not_ready",
            "timestamp": datetime.now().isoformat(),
            "error": str(e),
        } 