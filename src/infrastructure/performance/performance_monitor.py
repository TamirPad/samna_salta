"""
Performance Monitor

Real-time performance monitoring and optimization recommendations for the Samna Salta system.
"""

import asyncio
import time
import psutil
import threading
from collections import deque, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any
import statistics
import logging

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
        self.max_history_size = max_history_size
        self.metrics_history: deque = deque(maxlen=max_history_size)
        self.current_metrics: Dict[str, PerformanceMetric] = {}
        self.thresholds: Dict[str, Dict[str, float]] = {}
        self.alerts: List[PerformanceAlert] = []
        self.monitoring_active = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.custom_collectors: List[Callable] = []
        
        # Performance counters
        self.request_count = 0
        self.error_count = 0
        self.response_times: deque = deque(maxlen=1000)
        self.db_query_times: deque = deque(maxlen=1000)
        self.cache_hit_rates: deque = deque(maxlen=100)
        
        # Set default thresholds
        self._set_default_thresholds()
    
    def _set_default_thresholds(self):
        """Set default performance thresholds"""
        self.thresholds = {
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
        if self.monitoring_active:
            logger.warning("Performance monitoring already active")
            return
        
        self.monitoring_active = True
        self.monitor_thread = threading.Thread(
            target=self._monitoring_loop,
            args=(interval,),
            daemon=True
        )
        self.monitor_thread.start()
        logger.info(f"Performance monitoring started with {interval}s interval")
    
    def stop_monitoring(self):
        """Stop performance monitoring"""
        self.monitoring_active = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5.0)
        logger.info("Performance monitoring stopped")
    
    def _monitoring_loop(self, interval: float):
        """Main monitoring loop"""
        while self.monitoring_active:
            try:
                self._collect_system_metrics()
                self._collect_application_metrics()
                self._run_custom_collectors()
                self._check_thresholds()
                self._cleanup_old_data()
                time.sleep(interval)
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(interval)
    
    def _collect_system_metrics(self):
        """Collect system resource metrics"""
        timestamp = datetime.now()
        
        # CPU Usage
        cpu_percent = psutil.cpu_percent(interval=None)
        self._record_metric("cpu_usage", cpu_percent, timestamp, "%", "system")
        
        # Memory Usage
        memory = psutil.virtual_memory()
        self._record_metric("memory_usage", memory.percent, timestamp, "%", "system")
        self._record_metric("memory_available", memory.available / (1024**3), timestamp, "GB", "system")
        
        # Disk Usage
        disk = psutil.disk_usage('/')
        disk_percent = (disk.used / disk.total) * 100
        self._record_metric("disk_usage", disk_percent, timestamp, "%", "system")
        
        # Network I/O
        network = psutil.net_io_counters()
        self._record_metric("network_bytes_sent", network.bytes_sent, timestamp, "bytes", "system")
        self._record_metric("network_bytes_recv", network.bytes_recv, timestamp, "bytes", "system")
        
        # Process-specific metrics
        process = psutil.Process()
        self._record_metric("process_cpu", process.cpu_percent(), timestamp, "%", "process")
        self._record_metric("process_memory", process.memory_info().rss / (1024**2), timestamp, "MB", "process")
        self._record_metric("process_threads", process.num_threads(), timestamp, "count", "process")
    
    def _collect_application_metrics(self):
        """Collect application-specific metrics"""
        timestamp = datetime.now()
        
        # Request metrics
        self._record_metric("total_requests", self.request_count, timestamp, "count", "application")
        self._record_metric("total_errors", self.error_count, timestamp, "count", "application")
        
        # Error rate
        if self.request_count > 0:
            error_rate = (self.error_count / self.request_count) * 100
            self._record_metric("error_rate", error_rate, timestamp, "%", "application")
        
        # Response time metrics
        if self.response_times:
            avg_response_time = statistics.mean(self.response_times)
            self._record_metric("avg_response_time", avg_response_time, timestamp, "seconds", "application")
            
            p95_response_time = statistics.quantiles(self.response_times, n=20)[18]  # 95th percentile
            self._record_metric("p95_response_time", p95_response_time, timestamp, "seconds", "application")
        
        # Database query metrics
        if self.db_query_times:
            avg_query_time = statistics.mean(self.db_query_times)
            self._record_metric("avg_db_query_time", avg_query_time, timestamp, "seconds", "database")
        
        # Cache metrics
        if self.cache_hit_rates:
            avg_cache_hit_rate = statistics.mean(self.cache_hit_rates)
            self._record_metric("cache_hit_rate", avg_cache_hit_rate, timestamp, "%", "cache")
    
    def _run_custom_collectors(self):
        """Run custom metric collectors"""
        for collector in self.custom_collectors:
            try:
                collector(self)
            except Exception as e:
                logger.error(f"Error in custom collector: {e}")
    
    def _record_metric(self, name: str, value: float, timestamp: datetime, unit: str = "", category: str = "general", tags: Dict[str, str] = None):
        """Record a performance metric"""
        metric = PerformanceMetric(
            name=name,
            value=value,
            timestamp=timestamp,
            unit=unit,
            category=category,
            tags=tags or {}
        )
        
        self.current_metrics[name] = metric
        self.metrics_history.append(metric)
    
    def _check_thresholds(self):
        """Check metrics against thresholds and generate alerts"""
        for metric_name, metric in self.current_metrics.items():
            if metric_name in self.thresholds:
                thresholds = self.thresholds[metric_name]
                
                if metric.value >= thresholds.get('critical', float('inf')):
                    self._create_alert(metric_name, thresholds['critical'], metric.value, 'critical')
                elif metric.value >= thresholds.get('warning', float('inf')):
                    self._create_alert(metric_name, thresholds['warning'], metric.value, 'warning')
    
    def _create_alert(self, metric_name: str, threshold: float, current_value: float, severity: str):
        """Create a performance alert"""
        # Avoid duplicate alerts for the same metric
        recent_alerts = [
            alert for alert in self.alerts[-10:]  # Check last 10 alerts
            if alert.metric_name == metric_name and alert.severity == severity
        ]
        
        if recent_alerts:
            last_alert = recent_alerts[-1]
            if (datetime.now() - last_alert.timestamp).seconds < 300:  # 5 minutes
                return
        
        alert = PerformanceAlert(
            metric_name=metric_name,
            threshold=threshold,
            current_value=current_value,
            severity=severity,
            timestamp=datetime.now(),
            message=f"{metric_name} is {current_value:.2f}, exceeding {severity} threshold of {threshold:.2f}"
        )
        
        self.alerts.append(alert)
        logger.warning(f"Performance Alert [{severity.upper()}]: {alert.message}")
    
    def _cleanup_old_data(self):
        """Clean up old performance data"""
        # Remove alerts older than 24 hours
        cutoff_time = datetime.now() - timedelta(hours=24)
        self.alerts = [alert for alert in self.alerts if alert.timestamp > cutoff_time]
    
    def record_request(self, response_time: float, success: bool = True):
        """Record a request for performance tracking"""
        self.request_count += 1
        self.response_times.append(response_time)
        
        if not success:
            self.error_count += 1
    
    def record_db_query(self, query_time: float):
        """Record database query time"""
        self.db_query_times.append(query_time)
    
    def record_cache_hit_rate(self, hit_rate: float):
        """Record cache hit rate"""
        self.cache_hit_rates.append(hit_rate)
    
    def add_custom_collector(self, collector: Callable):
        """Add a custom metric collector function"""
        self.custom_collectors.append(collector)
    
    def set_threshold(self, metric_name: str, warning: float = None, critical: float = None):
        """Set custom thresholds for a metric"""
        if metric_name not in self.thresholds:
            self.thresholds[metric_name] = {}
        
        if warning is not None:
            self.thresholds[metric_name]['warning'] = warning
        if critical is not None:
            self.thresholds[metric_name]['critical'] = critical
    
    def get_current_metrics(self) -> Dict[str, PerformanceMetric]:
        """Get current performance metrics"""
        return self.current_metrics.copy()
    
    def get_metric_history(self, metric_name: str, hours: int = 1) -> List[PerformanceMetric]:
        """Get historical data for a specific metric"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        return [
            metric for metric in self.metrics_history
            if metric.name == metric_name and metric.timestamp > cutoff_time
        ]
    
    def get_recent_alerts(self, hours: int = 1) -> List[PerformanceAlert]:
        """Get recent performance alerts"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        return [alert for alert in self.alerts if alert.timestamp > cutoff_time]
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary"""
        current_metrics = self.get_current_metrics()
        recent_alerts = self.get_recent_alerts()
        
        # Calculate trends
        trends = self._calculate_trends()
        
        # Generate optimization recommendations
        recommendations = self._generate_recommendations()
        
        return {
            'timestamp': datetime.now(),
            'current_metrics': {name: {
                'value': metric.value,
                'unit': metric.unit,
                'category': metric.category
            } for name, metric in current_metrics.items()},
            'recent_alerts': [{
                'metric': alert.metric_name,
                'severity': alert.severity,
                'message': alert.message,
                'timestamp': alert.timestamp
            } for alert in recent_alerts],
            'trends': trends,
            'recommendations': recommendations,
            'system_health': self._calculate_system_health()
        }
    
    def _calculate_trends(self) -> Dict[str, str]:
        """Calculate performance trends"""
        trends = {}
        key_metrics = ['cpu_usage', 'memory_usage', 'avg_response_time', 'error_rate']
        
        for metric_name in key_metrics:
            history = self.get_metric_history(metric_name, hours=1)
            if len(history) >= 2:
                recent_values = [m.value for m in history[-10:]]  # Last 10 values
                older_values = [m.value for m in history[-20:-10]] if len(history) >= 20 else history[:10]
                
                if recent_values and older_values:
                    recent_avg = statistics.mean(recent_values)
                    older_avg = statistics.mean(older_values)
                    
                    if recent_avg > older_avg * 1.1:
                        trends[metric_name] = 'increasing'
                    elif recent_avg < older_avg * 0.9:
                        trends[metric_name] = 'decreasing'
                    else:
                        trends[metric_name] = 'stable'
        
        return trends
    
    def _generate_recommendations(self) -> List[OptimizationRecommendation]:
        """Generate optimization recommendations based on current metrics"""
        recommendations = []
        current_metrics = self.get_current_metrics()
        
        # High CPU usage recommendation
        if 'cpu_usage' in current_metrics and current_metrics['cpu_usage'].value > 80:
            recommendations.append(OptimizationRecommendation(
                category='cpu',
                priority='high',
                description='High CPU usage detected. Consider optimizing database queries and implementing async operations.',
                estimated_impact='20-40% CPU reduction',
                implementation_complexity='medium',
                code_examples=[
                    'Use async/await for I/O operations',
                    'Implement database query optimization',
                    'Add connection pooling'
                ]
            ))
        
        # High memory usage recommendation
        if 'memory_usage' in current_metrics and current_metrics['memory_usage'].value > 85:
            recommendations.append(OptimizationRecommendation(
                category='memory',
                priority='high',
                description='High memory usage detected. Implement caching optimization and memory leak detection.',
                estimated_impact='15-30% memory reduction',
                implementation_complexity='medium',
                code_examples=[
                    'Implement LRU cache with size limits',
                    'Use memory profiling tools',
                    'Optimize object lifecycle management'
                ]
            ))
        
        # Slow response time recommendation
        if 'avg_response_time' in current_metrics and current_metrics['avg_response_time'].value > 1.0:
            recommendations.append(OptimizationRecommendation(
                category='response_time',
                priority='high',
                description='Slow response times detected. Optimize database queries and implement caching.',
                estimated_impact='50-70% response time improvement',
                implementation_complexity='high',
                code_examples=[
                    'Add database indexes',
                    'Implement Redis caching',
                    'Use database query optimization',
                    'Add pagination for large datasets'
                ]
            ))
        
        # Low cache hit rate recommendation
        if 'cache_hit_rate' in current_metrics and current_metrics['cache_hit_rate'].value < 70:
            recommendations.append(OptimizationRecommendation(
                category='cache',
                priority='medium',
                description='Low cache hit rate detected. Review caching strategy and cache expiration policies.',
                estimated_impact='30-50% performance improvement',
                implementation_complexity='low',
                code_examples=[
                    'Implement intelligent cache warming',
                    'Optimize cache key strategies',
                    'Adjust cache expiration times'
                ]
            ))
        
        return recommendations
    
    def _calculate_system_health(self) -> str:
        """Calculate overall system health score"""
        current_metrics = self.get_current_metrics()
        recent_alerts = self.get_recent_alerts()
        
        # Health scoring based on key metrics
        health_score = 100
        
        # Deduct points for high resource usage
        if 'cpu_usage' in current_metrics:
            cpu_usage = current_metrics['cpu_usage'].value
            if cpu_usage > 90:
                health_score -= 30
            elif cpu_usage > 70:
                health_score -= 15
        
        if 'memory_usage' in current_metrics:
            memory_usage = current_metrics['memory_usage'].value
            if memory_usage > 95:
                health_score -= 25
            elif memory_usage > 80:
                health_score -= 10
        
        # Deduct points for slow response times
        if 'avg_response_time' in current_metrics:
            response_time = current_metrics['avg_response_time'].value
            if response_time > 3.0:
                health_score -= 20
            elif response_time > 1.0:
                health_score -= 10
        
        # Deduct points for high error rate
        if 'error_rate' in current_metrics:
            error_rate = current_metrics['error_rate'].value
            if error_rate > 10:
                health_score -= 25
            elif error_rate > 5:
                health_score -= 10
        
        # Deduct points for recent critical alerts
        critical_alerts = [alert for alert in recent_alerts if alert.severity == 'critical']
        health_score -= len(critical_alerts) * 5
        
        # Determine health status
        if health_score >= 90:
            return 'excellent'
        elif health_score >= 75:
            return 'good'
        elif health_score >= 60:
            return 'fair'
        elif health_score >= 40:
            return 'poor'
        else:
            return 'critical'
    
    def export_metrics(self, format: str = 'json') -> str:
        """Export metrics in various formats"""
        if format == 'json':
            import json
            return json.dumps(self.get_performance_summary(), default=str, indent=2)
        elif format == 'csv':
            # CSV export implementation
            import csv
            import io
            
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Write headers
            writer.writerow(['timestamp', 'metric_name', 'value', 'unit', 'category'])
            
            # Write data
            for metric in self.metrics_history:
                writer.writerow([
                    metric.timestamp,
                    metric.name,
                    metric.value,
                    metric.unit,
                    metric.category
                ])
            
            return output.getvalue()
        else:
            raise ValueError(f"Unsupported export format: {format}")


# Global performance monitor instance
_performance_monitor = None

def get_performance_monitor() -> PerformanceMonitor:
    """Get the global performance monitor instance"""
    global _performance_monitor
    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor()
    return _performance_monitor 