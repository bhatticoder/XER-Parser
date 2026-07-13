from flask import Flask, render_template, request, jsonify
import os
import sys
import json
import gc
import time
import logging
from werkzeug.utils import secure_filename

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("XER.WebApp")

def safe_remove(file_path: str, max_retries: int = 5, delay: float = 0.2):
    """Safely remove a file, retrying and triggering GC if locked."""
    if not os.path.exists(file_path):
        return
    for i in range(max_retries):
        try:
            os.remove(file_path)
            return
        except PermissionError:
            gc.collect()
            try:
                import jpype
                if jpype.isJVMStarted():
                    jpype.JClass('java.lang.System').gc()
            except Exception:
                pass
            time.sleep(delay)
    os.remove(file_path)


# Add parent directory to path so analytics & xerparser can be imported
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from xerparser.src.parser import file_reader, parser, is_supported_file
from xerparser.src.formatter import XerFormatter
from analytics import TitanByteOrchestrator

app = Flask(__name__, template_folder='templates', static_folder='static')
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
app.config['DEFAULT_OUTPUT'] = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'output')
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['DEFAULT_OUTPUT'], exist_ok=True)

ACCEPTED_EXTENSIONS = '.xer,.mpp,.mpt,.mpx,.xml,.pmxml,.pp,.ppx,.planner,.gan,.gnt,.cdpx,.cdpz,.sdef,.fts'


@app.route('/')
def index():
    return render_template('index.html',
                           default_output=app.config['DEFAULT_OUTPUT'].replace('\\', '/'),
                           accepted_extensions=ACCEPTED_EXTENSIONS)


@app.route('/upload', methods=['POST'])
def upload_files():
    """Legacy upload endpoint — parse only."""
    files = request.files.getlist('files')
    output_dir = request.form.get('output_dir', '').strip()

    if output_dir:
        output_dir = os.path.normpath(output_dir)
    else:
        output_dir = app.config['DEFAULT_OUTPUT']

    try:
        os.makedirs(output_dir, exist_ok=True)
    except Exception as e:
        return jsonify({'error': f'Cannot create output directory: {str(e)}'}), 400

    if not files or all(f.filename == '' for f in files):
        return jsonify({'error': 'No files uploaded'}), 400

    results = []
    formatter = XerFormatter()

    for f in files:
        fname = f.filename
        if not fname:
            continue

        if not is_supported_file(fname):
            results.append({'filename': fname, 'success': False, 'error': 'Unsupported file format'})
            continue

        safe_name = secure_filename(fname)
        fpath = os.path.join(app.config['UPLOAD_FOLDER'], safe_name)
        f.save(fpath)

        try:
            fpath_abs = os.path.abspath(fpath)
            file_path = file_reader(fpath_abs)
            tables = parser(file_path)

            formatted_text = formatter.format_xer_data(tables)

            base_name = os.path.splitext(safe_name)[0]
            output_name = f"{base_name}_parsed.txt"
            output_path = os.path.join(output_dir, output_name)

            with open(output_path, 'w', encoding='utf-8') as out_f:
                out_f.write(formatted_text)

            table_count = len(tables)
            record_count = sum(len(v) for v in tables.values())

            results.append({
                'filename': fname,
                'success': True,
                'output_file': output_name,
                'output_path': os.path.abspath(output_path),
                'tables': table_count,
                'records': record_count
            })
        except Exception as e:
            results.append({'filename': fname, 'success': False, 'error': str(e)})
        finally:
            if os.path.exists(fpath):
                safe_remove(fpath)

    success_count = sum(1 for r in results if r.get('success'))
    return jsonify({
        'results': results,
        'total': len(results),
        'success_count': success_count,
        'output_folder': os.path.abspath(output_dir)
    })


@app.route('/analyze', methods=['POST'])
def analyze_files():
    """Full analytics pipeline endpoint: Ingestion → Pandas → Graph CPM → LLM Report."""
    files = request.files.getlist('files')

    if not files or all(f.filename == '' for f in files):
        return jsonify({'error': 'No files uploaded'}), 400

    # Get API key from request or environment
    api_key = request.form.get('api_key', '').strip() or None

    output_dir = app.config['DEFAULT_OUTPUT']
    os.makedirs(output_dir, exist_ok=True)

    orchestrator = TitanByteOrchestrator(gemini_api_key=api_key)
    all_results = []

    for f in files:
        fname = f.filename
        if not fname:
            continue

        if not is_supported_file(fname):
            all_results.append({
                'filename': fname,
                'success': False,
                'error': 'Unsupported file format'
            })
            continue

        safe_name = secure_filename(fname)
        fpath = os.path.join(app.config['UPLOAD_FOLDER'], safe_name)
        f.save(fpath)

        try:
            fpath_abs = os.path.abspath(fpath)
            logger.info(f"Starting analytics pipeline for: {fname}")

            # Run the full 4-tier pipeline
            results = orchestrator.run_pipeline(fpath_abs)

            df_tasks = results['tasks_df']
            df_relations = results['relations_df']
            G = results['graph']
            critical_ids = results['critical_path_ids']
            report = results['report']

            # Compute summary metrics
            total_tasks = len(df_tasks[df_tasks['is_summary'] == False])
            total_relations = len(df_relations)
            graph_nodes = len(G.nodes)
            graph_edges = len(G.edges)
            critical_count = len(critical_ids)
            delayed = df_tasks[df_tasks['variance_days'] > 0]
            delayed_count = len(delayed)

            # Save report to output
            base_name = os.path.splitext(safe_name)[0]
            report_name = f"{base_name}_mitigation_report.md"
            report_path = os.path.join(output_dir, report_name)
            with open(report_path, 'w', encoding='utf-8') as rf:
                rf.write(report)

            # Build delayed tasks table for frontend
            delayed_table = []
            if not delayed.empty:
                for _, row in delayed.head(15).iterrows():
                    delayed_table.append({
                        'code': str(row.get('task_code', 'N/A')),
                        'name': str(row.get('task_name', 'N/A'))[:60],
                        'duration': round(float(row.get('planned_dur_days', 0)), 1),
                        'variance': round(float(row.get('variance_days', 0)), 1),
                        'float': round(float(row.get('total_float_days', 0)), 1),
                    })

            all_results.append({
                'filename': fname,
                'success': True,
                'metrics': {
                    'total_tasks': total_tasks,
                    'total_relations': total_relations,
                    'graph_nodes': graph_nodes,
                    'graph_edges': graph_edges,
                    'critical_path': critical_count,
                    'delayed_tasks': delayed_count,
                },
                'delayed_table': delayed_table,
                'report': report,
                'report_file': report_name,
                'report_path': os.path.abspath(report_path),
            })
            logger.info(f"Pipeline complete for {fname}: {critical_count} critical, {delayed_count} delayed")

        except Exception as e:
            logger.error(f"Pipeline failed for {fname}: {str(e)}")
            import traceback
            traceback.print_exc()
            all_results.append({
                'filename': fname,
                'success': False,
                'error': str(e)
            })
        finally:
            if os.path.exists(fpath):
                safe_remove(fpath)

    success_count = sum(1 for r in all_results if r.get('success'))
    return jsonify({
        'results': all_results,
        'total': len(all_results),
        'success_count': success_count,
        'output_folder': os.path.abspath(output_dir)
    })


if __name__ == '__main__':
    from waitress import serve
    print(" * Serving Flask app 'XER Analytics' using Waitress (Production WSGI)")
    print(" * Running on http://127.0.0.1:5000 (and all network interfaces)")
    serve(app, host='0.0.0.0', port=5000)
