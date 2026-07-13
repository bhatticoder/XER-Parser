import logging
from typing import Optional, Dict, Any, List, Tuple
import pandas as pd

from .ingestion import ProjectIngestionEngine
from .processing import ScheduleProcessingEngine
from .graph import ScheduleGraphEngine
from .llm import ExecutiveReportingEngine

logger = logging.getLogger("TitanByte.Orchestrator")

class TitanByteOrchestrator:
    """Orchestrator pipeline execution manager tying the Ingestion, Processing, Graph, and Gemini LLM layers."""

    def __init__(self, gemini_api_key: Optional[str] = None):
        """Initializes the orchestrator with configuration tokens."""
        self.gemini_api_key = gemini_api_key

    def run_pipeline(self, file_path: str) -> Dict[str, Any]:
        """Runs the entire multi-tiered pipeline:
        Ingestion -> Pandas Processing -> NetworkX DAG CPM -> Gemini Reporting.
        
        Args:
            file_path: The project file path (.xer or .mpp).
            
        Returns:
            A dictionary containing processed DataFrames, CPM metrics, and the final Markdown report.
        """
        logger.info("Initializing Titan Byte Analytics pipeline execution...")
        
        # Layer 1: Ingestion Tier
        validated_tasks, validated_relations = ProjectIngestionEngine.ingest_project(file_path)
        
        # Layer 2: Processing Tier (Pandas Engine)
        df_tasks, df_relations = ScheduleProcessingEngine.process_schedule(
            validated_tasks, 
            validated_relations
        )
        
        # Layer 3: Analytics Graph Tier (NetworkX Graph Engine)
        G = ScheduleGraphEngine.build_graph(df_tasks, df_relations)
        
        # Perform Critical Path Method (CPM)
        # Note: In case of graph cycles or errors, let them raise up so the pipeline fails cleanly
        schedule_cpm_metrics, critical_path_ids = ScheduleGraphEngine.calculate_cpm(G)
        
        # Feed graph-calculated Total Float and Early/Late dates back into the task DataFrame
        # for LLM report consumption.
        for node_id, metrics in schedule_cpm_metrics.items():
            mask = df_tasks['task_id_int'] == node_id if 'task_id_int' in df_tasks.columns else df_tasks['task_id'] == node_id
            if mask.any():
                df_tasks.loc[mask, 'graph_total_float_days'] = metrics['total_float'] / 8.0
                df_tasks.loc[mask, 'graph_early_start'] = metrics['early_start']
                df_tasks.loc[mask, 'graph_early_finish'] = metrics['early_finish']
                df_tasks.loc[mask, 'graph_late_start'] = metrics['late_start']
                df_tasks.loc[mask, 'graph_late_finish'] = metrics['late_finish']
                
        # Ensure our total float days falls back to computed values
        if 'graph_total_float_days' in df_tasks.columns:
            df_tasks['total_float_days'] = df_tasks['graph_total_float_days'].fillna(df_tasks['total_float_days'])
            
        logger.info(f"CPM Network Graph complete. Identified {len(critical_path_ids)} critical activities out of {len(G.nodes)} nodes.")
        
        # Layer 4: GenAI/LLM Tier (Gemini Engine)
        executive_report = ExecutiveReportingEngine.generate_mitigation_report(
            df_tasks=df_tasks,
            critical_path_ids=critical_path_ids,
            api_key=self.gemini_api_key
        )
        
        logger.info("Pipeline processing complete. Executive report generated successfully.")
        
        return {
            "tasks_df": df_tasks,
            "relations_df": df_relations,
            "graph": G,
            "critical_path_ids": critical_path_ids,
            "cpm_metrics": schedule_cpm_metrics,
            "report": executive_report
        }
