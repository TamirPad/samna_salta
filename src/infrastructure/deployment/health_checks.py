"""
Health Check System for Deployment Monitoring

Provides comprehensive health checks for database, cache, external services,
and overall system health monitoring.
"""

import asyncio
import logging
import psutil
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

from ..database.database_optimizations import DatabaseConnectionManager
from ..cache.cache_manager import CacheManager
from ..security.rate_limiter import RateLimiter
from ..logging.logger_config import get_performance_metrics
from ..logging.error_handler import get_error_statistics


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
    metadata: Dict[str, Any]


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
    
    async def perform_all_health_checks(self) -> Dict[str, Any]:
        """Perform all health checks and return comprehensive status"""
        start_time = time.time()
        
        health_checks = await asyncio.gather(
            self._check_database_health(),
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
            "checks": {k: self._serialize_health_check(v) for k, v in results.items()},
            "summary": self._generate_health_summary(results)
        }
    
    async def _check_database_health(self) -> HealthCheckResult:
        """Check database connectivity and performance"""
        start_time = time.time()
        
        try:
            # Try to get database connection manager
            from ..database.operations import get_engine
            from sqlalchemy import text
            
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
                    "invalid": pool.invalid()
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
                
        except Exception as e:
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
            
            cache_manager.set(test_key, test_value, ttl=60)
            retrieved_value = cache_manager.get(test_key)
            
            if retrieved_value != test_value:
                raise Exception("Cache set/get test failed")
            
            # Clean up test data
            cache_manager.delete(test_key)
            
            # Get cache statistics
            stats = cache_manager.get_statistics()
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
            
        except Exception as e:
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
            
        except Exception as e:
            return HealthCheckResult(
                service="system",
                status=HealthStatus.CRITICAL,
                message=f"System health check failed: {str(e)}",
                response_time=time.time() - start_time,
                timestamp=datetime.now(),
                metadata={"error": str(e)}
            )
    
    async def _check_application_health(self) -> HealthCheckResult:
        """Check application-specific health metrics"""
        start_time = time.time()
        
        try:
            # Get performance metrics
            perf_metrics = get_performance_metrics()
            error_stats = get_error_statistics()
            
            # Calculate error rate
            total_requests = perf_metrics.get('total_requests', 0)
            error_requests = error_stats.get('total_errors', 0)
            error_rate = (error_requests / max(1, total_requests)) * 100
            
            app_metrics = {
                "total_requests": total_requests,
                "error_rate": error_rate,
                "avg_response_time": perf_metrics.get('avg_response_time', 0),
                "slow_requests": perf_metrics.get('slow_requests', 0),
                "recent_errors": error_stats.get('recent_error_count', 0)
            }
            
            # Determine health
            issues = []
            if error_rate > self.alert_thresholds['error_rate']:
                issues.append(f"High error rate: {error_rate:.1f}%")
            if perf_metrics.get('avg_response_time', 0) > self.alert_thresholds['response_time']:
                issues.append(f"Slow response time: {perf_metrics.get('avg_response_time', 0):.2f}s")
            
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
                metadata=app_metrics
            )
            
        except Exception as e:
            return HealthCheckResult(
                service="application",
                status=HealthStatus.CRITICAL,
                message=f"Application health check failed: {str(e)}",
                response_time=time.time() - start_time,
                timestamp=datetime.now(),
                metadata={"error": str(e)}
            )
    
    async def _check_external_services(self) -> HealthCheckResult:
        """Check external service dependencies"""
        start_time = time.time()
        
        try:
            # Check Telegram API connectivity
            import httpx
            
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get("https://api.telegram.org/bot123:test/getMe")
                # We expect this to fail with 401, but it means the API is reachable
                
            external_status = {
                "telegram_api": "reachable",
                "response_time": time.time() - start_time
            }
            
            return HealthCheckResult(
                service="external",
                status=HealthStatus.HEALTHY,
                message="External services are reachable",
                response_time=time.time() - start_time,
                timestamp=datetime.now(),
                metadata=external_status
            )
            
        except Exception as e:
            return HealthCheckResult(
                service="external",
                status=HealthStatus.DEGRADED,
                message=f"External service check failed: {str(e)}",
                response_time=time.time() - start_time,
                timestamp=datetime.now(),
                metadata={"error": str(e)}
            )
    
    def _serialize_health_check(self, result: HealthCheckResult) -> Dict[str, Any]:
        """Serialize health check result for JSON output"""
        return {
            "status": result.status.value,
            "message": result.message,
            "response_time": round(result.response_time, 3),
            "timestamp": result.timestamp.isoformat(),
            "metadata": result.metadata
        }
    
    def _generate_health_summary(self, results: Dict[str, HealthCheckResult]) -> Dict[str, Any]:
        """Generate a summary of health check results"""
        status_counts = {}
        total_response_time = 0
        
        for result in results.values():
            status = result.status.value
            status_counts[status] = status_counts.get(status, 0) + 1
            total_response_time += result.response_time
        
        return {
            "total_checks": len(results),
            "status_distribution": status_counts,
            "average_response_time": round(total_response_time / max(1, len(results)), 3),
            "critical_issues": status_counts.get("critical", 0),
            "degraded_services": status_counts.get("degraded", 0)
        }


# Global health monitor instance
health_monitor = SystemHealthMonitor()


async def get_health_status() -> Dict[str, Any]:
    """Get current system health status"""
    return await health_monitor.perform_all_health_checks()


async def get_liveness_check() -> Dict[str, Any]:
    """Simple liveness check for basic health"""
    return {
        "status": "alive",
        "timestamp": datetime.now().isoformat(),
        "uptime": str(datetime.now() - health_monitor.start_time)
    }


async def get_readiness_check() -> Dict[str, Any]:
    """Readiness check for deployment readiness"""
    # Check critical services only
    db_check = await health_monitor._check_database_health()
    cache_check = await health_monitor._check_cache_health()
    
    if db_check.status == HealthStatus.CRITICAL or cache_check.status == HealthStatus.CRITICAL:
        return {
            "status": "not_ready",
            "timestamp": datetime.now().isoformat(),
            "issues": [
                f"Database: {db_check.message}" if db_check.status == HealthStatus.CRITICAL else None,
                f"Cache: {cache_check.message}" if cache_check.status == HealthStatus.CRITICAL else None
            ]
        }
    
    return {
        "status": "ready",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "database": db_check.status.value,
            "cache": cache_check.status.value
        }
    } 