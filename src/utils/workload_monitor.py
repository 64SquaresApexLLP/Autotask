"""
Real-time Workload Monitoring Utility

This module provides utilities for monitoring and managing technician workloads
in real-time across the AutoTask integration system.
"""

import logging
import threading
import time
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class WorkloadSnapshot:
    """Snapshot of technician workload at a specific time"""
    technician_email: str
    technician_name: str
    workload_count: int
    timestamp: datetime
    active_tickets: List[str]

class RealTimeWorkloadMonitor:
    """
    Real-time workload monitoring system for technicians
    
    Provides continuous monitoring and alerting for workload changes
    """
    
    def __init__(self, assignment_agent, monitoring_interval: int = 60):
        """
        Initialize the workload monitor
        
        Args:
            assignment_agent: Instance of AssignmentAgentIntegration
            monitoring_interval: Monitoring interval in seconds (default: 60)
        """
        self.assignment_agent = assignment_agent
        self.monitoring_interval = monitoring_interval
        self.is_monitoring = False
        self.monitor_thread = None
        self.workload_history: Dict[str, List[WorkloadSnapshot]] = {}
        self.current_workloads: Dict[str, int] = {}
        self.workload_alerts: List[Dict] = []
        
        # Workload thresholds for alerts
        self.high_workload_threshold = 8
        self.critical_workload_threshold = 12
        
    def start_monitoring(self):
        """Start real-time workload monitoring"""
        if self.is_monitoring:
            logger.warning("Workload monitoring is already running")
            return
            
        self.is_monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitor_thread.start()
        logger.info(f"🔄 Started real-time workload monitoring (interval: {self.monitoring_interval}s)")
        
    def stop_monitoring(self):
        """Stop real-time workload monitoring"""
        self.is_monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        logger.info("⏹️ Stopped real-time workload monitoring")
        
    def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.is_monitoring:
            try:
                self._check_all_workloads()
                time.sleep(self.monitoring_interval)
            except Exception as e:
                logger.error(f"❌ Error in workload monitoring loop: {str(e)}")
                time.sleep(self.monitoring_interval)
                
    def _check_all_workloads(self):
        """Check workloads for all technicians"""
        try:
            current_time = datetime.now()
            workload_summary = self.assignment_agent.refresh_all_technician_workloads()
            
            for email, workload in workload_summary.items():
                # Update current workloads
                previous_workload = self.current_workloads.get(email, 0)
                self.current_workloads[email] = workload
                
                # Check for workload changes
                if previous_workload != workload:
                    logger.info(f"📊 Workload change detected: {email} {previous_workload} → {workload}")
                    
                # Check for high workload alerts
                self._check_workload_alerts(email, workload, current_time)
                
                # Store in history (keep last 24 hours)
                self._store_workload_snapshot(email, workload, current_time)
                
        except Exception as e:
            logger.error(f"❌ Error checking workloads: {str(e)}")
            
    def _check_workload_alerts(self, email: str, workload: int, timestamp: datetime):
        """Check if workload exceeds thresholds and create alerts"""
        alert_level = None
        
        if workload >= self.critical_workload_threshold:
            alert_level = "CRITICAL"
        elif workload >= self.high_workload_threshold:
            alert_level = "HIGH"
            
        if alert_level:
            alert = {
                'technician_email': email,
                'workload': workload,
                'alert_level': alert_level,
                'timestamp': timestamp,
                'message': f"Technician {email} has {workload} active tickets ({alert_level} workload)"
            }
            
            self.workload_alerts.append(alert)
            logger.warning(f"⚠️ {alert_level} workload alert: {email} has {workload} active tickets")
            
            # Keep only recent alerts (last 100)
            if len(self.workload_alerts) > 100:
                self.workload_alerts = self.workload_alerts[-100:]
                
    def _store_workload_snapshot(self, email: str, workload: int, timestamp: datetime):
        """Store workload snapshot in history"""
        if email not in self.workload_history:
            self.workload_history[email] = []
            
        snapshot = WorkloadSnapshot(
            technician_email=email,
            technician_name=email.split('@')[0],  # Simple name extraction
            workload_count=workload,
            timestamp=timestamp,
            active_tickets=[]  # Could be populated with actual ticket IDs
        )
        
        self.workload_history[email].append(snapshot)
        
        # Keep only last 24 hours of data
        cutoff_time = timestamp.replace(hour=timestamp.hour - 24)
        self.workload_history[email] = [
            s for s in self.workload_history[email] 
            if s.timestamp > cutoff_time
        ]
        
    def get_current_workloads(self) -> Dict[str, int]:
        """Get current workload for all technicians"""
        return self.current_workloads.copy()
        
    def get_workload_alerts(self, limit: int = 50) -> List[Dict]:
        """Get recent workload alerts"""
        return self.workload_alerts[-limit:] if self.workload_alerts else []
        
    def get_technician_workload_history(self, email: str, hours: int = 24) -> List[WorkloadSnapshot]:
        """Get workload history for a specific technician"""
        if email not in self.workload_history:
            return []
            
        cutoff_time = datetime.now().replace(hour=datetime.now().hour - hours)
        return [
            snapshot for snapshot in self.workload_history[email]
            if snapshot.timestamp > cutoff_time
        ]
        
    def force_workload_refresh(self) -> Dict[str, int]:
        """Force immediate workload refresh for all technicians"""
        logger.info("🔄 Forcing immediate workload refresh")
        try:
            workload_summary = self.assignment_agent.refresh_all_technician_workloads()
            self.current_workloads.update(workload_summary)
            logger.info(f"✅ Forced refresh complete: {len(workload_summary)} technicians updated")
            return workload_summary
        except Exception as e:
            logger.error(f"❌ Error in forced workload refresh: {str(e)}")
            return {}
            
    def get_workload_statistics(self) -> Dict:
        """Get workload statistics across all technicians"""
        if not self.current_workloads:
            return {}
            
        workloads = list(self.current_workloads.values())
        
        return {
            'total_technicians': len(workloads),
            'total_active_tickets': sum(workloads),
            'average_workload': sum(workloads) / len(workloads) if workloads else 0,
            'max_workload': max(workloads) if workloads else 0,
            'min_workload': min(workloads) if workloads else 0,
            'high_workload_count': len([w for w in workloads if w >= self.high_workload_threshold]),
            'critical_workload_count': len([w for w in workloads if w >= self.critical_workload_threshold]),
            'last_updated': datetime.now()
        }

# Global workload monitor instance (to be initialized by the main application)
workload_monitor: Optional[RealTimeWorkloadMonitor] = None

def initialize_workload_monitor(assignment_agent, monitoring_interval: int = 60) -> RealTimeWorkloadMonitor:
    """Initialize the global workload monitor"""
    global workload_monitor
    workload_monitor = RealTimeWorkloadMonitor(assignment_agent, monitoring_interval)
    return workload_monitor

def get_workload_monitor() -> Optional[RealTimeWorkloadMonitor]:
    """Get the global workload monitor instance"""
    return workload_monitor
