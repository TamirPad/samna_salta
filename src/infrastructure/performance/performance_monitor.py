"""
Performance Monitor

Real-time performance monitoring and optimization recommendations for the Samna Salta system.
"""

import json
import logging
import statistics
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional

import psutil

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetric:
    """Individual performance metric"""
    name: str
    value: float
    timestamp: datetime
    unit: str = ""
    category: str = "general"
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class PerformanceAlert:
    """Performance alert when thresholds are exceeded"""
    metric_name: str
    threshold: float
    current_value: float
    severity: str  # 'warning', 'critical'
    timestamp: datetime
    message: str


@dataclass
class OptimizationRecommendation:
    """Performance optimization recommendation"""
    category: str
    priority: str  # 'high', 'medium', 'low'
    description: str
    estimated_impact: str
    implementation_complexity: str
    code_examples: List[str] = field(default_factory=list)


@dataclass
class PerformanceCounters:
    """Dataclass for performance counters"""
    request_count: int = 0
    error_count: int = 0
    response_times: deque = field(default_factory=lambda: deque(maxlen=1000))
    db_query_times: deque = field(default_factory=lambda: deque(maxlen=1000))
    cache_hit_rates: deque = field(default_factory=lambda: deque(maxlen=100))


@dataclass
class PerformanceState:
    """Dataclass for performance state"""
    # pylint: disable=too-many-instance-attributes
    max_history_size: int = 10000
    metrics_history: deque = field(
        default_factory=lambda: deque(maxlen=10000))
    current_metrics: Dict[str, PerformanceMetric] = field(default_factory=dict)
    thresholds: Dict[str, Dict[str, float]] = field(default_factory=dict)
    alerts: List[PerformanceAlert] = field(default_factory=list)
    monitoring_active: bool = False
    monitor_thread: Optional[threading.Thread] = None
    custom_collectors: List[Callable] = field(default_factory=list)
    counters: PerformanceCounters = field(default_factory=PerformanceCounters)


@dataclass
class RecordMetric:
    """Dataclass for record metric"""
    name: str
    value: float
    timestamp: datetime
    unit: str = ""
    category: str = "general"
    tags: Optional[Dict[str, str]] = None


