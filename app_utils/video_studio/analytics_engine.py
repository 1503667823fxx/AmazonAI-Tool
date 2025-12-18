"""
Analytics Engine and Cost Analysis for Video Studio

This module provides comprehensive usage statistics, cost analysis, and reporting
capabilities for the video generation workflow.

Validates: Requirements 7.5
"""

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from collections import defaultdict
from pathlib import Path


class ReportPeriod(Enum):
    """Time periods for reports"""
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    CUSTOM = "custom"


class CostCategory(Enum):
    """Categories of costs"""
    API_CALLS = "api_calls"
    STORAGE = "storage"
    COMPUTE = "compute"
    BANDWIDTH = "bandwidth"
    OTHER = "other"


@dataclass
class UsageRecord:
    """Record of a single usage event"""
    timestamp: datetime
    user_id: Optional[str]
    task_id: str
    model_name: str
    operation_type: str  # "generation", "rendering", "processing"
    duration_seconds: float
    input_size_mb: float = 0.0
    output_size_mb: float = 0.0
    success: bool = True
    error_type: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UsageRecord':
        """Create from dictionary"""
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)


@dataclass
class CostRecord:
    """Record of a cost item"""
    timestamp: datetime
    category: CostCategory
    amount: float
    currency: str = "USD"
    description: str = ""
    task_id: Optional[str] = None
    model_name: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "timestamp": self.timestamp.isoformat(),
            "category": self.category.value,
            "amount": self.amount,
            "currency": self.currency,
            "description": self.description,
            "task_id": self.task_id,
            "model_name": self.model_name,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CostRecord':
        """Create from dictionary"""
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        data['category'] = CostCategory(data['category'])
        return cls(**data)


@dataclass
class ModelPricing:
    """Pricing configuration for AI models"""
    model_name: str
    cost_per_second: float = 0.0
    cost_per_request: float = 0.0
    cost_per_mb_input: float = 0.0
    cost_per_mb_output: float = 0.0
    minimum_charge: float = 0.0
    currency: str = "USD"
    
    def calculate_cost(self, duration_seconds: float, input_mb: float = 0.0, output_mb: float = 0.0) -> float:
        """Calculate cost for a usage"""
        cost = 0.0
        
        if self.cost_per_second > 0:
            cost += duration_seconds * self.cost_per_second
        
        if self.cost_per_request > 0:
            cost += self.cost_per_request
        
        if self.cost_per_mb_input > 0:
            cost += input_mb * self.cost_per_mb_input
        
        if self.cost_per_mb_output > 0:
            cost += output_mb * self.cost_per_mb_output
        
        return max(cost, self.minimum_charge)


@dataclass
class UsageStatistics:
    """Aggregated usage statistics"""
    period_start: datetime
    period_end: datetime
    total_tasks: int = 0
    successful_tasks: int = 0
    failed_tasks: int = 0
    total_duration_seconds: float = 0.0
    total_input_mb: float = 0.0
    total_output_mb: float = 0.0
    unique_users: int = 0
    tasks_by_model: Dict[str, int] = field(default_factory=dict)
    tasks_by_operation: Dict[str, int] = field(default_factory=dict)
    errors_by_type: Dict[str, int] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "total_tasks": self.total_tasks,
            "successful_tasks": self.successful_tasks,
            "failed_tasks": self.failed_tasks,
            "success_rate": self.successful_tasks / self.total_tasks if self.total_tasks > 0 else 0.0,
            "total_duration_seconds": self.total_duration_seconds,
            "average_duration_seconds": self.total_duration_seconds / self.total_tasks if self.total_tasks > 0 else 0.0,
            "total_input_mb": self.total_input_mb,
            "total_output_mb": self.total_output_mb,
            "unique_users": self.unique_users,
            "tasks_by_model": self.tasks_by_model,
            "tasks_by_operation": self.tasks_by_operation,
            "errors_by_type": self.errors_by_type
        }


@dataclass
class CostAnalysis:
    """Cost analysis results"""
    period_start: datetime
    period_end: datetime
    total_cost: float = 0.0
    currency: str = "USD"
    costs_by_category: Dict[str, float] = field(default_factory=dict)
    costs_by_model: Dict[str, float] = field(default_factory=dict)
    costs_by_user: Dict[str, float] = field(default_factory=dict)
    projected_monthly_cost: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "total_cost": round(self.total_cost, 2),
            "currency": self.currency,
            "costs_by_category": {k: round(v, 2) for k, v in self.costs_by_category.items()},
            "costs_by_model": {k: round(v, 2) for k, v in self.costs_by_model.items()},
            "costs_by_user": {k: round(v, 2) for k, v in self.costs_by_user.items()},
            "projected_monthly_cost": round(self.projected_monthly_cost, 2)
        }


