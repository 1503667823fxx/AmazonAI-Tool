"""
Property-Based Tests for Statistical Reporting Accuracy

**Feature: video-studio-redesign, Property 14: 统计报告准确性**

Tests that the analytics engine generates accurate and detailed statistical
reports and analysis data for all usage and cost information.

**Validates: Requirements 7.5**
"""

import pytest
import shutil
from hypothesis import given, strategies as st, settings, assume, HealthCheck
from datetime import datetime, timedelta
from typing import List, Dict, Any
from pathlib import Path

from app_utils.video_studio.analytics_engine import (
    AnalyticsEngine,
    UsageRecord,
    CostRecord,
    ModelPricing,
    ReportPeriod,
    CostCategory,
    UsageStatistics,
    CostAnalysis
)


# ============================================================================
# Helper Strategies
# ============================================================================

@st.composite
def usage_record_strategy(draw):
    """Generate valid usage records"""
    timestamp = draw(st.datetimes(
        min_value=datetime(2024, 1, 1),
        max_value=datetime(2024, 12, 31)
    ))
    
    return UsageRecord(
        timestamp=timestamp,
        user_id=draw(st.one_of(st.none(), st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))))),
        task_id=draw(st.text(min_size=5, max_size=30, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')))),
        model_name=draw(st.sampled_from(["luma", "runway", "pika", "stable_video"])),
        operation_type=draw(st.sampled_from(["generation", "rendering", "processing"])),
        duration_seconds=draw(st.floats(min_value=1.0, max_value=300.0)),
        input_size_mb=draw(st.floats(min_value=0.0, max_value=100.0)),
        output_size_mb=draw(st.floats(min_value=0.0, max_value=500.0)),
        success=draw(st.booleans()),
        error_type=draw(st.one_of(st.none(), st.sampled_from(["timeout", "api_error", "validation_error"])))
    )


# ============================================================================
# Property 14.1: Report Generation Completeness
# ============================================================================

@given(
    record_count=st.integers(min_value=1, max_value=50),
    period=st.sampled_from([ReportPeriod.DAILY, ReportPeriod.WEEKLY, ReportPeriod.MONTHLY])
)
@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_property_report_generation_completeness(record_count, period):
    """
    Property: For any number of usage records and any report period,
    the generated report should contain all required sections and
    accurate aggregated data.
    
    Validates: Requirements 7.5
    """
    # Create temporary analytics engine
    test_path = f"./test_analytics_report_{datetime.now().timestamp()}"
    engine = AnalyticsEngine(storage_path=test_path)
    
    try:
        # Generate usage records within the period
        end_date = datetime.now()
        if period == ReportPeriod.DAILY:
            start_date = end_date - timedelta(days=1)
        elif period == ReportPeriod.WEEKLY:
            start_date = end_date - timedelta(weeks=1)
        else:  # MONTHLY
            start_date = end_date - timedelta(days=30)
        
        # Create records
        for i in range(record_count):
            timestamp = start_date + timedelta(seconds=(i * 60))
            usage = UsageRecord(
                timestamp=timestamp,
                user_id=f"user_{i % 5}",
                task_id=f"task_{i}",
                model_name=["luma", "runway", "pika"][i % 3],
                operation_type="generation",
                duration_seconds=float(i + 1),
                success=i % 4 != 0  # 75% success rate
            )
            engine.record_usage(usage)
        
        # Generate report
        report = engine.generate_report(period)
        
        # Property: Report must contain all required sections
        assert "report_generated" in report, "Report must have generation timestamp"
        assert "period" in report, "Report must specify period"
        assert "period_start" in report, "Report must have start date"
        assert "period_end" in report, "Report must have end date"
        assert "usage_statistics" in report, "Report must have usage statistics"
        assert "cost_analysis" in report, "Report must have cost analysis"
        assert "summary" in report, "Report must have summary"
        
        # Property: Usage statistics must be accurate
        usage_stats = report["usage_statistics"]
        assert usage_stats["total_tasks"] == record_count, \
            f"Total tasks should be {record_count}, got {usage_stats['total_tasks']}"
        
        # Property: Summary must contain key metrics
        summary = report["summary"]
        assert "total_tasks" in summary, "Summary must have total tasks"
        assert "success_rate" in summary, "Summary must have success rate"
        assert "total_cost" in summary, "Summary must have total cost"
        
    finally:
        # Cleanup
        if Path(test_path).exists():
            shutil.rmtree(test_path)


# ============================================================================
# Property 14.2: Cost Analysis Accuracy
# ============================================================================

@given(
    usage_records=st.lists(usage_record_strategy(), min_size=1, max_size=30)
)
@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_property_cost_analysis_accuracy(usage_records):
    """
    Property: For any set of usage records, the cost analysis should
    accurately calculate total costs, costs by category, and costs by model
    based on the configured pricing.
    
    Validates: Requirements 7.5
    """
    test_path = f"./test_analytics_cost_{datetime.now().timestamp()}"
    engine = AnalyticsEngine(storage_path=test_path)
    
    try:
        # Record all usage
        for usage in usage_records:
            engine.record_usage(usage)
        
        # Get date range
        timestamps = [r.timestamp for r in usage_records]
        start_date = min(timestamps)
        end_date = max(timestamps)
        
        # Get cost analysis
        analysis = engine.get_cost_analysis(start_date, end_date)
        
        # Calculate expected costs manually
        expected_total = 0.0
        expected_by_model = {}
        
        for usage in usage_records:
            if usage.model_name in engine.model_pricing:
                pricing = engine.model_pricing[usage.model_name]
                cost = pricing.calculate_cost(
                    usage.duration_seconds,
                    usage.input_size_mb,
                    usage.output_size_mb
                )
                expected_total += cost
                expected_by_model[usage.model_name] = expected_by_model.get(usage.model_name, 0.0) + cost
        
        # Property: Total cost should match expected
        assert abs(analysis.total_cost - expected_total) < 0.01, \
            f"Total cost mismatch: expected {expected_total:.2f}, got {analysis.total_cost:.2f}"
        
        # Property: Costs by model should match expected
        for model_name, expected_cost in expected_by_model.items():
            actual_cost = analysis.costs_by_model.get(model_name, 0.0)
            assert abs(actual_cost - expected_cost) < 0.01, \
                f"Cost for {model_name} mismatch: expected {expected_cost:.2f}, got {actual_cost:.2f}"
        
    finally:
        if Path(test_path).exists():
            shutil.rmtree(test_path)


# ============================================================================
# Property 14.3: Usage Statistics Aggregation Accuracy
# ============================================================================

@given(
    task_count=st.integers(min_value=5, max_value=50),
    success_rate=st.floats(min_value=0.0, max_value=1.0)
)
@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_property_usage_statistics_aggregation_accuracy(task_count, success_rate):
    """
    Property: For any number of tasks and success rate, the usage statistics
    should accurately aggregate all metrics including success rate, duration,
    data sizes, and task counts by model and operation.
    
    Validates: Requirements 7.5
    """
    test_path = f"./test_analytics_stats_{datetime.now().timestamp()}"
    engine = AnalyticsEngine(storage_path=test_path)
    
    try:
        start_date = datetime.now() - timedelta(hours=1)
        end_date = datetime.now()
        
        # Track expected values
        expected_successful = 0
        expected_failed = 0
        expected_duration = 0.0
        expected_input_mb = 0.0
        expected_output_mb = 0.0
        expected_by_model = {}
        expected_by_operation = {}
        unique_users = set()
        
        # Generate records
        for i in range(task_count):
            success = (i / task_count) < success_rate
            duration = float(i + 1)
            input_mb = float(i * 0.5)
            output_mb = float(i * 2.0)
            model = ["luma", "runway", "pika"][i % 3]
            operation = ["generation", "rendering"][i % 2]
            user_id = f"user_{i % 7}"
            
            if success:
                expected_successful += 1
            else:
                expected_failed += 1
            
            expected_duration += duration
            expected_input_mb += input_mb
            expected_output_mb += output_mb
            expected_by_model[model] = expected_by_model.get(model, 0) + 1
            expected_by_operation[operation] = expected_by_operation.get(operation, 0) + 1
            unique_users.add(user_id)
            
            usage = UsageRecord(
                timestamp=start_date + timedelta(minutes=i),
                user_id=user_id,
                task_id=f"task_{i}",
                model_name=model,
                operation_type=operation,
                duration_seconds=duration,
                input_size_mb=input_mb,
                output_size_mb=output_mb,
                success=success
            )
            engine.record_usage(usage)
        
        # Get statistics
        stats = engine.get_usage_statistics(start_date, end_date)
        
        # Property: All counts should match
        assert stats.total_tasks == task_count, \
            f"Total tasks: expected {task_count}, got {stats.total_tasks}"
        assert stats.successful_tasks == expected_successful, \
            f"Successful tasks: expected {expected_successful}, got {stats.successful_tasks}"
        assert stats.failed_tasks == expected_failed, \
            f"Failed tasks: expected {expected_failed}, got {stats.failed_tasks}"
        
        # Property: Aggregated values should match
        assert abs(stats.total_duration_seconds - expected_duration) < 0.1, \
            f"Duration: expected {expected_duration}, got {stats.total_duration_seconds}"
        assert abs(stats.total_input_mb - expected_input_mb) < 0.1, \
            f"Input MB: expected {expected_input_mb}, got {stats.total_input_mb}"
        assert abs(stats.total_output_mb - expected_output_mb) < 0.1, \
            f"Output MB: expected {expected_output_mb}, got {stats.total_output_mb}"
        
        # Property: Unique users should match
        assert stats.unique_users == len(unique_users), \
            f"Unique users: expected {len(unique_users)}, got {stats.unique_users}"
        
        # Property: Tasks by model should match
        for model, count in expected_by_model.items():
            assert stats.tasks_by_model[model] == count, \
                f"Tasks for {model}: expected {count}, got {stats.tasks_by_model[model]}"
        
        # Property: Tasks by operation should match
        for operation, count in expected_by_operation.items():
            assert stats.tasks_by_operation[operation] == count, \
                f"Tasks for {operation}: expected {count}, got {stats.tasks_by_operation[operation]}"
        
    finally:
        if Path(test_path).exists():
            shutil.rmtree(test_path)


# ============================================================================
# Property 14.4: Projected Cost Calculation Accuracy
# ============================================================================

@given(
    days_in_period=st.integers(min_value=1, max_value=30),
    daily_cost=st.floats(min_value=1.0, max_value=1000.0)
)
@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_property_projected_cost_calculation_accuracy(days_in_period, daily_cost):
    """
    Property: For any period length and cost pattern, the projected
    monthly cost should be accurately calculated based on the average
    daily cost in the period.
    
    Validates: Requirements 7.5
    """
    test_path = f"./test_analytics_projection_{datetime.now().timestamp()}"
    engine = AnalyticsEngine(storage_path=test_path)
    
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_in_period)
        
        # Create cost records with consistent daily cost
        total_cost = daily_cost * days_in_period
        
        for day in range(days_in_period):
            cost_record = CostRecord(
                timestamp=start_date + timedelta(days=day),
                category=CostCategory.API_CALLS,
                amount=daily_cost,
                currency="USD",
                description="Daily cost"
            )
            engine.record_cost(cost_record)
        
        # Get cost analysis
        analysis = engine.get_cost_analysis(start_date, end_date)
        
        # Calculate expected projected monthly cost
        expected_monthly = daily_cost * 30
        
        # Property: Total cost should match
        assert abs(analysis.total_cost - total_cost) < 0.01, \
            f"Total cost: expected {total_cost:.2f}, got {analysis.total_cost:.2f}"
        
        # Property: Projected monthly cost should be accurate
        assert abs(analysis.projected_monthly_cost - expected_monthly) < 1.0, \
            f"Projected monthly: expected {expected_monthly:.2f}, got {analysis.projected_monthly_cost:.2f}"
        
    finally:
        if Path(test_path).exists():
            shutil.rmtree(test_path)


