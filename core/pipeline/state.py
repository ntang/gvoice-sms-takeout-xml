"""
State management for pipeline stages.

Handles persistence of stage state and results using a hybrid SQLite/JSON approach.
"""

import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import StageResult

logger = logging.getLogger(__name__)


class StateManager:
    """Manages persistent state for pipeline stages."""
    
    def __init__(self, state_dir: Path):
        """
        Initialize state manager.
        
        Args:
            state_dir: Directory to store state files
        """
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        
        # SQLite database for stage execution tracking
        self.db_path = self.state_dir / "pipeline_state.db"
        self.init_database()
        
        # JSON files for lightweight state
        self.json_state_path = self.state_dir / "pipeline_config.json"
        
    def init_database(self) -> None:
        """Initialize the SQLite database for stage tracking."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS stage_executions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    stage_name TEXT NOT NULL,
                    execution_start TIMESTAMP,
                    execution_end TIMESTAMP,
                    success BOOLEAN,
                    records_processed INTEGER,
                    execution_time REAL,
                    error_count INTEGER,
                    metadata TEXT,  -- JSON blob
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS stage_outputs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    execution_id INTEGER,
                    output_file TEXT,
                    file_size INTEGER,
                    checksum TEXT,
                    FOREIGN KEY (execution_id) REFERENCES stage_executions(id)
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_stage_name 
                ON stage_executions(stage_name)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_execution_start 
                ON stage_executions(execution_start)
            """)
            
    def record_stage_start(self, stage_name: str) -> int:
        """
        Record the start of a stage execution.
        
        Args:
            stage_name: Name of the stage being executed
            
        Returns:
            int: Execution ID for tracking
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO stage_executions 
                (stage_name, execution_start, success)
                VALUES (?, ?, ?)
            """, (stage_name, datetime.now(), False))
            return cursor.lastrowid
            
    def record_stage_result(self, execution_id: int, result: StageResult) -> None:
        """
        Record the result of a stage execution.
        
        Args:
            execution_id: ID from record_stage_start
            result: Stage execution result
        """
        with sqlite3.connect(self.db_path) as conn:
            # Update main execution record
            conn.execute("""
                UPDATE stage_executions
                SET execution_end = ?,
                    success = ?,
                    records_processed = ?,
                    execution_time = ?,
                    error_count = ?,
                    metadata = ?
                WHERE id = ?
            """, (
                datetime.now(),
                result.success,
                result.records_processed,
                result.execution_time,
                len(result.errors),
                json.dumps(result.metadata),
                execution_id
            ))
            
            # Record output files
            for output_file in result.output_files:
                if output_file.exists():
                    file_size = output_file.stat().st_size
                else:
                    file_size = 0
                    
                conn.execute("""
                    INSERT INTO stage_outputs
                    (execution_id, output_file, file_size)
                    VALUES (?, ?, ?)
                """, (execution_id, str(output_file), file_size))
                
    def get_last_successful_execution(self, stage_name: str) -> Optional[Dict[str, Any]]:
        """
        Get the last successful execution of a stage.
        
        Args:
            stage_name: Name of the stage
            
        Returns:
            Dict with execution details or None if no successful execution
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM stage_executions
                WHERE stage_name = ? AND success = 1
                ORDER BY execution_end DESC
                LIMIT 1
            """, (stage_name,))
            
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None
            
    def is_stage_completed(self, stage_name: str) -> bool:
        """
        Check if a stage has completed successfully.
        
        Args:
            stage_name: Name of the stage
            
        Returns:
            bool: True if stage completed successfully
        """
        return self.get_last_successful_execution(stage_name) is not None
        
    def get_pipeline_status(self) -> Dict[str, Any]:
        """
        Get overall pipeline status.
        
        Returns:
            Dict with pipeline execution status
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Get latest execution for each stage
            cursor.execute("""
                SELECT stage_name,
                       MAX(execution_end) as last_execution,
                       success,
                       records_processed,
                       error_count
                FROM stage_executions
                WHERE execution_end IS NOT NULL
                GROUP BY stage_name
                ORDER BY last_execution DESC
            """)
            
            stages = []
            for row in cursor.fetchall():
                stages.append(dict(row))
                
            return {
                'stages': stages,
                'last_update': datetime.now().isoformat()
            }
            
    def save_json_state(self, data: Dict[str, Any]) -> None:
        """
        Save JSON state data.
        
        Args:
            data: Dictionary to save as JSON
        """
        with open(self.json_state_path, 'w') as f:
            json.dump(data, f, indent=2, default=str)
            
    def load_json_state(self) -> Dict[str, Any]:
        """
        Load JSON state data.
        
        Returns:
            Dict with saved state, empty dict if no state exists
        """
        if self.json_state_path.exists():
            try:
                with open(self.json_state_path, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to load JSON state: {e}")
                
        return {}
        
    def clear_stage_state(self, stage_name: str) -> None:
        """
        Clear all state for a specific stage.
        
        Args:
            stage_name: Name of the stage to clear
        """
        with sqlite3.connect(self.db_path) as conn:
            # Get execution IDs for this stage
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id FROM stage_executions WHERE stage_name = ?
            """, (stage_name,))
            
            execution_ids = [row[0] for row in cursor.fetchall()]
            
            # Delete output records
            for exec_id in execution_ids:
                conn.execute("""
                    DELETE FROM stage_outputs WHERE execution_id = ?
                """, (exec_id,))
                
            # Delete execution records
            conn.execute("""
                DELETE FROM stage_executions WHERE stage_name = ?
            """, (stage_name,))
            
        logger.info(f"Cleared state for stage: {stage_name}")
        
    def clear_all_state(self) -> None:
        """Clear all pipeline state."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM stage_outputs")
            conn.execute("DELETE FROM stage_executions")
            
        if self.json_state_path.exists():
            self.json_state_path.unlink()
            
        logger.info("Cleared all pipeline state")