class AnalyticsEngine:
    """
    Comprehensive analytics and cost analysis engine for Video Studio.
    
    Tracks usage, calculates costs, and generates detailed reports.
    """
    
    def __init__(self, storage_path: Optional[str] = None):
        """
        Initialize analytics engine.
        
        Args:
            storage_path: Path to store analytics data
        """
        self.storage_path = Path(storage_path or "./video_studio_analytics")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # In-memory storage
        self.usage_records: List[UsageRecord] = []
        self.cost_records: List[CostRecord] = []
        
        # Model pricing configuration
        self.model_pricing: Dict[str, ModelPricing] = {}
        
        # Load existing data
        self._load_data()
        self._load_pricing()
    
    def _load_data(self):
        """Load existing analytics data from disk"""
        usage_file = self.storage_path / "usage_records.json"
        cost_file = self.storage_path / "cost_records.json"
        
        try:
            if usage_file.exists():
                with open(usage_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.usage_records = [UsageRecord.from_dict(record) for record in data]
        except Exception:
            pass
        
        try:
            if cost_file.exists():
                with open(cost_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.cost_records = [CostRecord.from_dict(record) for record in data]
        except Exception:
            pass
    
    def _load_pricing(self):
        """Load model pricing configuration"""
        pricing_file = self.storage_path / "model_pricing.json"
        
        try:
            if pricing_file.exists():
                with open(pricing_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for model_name, pricing_data in data.items():
                        self.model_pricing[model_name] = ModelPricing(**pricing_data)
        except Exception:
            pass
        
        # Set default pricing if not loaded
        if not self.model_pricing:
            self._set_default_pricing()
    
    def _set_default_pricing(self):
        """Set default pricing for common models"""
        self.model_pricing = {
            "luma": ModelPricing(
                model_name="luma",
                cost_per_second=0.05,
                cost_per_request=0.10,
                minimum_charge=0.10
            ),
            "runway": ModelPricing(
                model_name="runway",
                cost_per_second=0.08,
                cost_per_request=0.15,
                minimum_charge=0.15
            ),
            "pika": ModelPricing(
                model_name="pika",
                cost_per_second=0.06,
                cost_per_request=0.12,
                minimum_charge=0.12
            ),
            "stable_video": ModelPricing(
                model_name="stable_video",
                cost_per_second=0.04,
                cost_per_request=0.08,
                minimum_charge=0.08
            )
        }
    
    def save_data(self) -> bool:
        """Save analytics data to disk"""
        try:
            # Save usage records
            usage_file = self.storage_path / "usage_records.json"
            with open(usage_file, 'w', encoding='utf-8') as f:
                data = [record.to_dict() for record in self.usage_records]
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            # Save cost records
            cost_file = self.storage_path / "cost_records.json"
            with open(cost_file, 'w', encoding='utf-8') as f:
                data = [record.to_dict() for record in self.cost_records]
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            return True
        except Exception:
            return False
    
    def save_pricing(self) -> bool:
        """Save model pricing configuration"""
        try:
            pricing_file = self.storage_path / "model_pricing.json"
            with open(pricing_file, 'w', encoding='utf-8') as f:
                data = {
                    name: asdict(pricing)
                    for name, pricing in self.model_pricing.items()
                }
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except Exception:
            return False
    
    def record_usage(self, usage: UsageRecord) -> bool:
        """Record a usage event"""
        try:
            self.usage_records.append(usage)
            
            # Calculate and record cost
            if usage.model_name in self.model_pricing:
                pricing = self.model_pricing[usage.model_name]
                cost = pricing.calculate_cost(
                    usage.duration_seconds,
                    usage.input_size_mb,
                    usage.output_size_mb
                )
                
                cost_record = CostRecord(
                    timestamp=usage.timestamp,
                    category=CostCategory.API_CALLS,
                    amount=cost,
                    currency=pricing.currency,
                    description=f"{usage.model_name} - {usage.operation_type}",
                    task_id=usage.task_id,
                    model_name=usage.model_name,
                    metadata={"duration": usage.duration_seconds}
                )
                self.cost_records.append(cost_record)
            
            return True
        except Exception:
            return False
    
    def record_cost(self, cost: CostRecord) -> bool:
        """Record a cost item"""
        try:
            self.cost_records.append(cost)
            return True
        except Exception:
            return False
    
    def set_model_pricing(self, model_name: str, pricing: ModelPricing) -> bool:
        """Set pricing for a model"""
        try:
            self.model_pricing[model_name] = pricing
            return True
        except Exception:
            return False
    
    def get_usage_statistics(self, start_date: datetime, end_date: datetime) -> UsageStatistics:
        """
        Calculate usage statistics for a time period.
        
        Args:
            start_date: Start of period
            end_date: End of period
        
        Returns:
            UsageStatistics object
        """
        # Filter records by date range
        records = [
            r for r in self.usage_records
            if start_date <= r.timestamp <= end_date
        ]
        
        stats = UsageStatistics(
            period_start=start_date,
            period_end=end_date
        )
        
        if not records:
            return stats
        
        # Calculate statistics
        stats.total_tasks = len(records)
        stats.successful_tasks = sum(1 for r in records if r.success)
        stats.failed_tasks = stats.total_tasks - stats.successful_tasks
        stats.total_duration_seconds = sum(r.duration_seconds for r in records)
        stats.total_input_mb = sum(r.input_size_mb for r in records)
        stats.total_output_mb = sum(r.output_size_mb for r in records)
        
        # Unique users
        unique_users = set(r.user_id for r in records if r.user_id)
        stats.unique_users = len(unique_users)
        
        # Tasks by model
        for record in records:
            stats.tasks_by_model[record.model_name] = stats.tasks_by_model.get(record.model_name, 0) + 1
        
        # Tasks by operation
        for record in records:
            stats.tasks_by_operation[record.operation_type] = stats.tasks_by_operation.get(record.operation_type, 0) + 1
        
        # Errors by type
        for record in records:
            if not record.success and record.error_type:
                stats.errors_by_type[record.error_type] = stats.errors_by_type.get(record.error_type, 0) + 1
        
        return stats
    
    def get_cost_analysis(self, start_date: datetime, end_date: datetime) -> CostAnalysis:
        """
        Calculate cost analysis for a time period.
        
        Args:
            start_date: Start of period
            end_date: End of period
        
        Returns:
            CostAnalysis object
        """
        # Filter records by date range
        records = [
            r for r in self.cost_records
            if start_date <= r.timestamp <= end_date
        ]
        
        analysis = CostAnalysis(
            period_start=start_date,
            period_end=end_date
        )
        
        if not records:
            return analysis
        
        # Calculate total cost
        analysis.total_cost = sum(r.amount for r in records)
        
        # Costs by category
        for record in records:
            category = record.category.value
            analysis.costs_by_category[category] = analysis.costs_by_category.get(category, 0.0) + record.amount
        
        # Costs by model
        for record in records:
            if record.model_name:
                analysis.costs_by_model[record.model_name] = analysis.costs_by_model.get(record.model_name, 0.0) + record.amount
        
        # Costs by user (from usage records)
        usage_records = [
            r for r in self.usage_records
            if start_date <= r.timestamp <= end_date and r.user_id
        ]
        
        for usage in usage_records:
            if usage.model_name in self.model_pricing:
                pricing = self.model_pricing[usage.model_name]
                cost = pricing.calculate_cost(usage.duration_seconds, usage.input_size_mb, usage.output_size_mb)
                
                user_id = usage.user_id or "unknown"
                analysis.costs_by_user[user_id] = analysis.costs_by_user.get(user_id, 0.0) + cost
        
        # Project monthly cost
        period_days = (end_date - start_date).days
        if period_days > 0:
            daily_cost = analysis.total_cost / period_days
            analysis.projected_monthly_cost = daily_cost * 30
        
        return analysis
    
    def generate_report(self, period: ReportPeriod, custom_start: Optional[datetime] = None, 
                       custom_end: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Generate a comprehensive report for a time period.
        
        Args:
            period: Report period type
            custom_start: Custom start date (for CUSTOM period)
            custom_end: Custom end date (for CUSTOM period)
        
        Returns:
            Dictionary containing report data
        """
        # Determine date range
        end_date = datetime.now()
        
        if period == ReportPeriod.HOURLY:
            start_date = end_date - timedelta(hours=1)
        elif period == ReportPeriod.DAILY:
            start_date = end_date - timedelta(days=1)
        elif period == ReportPeriod.WEEKLY:
            start_date = end_date - timedelta(weeks=1)
        elif period == ReportPeriod.MONTHLY:
            start_date = end_date - timedelta(days=30)
        elif period == ReportPeriod.CUSTOM:
            if not custom_start or not custom_end:
                raise ValueError("Custom period requires start and end dates")
            start_date = custom_start
            end_date = custom_end
        else:
            start_date = end_date - timedelta(days=1)
        
        # Get statistics and cost analysis
        usage_stats = self.get_usage_statistics(start_date, end_date)
        cost_analysis = self.get_cost_analysis(start_date, end_date)
        
        # Build report
        report = {
            "report_generated": datetime.now().isoformat(),
            "period": period.value,
            "period_start": start_date.isoformat(),
            "period_end": end_date.isoformat(),
            "usage_statistics": usage_stats.to_dict(),
            "cost_analysis": cost_analysis.to_dict(),
            "summary": {
                "total_tasks": usage_stats.total_tasks,
                "success_rate": usage_stats.successful_tasks / usage_stats.total_tasks if usage_stats.total_tasks > 0 else 0.0,
                "total_cost": cost_analysis.total_cost,
                "average_cost_per_task": cost_analysis.total_cost / usage_stats.total_tasks if usage_stats.total_tasks > 0 else 0.0,
                "most_used_model": max(usage_stats.tasks_by_model.items(), key=lambda x: x[1])[0] if usage_stats.tasks_by_model else None,
                "most_expensive_model": max(cost_analysis.costs_by_model.items(), key=lambda x: x[1])[0] if cost_analysis.costs_by_model else None
            }
        }
        
        return report
    
    def export_report(self, report: Dict[str, Any], filename: Optional[str] = None) -> bool:
        """
        Export report to JSON file.
        
        Args:
            report: Report data dictionary
            filename: Optional filename (auto-generated if None)
        
        Returns:
            True if successful
        """
        try:
            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"report_{timestamp}.json"
            
            report_path = self.storage_path / filename
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            
            return True
        except Exception:
            return False
    
    def get_top_users(self, limit: int = 10, start_date: Optional[datetime] = None, 
                     end_date: Optional[datetime] = None) -> List[Tuple[str, int, float]]:
        """
        Get top users by usage and cost.
        
        Args:
            limit: Number of top users to return
            start_date: Optional start date filter
            end_date: Optional end date filter
        
        Returns:
            List of (user_id, task_count, total_cost) tuples
        """
        # Filter records
        records = self.usage_records
        if start_date:
            records = [r for r in records if r.timestamp >= start_date]
        if end_date:
            records = [r for r in records if r.timestamp <= end_date]
        
        # Aggregate by user
        user_stats = defaultdict(lambda: {"tasks": 0, "cost": 0.0})
        
        for record in records:
            if not record.user_id:
                continue
            
            user_stats[record.user_id]["tasks"] += 1
            
            # Calculate cost
            if record.model_name in self.model_pricing:
                pricing = self.model_pricing[record.model_name]
                cost = pricing.calculate_cost(record.duration_seconds, record.input_size_mb, record.output_size_mb)
                user_stats[record.user_id]["cost"] += cost
        
        # Sort by cost and return top users
        sorted_users = sorted(
            [(user_id, stats["tasks"], stats["cost"]) for user_id, stats in user_stats.items()],
            key=lambda x: x[2],
            reverse=True
        )
        
        return sorted_users[:limit]
    
    def cleanup_old_records(self, days_to_keep: int = 90) -> int:
        """
        Clean up old records to save space.
        
        Args:
            days_to_keep: Number of days of records to keep
        
        Returns:
            Number of records removed
        """
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        
        # Remove old usage records
        original_usage_count = len(self.usage_records)
        self.usage_records = [r for r in self.usage_records if r.timestamp >= cutoff_date]
        
        # Remove old cost records
        original_cost_count = len(self.cost_records)
        self.cost_records = [r for r in self.cost_records if r.timestamp >= cutoff_date]
        
        removed_count = (original_usage_count - len(self.usage_records)) + (original_cost_count - len(self.cost_records))
        
        # Save updated data
        self.save_data()
        
        return removed_count


# Global analytics engine instance
analytics_engine = AnalyticsEngine()


def get_analytics_engine() -> AnalyticsEngine:
    """Get the global analytics engine instance"""
    return analytics_engine


def record_usage(usage: UsageRecord) -> bool:
    """Record a usage event"""
    return analytics_engine.record_usage(usage)


def generate_report(period: ReportPeriod, custom_start: Optional[datetime] = None, 
                   custom_end: Optional[datetime] = None) -> Dict[str, Any]:
    """Generate a report"""
    return analytics_engine.generate_report(period, custom_start, custom_end)


def get_cost_analysis(start_date: datetime, end_date: datetime) -> CostAnalysis:
    """Get cost analysis"""
    return analytics_engine.get_cost_analysis(start_date, end_date)