# ============================================================================
# Property 14.5: Top Users Ranking Accuracy
# ============================================================================

@given(
    user_count=st.integers(min_value=2, max_value=20),
    tasks_per_user=st.integers(min_value=1, max_value=10)
)
@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_property_top_users_ranking_accuracy(user_count, tasks_per_user):
    """
    Property: For any number of users and tasks, the top users ranking
    should accurately reflect usage and cost, sorted by total cost in
    descending order.
    
    Validates: Requirements 7.5
    """
    test_path = f"./test_analytics_topusers_{datetime.now().timestamp()}"
    engine = AnalyticsEngine(storage_path=test_path)
    
    try:
        # Create usage records with different costs per user
        expected_user_costs = {}
        
        for user_idx in range(user_count):
            user_id = f"user_{user_idx}"
            # Each user has progressively higher cost (user_0 cheapest, user_N most expensive)
            cost_multiplier = user_idx + 1
            
            for task_idx in range(tasks_per_user):
                usage = UsageRecord(
                    timestamp=datetime.now() - timedelta(minutes=user_idx * tasks_per_user + task_idx),
                    user_id=user_id,
                    task_id=f"task_{user_idx}_{task_idx}",
                    model_name="luma",
                    operation_type="generation",
                    duration_seconds=10.0 * cost_multiplier,
                    success=True
                )
                engine.record_usage(usage)
                
                # Calculate expected cost
                pricing = engine.model_pricing["luma"]
                cost = pricing.calculate_cost(10.0 * cost_multiplier, 0.0, 0.0)
                expected_user_costs[user_id] = expected_user_costs.get(user_id, 0.0) + cost
        
        # Get top users
        top_users = engine.get_top_users(limit=user_count)
        
        # Property: Should return correct number of users
        assert len(top_users) == user_count, \
            f"Should return {user_count} users, got {len(top_users)}"
        
        # Property: Users should be sorted by cost (descending)
        for i in range(len(top_users) - 1):
            assert top_users[i][2] >= top_users[i + 1][2], \
                f"Users should be sorted by cost: {top_users[i][2]} < {top_users[i + 1][2]}"
        
        # Property: Each user's cost should match expected
        for user_id, task_count, total_cost in top_users:
            expected_cost = expected_user_costs[user_id]
            assert abs(total_cost - expected_cost) < 0.01, \
                f"Cost for {user_id}: expected {expected_cost:.2f}, got {total_cost:.2f}"
            
            # Property: Task count should match
            assert task_count == tasks_per_user, \
                f"Task count for {user_id}: expected {tasks_per_user}, got {task_count}"
        
    finally:
        if Path(test_path).exists():
            shutil.rmtree(test_path)


