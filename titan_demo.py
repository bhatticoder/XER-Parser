"""Analytics Demonstration Script.
Executes the high-performance architectural pipeline on project files.
Usage:
    python titan_demo.py [file_path]
"""

import sys
import os
import logging
from pathlib import Path

# Add project root to sys path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from analytics import TitanByteOrchestrator

# Configure root logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def run_demo():
    print("=" * 80)
    print("ANALYTICS - INTEGRATED PIPELINE DEMO")
    print("=" * 80)
    
    # 1. Resolve path to project file
    if len(sys.argv) > 1:
        project_file = sys.argv[1]
    else:
        # Fall back to sample construction file in G:\Projects\XER\Files
        project_file = os.path.join("Files", "CONSRTRUCTION.xer")
        if not os.path.exists(project_file):
            project_file = os.path.join("Files", "Hotel Project.xer")
            
    print(f"Target Project File: {project_file}")
    if not os.path.exists(project_file):
        print(f"[ERROR] Sample project file not found: {project_file}")
        print("Please place a valid .xer or .mpp project file inside the 'Files' directory.")
        sys.exit(1)
        
    # Get API key if setup in environment
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("[NOTE] GEMINI_API_KEY missing from environment. Starting pipeline in OFFLINE mode.")
    else:
        print("[OK] GEMINI_API_KEY detected. Online Gemini 1.5 Pro analysis activated.")
        
    # 2. Initialize Orchestrator
    orchestrator = TitanByteOrchestrator(gemini_api_key=api_key)
    
    try:
        # 3. Process Project through Pipeline
        results = orchestrator.run_pipeline(project_file)
        
        # 4. Display Processing Results
        df_tasks = results["tasks_df"]
        df_relations = results["relations_df"]
        cpm_metrics = results["cpm_metrics"]
        critical_nodes = results["critical_path_ids"]
        report = results["report"]
        
        print("\n" + "=" * 50)
        print("PIPELINE EXECUTION METRICS")
        print("=" * 50)
        print(f"Total Conformed Activities Ingested: {len(df_tasks)}")
        print(f"Total Dependency Lines Conformed : {len(df_relations)}")
        print(f"Network Nodes in Graph Model      : {len(results['graph'].nodes)}")
        print(f"Network Edges in Graph Model      : {len(results['graph'].edges)}")
        print(f"Graph-Calculated Critical Path    : {len(critical_nodes)} activities")
        print("-" * 50)
        
        # Display sample tasks with delays
        delayed_tasks = df_tasks[df_tasks['variance_days'] > 0]
        print(f"\nDelayed Activities Spotted (Total {len(delayed_tasks)}):")
        if not delayed_tasks.empty:
            print(delayed_tasks[['task_code', 'task_name', 'planned_dur_days', 'variance_days', 'total_float_days']].head(10).to_string(index=False))
        else:
            print("No delayed activities spotted based on current baseline end date checks.")
            
        # 5. Save and Export report
        output_dir = "output"
        os.makedirs(output_dir, exist_ok=True)
        report_file = os.path.join(output_dir, "mitigation_report.md")
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
            
        print("\n" + "=" * 50)
        print(f"RISK REPORT SAVED TO: {os.path.abspath(report_file)}")
        print("=" * 50)
        
        # Print first 50 lines of report as preview
        print("\nReport Preview:\n")
        preview_lines = report.splitlines()[:40]
        print("\n".join(preview_lines))
        if len(preview_lines) >= 40:
            print("\n... [Truncated. Read complete report in output/mitigation_report.md] ...")
            
    except Exception as e:
        print(f"\n[FATAL ERROR] Pipeline failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    run_demo()
