"""Project File Parser - Uses MPXJ to parse project management files

Supports all formats that MPXJ supports:
- Oracle Primavera P6: .xer, .pmxml
- Microsoft Project: .mpp, .mpt, .mpx, .xml (MSPDI)
- Asta Powerproject: .pp
- And many more...
"""

import mpxj
import jpype
import jpype.imports
from typing import Dict, List, Any, Optional
from pathlib import Path

# Track JVM state
_jvm_started = False


def _ensure_jvm():
    """Start the JVM if not already running"""
    global _jvm_started
    if not _jvm_started and not jpype.isJVMStarted():
        jpype.startJVM()
        _jvm_started = True


def _java_to_python(value) -> Any:
    """Convert a Java object to a Python-native value"""
    if value is None:
        return None
    
    # Convert common Java types
    type_name = type(value).__name__
    
    # String
    if isinstance(value, str):
        return value
    
    # Number types
    try:
        if hasattr(value, 'doubleValue'):
            return value.doubleValue()
        if hasattr(value, 'intValue'):
            return value.intValue()
    except Exception:
        pass
    
    # Duration
    if hasattr(value, 'getDuration') and hasattr(value, 'getUnits'):
        try:
            return f"{value.getDuration()} {value.getUnits().toString()}"
        except Exception:
            pass
    
    # Date/time types
    if hasattr(value, 'toString'):
        s = str(value.toString())
        return s
    
    return str(value)


def file_reader(filename: str) -> str:
    """Read project file - kept for backward compatibility
    
    Args:
        filename: Path to the project file
        
    Returns:
        Absolute path as string (MPXJ reads files directly)
        
    Raises:
        FileNotFoundError: If file doesn't exist
    """
    file_path = Path(filename)
    
    if not file_path.is_absolute() and not file_path.exists():
        file_path = Path.cwd() / filename
    
    if not file_path.exists():
        raise FileNotFoundError(f"Project file not found: {filename}")
    
    return str(file_path.absolute())


def parser(file_path: str) -> Dict[str, List[Dict[str, Any]]]:
    """Parse a project file using MPXJ
    
    Args:
        file_path: Path to the project file (any supported format)
        
    Returns:
        Dictionary with table names as keys and list of records as values.
        Compatible with the old XER parser output format.
    """
    _ensure_jvm()
    
    from org.mpxj.reader import UniversalProjectReader  # type: ignore
    
    reader = UniversalProjectReader()
    project = reader.read(file_path)
    
    if project is None:
        raise ValueError(f"Could not parse file: {file_path}")
    
    tables = {}
    
    # Extract Projects
    tables["PROJECT"] = _extract_project_info(project)
    
    # Extract WBS
    wbs_list = _extract_wbs(project)
    if wbs_list:
        tables["PROJWBS"] = wbs_list
    
    # Extract Tasks
    tasks = _extract_tasks(project)
    if tasks:
        tables["TASK"] = tasks
    
    # Extract Resources
    resources = _extract_resources(project)
    if resources:
        tables["RSRC"] = resources
    
    # Extract Resource Assignments
    assignments = _extract_assignments(project)
    if assignments:
        tables["TASKRSRC"] = assignments
    
    # Extract Calendars
    calendars = _extract_calendars(project)
    if calendars:
        tables["CALENDAR"] = calendars
    
    # Extract Predecessors
    predecessors = _extract_predecessors(project)
    if predecessors:
        tables["TASKPRED"] = predecessors
    
    return tables


def _extract_project_info(project) -> List[Dict[str, Any]]:
    """Extract project-level information"""
    props = project.getProjectProperties()
    
    proj = {
        "proj_id": _java_to_python(props.getUniqueID()) or 1,
        "proj_short_name": _java_to_python(props.getProjectTitle()) or _java_to_python(props.getName()) or "(untitled)",
        "proj_name": _java_to_python(props.getName()),
        "plan_start_date": _java_to_python(props.getStartDate()),
        "plan_end_date": _java_to_python(props.getFinishDate()),
        "status_code": _java_to_python(props.getStatusDate()),
        "company_name": _java_to_python(props.getCompany()),
        "author": _java_to_python(props.getAuthor()),
        "last_updated": _java_to_python(props.getLastSaved()),
    }
    
    return [proj]


