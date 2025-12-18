"""
Cleanup Service for Video Studio

This module provides automated cleanup and space optimization services
for the Video Studio asset management system.
"""

import os
import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import json

from .asset_manager import AssetManager, AssetType, AssetStatus
from .video_manager import VideoManager
from .config import get_config, StorageConfig
from .error_handler import VideoStudioErrorHandler


class CleanupPolicy(Enum):
    """Cleanup policy types"""
    AGE_BASED = "age_based"
    SIZE_BASED = "size_based"
    USAGE_BASED = "usage_based"
    MANUAL = "manual"


@dataclass
class CleanupRule:
    """Rule for automated cleanup"""
    name: str
    policy: CleanupPolicy
    enabled: bool = True
    max_age_hours: Optional[int] = None
    max_size_mb: Optional[int] = None
    min_access_count: Optional[int] = None
    asset_types: List[AssetType] = field(default_factory=list)
    tags_include: List[str] = field(default_factory=list)
    tags_exclude: List[str] = field(default_factory=list)
    preserve_recent_hours: int = 24  # Always preserve assets newer than this
    
    def matches_asset(self, metadata) -> bool:
        """Check if cleanup rule matches an asset"""
        # Check asset type filter
        if self.asset_types and metadata.asset_type not in self.asset_types:
            return False
        
        # Check tag filters
        if self.tags_include:
            if not any(tag in metadata.tags for tag in self.tags_include):
                return False
        
        if self.tags_exclude:
            if any(tag in metadata.tags for tag in self.tags_exclude):
                return False
        
        # Check preservation period
        age_hours = (datetime.now() - metadata.created_at).total_seconds() / 3600
        if age_hours < self.preserve_recent_hours:
            return False
        
        # Apply policy-specific checks
        if self.policy == CleanupPolicy.AGE_BASED and self.max_age_hours:
            last_access_hours = (datetime.now() - metadata.last_accessed).total_seconds() / 3600
            return last_access_hours > self.max_age_hours
        
        elif self.policy == CleanupPolicy.SIZE_BASED and self.max_size_mb:
            size_mb = metadata.file_size / (1024 * 1024)
            return size_mb > self.max_size_mb
        
        elif self.policy == CleanupPolicy.USAGE_BASED and self.min_access_count:
            # This would require tracking access counts (not implemented in basic metadata)
            return False
        
        return True


@dataclass
class CleanupResult:
    """Result of cleanup operation"""
    files_deleted: int = 0
    space_freed_mb: float = 0.0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)


