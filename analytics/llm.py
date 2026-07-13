import os
import json
import logging
from typing import List, Dict, Any, Optional
import pandas as pd
from groq import Groq

logger = logging.getLogger("XER.LLM")

# Load .env file from project root
from pathlib import Path
try:
    _current = Path(__file__).resolve().parent
    for _ in range(3):
        _dotenv = _current / ".env"
        if _dotenv.exists():
            with open(_dotenv, "r", encoding="utf-8") as _f:
                for _line in _f:
                    _line = _line.strip()
                    if not _line or _line.startswith("#"):
                        continue
                    if "=" in _line:
                        _k, _v = _line.split("=", 1)
                        os.environ[_k.strip()] = _v.strip().strip('"').strip("'")
            break
        _current = _current.parent
except Exception:
    pass


class ExecutiveReportingEngine:
    """GenAI Tier wrapping Groq API (Llama/Mixtral) to produce executive schedule mitigation roadmaps."""

    # Models to try in priority order (Groq-hosted)
    MODELS = [
        "llama-3.3-70b-versatile",
        "llama-3.1-70b-versatile",
        "llama-3.1-8b-instant",
        "mixtral-8x7b-32768",
        "gemma2-9b-it",
    ]

    @classmethod
    def generate_mitigation_report(
        cls,
        df_tasks: pd.DataFrame, 
        critical_path_ids: List[int],
        api_key: Optional[str] = None
    ) -> str:
        """Filters schedule down to critical delayed tasks, builds prompt, and runs Groq API analysis.
        
        Args:
            df_tasks: Processed Pandas DataFrame of tasks.
            critical_path_ids: List of task IDs identified as critical (Total Float <= tolerance).
            api_key: Optional Groq API key (defaults to GROQ_API_KEY env variable).
            
        Returns:
            A string containing the Markdown executive report.
        """
        # 1. Isolate the target token datasets
        critical_set = set(critical_path_ids)
        df_tasks['task_id_int'] = df_tasks['task_id'].astype(int)
        
        critical_tasks = df_tasks[
            (df_tasks['task_id_int'].isin(critical_set)) & 
            (df_tasks['variance_days'] > 0) &
            (df_tasks['is_summary'] == False) & 
            (df_tasks['status_code'] != "TK_Complete")
        ]
        
        columns_to_send = [
            'task_code', 'task_name', 'status_code', 
            'planned_dur_days', 'variance_days', 'total_float_days'
        ]
        available_cols = [col for col in columns_to_send if col in df_tasks.columns]
        df_llm_payload = critical_tasks[available_cols]
        
        payload_json = df_llm_payload.to_json(orient='records', indent=2)
        
        total_delayed_count = len(critical_tasks)
        total_project_tasks = len(df_tasks[df_tasks['is_summary'] == False])
        
        logger.info(f"Target token optimization: filtered down to {total_delayed_count} critical delayed tasks out of {total_project_tasks} total tasks.")
        
        if total_delayed_count == 0:
            logger.info("No critical delayed tasks identified. Generating a perfect schedule report.")
            payload_json = "[] (All critical path tasks are on schedule with 0 or negative variance)"
            
        # 2. System Prompt Engineering
        system_instruction = (
            "You are Analytics AI, a Principal Construction Controller and System Architect. "
            "You specialize in forensic schedule analysis, project risk mitigation, and CPM (Critical Path Method). "
            "Your output must be structured, highly professional, executive-ready, and entirely deterministic based on the provided metrics. "
            "Do NOT invent dates or durations. Focus strictly on analyzing schedule slippage, bottleneck tasks, and delivering high-fidelity recovery roadmaps. "
            "Format your output in clean GitHub Flavored Markdown. No conversational preamble. Begin directly with the report title."
        )
        
        # 3. User Prompt
        prompt = f"""### Project Schedule Risk & Delay Mitigation Report
Ingested Schedule Performance Summary:
- Total Non-Summary Activities: {total_project_tasks}
- Number of Critical path Delay Bottlenecks (Critical Path AND Delay Variance > 0): {total_delayed_count}

Target Slice of Critical Delayed Tasks (JSON):
```json
{payload_json}
```

Instructions for Executive Roadmap Analysis:
1. **Schedule Forensic Summary**: Summarize the critical bottlenecks. What percentage of the critical path is sliding, and which tasks present the highest risk?
2. **Deterministic Impact Assessment**: Calculate the cumulative delay threat based on the variance statistics provided. Highlight key activities causing immediate push-outs.
3. **Strategic Recovery & Mitigation Actions**: For each delayed task in the JSON payload, prescribe explicit, industry-standard mitigation strategies. This includes crashed schedule options, fast-tracking opportunities, and resource reallocation techniques.
4. **Resilience Plan**: Detail concrete recommendations for structural checkpoints, resource re-leveling, or escalation protocols to maintain structural milestone constraints.

Ensure the final report is compiled in professional, clean GitHub Flavored Markdown. No conversational preamble. Begin directly with the report title."""

        # 4. Get Groq API Key
        env_key = api_key or os.environ.get("GROQ_API_KEY")
        if not env_key:
            logger.warning("GROQ_API_KEY not found. Returning local deterministic report.")
            return cls._generate_offline_mock_report(critical_tasks, total_project_tasks)
            
        # 5. Call Groq API with model fallback chain
        last_error = None
        
        for model_name in cls.MODELS:
            try:
                logger.info(f"Attempting report generation with Groq model: {model_name}")
                client = Groq(api_key=env_key)
                
                chat_completion = client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": system_instruction},
                        {"role": "user", "content": prompt}
                    ],
                    model=model_name,
                    temperature=0.2,
                    top_p=0.95,
                    max_tokens=4096,
                )
                
                response_text = chat_completion.choices[0].message.content
                if response_text and response_text.strip():
                    logger.info(f"Successfully generated report using Groq/{model_name}")
                    return response_text.strip()
                else:
                    raise ValueError(f"Empty response from Groq/{model_name}")
                    
            except Exception as e:
                logger.warning(f"Groq model {model_name} failed: {str(e)}")
                last_error = e
                continue
                
        # All models failed — fallback to offline
        logger.warning(f"All Groq models failed. Falling back to offline report. Last error: {str(last_error)}")
        return cls._generate_offline_mock_report(critical_tasks, total_project_tasks)

    @classmethod
    def _generate_offline_mock_report(cls, df_critical_delayed: pd.DataFrame, total_tasks: int) -> str:
        """Deterministic offline backup report generator."""
        report = []
        report.append("# XER ANALYTICS - SCHEDULE MITIGATION ROADMAP (OFFLINE MODE)")
        report.append("\n> [!NOTE]\n> Generating local deterministic analysis report (API unavailable or quota exceeded).\n")
        
        report.append(f"### Forensic Performance Summary")
        report.append(f"- **Total Project Tasks (Leaf Level)**: {total_tasks}")
        report.append(f"- **Critical Delayed Activities**: {len(df_critical_delayed)}")
        slippage = (len(df_critical_delayed) / total_tasks * 100) if total_tasks > 0 else 0.0
        report.append(f"- **Critical Path Slippage Ratio**: {slippage:.1f}% of network currently late")
        
        report.append("\n### Identified Schedule Bottlenecks")
        if df_critical_delayed.empty:
            report.append("\nNo activities are currently on the critical path with positive delay variance.")
        else:
            headers = ["Activity Code", "Activity Name", "Planned Duration (Days)", "Delay (Days)", "Total Float"]
            report.append("| " + " | ".join(headers) + " |")
            report.append("|" + "---|"*len(headers) + "|")
            for _, row in df_critical_delayed.iterrows():
                report.append(f"| {row['task_code']} | {row['task_name']} | {row['planned_dur_days']:.1f} | {row['variance_days']:.1f} | {row['total_float_days']:.1f} |")
        
        report.append("\n### Deterministic Recovery Actions (Prescribed)")
        for _, row in df_critical_delayed.iterrows():
            code = row['task_code']
            val = row['variance_days']
            report.append(f"\n#### [{code}] {row['task_name']}")
            report.append(f"- **Metrics**: Current delay variance is **{val:.1f} days** on the critical path.")
            report.append("- **Mitigation Recovery Options**:")
            report.append("  1. **Fast-Tracking**: Overlap with successors where relationship is Finish-to-Start (FS), converting to Start-to-Start (SS) with lags if layout properties allow.")
            report.append("  2. **Crashing**: Double shifts on labor crews to reduce remaining duration by working double capacity.")
            report.append("  3. **Resource Shifting**: Reallocate non-critical labor/materials from tasks with high Total Float to restore schedule sequence.")
            
        return "\n".join(report)