def _extract_wbs(project) -> List[Dict[str, Any]]:
    """Extract Work Breakdown Structure"""
    wbs_list = []
    tasks = project.getTasks()
    
    for task in tasks:
        # In MPXJ, WBS elements are tasks with child tasks
        if task.getSummary():
            wbs_entry = {
                "wbs_id": _java_to_python(task.getUniqueID()),
                "wbs_name": _java_to_python(task.getName()),
                "wbs_short_name": _java_to_python(task.getWBS()),
                "parent_wbs_id": _java_to_python(task.getParentTask().getUniqueID()) if task.getParentTask() else None,
                "seq_num": _java_to_python(task.getID()),
                "proj_id": _java_to_python(project.getProjectProperties().getUniqueID()) or 1,
            }
            wbs_list.append(wbs_entry)
    
    return wbs_list


def _extract_tasks(project) -> List[Dict[str, Any]]:
    """Extract task information"""
    task_list = []
    tasks = project.getTasks()
    
    for task in tasks:
        # Skip summary (WBS) tasks — only include leaf tasks
        if task.getID() is None:
            continue
        
        task_entry = {
            "task_id": _java_to_python(task.getUniqueID()),
            "task_code": _java_to_python(task.getWBS()) or f"T{_java_to_python(task.getUniqueID())}",
            "task_name": _java_to_python(task.getName()),
            "status_code": _get_task_status(task),
            "proj_id": _java_to_python(project.getProjectProperties().getUniqueID()) or 1,
            "wbs_id": _java_to_python(task.getParentTask().getUniqueID()) if task.getParentTask() else None,
            "planned_dur_hr_cnt": _java_to_python(task.getDuration()),
            "act_start_date": _java_to_python(task.getActualStart()),
            "act_end_date": _java_to_python(task.getActualFinish()),
            "early_start_date": _java_to_python(task.getEarlyStart()),
            "early_end_date": _java_to_python(task.getEarlyFinish()),
            "late_start_date": _java_to_python(task.getLateStart()),
            "late_end_date": _java_to_python(task.getLateFinish()),
            "total_float_hr_cnt": _java_to_python(task.getTotalSlack()),
            "pct_complete": _java_to_python(task.getPercentageComplete()),
            "description": _java_to_python(task.getNotes()) if task.getNotes() else None,
            "is_summary": bool(task.getSummary()),
            "is_milestone": bool(task.getMilestone()),
            "baseline_start_date": _java_to_python(task.getBaselineStart()),
            "baseline_end_date": _java_to_python(task.getBaselineFinish()),
            "planned_start_date": _java_to_python(task.getPlannedStart()),
            "planned_end_date": _java_to_python(task.getPlannedFinish()),
        }
        task_list.append(task_entry)
    
    return task_list


def _get_task_status(task) -> str:
    """Determine task status string"""
    try:
        pct = task.getPercentageComplete()
        if pct is not None:
            pct_val = float(str(pct))
            if pct_val >= 100:
                return "TK_Complete"
            elif pct_val > 0:
                return "TK_Active"
        
        if task.getActualStart() is not None and task.getActualFinish() is not None:
            return "TK_Complete"
        elif task.getActualStart() is not None:
            return "TK_Active"
        
        return "TK_NotStart"
    except Exception:
        return "TK_NotStart"


def _extract_resources(project) -> List[Dict[str, Any]]:
    """Extract resource information"""
    resource_list = []
    resources = project.getResources()
    
    for rsrc in resources:
        if rsrc.getID() is None:
            continue
        
        rsrc_entry = {
            "rsrc_id": _java_to_python(rsrc.getUniqueID()),
            "rsrc_name": _java_to_python(rsrc.getName()),
            "rsrc_short_name": _java_to_python(rsrc.getInitials()),
            "rsrc_type": _java_to_python(rsrc.getType()),
            "email_addr": _java_to_python(rsrc.getEmailAddress()),
            "def_qty_per_hr": _java_to_python(rsrc.getMaxUnits()),
            "active_flag": "Y",
        }
        resource_list.append(rsrc_entry)
    
    return resource_list


