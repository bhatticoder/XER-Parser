"""XER Parser Test Script

This script demonstrates the complete XER parser functionality.
It loads an XER file, parses it, displays information, and exports formatted data.
"""

from xerparser.src.parser import file_reader, parser
from xerparser.src.formatter import format_xer_file
from xerparser.src.commands import XerCommand

def main():
    """Main test function"""
    print("=" * 80)
    print("XER FILE PARSER - COMPLETE PROJECT")
    print("=" * 80)
    print()
    
    # Create command interface
    cmd = XerCommand()
    
    # Load and parse the XER file
    xer_file = "Hotel Project.xer"
    
    if not cmd.load_file(xer_file):
        print("Failed to load XER file. Exiting.")
        return
    
    print()
    
    # Display summary
    cmd.show_summary()
    print()
    
    # Display projects
    cmd.show_projects()
    print()
    
    # Display tasks
    cmd.show_tasks()
    print()
    
    # Display resources
    cmd.show_resources()
    print()
    
    # Export formatted data to file
    output_file = cmd.export_formatted("output/parsed_xer.txt")
    print()
    
    # Manual parsing demonstration
    print("=" * 80)
    print("MANUAL PARSING DEMONSTRATION")
    print("=" * 80)
    print()
    
    xer_contents = file_reader(xer_file)
    tables = parser(xer_contents)
    
    # Iterate projects
    for proj in tables.get("PROJECT", []):
        proj_id = proj.get("proj_id")
        code = proj.get("proj_short_name") or proj.get("proj_id")
        name = proj.get("proj_name") or "(no name)"
        print(f"Parsed Project: {name} (Code: {code})")
        print("-" * 50)
        
        # Print tasks belonging to this project
        for task in tables.get("TASK", []):
            if task.get("proj_id") != proj_id:
                continue
            tcode = task.get("task_code") or task.get("task_id")
            tname = task.get("task_name") or "(no name)"
            status = task.get("status_code") or "(no status)"
            print(f"[{tcode}] {tname} -> Status: {status}")
    
    print()
    print("=" * 80)
    print("[OK] Test completed successfully!")
    print("=" * 80)


if __name__ == "__main__":
    main()