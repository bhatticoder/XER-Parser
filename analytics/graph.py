import logging
import networkx as nx
import pandas as pd
from typing import Dict, List, Set, Tuple, Any

logger = logging.getLogger("TitanByte.Graph")

class ScheduleGraphEngine:
    """NetworkX Directed Graph Engine implementing the Critical Path Method (CPM) and longest path calculations."""

    @staticmethod
    def build_graph(df_tasks: pd.DataFrame, df_relations: pd.DataFrame) -> nx.DiGraph:
        """Constructs a Directed Graph from the conformed tasks and relations.
        
        Args:
            df_tasks: DataFrame of conformed tasks.
            df_relations: DataFrame of conformed relationships.
            
        Returns:
            A NetworkX DiGraph representing the project network.
        """
        G = nx.DiGraph()
        
        # 1. Filter out summary/WBS level tasks if they are just parents, focusing on leaf actions.
        # But we keep summary tasks if they are the only tasks, or just let users keep them.
        # Standard schedule calculations are performed on physical leaf activities.
        leaf_tasks = df_tasks[df_tasks['is_summary'] == False]
        if leaf_tasks.empty:
            leaf_tasks = df_tasks  # fallback if no summary/leaf flag is set
            
        # Add task nodes with characteristics
        for _, row in leaf_tasks.iterrows():
            tid = int(row['task_id'])
            G.add_node(
                tid,
                task_code=str(row['task_code']),
                task_name=str(row['task_name']),
                duration=float(row['planned_dur_hr_cnt']),
                variance_days=float(row['variance_days']),
                pct_complete=float(row['pct_complete']),
                status_code=str(row['status_code'])
            )
            
        # Add edges (dependencies) from relationships
        valid_nodes = set(G.nodes())
        for _, row in df_relations.iterrows():
            src = int(row['pred_task_id'])
            dst = int(row['task_id'])
            lag = float(row['lag_hr_cnt'])
            pred_type = str(row['pred_type'])
            
            # Draw edges only between valid activities in the network
            if src in valid_nodes and dst in valid_nodes:
                # Store lag weight and type
                G.add_edge(src, dst, weight=lag, lag=lag, type=pred_type)
            else:
                logger.debug(f"Skipping relation {src} -> {dst} because one or both nodes are missing.")
                
        return G

    @classmethod
    def calculate_cpm(cls, G: nx.DiGraph, float_tolerance: float = 0.01) -> Tuple[Dict[int, Dict[str, float]], List[int]]:
        """Calculates Early/Late Start/Finish times, Total Float, and retrieves the Critical Path.
        
        Args:
            G: The NetworkX Project DiGraph.
            float_tolerance: Tolerance in hours to classify a task as critical (default 0.01).
            
        Returns:
            A tuple containing: (dictionary of schedule times per node, list of critical path task IDs)
        """
        # Validate cycle presence (schedules must be DAGs)
        if not nx.is_directed_acyclic_graph(G):
            cycles = list(nx.simple_cycles(G))
            logger.error(f"Schedule network is not acyclic! Cycles found: {cycles}")
            raise ValueError(f"Cycle detected in project schedule network: {cycles}")
            
        # Get topological order
        topo_order = list(nx.topological_sort(G))
        
        # 1. Forward Pass (Early Start/Finish)
        early_start: Dict[int, float] = {}
        early_finish: Dict[int, float] = {}
        
        for node in topo_order:
            duration = G.nodes[node]['duration']
            preds = list(G.predecessors(node))
            if not preds:
                es = 0.0
            else:
                # Target ES is the maximum of (predecessor EF + lag)
                es = max(early_finish[p] + G.edges[p, node]['lag'] for p in preds)
                
            early_start[node] = es
            early_finish[node] = es + duration
            
        # 2. Backward Pass (Late Start/Finish)
        late_start: Dict[int, float] = {}
        late_finish: Dict[int, float] = {}
        
        # Project max duration is the boundary finish date
        project_finish = max(early_finish.values()) if early_finish else 0.0
        
        for node in reversed(topo_order):
            duration = G.nodes[node]['duration']
            succs = list(G.successors(node))
            if not succs:
                lf = project_finish
            else:
                # Target LF is the minimum of (successor LS - lag)
                lf = min(late_finish[s] - duration - G.edges[node, s]['lag'] for s in succs)
                
            late_finish[node] = lf
            late_start[node] = lf - duration
            
        # 3. Calculate Float & Identify Critical Path
        schedule_metrics: Dict[int, Dict[str, float]] = {}
        critical_path_nodes: List[int] = []
        
        # Establish edges with absolute weights: predecessor duration + lag
        # useful for verify-checking the longest path in NetworkX
        for (u, v) in G.edges():
            pred_dur = G.nodes[u]['duration']
            lag = G.edges[u, v]['lag']
            # Longest path works by maximizing path weights.
            G.edges[u, v]['longest_path_weight'] = pred_dur + lag
            
        for node in G.nodes():
            es = early_start[node]
            ef = early_finish[node]
            ls = late_start[node]
            lf = late_finish[node]
            
            # total float = LS - ES or LF - EF
            total_float = ls - es
            
            schedule_metrics[node] = {
                "early_start": es,
                "early_finish": ef,
                "late_start": ls,
                "late_finish": lf,
                "total_float": total_float,
            }
            
            if total_float <= float_tolerance:
                critical_path_nodes.append(node)
                
        # Alternative verification: NetworkX longest path (sequences of tasks)
        # We can extract the maximum path length Task IDs.
        # But wait! If we have virtual entry/sinks, we can run dag_longest_path.
        # Let's compute it if we have weights.
        try:
            # dag_longest_path returns the sequence of nodes that has the maximum weight sum.
            longest_node_sequence = nx.dag_longest_path(G, weight='longest_path_weight')
        except Exception as e:
            logger.warning(f"Could not compute topological longest path: {str(e)}")
            longest_node_sequence = []
            
        # Return the metrics and nodes
        return schedule_metrics, critical_path_nodes
