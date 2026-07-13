"""XER Formatter - Converts parsed XER data to formatted text output"""

from typing import Dict, List, Any
from pathlib import Path
from datetime import datetime


class XerFormatter:
    """Formats parsed XER data for display and file output"""
    
    def __init__(self):
        self.output_lines = []
    
    def format_xer_data(self, tables: Dict[str, List[Dict[str, Any]]]) -> str:
        """Format complete XER data into readable text
        
        Args:
            tables: Parsed tables from parser
            
        Returns:
            Formatted text representation
        """
        self.output_lines = []
        
        # Header
        self._add_header()
        
        # Project Information
        self._add_projects(tables)
        
        # Work Breakdown Structure
        self._add_wbs(tables)
        
        # Tasks
        self._add_tasks(tables)
        
        # Resources
        self._add_resources(tables)
        
        # Assignments
        self._add_assignments(tables)
        
        # Calendars
        self._add_calendars(tables)
        
        return '\n'.join(self.output_lines)
    
    def _add_header(self):
        """Add formatted header section"""
        self.output_lines.append("=" * 80)
        self.output_lines.append("XER FILE PARSER - PROJECT MANAGEMENT DATA REPORT")
        self.output_lines.append("=" * 80)
        self.output_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.output_lines.append("=" * 80)
        self.output_lines.append("")
    
    def _add_projects(self, tables: Dict[str, List[Dict[str, Any]]]):
        """Add projects section"""
        projects = tables.get("PROJECT", [])
        
        if not projects:
            self.output_lines.append("No projects found in XER file.\n")
            return
        
        self.output_lines.append("PROJECT INFORMATION")
        self.output_lines.append("-" * 80)
        
        for proj in projects:
            proj_id = proj.get("proj_id", "N/A")
            name = proj.get("proj_short_name") or "(no name)"
            
            self.output_lines.append(f"\nProject ID: {proj_id}")
            self.output_lines.append(f"Short Name: {name}")
            
            # Add more fields if available
            if proj.get("plan_start_date"):
                self.output_lines.append(f"Start Date: {proj.get('plan_start_date')}")
            if proj.get("plan_end_date"):
                self.output_lines.append(f"End Date: {proj.get('plan_end_date')}")
            if proj.get("critical_drtn_hr_cnt"):
                self.output_lines.append(f"Critical Duration (hrs): {proj.get('critical_drtn_hr_cnt')}")
        
        self.output_lines.append("")
    
    def _add_wbs(self, tables: Dict[str, List[Dict[str, Any]]]):
        """Add Work Breakdown Structure section"""
        wbs_list = tables.get("PROJWBS", [])
        
        if not wbs_list:
            return
        
        self.output_lines.append("WORK BREAKDOWN STRUCTURE (WBS)")
        self.output_lines.append("-" * 80)
        
        # Sort by parent/sequence to show hierarchy
        for wbs in sorted(wbs_list, key=lambda x: (x.get("parent_wbs_id") or 0, x.get("seq_num") or 0)):
            wbs_id = wbs.get("wbs_id", "N/A")
            name = wbs.get("wbs_name") or wbs.get("wbs_short_name", "(no name)")
            parent_id = wbs.get("parent_wbs_id")
            
            indent = "  " if parent_id else ""
            self.output_lines.append(f"{indent}[{wbs_id}] {name}")
        
        self.output_lines.append("")
    
    def _add_tasks(self, tables: Dict[str, List[Dict[str, Any]]]):
        """Add tasks section"""
        tasks = tables.get("TASK", [])
        
        if not tasks:
            return
        
        self.output_lines.append("TASKS")
        self.output_lines.append("-" * 80)
        
        for task in tasks:
            task_id = task.get("task_id", "N/A")
            code = task.get("task_code") or f"T{task_id}"
            name = task.get("task_name") or "(no name)"
            status = task.get("status_code") or "(no status)"
            
            self.output_lines.append(f"\n[{code}] {name}")
            self.output_lines.append(f"  Task ID: {task_id}")
            self.output_lines.append(f"  Status: {status}")
            
            if task.get("description"):
                self.output_lines.append(f"  Description: {task.get('description')}")
            if task.get("planned_dur_hr_cnt"):
                self.output_lines.append(f"  Planned Duration (hrs): {task.get('planned_dur_hr_cnt')}")
            if task.get("act_work_qty"):
                self.output_lines.append(f"  Actual Work: {task.get('act_work_qty')}")
        
        self.output_lines.append("")
    
    def _add_resources(self, tables: Dict[str, List[Dict[str, Any]]]):
        """Add resources section"""
        resources = tables.get("RSRC", [])
        
        if not resources:
            return
        
        self.output_lines.append("RESOURCES")
        self.output_lines.append("-" * 80)
        
        for rsrc in resources:
            rsrc_id = rsrc.get("rsrc_id", "N/A")
            name = rsrc.get("rsrc_name") or rsrc.get("rsrc_short_name", "(no name)")
            rsrc_type = rsrc.get("rsrc_type", "N/A")
            
            self.output_lines.append(f"\n[{rsrc_id}] {name}")
            self.output_lines.append(f"  Type: {rsrc_type}")
            
            if rsrc.get("def_qty_per_hr"):
                self.output_lines.append(f"  Qty per Hour: {rsrc.get('def_qty_per_hr')}")
            if rsrc.get("rsrc_title_name"):
                self.output_lines.append(f"  Title: {rsrc.get('rsrc_title_name')}")
        
        self.output_lines.append("")
    
    def _add_assignments(self, tables: Dict[str, List[Dict[str, Any]]]):
        """Add task resource assignments section"""
        assignments = tables.get("TASKRSRC", [])
        
        if not assignments:
            return
        
        self.output_lines.append("TASK RESOURCE ASSIGNMENTS")
        self.output_lines.append("-" * 80)
        
        for assign in assignments[:50]:  # Limit to first 50 for readability
            task_id = assign.get("task_id", "N/A")
            rsrc_id = assign.get("rsrc_id", "N/A")
            qty = assign.get("act_qty") or assign.get("plan_qty") or "N/A"
            
            self.output_lines.append(f"Task {task_id} <- Resource {rsrc_id} (Qty: {qty})")
        
        if len(assignments) > 50:
            self.output_lines.append(f"\n... and {len(assignments) - 50} more assignments")
        
        self.output_lines.append("")
    
    def _add_calendars(self, tables: Dict[str, List[Dict[str, Any]]]):
        """Add calendars section"""
        calendars = tables.get("CALENDAR", [])
        
        if not calendars:
            return
        
        self.output_lines.append("CALENDARS")
        self.output_lines.append("-" * 80)
        
        for cal in calendars:
            cal_id = cal.get("clndr_id", "N/A")
            name = cal.get("clndr_name", "(no name)")
            cal_type = cal.get("clndr_type", "N/A")
            default = cal.get("default_flag", "N")
            
            self.output_lines.append(f"\n[{cal_id}] {name}")
            self.output_lines.append(f"  Type: {cal_type}")
            self.output_lines.append(f"  Default: {'Yes' if default == 'Y' else 'No'}")
        
        self.output_lines.append("")
    
    def save_to_file(self, formatted_content: str, output_path: str = "output/parsed_xer.txt"):
        """Save formatted content to file
        
        Args:
            formatted_content: The formatted text content
            output_path: Path where to save the file
            
        Returns:
            Path to saved file
        """
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(formatted_content)
        
        return str(output_file.absolute())


def format_xer_file(tables: Dict[str, List[Dict[str, Any]]], output_path: str = "output/parsed_xer.txt") -> str:
    """Convenience function to format and save XER data
    
    Args:
        tables: Parsed tables from parser
        output_path: Path to save formatted output
        
    Returns:
        Path to saved file
    """
    formatter = XerFormatter()
    formatted = formatter.format_xer_data(tables)
    return formatter.save_to_file(formatted, output_path)