# ============================================================================
# Property 14.6: Report Export and Persistence
# ============================================================================

@given(
    record_count=st.integers(min_value=1, max_value=20)
)
@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_property_report_export_and_persistence(record_count):
    """
    Property: For any generated report, the export functionality should
    successfully save the report to disk and the saved data should match
    the original report exactly.
    
    Validates: Requirements 7.5
    """
    test_path = f"./test_analytics_export_{datetime.now().timestamp()}"
    engine = AnalyticsEngine(storage_path=test_path)
    
    try:
        # Create some usage records
        start_date = datetime.now() - timedelta(hours=1)
        
        for i in range(record_count):
            usage = UsageRecord(
                timestamp=start_date + timedelta(minutes=i),
                user_id=f"user_{i}",
                task_id=f"task_{i}",
                model_name="luma",
                operation_type="generation",
                duration_seconds=float(i + 1),
                success=True
            )
            engine.record_usage(usage)
        
        # Generate report
        report = engine.generate_report(ReportPeriod.HOURLY)
        
        # Export report
        export_filename = "test_report.json"
        success = engine.export_report(report, export_filename)
        
        # Property: Export should succeed
        assert success, "Report export should succeed"
        
        # Property: Exported file should exist
        export_path = Path(test_path) / export_filename
        assert export_path.exists(), "Exported report file should exist"
        
        # Property: Exported data should match original report
        import json
        with open(export_path, 'r', encoding='utf-8') as f:
            loaded_report = json.load(f)
        
        # Check key fields match
        assert loaded_report["period"] == report["period"], \
            "Exported report period should match"
        assert loaded_report["usage_statistics"]["total_tasks"] == report["usage_statistics"]["total_tasks"], \
            "Exported task count should match"
        
    finally:
        if Path(test_path).exists():
            shutil.rmtree(test_path)


