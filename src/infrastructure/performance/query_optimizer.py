"""
Database Query Optimizer

Advanced database query optimization with intelligent analysis and performance improvements.
"""

import logging
import time
import hashlib
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta

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
        self.query_metrics: Dict[str, List[QueryMetrics]] = defaultdict(list)
        self.optimization_cache: Dict[str, List[QueryOptimization]] = {}
        self.query_patterns: Dict[str, int] = defaultdict(int)
        
    def analyze_query(self, query: str, execution_time: float, rows_examined: int = 0, rows_returned: int = 0) -> str:
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
        
        return f"Query performed well (${execution_time:.3f}s)"
    
    def _hash_query(self, query: str) -> str:
        """Generate hash for query normalization"""
        # Normalize query by removing parameters and formatting
        normalized = self._normalize_query(query)
        return hashlib.md5(normalized.encode()).hexdigest()
    
    def _normalize_query(self, query: str) -> str:
        """Normalize query for pattern matching"""
        import re
        
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
        
        if query_lower.startswith('select'):
            return 'SELECT'
        elif query_lower.startswith('insert'):
            return 'INSERT'
        elif query_lower.startswith('update'):
            return 'UPDATE'
        elif query_lower.startswith('delete'):
            return 'DELETE'
        elif query_lower.startswith('create'):
            return 'CREATE'
        elif query_lower.startswith('alter'):
            return 'ALTER'
        elif query_lower.startswith('drop'):
            return 'DROP'
        else:
            return 'OTHER'
    
    def _extract_table_names(self, query: str) -> List[str]:
        """Extract table names from query"""
        import re
        
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
    
    def _generate_optimizations(self, query: str, metrics: QueryMetrics) -> List[QueryOptimization]:
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
                sql_suggestion='Use JOIN or batch queries instead of multiple single queries'
            ))
        
        return optimizations
    
    def _detect_n_plus_one_pattern(self, query_hash: str) -> bool:
        """Detect N+1 query patterns"""
        recent_metrics = self.query_metrics[query_hash][-10:]  # Last 10 executions
        
        if len(recent_metrics) >= 5:
            # Check if query is executed frequently in short time spans
            time_spans = []
            for i in range(1, len(recent_metrics)):
                time_diff = (recent_metrics[i].timestamp - recent_metrics[i-1].timestamp).total_seconds()
                time_spans.append(time_diff)
            
            # If queries are executed very frequently (< 1 second apart)
            avg_time_span = sum(time_spans) / len(time_spans) if time_spans else 0
            return avg_time_span < 1.0
        
        return False
    
    def _format_optimization_report(self, query: str, metrics: QueryMetrics, optimizations: List[QueryOptimization]) -> str:
        """Format optimization report"""
        report = f"""
SLOW QUERY DETECTED
===================
Execution Time: {metrics.execution_time:.3f}s
Rows Examined: {metrics.rows_examined}
Rows Returned: {metrics.rows_returned}

Query:
{query[:200]}{'...' if len(query) > 200 else ''}

OPTIMIZATION SUGGESTIONS:
"""
        
        for i, opt in enumerate(optimizations, 1):
            report += f"""
{i}. {opt.optimization_type.upper()} [{opt.priority.upper()} PRIORITY]
   Description: {opt.description}
   Estimated Impact: {opt.estimated_improvement}
   Suggestion: {opt.sql_suggestion}
"""
        
        return report
    
    def get_query_statistics(self, hours: int = 24) -> Dict[str, Any]:
        """Get comprehensive query statistics"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        total_queries = 0
        slow_queries = 0
        total_time = 0
        avg_times_by_type = defaultdict(list)
        
        for query_hash, metrics_list in self.query_metrics.items():
            recent_metrics = [m for m in metrics_list if m.timestamp > cutoff_time]
            
            for metric in recent_metrics:
                total_queries += 1
                total_time += metric.execution_time
                
                if metric.execution_time > self.slow_query_threshold:
                    slow_queries += 1
                
                query_type = self._extract_query_type(metric.query_text)
                avg_times_by_type[query_type].append(metric.execution_time)
        
        # Calculate averages
        avg_query_time = total_time / total_queries if total_queries > 0 else 0
        slow_query_percentage = (slow_queries / total_queries * 100) if total_queries > 0 else 0
        
        avg_times = {}
        for query_type, times in avg_times_by_type.items():
            avg_times[query_type] = sum(times) / len(times)
        
        return {
            'total_queries': total_queries,
            'slow_queries': slow_queries,
            'slow_query_percentage': slow_query_percentage,
            'avg_query_time': avg_query_time,
            'total_query_time': total_time,
            'avg_times_by_type': avg_times,
            'most_common_patterns': self._get_top_patterns(),
            'optimization_opportunities': len(self.optimization_cache)
        }
    
    def _get_top_patterns(self, limit: int = 10) -> List[Tuple[str, int]]:
        """Get most common query patterns"""
        return sorted(self.query_patterns.items(), key=lambda x: x[1], reverse=True)[:limit]
    
    def get_optimization_recommendations(self) -> List[QueryOptimization]:
        """Get all active optimization recommendations"""
        all_optimizations = []
        for optimizations in self.optimization_cache.values():
            all_optimizations.extend(optimizations)
        
        # Sort by priority
        priority_order = {'high': 0, 'medium': 1, 'low': 2}
        return sorted(all_optimizations, key=lambda x: priority_order.get(x.priority, 3))
    
    def suggest_indexes(self) -> List[str]:
        """Suggest database indexes based on query patterns"""
        index_suggestions = []
        
        # Analyze WHERE clauses for index opportunities
        for query_hash, metrics_list in self.query_metrics.items():
            if metrics_list:
                query_text = metrics_list[0].query_text
                where_columns = self._extract_where_columns(query_text)
                
                for table, columns in where_columns.items():
                    if len(columns) == 1:
                        index_suggestions.append(f"CREATE INDEX idx_{table}_{columns[0]} ON {table}({columns[0]});")
                    elif len(columns) > 1:
                        col_list = ', '.join(columns)
                        index_suggestions.append(f"CREATE INDEX idx_{table}_composite ON {table}({col_list});")
        
        return list(set(index_suggestions))  # Remove duplicates
    
    def _extract_where_columns(self, query: str) -> Dict[str, List[str]]:
        """Extract columns used in WHERE clauses"""
        import re
        
        result = defaultdict(list)
        query_lower = query.lower()
        
        # Extract table names and their aliases
        tables = self._extract_table_names(query)
        
        # Find WHERE clauses
        where_match = re.search(r'where\s+(.*?)(?:\s+(?:group|order|limit|;)|$)', query_lower, re.DOTALL)
        if where_match:
            where_clause = where_match.group(1)
            
            # Extract column references
            column_matches = re.findall(r'(\w+)\.(\w+)\s*[=<>!]', where_clause)
            for table_alias, column in column_matches:
                if table_alias in tables:
                    result[table_alias].append(column)
            
            # Extract simple column references (without table prefix)
            simple_matches = re.findall(r'\b(\w+)\s*[=<>!]', where_clause)
            if tables and len(tables) == 1:  # Only one table, assume columns belong to it
                table = tables[0]
                for column in simple_matches:
                    if column not in ['and', 'or', 'not', 'in', 'like']:
                        result[table].append(column)
        
        return dict(result)
    
    def clear_old_metrics(self, days: int = 7):
        """Clear old query metrics to prevent memory bloat"""
        cutoff_time = datetime.now() - timedelta(days=days)
        
        for query_hash in list(self.query_metrics.keys()):
            self.query_metrics[query_hash] = [
                metric for metric in self.query_metrics[query_hash]
                if metric.timestamp > cutoff_time
            ]
            
            # Remove empty entries
            if not self.query_metrics[query_hash]:
                del self.query_metrics[query_hash]
        
        logger.info(f"Cleared query metrics older than {days} days")


# Context manager for automatic query analysis
class QueryAnalyzer:
    """Context manager for automatic query performance analysis"""
    
    def __init__(self, optimizer: QueryOptimizer, query: str):
        self.optimizer = optimizer
        self.query = query
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            execution_time = time.time() - self.start_time
            result = self.optimizer.analyze_query(self.query, execution_time)
            
            if execution_time > self.optimizer.slow_query_threshold:
                logger.warning(f"Slow query detected: {execution_time:.3f}s")
                logger.info(result)


# Global query optimizer instance
_query_optimizer = None

def get_query_optimizer() -> QueryOptimizer:
    """Get the global query optimizer instance"""
    global _query_optimizer
    if _query_optimizer is None:
        _query_optimizer = QueryOptimizer()
    return _query_optimizer 