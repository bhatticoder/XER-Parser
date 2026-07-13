from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class TaskModel(BaseModel):
    """Model representing a project task matching Oracle P6 TASK schema."""
    task_id: int = Field(description="Unique task identifier")
    task_code: str = Field(description="User-defined activity code identifier")
    task_name: str = Field(description="Descriptive name of the task")
    status_code: str = Field(description="Current status (TK_NotStart, TK_Active, TK_Complete)")
    proj_id: int = Field(description="Associated project ID")
    wbs_id: Optional[int] = Field(default=None, description="Reference ID to the Work Breakdown Structure")
    planned_dur_hr_cnt: float = Field(default=0.0, description="Planned duration of task in hours")
    act_start_date: Optional[datetime] = Field(default=None, description="Actual start date and time")
    act_end_date: Optional[datetime] = Field(default=None, description="Actual finish date and time")
    early_start_date: Optional[datetime] = Field(default=None, description="Calculated earliest start date")
    early_end_date: Optional[datetime] = Field(default=None, description="Calculated earliest finish date")
    late_start_date: Optional[datetime] = Field(default=None, description="Calculated latest start date")
    late_end_date: Optional[datetime] = Field(default=None, description="Calculated latest finish date")
    baseline_start_date: Optional[datetime] = Field(default=None, description="Baseline milestone start date")
    baseline_end_date: Optional[datetime] = Field(default=None, description="Baseline target finish date")
    planned_start_date: Optional[datetime] = Field(default=None, description="Planned start date")
    planned_end_date: Optional[datetime] = Field(default=None, description="Planned completion date")
    total_float_hr_cnt: float = Field(default=0.0, description="Slack duration in hours")
    pct_complete: float = Field(default=0.0, description="Percent complete progress (0.0 to 100.0 or 0.0 to 1.0)")
    description: Optional[str] = Field(default=None, description="Optional annotations or notes")
    is_summary: bool = Field(default=False, description="Flag indicating if this is a summary or WBS task")
    is_milestone: bool = Field(default=False, description="Flag indicating milestone status")

class RelationshipModel(BaseModel):
    """Model representing dependency relationships inside Oracle P6 TASKPRED schema."""
    task_id: int = Field(description="Successor task unique ID")
    pred_task_id: int = Field(description="Predecessor task unique ID")
    pred_type: str = Field(description="Dependency relationship type (FS: Finish-Start, SS: Start-Start, etc.)")
    lag_hr_cnt: float = Field(default=0.0, description="Lag constraint offset in hours")
