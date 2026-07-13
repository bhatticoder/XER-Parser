#!/usr/bin/env python
"""XER File Parser Command-Line Interface

Standalone CLI for parsing and processing XER files.

Usage:
    python cli.py load CONSTRUCTION.xer       # Load XER file
    python cli.py projects                    # Show projects
    python cli.py tasks                       # Show tasks
    python cli.py resources                   # Show resources
    python cli.py summary                     # Show summary
    python cli.py export output.txt           # Export formatted data
    python cli.py help                        # Show help
"""

import sys
import argparse
from xerparser.src.commands import XerCommand
from xerparser.src.parser import file_reader, parser
from xerparser.src.formatter import format_xer_file


def main():
    """Main CLI entry point"""
    parser_cmd = argparse.ArgumentParser(
        description='XER File Parser - Parse Oracle Primavera P6 XER files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  python cli.py load CONSTRUCTION.xer        Load and process XER file
  python cli.py projects                     List all projects
  python cli.py tasks                        List all tasks
  python cli.py resources                    List all resources
  python cli.py summary                      Show file summary
  python cli.py export report.txt            Export formatted report
        '''
    )
    
    parser_cmd.add_argument('command', nargs='?', default='help',
                           help='Command to execute')
    parser_cmd.add_argument('args', nargs='*',
                           help='Command arguments')
    
    args = parser_cmd.parse_args()
    
    cmd = XerCommand()
    
    # Route commands
    if args.command == 'help':
        parser_cmd.print_help()
        sys.exit(0)
    
    elif args.command == 'load':
        if not args.args:
            print("Error: specify XER file to load")
            sys.exit(1)
        filename = args.args[0]
        if cmd.load_file(filename):
            cmd.show_summary()
            cmd.export_formatted()
            sys.exit(0)
        else:
            sys.exit(1)
    
    elif args.command == 'projects':
        if not cmd.current_file:
            print("Error: no file loaded. Use 'load' command first.")
            sys.exit(1)
        cmd.show_projects()
        sys.exit(0)
    
    elif args.command == 'tasks':
        if not cmd.current_file:
            print("Error: no file loaded. Use 'load' command first.")
            sys.exit(1)
        cmd.show_tasks()
        sys.exit(0)
    
    elif args.command == 'resources':
        if not cmd.current_file:
            print("Error: no file loaded. Use 'load' command first.")
            sys.exit(1)
        cmd.show_resources()
        sys.exit(0)
    
    elif args.command == 'summary':
        if not cmd.current_file:
            print("Error: no file loaded. Use 'load' command first.")
            sys.exit(1)
        cmd.show_summary()
        sys.exit(0)
    
    elif args.command == 'export':
        if not cmd.current_file:
            print("Error: no file loaded. Use 'load' command first.")
            sys.exit(1)
        output_path = args.args[0] if args.args else "output/parsed_xer.txt"
        cmd.export_formatted(output_path)
        sys.exit(0)
    
    else:
        print(f"Unknown command: {args.command}")
        parser_cmd.print_help()
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user.")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