class PerformanceMonitor:
    """
    Comprehensive performance monitoring system

    Features:
    - Real-time metric collection
    - Performance alerting
    - Optimization recommendations
    - Historical performance tracking
    - Resource usage monitoring
    """

    def __init__(self, max_history_size: int = 10000):
        self.state = PerformanceState(max_history_size=max_history_size)
        self._set_default_thresholds()

    def _set_default_thresholds(self):
        """Set default performance thresholds"""
        self.state.thresholds = {
            'cpu_usage': {'warning': 70.0, 'critical': 90.0},
            'memory_usage': {'warning': 80.0, 'critical': 95.0},
            'disk_usage': {'warning': 85.0, 'critical': 95.0},
            'response_time': {'warning': 1.0, 'critical': 3.0},
            'error_rate': {'warning': 5.0, 'critical': 10.0},
            'db_query_time': {'warning': 0.5, 'critical': 2.0},
            'cache_hit_rate': {'warning': 70.0, 'critical': 50.0}
        }

    def start_monitoring(self, interval: float = 5.0):
        """Start real-time performance monitoring"""
        if self.state.monitoring_active:
            logger.warning("Performance monitoring already active")
            return

        self.state.monitoring_active = True
        self.state.monitor_thread = threading.Thread(
            target=self._monitoring_loop,
            args=(interval,),
            daemon=True
        )
        self.state.monitor_thread.start()
        logger.info("Performance monitoring started with %s interval", interval)

    def stop_monitoring(self):
        """Stop performance monitoring"""
        self.state.monitoring_active = False
        if self.state.monitor_thread:
            self.state.monitor_thread.join(timeout=5.0)
        logger.info("Performance monitoring stopped")

    def _monitoring_loop(self, interval: float):
        """Main monitoring loop"""
        while self.state.monitoring_active:
            try:
                self._collect_system_metrics()
                self._collect_application_metrics()
                self._run_custom_collectors()
                self._check_thresholds()
                self._cleanup_old_data()
                time.sleep(interval)
            except (IOError, OSError) as e:
                logger.error("Error in monitoring loop: %s", e)
                time.sleep(interval)

    def _collect_system_metrics(self):
        """Collect system resource metrics"""
        timestamp = datetime.now()

        # CPU Usage
        cpu_percent = psutil.cpu_percent(interval=None)
        self._record_metric(RecordMetric(
            name="cpu_usage",
            value=cpu_percent,
            timestamp=timestamp,
            unit="%",
            category="system"
        ))

        # Memory Usage
        memory = psutil.virtual_memory()
        self._record_metric(RecordMetric(
            name="memory_usage",
            value=memory.percent,
            timestamp=timestamp,
            unit="%",
            category="system"
        ))
        self._record_metric(RecordMetric(
            name="memory_available",
            value=memory.available / (1024**3),
            timestamp=timestamp,
            unit="GB",
            category="system"
        ))

        # Disk Usage
        disk = psutil.disk_usage('/')
        disk_percent = (disk.used / disk.total) * 100
        self._record_metric(RecordMetric(
            name="disk_usage",
            value=disk_percent,
            timestamp=timestamp,
            unit="%",
            category="system"
        ))

        # Network I/O
        network = psutil.net_io_counters()
        self._record_metric(RecordMetric(
            name="network_bytes_sent",
            value=network.bytes_sent,
            timestamp=timestamp,
            unit="bytes",
            category="system"
        ))
        self._record_metric(RecordMetric(
            name="network_bytes_recv",
            value=network.bytes_recv,
            timestamp=timestamp,
            unit="bytes",
            category="system"
        ))

        # Process-specific metrics
        process = psutil.Process()
        self._record_metric(RecordMetric(
            name="process_cpu",
            value=process.cpu_percent(),
            timestamp=timestamp,
            unit="%",
            category="process"
        ))
        self._record_metric(RecordMetric(
            name="process_memory",
            value=process.memory_info().rss / (1024**2),
            timestamp=timestamp,
            unit="MB",
            category="process"
        ))
        self._record_metric(RecordMetric(
            name="process_threads",
            value=process.num_threads(),
            timestamp=timestamp,
            unit="count",
            category="process"
        ))

    def _collect_application_metrics(self):
        """Collect application-specific metrics"""
        timestamp = datetime.now()

        # Request metrics
        self._record_metric(RecordMetric(
            name="total_requests",
            value=self.state.counters.request_count,
            timestamp=timestamp,
            unit="count",
            category="application"
        ))
        self._record_metric(RecordMetric(
            name="total_errors",
            value=self.state.counters.error_count,
            timestamp=timestamp,
            unit="count",
            category="application"
        ))

        # Error rate
        if self.state.counters.request_count > 0:
            error_rate = (self.state.counters.error_count /
                          self.state.counters.request_count) * 100
            self._record_metric(RecordMetric(
                name="error_rate",
                value=error_rate,
                timestamp=timestamp,
                unit="%",
                category="application"
            ))

        # Response time metrics
        if self.state.counters.response_times:
            avg_response_time = statistics.mean(
                self.state.counters.response_times)
            self._record_metric(RecordMetric(
                name="avg_response_time",
                value=avg_response_time,
                timestamp=timestamp,
                unit="seconds",
                category="application"
            ))

            p95_response_time = statistics.quantiles(
                self.state.counters.response_times, n=20)[18]
            self._record_metric(RecordMetric(
                name="p95_response_time",
                value=p95_response_time,
                timestamp=timestamp,
                unit="seconds",
                category="application"
            ))

        # Database query metrics
        if self.state.counters.db_query_times:
            avg_query_time = statistics.mean(self.state.counters.db_query_times)
            self._record_metric(RecordMetric(
                name="avg_db_query_time",
                value=avg_query_time,
                timestamp=timestamp,
                unit="seconds",
                category="database"
            ))

        # Cache metrics
        if self.state.counters.cache_hit_rates:
            avg_cache_hit_rate = statistics.mean(
                self.state.counters.cache_hit_rates)
            self._record_metric(RecordMetric(
                name="cache_hit_rate",
                value=avg_cache_hit_rate,
                timestamp=timestamp,
                unit="%",
                category="cache"
            ))

    def _run_custom_collectors(self):
        """Run custom metric collectors"""
        for collector in self.state.custom_collectors:
            try:
                collector(self)
            except (IOError, OSError) as e:
                logger.error("Error in custom collector: %s", e)

    def _record_metric(self, metric: RecordMetric):
        """Record a performance metric"""
        metric_data = PerformanceMetric(
            name=metric.name,
            value=metric.value,
            timestamp=metric.timestamp,
            unit=metric.unit,
            category=metric.category,
            tags=metric.tags or {}
        )

        self.state.current_metrics[metric.name] = metric_data
        self.state.metrics_history.append(metric_data)

    def _check_thresholds(self):
        """Check metrics against thresholds and generate alerts"""
        for metric_name, metric in self.state.current_metrics.items():
            if metric_name in self.state.thresholds:
                thresholds = self.state.thresholds[metric_name]

                if metric.value >= thresholds.get('critical', float('inf')):
                    self._create_alert(
                        metric_name,
                        thresholds['critical'],
                        metric.value,
                        'critical'
                    )
                elif metric.value >= thresholds.get('warning', float('inf')):
                    self._create_alert(
                        metric_name,
                        thresholds['warning'],
                        metric.value,
                        'warning'
                    )

    def _create_alert(
        self,
        metric_name: str,
        threshold: float,
        current_value: float,
        severity: str
    ):
        """Create a performance alert"""
        # Avoid duplicate alerts for the same metric
        recent_alerts = [
            alert for alert in self.state.alerts[-10:]
            if alert.metric_name == metric_name and alert.severity == severity
        ]

        if recent_alerts:
            last_alert = recent_alerts[-1]
            if (datetime.now() - last_alert.timestamp).seconds < 300:
                return

        alert = PerformanceAlert(
            metric_name=metric_name,
            threshold=threshold,
            current_value=current_value,
            severity=severity,
            timestamp=datetime.now(),
            message=(
                f"{metric_name} is {current_value:.2f}, "
                f"exceeding {severity} threshold of {threshold:.2f}"
            )
        )

        self.state.alerts.append(alert)
        logger.warning("Performance alert: %s", alert.message)

    def _cleanup_old_data(self):
        """Clean up old metric and alert data"""
        # Remove alerts older than 24 hours
        cutoff_time = datetime.now() - timedelta(hours=24)
        self.state.alerts = [alert for alert in self.state.alerts if alert.timestamp > cutoff_time]

    def record_request(self, response_time: float, success: bool = True):
        """Record a request for performance tracking"""
        self.state.counters.request_count += 1
        if not success:
            self.state.counters.error_count += 1
        self.state.counters.response_times.append(response_time)

    def record_db_query(self, query_time: float):
        """Record a database query time"""
        self.state.counters.db_query_times.append(query_time)

    def record_cache_hit_rate(self, hit_rate: float):
        """Record a cache hit rate"""
        self.state.counters.cache_hit_rates.append(hit_rate)

    def add_custom_collector(self, collector: Callable):
        """Add a custom metric collector"""
        self.state.custom_collectors.append(collector)

    def set_threshold(
        self,
        metric_name: str,
        warning: Optional[float] = None,
        critical: Optional[float] = None
    ):
        """Set a performance threshold for a metric"""
        if metric_name not in self.state.thresholds:
            self.state.thresholds[metric_name] = {}
        if warning is not None:
            self.state.thresholds[metric_name]['warning'] = warning
        if critical is not None:
            self.state.thresholds[metric_name]['critical'] = critical

    def get_current_metrics(self) -> Dict[str, PerformanceMetric]:
        """Get the current values of all metrics"""
        return self.state.current_metrics

    def get_metric_history(
            self,
            metric_name: str,
            hours: int = 1) -> List[PerformanceMetric]:
        """Get the historical data for a specific metric"""
        history = []
        cutoff = datetime.now() - timedelta(hours=hours)
        for metric in self.state.metrics_history:
            if metric.name == metric_name and metric.timestamp >= cutoff:
                history.append(metric)
        return history

    def get_recent_alerts(self, hours: int = 1) -> List[PerformanceAlert]:
        """Get recent performance alerts"""
        cutoff = datetime.now() - timedelta(hours=hours)
        return [alert for alert in self.state.alerts if alert.timestamp >= cutoff]

    def get_performance_summary(self) -> Dict[str, Any]:
        """Get a summary of the current performance"""
        summary = {
            "total_requests": self.state.counters.request_count,
            "total_errors": self.state.counters.error_count,
            "error_rate": (self.state.counters.error_count /
                           self.state.counters.request_count
                           if self.state.counters.request_count > 0 else 0),
            "avg_response_time": (statistics.mean(self.state.counters.response_times)
                                  if self.state.counters.response_times else 0),
            "avg_db_query_time": (statistics.mean(self.state.counters.db_query_times)
                                  if self.state.counters.db_query_times else 0),
            "avg_cache_hit_rate": (statistics.mean(self.state.counters.cache_hit_rates)
                                   if self.state.counters.cache_hit_rates else 0),
            "current_cpu_usage": (self.state.current_metrics['cpu_usage'].value
                                  if 'cpu_usage' in self.state.current_metrics else 0),
            "current_memory_usage": (self.state.current_metrics['memory_usage'].value
                                     if 'memory_usage' in self.state.current_metrics else 0),
            "active_alerts": len(self.get_recent_alerts(1)),
            "monitoring_active": self.state.monitoring_active,
            "system_health": self._calculate_system_health()
        }
        summary.update(self._calculate_trends())
        return summary

    def _calculate_trends(self) -> Dict[str, str]:
        """Calculate performance trends"""
        trends = {}
        for metric_name in ['avg_response_time', 'error_rate', 'cpu_usage']:
            history = [
                m.value for m in self.get_metric_history(
                    metric_name, hours=1)]
            if len(history) > 10:
                first_half_avg = statistics.mean(history[:len(history)//2])
                second_half_avg = statistics.mean(history[len(history)//2:])
                if second_half_avg > first_half_avg * 1.1:
                    trends[f"{metric_name}_trend"] = "increasing"
                elif second_half_avg < first_half_avg * 0.9:
                    trends[f"{metric_name}_trend"] = "decreasing"
                else:
                    trends[f"{metric_name}_trend"] = "stable"
        return trends

    def _generate_recommendations(self) -> List[OptimizationRecommendation]:
        """Generate performance optimization recommendations"""
        recommendations = []
        summary = self.get_performance_summary()

        # High response time
        if summary['avg_response_time'] > self.state.thresholds['response_time']['warning']:
            recommendations.append(
                OptimizationRecommendation(
                    category="Response Time",
                    priority="High",
                    description="Average response time is high. "
                                "Consider optimizing critical code paths, "
                                "caching frequent queries, or using "
                                "asynchronous operations.",
                    estimated_impact="Reduces latency, improves user experience.",
                    implementation_complexity="Medium to High",
                    code_examples=[
                        "async def process_data(data): await asyncio.sleep(1)",
                        "@functools.lru_cache(maxsize=128) def get_data(id): ..."
                    ]
                )
            )

        # High error rate
        if summary['error_rate'] > self.state.thresholds['error_rate']['warning']:
            recommendations.append(
                OptimizationRecommendation(
                    category="Reliability",
                    priority="High",
                    description="Error rate is high. "
                                "Review recent code changes for bugs, "
                                "improve error handling, and add "
                                "more comprehensive tests.",
                    estimated_impact="Improves system stability and reliability.",
                    implementation_complexity="Medium",
                    code_examples=[
                        "try: ... except SpecificError as e: logger.error(...)",
                        "assert result is not None, 'Result should not be None'"
                    ]
                )
            )

        # High DB query time
        if summary['avg_db_query_time'] > self.state.thresholds['db_query_time']['warning']:
            recommendations.append(
                OptimizationRecommendation(
                    category="Database",
                    priority="High",
                    description="Average database query time is high. "
                                "Analyze slow queries (e.g., using EXPLAIN), "
                                "add indexes to frequently queried columns, "
                                "and optimize query logic.",
                    estimated_impact="Reduces database load, improves response time.",
                    implementation_complexity="Medium",
                    code_examples=[
                        "CREATE INDEX idx_user_id ON orders (user_id);",
                        "SELECT ... FROM ... WHERE ... (Use specific columns)"
                    ]
                )
            )

        # Low cache hit rate
        if summary['avg_cache_hit_rate'] < self.state.thresholds['cache_hit_rate']['warning']:
            recommendations.append(
                OptimizationRecommendation(
                    category="Caching",
                    priority="Medium",
                    description="Cache hit rate is low. "
                                "Increase cache size, adjust cache TTL, "
                                "or identify and cache frequently "
                                "accessed, non-volatile data.",
                    estimated_impact="Reduces load on data sources, "
                                   "improves performance.",
                    implementation_complexity="Medium",
                    code_examples=[
                        "cache.set('key', value, timeout=3600)",
                        "cached_data = cache.get('key') or db.get_data()"
                    ]
                )
            )

        # High CPU/Memory usage
        if (summary['current_cpu_usage'] > self.state.thresholds['cpu_usage']['warning'] or
                summary['current_memory_usage'] > self.state.thresholds['memory_usage']['warning']):
            recommendations.append(
                OptimizationRecommendation(
                    category="Resource Management",
                    priority="High",
                    description="CPU or Memory usage is high. "
                                "Profile application to identify "
                                "bottlenecks, optimize algorithms, "
                                "or consider scaling resources.",
                    estimated_impact="Improves system stability, "
                                   "reduces resource costs.",
                    implementation_complexity="High",
                    code_examples=[
                        "import cProfile; cProfile.run('my_func()')",
                        "Use generators instead of lists for large datasets"
                    ]
                )
            )

        return recommendations

    def _calculate_system_health(self) -> str:
        """Calculate a system health score"""
        score = 100
        summary = self.get_performance_summary()

        # Penalize for high response time
        if summary['avg_response_time'] > self.state.thresholds['response_time']['warning']:
            score -= 20
        if summary['avg_response_time'] > self.state.thresholds['response_time']['critical']:
            score -= 30

        # Penalize for error rate
        if summary['error_rate'] > self.state.thresholds['error_rate']['warning']:
            score -= 20
        if summary['error_rate'] > self.state.thresholds['error_rate']['critical']:
            score -= 30

        # Penalize for resource usage
        if summary['current_cpu_usage'] > self.state.thresholds['cpu_usage']['warning']:
            score -= 10
        if summary['current_memory_usage'] > self.state.thresholds['memory_usage']['warning']:
            score -= 10

        score = max(0, score)

        if score > 80:
            return "Excellent"
        if score > 60:
            return "Good"
        if score > 40:
            return "Average"
        return "Poor"

    def export_metrics(self, export_format: str = 'json') -> str:
        """Export metrics to a specified format"""
        if export_format == 'json':
            return self.export_to_json()
        if export_format == 'prometheus':
            return self.export_to_prometheus()
        raise ValueError("Unsupported export format")

    def export_to_json(self) -> str:
        """Export current metrics to JSON format"""
        return json.dumps({
            "summary": self.get_performance_summary(),
            "current_metrics": {
                k: v.__dict__ for k,
                v in self.state.current_metrics.items()},
            "recent_alerts": [a.__dict__ for a in self.get_recent_alerts(1)],
            "recommendations": [r.__dict__ for r in self._generate_recommendations()]
        }, default=str, indent=4)

    def export_to_prometheus(self) -> str:
        """Export current metrics to Prometheus format"""
        lines = []
        for metric in self.state.current_metrics.values():
            labels = ",".join(
                [f'{k}="{v}"' for k,
                 v in metric.tags.items()] + [f'category="{metric.category}"'])
            lines.append(
                f'# HELP samna_salta_{metric.name} {metric.name}\n'
                f'# TYPE samna_salta_{metric.name} gauge\n'
                f'samna_salta_{metric.name}{{{labels}}} {metric.value}'
            )
        return "\n".join(lines)
