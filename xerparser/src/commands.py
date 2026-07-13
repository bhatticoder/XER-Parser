"""XER Command Interface - Provides commands for working with XER files"""

import sys
from typing import Dict, List, Any
from pathlib import Path

from .parser import file_reader, parser, get_projects, get_tasks_for_project, get_resources
from .formatter import XerFormatter


class XerCommand:
    """Command interface for XER file operations"""
    
    def __init__(self):
        self.current_tables = None
        self.current_file = None
    
    def load_file(self, filename: str) -> bool:
        """Load and parse an XER file
        
        Args:
            filename: Path to XER file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            print(f"Loading XER file: {filename}")
            xer_content = file_reader(filename)
            self.current_tables = parser(xer_content)
            self.current_file = filename
            print(f"[OK] Successfully loaded {filename}")
            print(f"[OK] Found {len(self.current_tables)} tables")
            return True
        except FileNotFoundError:
            print(f"[ERROR] Error: File not found - {filename}")
            return False
        except Exception as e:
            print(f"[ERROR] Error loading file: {str(e)}")
            return False
    
    def show_projects(self) -> bool:
        """Display all projects in the file"""
        if not self._check_loaded():
            return False
        
        projects = get_projects(self.current_tables)
        
        if not projects:
            print("No projects found in the XER file.")
            return False
        
        print(f"\n{'Projects Found:':^50}")
        print("-" * 80)
        print(f"{'ID':<10} {'Name':<40} {'Status':<20}")
        print("-" * 80)
        
        for proj in projects:
            proj_id = proj.get("proj_id", "N/A")
            name = proj.get("proj_short_name") or proj.get("proj_name") or "(no name)"
            name = name[:39]  # Truncate to fit
            status = proj.get("status_code") or "(active)"
            print(f"{proj_id:<10} {name:<40} {status:<20}")
        
        print("-" * 80)
        return True
    
    def show_tasks(self, proj_id: int = None) -> bool:
        """Display tasks, optionally filtered by project"""
        if not self._check_loaded():
            return False
        
        if proj_id is None:
            tasks = self.current_tables.get("TASK", [])
            print(f"\nAll Tasks ({len(tasks)} total):")
        else:
            tasks = get_tasks_for_project(self.current_tables, proj_id)
            print(f"\nTasks for Project {proj_id}:")
        
        if not tasks:
            print("No tasks found.")
            return False
        
        print("-" * 100)
        print(f"{'Code':<15} {'Name':<40} {'Status':<15} {'Duration':<15}")
        print("-" * 100)
        
        for task in tasks[:100]:  # Limit to first 100
            code = task.get("task_code") or str(task.get("task_id", "N/A"))
            name = task.get("task_name") or "(no name)"
            name = name[:39]
            status = task.get("status_code") or ""
            duration = task.get("planned_dur_hr_cnt") or ""
            
            print(f"{code:<15} {name:<40} {status:<15} {duration:<15}")
        
        if len(tasks) > 100:
            print(f"... and {len(tasks) - 100} more tasks")
        
        print("-" * 100)
        return True
    
    def show_resources(self) -> bool:
        """Display all resources"""
        if not self._check_loaded():
            return False
        
        resources = get_resources(self.current_tables)
        
        if not resources:
            print("No resources found in the XER file.")
            return False
        
        print(f"\nResources ({len(resources)} total):")
        print("-" * 80)
        print(f"{'ID':<10} {'Name':<30} {'Type':<15} {'Status':<15}")
        print("-" * 80)
        
        for rsrc in resources[:100]:
            rsrc_id = rsrc.get("rsrc_id", "N/A")
            name = rsrc.get("rsrc_name") or rsrc.get("rsrc_short_name") or "(no name)"
            name = name[:29]
            rsrc_type = rsrc.get("rsrc_type") or "N/A"
            active = "Active" if rsrc.get("active_flag") == "Y" else "Inactive"
            
            print(f"{rsrc_id:<10} {name:<30} {rsrc_type:<15} {active:<15}")
        
        if len(resources) > 100:
            print(f"... and {len(resources) - 100} more resources")
        
        print("-" * 80)
        return True
    
    def show_summary(self) -> bool:
        """Display summary of XER file contents"""
        if not self._check_loaded():
            return False
        
        print(f"\n{'XER File Summary':^50}")
        print("=" * 80)
        print(f"File: {self.current_file}")
        print("-" * 80)
        
        for table_name in sorted(self.current_tables.keys()):
            count = len(self.current_tables[table_name])
            print(f"  {table_name:<20} : {count:>5} records")
        
        print("=" * 80)
        return True
    
    def export_formatted(self, output_path: str = "output/parsed_xer.txt") -> bool:
        """Export formatted XER data to text file"""
        if not self._check_loaded():
            return False
        
        try:
            formatter = XerFormatter()
            formatted = formatter.format_xer_data(self.current_tables)
            output_file = formatter.save_to_file(formatted, output_path)
            print(f"[OK] Exported formatted data to: {output_file}")
            return True
        except Exception as e:
            print(f"[ERROR] Error exporting data: {str(e)}")
            return False
    
    def get_table_data(self, table_name: str) -> List[Dict[str, Any]]:
        """Get raw data from a specific table
        
        Args:
            table_name: Name of the table
            
        Returns:
            List of records in the table
        """
        if not self._check_loaded():
            return []
        
        return self.current_tables.get(table_name, [])
    
    def _check_loaded(self) -> bool:
        """Check if a file is loaded"""
        if self.current_tables is None:
            print("[ERROR] No XER file loaded. Use load_file() first.")
            return False
        return True
    
    def interactive(self):
        """Start interactive command mode"""
        print("\nXER File Parser - Interactive Mode")
        print("Commands: load, projects, tasks, resources, summary, export, exit")
        print("-" * 80)
        
        while True:
            try:
                cmd = input("\n> ").strip().lower()
                
                if not cmd:
                    continue
                
                if cmd == "exit" or cmd == "quit":
                    print("Goodbye!")
                    break
                
                elif cmd.startswith("load "):
                    filename = cmd.split(" ", 1)[1].strip().strip('"\'')
                    self.load_file(filename)
                
                elif cmd == "projects":
                    self.show_projects()
                
                elif cmd == "tasks":
                    self.show_tasks()
                
                elif cmd == "resources":
                    self.show_resources()
                
                elif cmd == "summary":
                    self.show_summary()
                
                elif cmd.startswith("export"):
                    parts = cmd.split(" ", 1)
                    output_path = parts[1].strip().strip('"\'') if len(parts) > 1 else "output/parsed_xer.txt"
                    self.export_formatted(output_path)
                
                elif cmd == "help":
                    self._print_help()
                
                else:
                    print(f"Unknown command: {cmd}")
                    self._print_help()
            
            except KeyboardInterrupt:
                print("\n\nInterrupted. Type 'exit' to quit.")
            except Exception as e:
                print(f"Error: {str(e)}")
    
    @staticmethod
    def _print_help():
        """Print help information"""
        print("\nAvailable Commands:")
        print("  load <filename>     - Load and parse an XER file")
        print("  projects            - Show all projects")
        print("  tasks               - Show all tasks")
        print("  resources           - Show all resources")
        print("  summary             - Show file summary")
        print("  export [path]       - Export formatted data to file")
        print("  help                - Show this help message")
        print("  exit                - Exit the program")


def main():
    """Main entry point for command-line interface"""
    cmd = XerCommand()
    
    # If a file is provided as argument, load it
    if len(sys.argv) > 1:
        filename = sys.argv[1]
        if cmd.load_file(filename):
            cmd.show_summary()
            cmd.export_formatted()
        else:
            sys.exit(1)
    else:
        # Start interactive mode
        cmd.interactive()


if __name__ == "__main__":
    main()