def _extract_assignments(project) -> List[Dict[str, Any]]:
    """Extract task-resource assignments"""
    assignment_list = []
    assignments = project.getResourceAssignments()
    
    for assign in assignments:
        task = assign.getTask()
        rsrc = assign.getResource()
        
        if task is None:
            continue
        
        assign_entry = {
            "task_id": _java_to_python(task.getUniqueID()),
            "rsrc_id": _java_to_python(rsrc.getUniqueID()) if rsrc else None,
            "rsrc_name": _java_to_python(rsrc.getName()) if rsrc else None,
            "plan_qty": _java_to_python(assign.getWork()),
            "act_qty": _java_to_python(assign.getActualWork()),
            "act_start_date": _java_to_python(assign.getActualStart()),
            "act_end_date": _java_to_python(assign.getActualFinish()),
        }
        assignment_list.append(assign_entry)
    
    return assignment_list


def _extract_calendars(project) -> List[Dict[str, Any]]:
    """Extract calendar information"""
    calendar_list = []
    calendars = project.getCalendars()
    
    for cal in calendars:
        cal_entry = {
            "clndr_id": _java_to_python(cal.getUniqueID()),
            "clndr_name": _java_to_python(cal.getName()),
            "clndr_type": "CA_Base" if cal.getParent() is None else "CA_Project",
            "default_flag": "Y" if cal == project.getDefaultCalendar() else "N",
        }
        calendar_list.append(cal_entry)
    
    return calendar_list


def _extract_predecessors(project) -> List[Dict[str, Any]]:
    """Extract task predecessor relationships"""
    pred_list = []
    tasks = project.getTasks()
    
    for task in tasks:
        predecessors = task.getPredecessors()
        if predecessors:
            for pred in predecessors:
                pred_task = pred.getPredecessorTask()
                if pred_task is None:
                    continue
                
                pred_entry = {
                    "task_id": _java_to_python(task.getUniqueID()),
                    "pred_task_id": _java_to_python(pred_task.getUniqueID()),
                    "pred_type": _java_to_python(pred.getType()),
                    "lag_hr_cnt": _java_to_python(pred.getLag()),
                }
                pred_list.append(pred_entry)
    
    return pred_list


# ===== Backward-compatible helper functions =====

class XerFile:
    """Main file handler - kept for backward compatibility"""
    
    def __init__(self):
        self.header = {}
        self.tables = {}
        self.metadata = {}
    
    def __repr__(self):
        return f"<ProjectFile: {len(self.tables)} tables>"


def get_projects(tables: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """Extract project information from parsed tables"""
    return tables.get("PROJECT", [])


def get_tasks_for_project(tables: Dict[str, List[Dict[str, Any]]], proj_id: int) -> List[Dict[str, Any]]:
    """Get all tasks for a specific project"""
    all_tasks = tables.get("TASK", [])
    return [task for task in all_tasks if task.get("proj_id") == proj_id]


def get_resources(tables: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """Extract resource information"""
    return tables.get("RSRC", [])


def get_assignments(tables: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """Extract task assignment information"""
    return tables.get("TASKRSRC", [])


def get_calendars(tables: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """Extract calendar information"""
    return tables.get("CALENDAR", [])


def get_wbs(tables: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """Extract Work Breakdown Structure information"""
    return tables.get("PROJWBS", [])


# Supported file extensions
SUPPORTED_EXTENSIONS = {
    '.xer', '.mpp', '.mpt', '.mpx', '.xml', '.pmxml',
    '.pp', '.ppx', '.planner', '.gan', '.gnt',
    '.cdpx', '.cdpz', '.sdef', '.fts', '.schedule_grid',
}


def is_supported_file(filename: str) -> bool:
    """Check if a file extension is supported by MPXJ"""
    ext = Path(filename).suffix.lower()
    return ext in SUPPORTED_EXTENSIONS