# ============================================================================
# Property 14.7: Multi-Period Report Consistency
# ============================================================================

@given(
    period_type=st.sampled_from([ReportPeriod.DAILY, ReportPeriod.WEEKLY, ReportPeriod.MONTHLY])
)
@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_property_multi_period_report_consistency(period_type):
    """
    Property: For any report period type, reports generated for the same
    data should be consistent and contain accurate date ranges matching
    the period specification.
    
    Validates: Requirements 7.5
    """
    test_path = f"./test_analytics_multiperiod_{datetime.now().timestamp()}"
    engine = AnalyticsEngine(storage_path=test_path)
    
    try:
        # Create usage records spanning multiple days
        base_date = datetime.now() - timedelta(days=35)
        
        for day in range(35):
            for hour in range(3):  # 3 records per day
                usage = UsageRecord(
                    timestamp=base_date + timedelta(days=day, hours=hour),
                    user_id=f"user_{day % 5}",
                    task_id=f"task_{day}_{hour}",
                    model_name="luma",
                    operation_type="generation",
                    duration_seconds=10.0,
                    success=True
                )
                engine.record_usage(usage)
        
        # Generate report
        report = engine.generate_report(period_type)
        
        # Property: Report should have correct period type
        assert report["period"] == period_type.value, \
            f"Report period should be {period_type.value}"
        
        # Property: Date range should match period type
        start = datetime.fromisoformat(report["period_start"])
        end = datetime.fromisoformat(report["period_end"])
        
        period_days = (end - start).days
        
        if period_type == ReportPeriod.DAILY:
            assert 0 <= period_days <= 1, \
                f"Daily report should span ~1 day, got {period_days}"
        elif period_type == ReportPeriod.WEEKLY:
            assert 6 <= period_days <= 8, \
                f"Weekly report should span ~7 days, got {period_days}"
        elif period_type == ReportPeriod.MONTHLY:
            assert 28 <= period_days <= 31, \
                f"Monthly report should span ~30 days, got {period_days}"
        
        # Property: Usage statistics should only include records in range
        stats = report["usage_statistics"]
        assert stats["total_tasks"] > 0, \
            "Report should contain tasks within the period"
        
    finally:
        if Path(test_path).exists():
            shutil.rmtree(test_path)


