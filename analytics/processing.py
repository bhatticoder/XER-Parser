import pandas as pd
import numpy as np
from typing import List, Tuple
from .models import TaskModel, RelationshipModel

class ScheduleProcessingEngine:
    """Vectorized Pandas processing engine to convert project models, cast datetimes, and compute delay variance."""

    @staticmethod
    def process_schedule(
        tasks: List[TaskModel], 
        relations: List[RelationshipModel]
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Convert validated task and relation lists into Pandas DataFrames and execute schedule metrics.
        
        Args:
            tasks: List of TaskModel objects.
            relations: List of RelationshipModel objects.
            
        Returns:
            A tuple of (Processed Task DataFrame, Processed Relationship DataFrame)
        """
        # Convert models to dictionaries
        task_dicts = [task.model_dump() for task in tasks]
        rel_dicts = [rel.model_dump() for rel in relations]
        
        # Initialize DataFrames
        df_tasks = pd.DataFrame(task_dicts) if task_dicts else pd.DataFrame(columns=TaskModel.model_fields.keys())
        df_relations = pd.DataFrame(rel_dicts) if rel_dicts else pd.DataFrame(columns=RelationshipModel.model_fields.keys())
        
        if df_tasks.empty:
            df_tasks['variance_days'] = pd.Series(dtype=float)
            df_tasks['variance_hours'] = pd.Series(dtype=float)
            return df_tasks, df_relations

        # 1. Force explicit datetime casting on all date fields
        datetime_cols = [
            'act_start_date', 'act_end_date', 
            'early_start_date', 'early_end_date', 
            'late_start_date', 'late_end_date', 
            'baseline_start_date', 'baseline_end_date',
            'planned_start_date', 'planned_end_date'
        ]
        for col in datetime_cols:
            if col in df_tasks.columns:
                df_tasks[col] = pd.to_datetime(df_tasks[col], errors='coerce')
        
        # 2. Vectorized computation of Schedule Variance:
        # Variance = Current Finish Date (early_end_date) - Baseline Target Finish Date (baseline_end_date)
        # Note: If baseline_end_date is NaT, fallback to planned_end_date, or early_end_date (resulting in 0 variance)
        target_finish = df_tasks['baseline_end_date'].copy()
        
        if 'planned_end_date' in df_tasks.columns:
            target_finish = target_finish.fillna(df_tasks['planned_end_date'])
        
        if 'early_end_date' in df_tasks.columns:
            target_finish = target_finish.fillna(df_tasks['early_end_date'])
            
        # Calculate difference in seconds then convert to hours/days
        time_diff = df_tasks['early_end_date'] - target_finish
        
        # Total float and duration mapping
        df_tasks['variance_hours'] = time_diff.dt.total_seconds() / 3600.0
        df_tasks['variance_days'] = time_diff.dt.total_seconds() / 86400.0
        
        # Fill missing variance with 0.0
        df_tasks['variance_hours'] = df_tasks['variance_hours'].fillna(0.0)
        df_tasks['variance_days'] = df_tasks['variance_days'].fillna(0.0)
        
        # Add basic duration conversions mapping
        df_tasks['planned_dur_days'] = df_tasks['planned_dur_hr_cnt'] / 8.0
        df_tasks['total_float_days'] = df_tasks['total_float_hr_cnt'] / 8.0
        
        return df_tasks, df_relations
