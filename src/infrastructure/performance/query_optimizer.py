"""
Database Query Optimizer

Advanced database query optimization with intelligent analysis and performance improvements.
"""

import logging
import time
import hashlib
import re
from collections import defaultdict
from dataclasses import dataclass
from typing import Any
from datetime import datetime, timedelta
import threading

logger = logging.getLogger(__name__)


@dataclass
class QueryMetrics:
    """Query performance metrics"""
    query_hash: str
    execution_time: float
    rows_examined: int
    rows_returned: int
    timestamp: datetime
    query_text: str = ""


@dataclass
class QueryOptimization:
    """Query optimization suggestion"""
    query_hash: str
    optimization_type: str
    description: str
    estimated_improvement: str
    priority: str  # 'high', 'medium', 'low'
    sql_suggestion: str = ""


class QueryOptimizer:
    """
    Intelligent database query optimizer

    Features:
    - Query performance analysis
    - Automatic optimization suggestions
    - Query caching recommendations
    - Index recommendations
    - Slow query detection
    """

    def __init__(self, slow_query_threshold: float = 1.0):
        self.slow_query_threshold = slow_query_threshold
        self.query_metrics: dict[str, list[QueryMetrics]] = defaultdict(list)
        self.optimization_cache: dict[str, list[QueryOptimization]] = {}
        self.query_patterns: dict[str, int] = defaultdict(int)

    def analyze_query(
        self,
        query: str,
        execution_time: float,
        rows_examined: int = 0,
        rows_returned: int = 0,
    ) -> str:
        """Analyze query performance and return optimization suggestions"""
        query_hash = self._hash_query(query)

        # Record metrics
        metrics = QueryMetrics(
            query_hash=query_hash,
            execution_time=execution_time,
            rows_examined=rows_examined,
            rows_returned=rows_returned,
            timestamp=datetime.now(),
            query_text=query
        )

        self.query_metrics[query_hash].append(metrics)
        self._update_query_patterns(query)

        # Generate optimizations if needed
        if execution_time > self.slow_query_threshold:
            optimizations = self._generate_optimizations(query, metrics)
            self.optimization_cache[query_hash] = optimizations

            return self._format_optimization_report(query, metrics, optimizations)

        return f"Query performed well ({execution_time:.3f}s)"

    def _hash_query(self, query: str) -> str:
        """Generate hash for query normalization"""
        # Normalize query by removing parameters and formatting
        normalized = self._normalize_query(query)
        return hashlib.md5(normalized.encode()).hexdigest()

    def _normalize_query(self, query: str) -> str:
        """Normalize query for pattern matching"""

        # Convert to lowercase
        normalized = query.lower().strip()

        # Replace parameter placeholders
        normalized = re.sub(r'\$\d+', '?', normalized)  # PostgreSQL parameters
        normalized = re.sub(r'%\([^)]+\)s', '?', normalized)  # Python string formatting
        normalized = re.sub(r"'[^']*'", "'?'", normalized)  # String literals
        normalized = re.sub(r'\b\d+\b', '?', normalized)  # Numeric literals

        # Remove extra whitespace
        normalized = re.sub(r'\s+', ' ', normalized)

        return normalized

    def _update_query_patterns(self, query: str):
        """Update query pattern statistics"""
        # Extract query type
        query_type = self._extract_query_type(query)
        self.query_patterns[query_type] += 1

        # Extract table names
        tables = self._extract_table_names(query)
        for table in tables:
            self.query_patterns[f"table:{table}"] += 1

    def _extract_query_type(self, query: str) -> str:
        """Extract the type of SQL query"""
        query_lower = query.lower().strip()
        query_type = "OTHER"

        if query_lower.startswith('select'):
            query_type = 'SELECT'
        elif query_lower.startswith('insert'):
            query_type = 'INSERT'
        elif query_lower.startswith('update'):
            query_type = 'UPDATE'
        elif query_lower.startswith('delete'):
            query_type = 'DELETE'
        elif query_lower.startswith('create'):
            query_type = 'CREATE'
        elif query_lower.startswith('alter'):
            query_type = 'ALTER'
        elif query_lower.startswith('drop'):
            query_type = 'DROP'

        return query_type

    def _extract_table_names(self, query: str) -> list[str]:
        """Extract table names from query"""

        tables = []
        query_lower = query.lower()

        # Find tables after FROM
        from_matches = re.findall(r'from\s+(\w+)', query_lower)
        tables.extend(from_matches)

        # Find tables after JOIN
        join_matches = re.findall(r'join\s+(\w+)', query_lower)
        tables.extend(join_matches)

        # Find tables after INSERT INTO
        insert_matches = re.findall(r'insert\s+into\s+(\w+)', query_lower)
        tables.extend(insert_matches)

        # Find tables after UPDATE
        update_matches = re.findall(r'update\s+(\w+)', query_lower)
        tables.extend(update_matches)

        return list(set(tables))  # Remove duplicates

    def _generate_optimizations(self, query: str, metrics: QueryMetrics) -> list[QueryOptimization]:
        """Generate optimization suggestions for slow query"""
        optimizations = []
        query_lower = query.lower()

        # Check for missing WHERE clause
        if 'select' in query_lower and 'where' not in query_lower:
            optimizations.append(QueryOptimization(
                query_hash=metrics.query_hash,
                optimization_type='missing_where',
                description='Query lacks WHERE clause, potentially scanning entire table',
                estimated_improvement='50-90% performance improvement',
                priority='high',
                sql_suggestion='Add WHERE clause to filter results'
            ))

        # Check for SELECT *
        if 'select *' in query_lower:
            optimizations.append(QueryOptimization(
                query_hash=metrics.query_hash,
                optimization_type='select_star',
                description='Using SELECT * retrieves unnecessary columns',
                estimated_improvement='10-30% performance improvement',
                priority='medium',
                sql_suggestion='Select only required columns: SELECT col1, col2 FROM table'
            ))

        # Check for high row examination ratio
        if metrics.rows_examined > 0 and metrics.rows_returned > 0:
            examination_ratio = metrics.rows_examined / metrics.rows_returned
            if examination_ratio > 10:
                optimizations.append(QueryOptimization(
                    query_hash=metrics.query_hash,
                    optimization_type='high_examination_ratio',
                    description=f'Query examines {examination_ratio:.1f}x more rows than returned',
                    estimated_improvement='30-70% performance improvement',
                    priority='high',
                    sql_suggestion='Add indexes on WHERE clause columns'
                ))

        # Check for ORDER BY without LIMIT
        if 'order by' in query_lower and 'limit' not in query_lower:
            optimizations.append(QueryOptimization(
                query_hash=metrics.query_hash,
                optimization_type='order_without_limit',
                description='ORDER BY without LIMIT sorts entire result set',
                estimated_improvement='20-50% performance improvement',
                priority='medium',
                sql_suggestion='Add LIMIT clause if not all results are needed'
            ))

        # Check for LIKE with leading wildcard
        if re.search(r"like\s+['\"]%", query_lower):
            optimizations.append(QueryOptimization(
                query_hash=metrics.query_hash,
                optimization_type='leading_wildcard',
                description='LIKE with leading wildcard prevents index usage',
                estimated_improvement='40-80% performance improvement',
                priority='high',
                sql_suggestion='Use full-text search or reorganize LIKE pattern'
            ))

        # Check for N+1 query pattern
        if self._detect_n_plus_one_pattern(metrics.query_hash):
            optimizations.append(QueryOptimization(
                query_hash=metrics.query_hash,
                optimization_type='n_plus_one',
                description='Possible N+1 query pattern detected',
                estimated_improvement='60-90% performance improvement',
                priority='high',
                sql_suggestion='Use JOIN or batch queries instead '
                               'of multiple single queries'
            ))

        return optimizations

    def _detect_n_plus_one_pattern(self, query_hash: str) -> bool:
        """Detect N+1 query patterns"""
        recent_metrics = self.query_metrics[query_hash][-10:]  # Last 10 executions

        if len(recent_metrics) >= 5:
            # Check if query is executed frequently in short time spans
            time_spans = []
            for i in range(1, len(recent_metrics)):
                time_diff = (recent_metrics[i].timestamp -
                             recent_metrics[i-1].timestamp).total_seconds()
                time_spans.append(time_diff)

            # If average time between executions is very short
            if time_spans and sum(time_spans) / len(time_spans) < 0.1:
                return True

        return False

    def _format_optimization_report(
        self,
        query: str,
        metrics: QueryMetrics,
        optimizations: list[QueryOptimization]
    ) -> str:
        """Format optimization report"""
        report = (
            f"Slow Query Detected:\n"
            f"  Query: {query}\n"
            f"  Execution Time: {metrics.execution_time:.3f}s\n"
            f"  Rows Examined: {metrics.rows_examined}\n"
            f"  Rows Returned: {metrics.rows_returned}\n"
            f"  Timestamp: {metrics.timestamp}\n"
            f"Optimizations:\n"
        )
        for opt in optimizations:
            report += (
                f"  - [{opt.priority.upper()}] {opt.description}\n"
                f"    Suggestion: {opt.sql_suggestion}\n"
            )
        return report

    def get_query_statistics(self, hours: int = 24) -> dict[str, Any]:
        """Get query performance statistics"""
        stats: dict[str, Any] = {
            'total_queries': 0,
            'slow_queries': 0,
            'average_execution_time': 0,
            'total_execution_time': 0,
            'top_slow_queries': [],
            'top_frequent_queries': []
        }
        all_metrics = []
        cutoff = datetime.now() - timedelta(hours=hours)

        for metrics_list in self.query_metrics.values():
            for metrics in metrics_list:
                if metrics.timestamp >= cutoff:
                    all_metrics.append(metrics)
                    stats['total_queries'] += 1
                    stats['total_execution_time'] += metrics.execution_time
                    if metrics.execution_time > self.slow_query_threshold:
                        stats['slow_queries'] += 1

        if stats['total_queries'] > 0:
            stats['average_execution_time'] = stats['total_execution_time'] / \
                stats['total_queries']

        # Sort queries by execution time
        sorted_by_time = sorted(
            all_metrics, key=lambda m: m.execution_time, reverse=True)
        stats['top_slow_queries'] = [
            (m.query_text, m.execution_time) for m in sorted_by_time[:5]]

        # Get most frequent queries
        frequent_queries = sorted(
            self.query_metrics.items(), key=lambda item: len(item[1]), reverse=True)
        stats['top_frequent_queries'] = [
            (item[1][0].query_text, len(item[1])) for item in frequent_queries[:5]]

        return stats

    def _get_top_patterns(self, limit: int = 10) -> list[tuple[str, int]]:
        """Get top query patterns"""
        return sorted(self.query_patterns.items(), key=lambda item: item[1], reverse=True)[:limit]

    def get_optimization_recommendations(self) -> list[QueryOptimization]:
        """Get all generated optimization recommendations"""
        recommendations = []
        for opt_list in self.optimization_cache.values():
            recommendations.extend(opt_list)
        return recommendations

    def suggest_indexes(self) -> list[str]:
        """Suggest potential indexes based on query analysis"""
        suggestions = []

        # Analyze WHERE clauses for index candidates
        where_columns = defaultdict(int)
        for metrics_list in self.query_metrics.values():
            for metrics in metrics_list:
                cols = self._extract_where_columns(metrics.query_text)
                for table, columns in cols.items():
                    for column in columns:
                        where_columns[f"{table}.{column}"] += 1

        # Suggest indexes for frequently filtered columns
        for col, count in where_columns.items():
            if count > 10:  # Arbitrary threshold
                suggestions.append(f"Consider index on {col} (used in WHERE {count} times)")

        return suggestions

    def _extract_where_columns(self, query: str) -> dict[str, list[str]]:
        """Extract table and column names from WHERE clause"""
        # This is a simplified implementation
        # A full SQL parser would be more robust
        columns = defaultdict(list)

        # Find table name
        table_match = re.search(r'from\s+(\w+)', query, re.IGNORECASE)
        if not table_match:
            return columns

        table = table_match.group(1)

        # Find WHERE clause
        where_match = re.search(r'where\s+(.*)', query, re.IGNORECASE)
        if not where_match:
            return columns

        where_clause = where_match.group(1)

        # Find column names in WHERE clause
        # This regex looks for patterns like `column = value` or `column > value`
        col_matches = re.findall(r'(\w+)\s*[=<>!]', where_clause)

        for col in col_matches:
            columns[table].append(col)

        return columns

    def clear_old_metrics(self, days: int = 7):
        """Clear old query metrics to save memory"""
        cutoff_date = datetime.now() - timedelta(days=days)
        for query_hash in list(self.query_metrics.keys()):
            self.query_metrics[query_hash] = [
                m for m in self.query_metrics[query_hash]
                if m.timestamp >= cutoff_date
            ]
            if not self.query_metrics[query_hash]:
                del self.query_metrics[query_hash]


class QueryAnalyzer:
    """Context manager for analyzing query performance"""

    def __init__(self, optimizer: QueryOptimizer, query: str):
        self.optimizer = optimizer
        self.query = query
        self.start_time = 0.0

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        end_time = time.time()
        execution_time = end_time - self.start_time
        report = self.optimizer.analyze_query(self.query, execution_time)
        logger.info(report)


_optimizer_instance: QueryOptimizer | None = None
_optimizer_lock = threading.Lock()


def get_query_optimizer() -> QueryOptimizer:
    """Get the global QueryOptimizer instance."""
    if _optimizer_instance is None:
        with _optimizer_lock:
            # Check again inside the lock to ensure thread safety
            if _optimizer_instance is None:
                _optimizer_instance = QueryOptimizer()
    return _optimizer_instance
