import logging
import re
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path

from xerparser.src.parser import parser as parse_project_file
from .models import TaskModel, RelationshipModel

# Setup logger for Titan Ingestion Tier
logger = logging.getLogger("TitanByte.Ingestion")
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

class ProjectIngestionEngine:
    """Ingestion Engine utilizing MPXJ to load project data and conform it to validated models."""

    @staticmethod
    def clean_float(value: Any) -> float:
        """Clean string durations or lag weights (e.g. '608.0 h') into float."""
        if value is None:
            return 0.0
        if isinstance(value, (int, float)):
            return float(value)
        
        s = str(value).strip().lower()
        if not s:
            return 0.0
        
        # Regex to find the first numeric/decimal sequence
        match = re.search(r"[-+]?\d*\.?\d+", s)
        if match:
            try:
                return float(match.group())
            except ValueError:
                pass
        return 0.0

    @staticmethod
    def clean_datetime(value: Any) -> Optional[datetime]:
        """Convert ISO/standard dates from MPXJ string exports into Python datetime."""
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        
        s = str(value).strip()
        if not s:
            return None
        
        # Accept multiple datetime patterns exported by Java/JPype
        for fmt in (
            "%Y-%m-%dT%H:%M:%S", 
            "%Y-%m-%dT%H:%M",
            "%Y-%m-%d %H:%M:%S", 
            "%Y-%m-%d %H:%M", 
            "%Y-%m-%d"
        ):
            try:
                return datetime.strptime(s, fmt)
            except ValueError:
                continue
        
        try:
            return datetime.fromisoformat(s)
        except ValueError:
            logger.warning(f"Unable to parse date string: '{s}'")
            return None

    @classmethod
    def ingest_project(cls, file_path: str) -> tuple[List[TaskModel], List[RelationshipModel]]:
        """Reads XER/MPP file via MPXJ and returns validated models.
        
        Args:
            file_path: Absolute or relative path to project file.
            
        Returns:
            A tuple containing: (list of validated TaskModels, list of validated RelationshipModels)
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        logger.info(f"Ingesting project file: {path.name}")
        
        # Parse project file
        try:
            tables = parse_project_file(str(path.absolute()))
        except Exception as e:
            logger.error(f"Failed to parse project file with MPXJ: {str(e)}")
            raise ValueError(f"MPXJ Parsing Error: {str(e)}") from e

        raw_tasks = tables.get("TASK", [])
        raw_relations = tables.get("TASKPRED", [])
        
        logger.info(f"Loaded {len(raw_tasks)} raw tasks and {len(raw_relations)} raw relations from file.")
        
        validated_tasks: List[TaskModel] = []
        validated_relations: List[RelationshipModel] = []
        
        # Conforming and validating tasks
        for idx, task in enumerate(raw_tasks):
            try:
                task_id_raw = task.get("task_id")
                if task_id_raw is None:
                    logger.warning(f"Skipping task index {idx}: missing task_id")
                    continue
                
                # Check for primary keys
                task_id = int(float(str(task_id_raw)))
                
                # Build fields conforming to schema types
                model_data = {
                    "task_id": task_id,
                    "task_code": str(task.get("task_code") or f"T{task_id}"),
                    "task_name": str(task.get("task_name") or "(untitled)"),
                    "status_code": str(task.get("status_code") or "TK_NotStart"),
                    "proj_id": int(float(str(task.get("proj_id") or 1))),
                    "wbs_id": int(float(str(task.get("wbs_id")))) if task.get("wbs_id") is not None else None,
                    "planned_dur_hr_cnt": cls.clean_float(task.get("planned_dur_hr_cnt")),
                    "act_start_date": cls.clean_datetime(task.get("act_start_date")),
                    "act_end_date": cls.clean_datetime(task.get("act_end_date")),
                    "early_start_date": cls.clean_datetime(task.get("early_start_date")),
                    "early_end_date": cls.clean_datetime(task.get("early_end_date")),
                    "late_start_date": cls.clean_datetime(task.get("late_start_date")),
                    "late_end_date": cls.clean_datetime(task.get("late_end_date")),
                    "baseline_start_date": cls.clean_datetime(task.get("baseline_start_date")),
                    "baseline_end_date": cls.clean_datetime(task.get("baseline_end_date")),
                    "planned_start_date": cls.clean_datetime(task.get("planned_start_date")),
                    "planned_end_date": cls.clean_datetime(task.get("planned_end_date")),
                    "total_float_hr_cnt": cls.clean_float(task.get("total_float_hr_cnt")),
                    "pct_complete": float(task.get("pct_complete") or 0.0),
                    "description": task.get("description"),
                    "is_summary": bool(task.get("is_summary")),
                    "is_milestone": bool(task.get("is_milestone")),
                }
                
                # Pydantic validation
                task_model = TaskModel(**model_data)
                validated_tasks.append(task_model)
                
            except Exception as e:
                logger.warning(f"Task validation failure at index {idx}: {str(e)}")
                continue

        # Conforming and validating relationships
        for idx, rel in enumerate(raw_relations):
            try:
                task_id_raw = rel.get("task_id")
                pred_task_id_raw = rel.get("pred_task_id")
                
                if task_id_raw is None or pred_task_id_raw is None:
                    continue
                
                relation_data = {
                    "task_id": int(float(str(task_id_raw))),
                    "pred_task_id": int(float(str(pred_task_id_raw))),
                    "pred_type": str(rel.get("pred_type") or "FS").strip().upper(),
                    "lag_hr_cnt": cls.clean_float(rel.get("lag_hr_cnt")),
                }
                
                rel_model = RelationshipModel(**relation_data)
                validated_relations.append(rel_model)
                
            except Exception as e:
                logger.warning(f"Relation validation failure at index {idx}: {str(e)}")
                continue

        logger.info(f"Conformed {len(validated_tasks)} TaskModel objects and {len(validated_relations)} RelationshipModel objects.")
        return validated_tasks, validated_relations