# ============================================================================
# Property 14.8: Cost Category Breakdown Accuracy
# ============================================================================

@given(
    api_cost=st.floats(min_value=10.0, max_value=1000.0),
    storage_cost=st.floats(min_value=5.0, max_value=500.0),
    compute_cost=st.floats(min_value=20.0, max_value=2000.0)
)
@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_property_cost_category_breakdown_accuracy(api_cost, storage_cost, compute_cost):
    """
    Property: For any combination of costs across different categories,
    the cost analysis should accurately break down costs by category
    and the sum should equal the total cost.
    
    Validates: Requirements 7.5
    """
    test_path = f"./test_analytics_categories_{datetime.now().timestamp()}"
    engine = AnalyticsEngine(storage_path=test_path)
    
    try:
        start_date = datetime.now() - timedelta(hours=1)
        end_date = datetime.now()
        
        # Record costs in different categories
        costs = [
            (CostCategory.API_CALLS, api_cost),
            (CostCategory.STORAGE, storage_cost),
            (CostCategory.COMPUTE, compute_cost)
        ]
        
        expected_total = api_cost + storage_cost + compute_cost
        
        for category, amount in costs:
            cost_record = CostRecord(
                timestamp=start_date,
                category=category,
                amount=amount,
                currency="USD",
                description=f"{category.value} cost"
            )
            engine.record_cost(cost_record)
        
        # Get cost analysis
        analysis = engine.get_cost_analysis(start_date, end_date)
        
        # Property: Total cost should equal sum of all categories
        assert abs(analysis.total_cost - expected_total) < 0.01, \
            f"Total cost should be {expected_total:.2f}, got {analysis.total_cost:.2f}"
        
        # Property: Each category cost should match
        assert abs(analysis.costs_by_category.get("api_calls", 0.0) - api_cost) < 0.01, \
            f"API cost should be {api_cost:.2f}"
        assert abs(analysis.costs_by_category.get("storage", 0.0) - storage_cost) < 0.01, \
            f"Storage cost should be {storage_cost:.2f}"
        assert abs(analysis.costs_by_category.get("compute", 0.0) - compute_cost) < 0.01, \
            f"Compute cost should be {compute_cost:.2f}"
        
        # Property: Sum of category costs should equal total
        category_sum = sum(analysis.costs_by_category.values())
        assert abs(category_sum - expected_total) < 0.01, \
            f"Sum of categories {category_sum:.2f} should equal total {expected_total:.2f}"
        
    finally:
        if Path(test_path).exists():
            shutil.rmtree(test_path)