class CleanupService:
    """
    Automated cleanup and space optimization service.
    
    Provides intelligent cleanup based on configurable rules,
    storage monitoring, and automated maintenance tasks.
    """
    
    def __init__(self, asset_manager: Optional[AssetManager] = None,
                 video_manager: Optional[VideoManager] = None):
        """Initialize CleanupService"""
        self.asset_manager = asset_manager or AssetManager()
        self.video_manager = video_manager or VideoManager(self.asset_manager)
        self.config = get_config().storage
        self.error_handler = VideoStudioErrorHandler()
        self.logger = logging.getLogger(__name__)
        
        # Default cleanup rules
        self.cleanup_rules = self._create_default_rules()
        
        # Load custom rules if they exist
        self._load_cleanup_rules()
        
        # Monitoring thresholds
        self.warning_threshold_percent = 80
        self.critical_threshold_percent = 90
        
        # Statistics tracking
        self.last_cleanup_time: Optional[datetime] = None
        self.cleanup_history: List[Dict[str, Any]] = []
    
    def _create_default_rules(self) -> List[CleanupRule]:
        """Create default cleanup rules"""
        return [
            CleanupRule(
                name="expired_temp_files",
                policy=CleanupPolicy.AGE_BASED,
                max_age_hours=1,
                asset_types=[AssetType.TEMP],
                preserve_recent_hours=0  # No preservation for temp files
            ),
            CleanupRule(
                name="old_processed_images",
                policy=CleanupPolicy.AGE_BASED,
                max_age_hours=168,  # 7 days
                asset_types=[AssetType.IMAGE],
                tags_include=["processed"]
            ),
            CleanupRule(
                name="old_processed_videos",
                policy=CleanupPolicy.AGE_BASED,
                max_age_hours=336,  # 14 days
                asset_types=[AssetType.VIDEO],
                tags_include=["processed"]
            ),
            CleanupRule(
                name="large_unused_files",
                policy=CleanupPolicy.SIZE_BASED,
                max_size_mb=100,
                max_age_hours=72  # Only clean large files older than 3 days
            ),
            CleanupRule(
                name="error_status_files",
                policy=CleanupPolicy.AGE_BASED,
                max_age_hours=24,
                preserve_recent_hours=1
            )
        ]
    
    def _load_cleanup_rules(self) -> None:
        """Load custom cleanup rules from configuration"""
        try:
            rules_file = self.asset_manager.metadata_path / "cleanup_rules.json"
            if rules_file.exists():
                with open(rules_file, 'r', encoding='utf-8') as f:
                    rules_data = json.load(f)
                    
                custom_rules = []
                for rule_data in rules_data:
                    # Convert asset types from strings
                    if 'asset_types' in rule_data:
                        rule_data['asset_types'] = [
                            AssetType(at) for at in rule_data['asset_types']
                        ]
                    
                    # Convert policy from string
                    if 'policy' in rule_data:
                        rule_data['policy'] = CleanupPolicy(rule_data['policy'])
                    
                    custom_rules.append(CleanupRule(**rule_data))
                
                # Replace default rules with custom ones
                self.cleanup_rules = custom_rules
                self.logger.info(f"Loaded {len(custom_rules)} custom cleanup rules")
        
        except Exception as e:
            self.logger.warning(f"Failed to load custom cleanup rules: {e}")
    
    def _save_cleanup_rules(self) -> None:
        """Save cleanup rules to configuration"""
        try:
            rules_file = self.asset_manager.metadata_path / "cleanup_rules.json"
            rules_data = []
            
            for rule in self.cleanup_rules:
                rule_dict = {
                    'name': rule.name,
                    'policy': rule.policy.value,
                    'enabled': rule.enabled,
                    'max_age_hours': rule.max_age_hours,
                    'max_size_mb': rule.max_size_mb,
                    'min_access_count': rule.min_access_count,
                    'asset_types': [at.value for at in rule.asset_types],
                    'tags_include': rule.tags_include,
                    'tags_exclude': rule.tags_exclude,
                    'preserve_recent_hours': rule.preserve_recent_hours
                }
                rules_data.append(rule_dict)
            
            with open(rules_file, 'w', encoding='utf-8') as f:
                json.dump(rules_data, f, indent=2, ensure_ascii=False)
        
        except Exception as e:
            self.logger.error(f"Failed to save cleanup rules: {e}")
    
    async def run_cleanup(self, dry_run: bool = False) -> CleanupResult:
        """
        Run automated cleanup based on configured rules.
        
        Args:
            dry_run: If True, only simulate cleanup without deleting files
            
        Returns:
            CleanupResult with operation details
        """
        result = CleanupResult()
        start_time = datetime.now()
        
        try:
            self.logger.info(f"Starting cleanup operation (dry_run={dry_run})")
            
            # Get all assets
            all_assets = list(self.asset_manager._asset_registry.values())
            
            # Apply each cleanup rule
            for rule in self.cleanup_rules:
                if not rule.enabled:
                    continue
                
                rule_result = await self._apply_cleanup_rule(rule, all_assets, dry_run)
                
                result.files_deleted += rule_result.files_deleted
                result.space_freed_mb += rule_result.space_freed_mb
                result.errors.extend(rule_result.errors)
                result.warnings.extend(rule_result.warnings)
                result.details[rule.name] = {
                    'files_deleted': rule_result.files_deleted,
                    'space_freed_mb': rule_result.space_freed_mb,
                    'errors': rule_result.errors
                }
            
            # Clean up empty directories
            if not dry_run:
                await self.asset_manager._cleanup_empty_directories()
            
            # Update cleanup history
            if not dry_run:
                self.last_cleanup_time = datetime.now()
                self._record_cleanup_history(result, start_time)
            
            duration = (datetime.now() - start_time).total_seconds()
            self.logger.info(
                f"Cleanup completed in {duration:.2f}s: "
                f"{result.files_deleted} files, {result.space_freed_mb:.2f}MB freed"
            )
            
        except Exception as e:
            error_msg = f"Cleanup operation failed: {str(e)}"
            result.errors.append(error_msg)
            self.logger.error(error_msg)
        
        return result
    
    async def _apply_cleanup_rule(self, rule: CleanupRule, assets: List, dry_run: bool) -> CleanupResult:
        """Apply a single cleanup rule to assets"""
        result = CleanupResult()
        
        try:
            matching_assets = [asset for asset in assets if rule.matches_asset(asset)]
            
            for asset in matching_assets:
                try:
                    if dry_run:
                        # Just calculate what would be deleted
                        result.files_deleted += 1
                        result.space_freed_mb += asset.file_size / (1024 * 1024)
                    else:
                        # Actually delete the asset
                        if await self.asset_manager.delete_asset(asset.asset_id):
                            result.files_deleted += 1
                            result.space_freed_mb += asset.file_size / (1024 * 1024)
                        else:
                            result.errors.append(f"Failed to delete asset {asset.asset_id}")
                
                except Exception as e:
                    error_msg = f"Error processing asset {asset.asset_id}: {str(e)}"
                    result.errors.append(error_msg)
                    self.logger.warning(error_msg)
            
            self.logger.debug(
                f"Rule '{rule.name}': {result.files_deleted} files, "
                f"{result.space_freed_mb:.2f}MB (dry_run={dry_run})"
            )
        
        except Exception as e:
            error_msg = f"Failed to apply cleanup rule '{rule.name}': {str(e)}"
            result.errors.append(error_msg)
            self.logger.error(error_msg)
        
        return result
    
    def _record_cleanup_history(self, result: CleanupResult, start_time: datetime) -> None:
        """Record cleanup operation in history"""
        history_entry = {
            'timestamp': start_time.isoformat(),
            'duration_seconds': (datetime.now() - start_time).total_seconds(),
            'files_deleted': result.files_deleted,
            'space_freed_mb': result.space_freed_mb,
            'errors_count': len(result.errors),
            'warnings_count': len(result.warnings),
            'rule_details': result.details
        }
        
        self.cleanup_history.append(history_entry)
        
        # Keep only last 100 entries
        if len(self.cleanup_history) > 100:
            self.cleanup_history = self.cleanup_history[-100:]
        
        # Save to file
        try:
            history_file = self.asset_manager.metadata_path / "cleanup_history.json"
            with open(history_file, 'w', encoding='utf-8') as f:
                json.dump(self.cleanup_history, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.warning(f"Failed to save cleanup history: {e}")
    
    def check_storage_health(self) -> Dict[str, Any]:
        """
        Check storage health and return recommendations.
        
        Returns:
            Storage health report with recommendations
        """
        stats = self.asset_manager.get_storage_stats()
        health_report = {
            'status': 'healthy',
            'warnings': [],
            'recommendations': [],
            'stats': stats,
            'thresholds': {
                'warning_percent': self.warning_threshold_percent,
                'critical_percent': self.critical_threshold_percent
            }
        }
        
        # Check disk usage
        if 'disk_usage_percent' in stats:
            usage_percent = stats['disk_usage_percent']
            
            if usage_percent >= self.critical_threshold_percent:
                health_report['status'] = 'critical'
                health_report['warnings'].append(
                    f"Disk usage is critical: {usage_percent:.1f}%"
                )
                health_report['recommendations'].append(
                    "Immediate cleanup required - consider aggressive cleanup rules"
                )
            elif usage_percent >= self.warning_threshold_percent:
                health_report['status'] = 'warning'
                health_report['warnings'].append(
                    f"Disk usage is high: {usage_percent:.1f}%"
                )
                health_report['recommendations'].append(
                    "Schedule cleanup soon to prevent storage issues"
                )
        
        # Check asset storage limits
        max_storage_bytes = self.config.max_storage_gb * 1024 * 1024 * 1024
        if stats['total_size_bytes'] > max_storage_bytes:
            health_report['status'] = 'warning'
            health_report['warnings'].append(
                f"Asset storage exceeds configured limit: "
                f"{stats['total_size_mb']:.1f}MB > {self.config.max_storage_gb * 1024}MB"
            )
            health_report['recommendations'].append(
                "Run cleanup or increase storage limit configuration"
            )
        
        # Check for error status assets
        error_assets = len([
            asset for asset in self.asset_manager._asset_registry.values()
            if asset.status == AssetStatus.ERROR
        ])
        
        if error_assets > 0:
            health_report['warnings'].append(f"{error_assets} assets in error status")
            health_report['recommendations'].append("Clean up failed assets")
        
        # Check cleanup frequency
        if self.last_cleanup_time:
            hours_since_cleanup = (datetime.now() - self.last_cleanup_time).total_seconds() / 3600
            if hours_since_cleanup > self.config.cleanup_interval_hours * 2:
                health_report['warnings'].append(
                    f"No cleanup for {hours_since_cleanup:.1f} hours"
                )
                health_report['recommendations'].append("Run scheduled cleanup")
        else:
            health_report['warnings'].append("No cleanup history found")
            health_report['recommendations'].append("Run initial cleanup")
        
        return health_report
    
    async def optimize_storage(self) -> Dict[str, Any]:
        """
        Comprehensive storage optimization.
        
        Returns:
            Optimization results
        """
        optimization_result = {
            'cleanup_result': None,
            'defrag_result': None,
            'compression_result': None,
            'total_space_freed_mb': 0.0,
            'recommendations': []
        }
        
        try:
            # Run cleanup
            cleanup_result = await self.run_cleanup(dry_run=False)
            optimization_result['cleanup_result'] = cleanup_result.__dict__
            optimization_result['total_space_freed_mb'] += cleanup_result.space_freed_mb
            
            # Optimize asset storage (consolidate processed files)
            consolidation_result = await self._consolidate_processed_assets()
            optimization_result['consolidation_result'] = consolidation_result
            optimization_result['total_space_freed_mb'] += consolidation_result.get('space_freed_mb', 0)
            
            # Generate recommendations
            health_report = self.check_storage_health()
            optimization_result['recommendations'] = health_report['recommendations']
            
            self.logger.info(
                f"Storage optimization completed: "
                f"{optimization_result['total_space_freed_mb']:.2f}MB freed"
            )
        
        except Exception as e:
            self.logger.error(f"Storage optimization failed: {e}")
            optimization_result['error'] = str(e)
        
        return optimization_result
    
    async def _consolidate_processed_assets(self) -> Dict[str, Any]:
        """Consolidate processed assets to reduce duplication"""
        result = {
            'duplicates_removed': 0,
            'space_freed_mb': 0.0,
            'errors': []
        }
        
        try:
            # Find processed assets with same source
            processed_assets = [
                asset for asset in self.asset_manager._asset_registry.values()
                if 'processed' in asset.tags and asset.metadata.get('source_asset_id')
            ]
            
            # Group by source asset
            source_groups = {}
            for asset in processed_assets:
                source_id = asset.metadata['source_asset_id']
                if source_id not in source_groups:
                    source_groups[source_id] = []
                source_groups[source_id].append(asset)
            
            # Remove older duplicates (keep most recent)
            for source_id, assets in source_groups.items():
                if len(assets) > 3:  # Keep max 3 processed versions
                    # Sort by creation time, keep newest 3
                    assets.sort(key=lambda a: a.created_at, reverse=True)
                    to_delete = assets[3:]
                    
                    for asset in to_delete:
                        if await self.asset_manager.delete_asset(asset.asset_id):
                            result['duplicates_removed'] += 1
                            result['space_freed_mb'] += asset.file_size / (1024 * 1024)
        
        except Exception as e:
            error_msg = f"Asset consolidation failed: {str(e)}"
            result['errors'].append(error_msg)
            self.logger.error(error_msg)
        
        return result
    
    def add_cleanup_rule(self, rule: CleanupRule) -> None:
        """Add a new cleanup rule"""
        self.cleanup_rules.append(rule)
        self._save_cleanup_rules()
        self.logger.info(f"Added cleanup rule: {rule.name}")
    
    def remove_cleanup_rule(self, rule_name: str) -> bool:
        """Remove a cleanup rule by name"""
        original_count = len(self.cleanup_rules)
        self.cleanup_rules = [r for r in self.cleanup_rules if r.name != rule_name]
        
        if len(self.cleanup_rules) < original_count:
            self._save_cleanup_rules()
            self.logger.info(f"Removed cleanup rule: {rule_name}")
            return True
        
        return False
    
    def get_cleanup_rules(self) -> List[CleanupRule]:
        """Get all cleanup rules"""
        return self.cleanup_rules.copy()
    
    def get_cleanup_history(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get cleanup history"""
        history = self.cleanup_history.copy()
        if limit:
            history = history[-limit:]
        return history
    
    async def schedule_cleanup(self, interval_hours: int = 24) -> None:
        """
        Schedule automatic cleanup to run at specified intervals.
        
        Args:
            interval_hours: Cleanup interval in hours
        """
        self.logger.info(f"Scheduling automatic cleanup every {interval_hours} hours")
        
        while True:
            try:
                await asyncio.sleep(interval_hours * 3600)  # Convert to seconds
                
                # Check if cleanup is needed
                health_report = self.check_storage_health()
                if health_report['status'] in ['warning', 'critical']:
                    self.logger.info("Running scheduled cleanup due to storage warnings")
                    await self.run_cleanup(dry_run=False)
                else:
                    self.logger.debug("Scheduled cleanup skipped - storage healthy")
            
            except Exception as e:
                self.logger.error(f"Scheduled cleanup failed: {e}")
                # Continue the loop even if cleanup fails


# Global cleanup service instance
_cleanup_service = None


def get_cleanup_service() -> CleanupService:
    """Get global CleanupService instance"""
    global _cleanup_service
    if _cleanup_service is None:
        _cleanup_service = CleanupService()
    return _cleanup_service


# Convenience functions
async def run_cleanup(dry_run: bool = False) -> CleanupResult:
    """Run cleanup operation"""
    return await get_cleanup_service().run_cleanup(dry_run)


def check_storage_health() -> Dict[str, Any]:
    """Check storage health"""
    return get_cleanup_service().check_storage_health()


async def optimize_storage() -> Dict[str, Any]:
    """Optimize storage"""
    return await get_cleanup_service().optimize_storage()