# ============================================================================
# Property 14.9: Success Rate Calculation Accuracy
# ============================================================================

@given(
    total_tasks=st.integers(min_value=10, max_value=100),
    success_percentage=st.integers(min_value=0, max_value=100)
)
@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_property_success_rate_calculation_accuracy(total_tasks, success_percentage):
    """
    Property: For any number of tasks and success percentage, the
    calculated success rate in reports should accurately reflect the
    ratio of successful to total tasks.
    
    Validates: Requirements 7.5
    """
    test_path = f"./test_analytics_successrate_{datetime.now().timestamp()}"
    engine = AnalyticsEngine(storage_path=test_path)
    
    try:
        start_date = datetime.now() - timedelta(hours=1)
        
        # Calculate number of successful tasks
        successful_count = int(total_tasks * success_percentage / 100)
        
        # Create tasks with specified success rate
        for i in range(total_tasks):
            success = i < successful_count
            
            usage = UsageRecord(
                timestamp=start_date + timedelta(minutes=i),
                user_id=f"user_{i}",
                task_id=f"task_{i}",
                model_name="luma",
                operation_type="generation",
                duration_seconds=10.0,
                success=success,
                error_type=None if success else "test_error"
            )
            engine.record_usage(usage)
        
        # Generate report
        report = engine.generate_report(ReportPeriod.HOURLY)
        
        # Property: Total tasks should match
        assert report["usage_statistics"]["total_tasks"] == total_tasks, \
            f"Total tasks should be {total_tasks}"
        
        # Property: Successful tasks should match
        assert report["usage_statistics"]["successful_tasks"] == successful_count, \
            f"Successful tasks should be {successful_count}"
        
        # Property: Failed tasks should match
        failed_count = total_tasks - successful_count
        assert report["usage_statistics"]["failed_tasks"] == failed_count, \
            f"Failed tasks should be {failed_count}"
        
        # Property: Success rate should be accurate
        expected_rate = successful_count / total_tasks if total_tasks > 0 else 0.0
        actual_rate = report["usage_statistics"]["success_rate"]
        
        assert abs(actual_rate - expected_rate) < 0.01, \
            f"Success rate should be {expected_rate:.2f}, got {actual_rate:.2f}"
        
    finally:
        if Path(test_path).exists():
            shutil.rmtree(test_path)


# ============================================================================
# Test Runner
# ============================================================================

def run_all_property_tests():
    """Run all property-based tests for statistical reporting accuracy"""
    print("Running Property-Based Tests for Statistical Reporting Accuracy")
    print("=" * 80)
    print()
    
    all_passed = True
    
    tests = [
        ("14.1: Report Generation Completeness", test_property_report_generation_completeness),
        ("14.2: Cost Analysis Accuracy", test_property_cost_analysis_accuracy),
        ("14.3: Usage Statistics Aggregation Accuracy", test_property_usage_statistics_aggregation_accuracy),
        ("14.4: Projected Cost Calculation Accuracy", test_property_projected_cost_calculation_accuracy),
        ("14.5: Top Users Ranking Accuracy", test_property_top_users_ranking_accuracy),
        ("14.6: Report Export and Persistence", test_property_report_export_and_persistence),
        ("14.7: Multi-Period Report Consistency", test_property_multi_period_report_consistency),
        ("14.8: Cost Category Breakdown Accuracy", test_property_cost_category_breakdown_accuracy),
        ("14.9: Success Rate Calculation Accuracy", test_property_success_rate_calculation_accuracy),
    ]
    
    for test_name, test_func in tests:
        print(f"Test {test_name}")
        try:
            test_func()
            print("✓ PASSED\n")
        except Exception as e:
            print(f"✗ FAILED: {e}\n")
            all_passed = False
    
    print("=" * 80)
    if all_passed:
        print("✓ ALL PROPERTY TESTS PASSED")
    else:
        print("✗ SOME PROPERTY TESTS FAILED")
    print("=" * 80)
    
    return all_passed


if __name__ == "__main__":
    import sys
    success = run_all_property_tests()
    sys.exit(0 if success else 1)
