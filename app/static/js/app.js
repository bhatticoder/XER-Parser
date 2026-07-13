// ========== DOM Refs ==========
const uploadArea = document.getElementById('upload-area');
const fileInput = document.getElementById('file-input');
const browseLink = document.getElementById('browse-link');
const fileQueue = document.getElementById('file-queue');
const queueList = document.getElementById('queue-list');
const queueCount = document.getElementById('queue-count');
const clearQueueBtn = document.getElementById('clear-queue-btn');
const analyzeBtn = document.getElementById('analyze-btn');
const progressWrap = document.getElementById('upload-progress');
const progressBar = document.getElementById('progress-bar');
const progressLabel = document.getElementById('progress-label');
const progressPct = document.getElementById('progress-pct');
const pipelineStatus = document.getElementById('pipeline-status');
const resultsSection = document.getElementById('results-section');
const metricsGrid = document.getElementById('metrics-grid');
const delayedCard = document.getElementById('delayed-card');
const delayedTbody = document.getElementById('delayed-tbody');
const reportCard = document.getElementById('report-card');
const reportContent = document.getElementById('report-content');
const reportSource = document.getElementById('report-source');
const reportSavedInfo = document.getElementById('report-saved-info');
const copyReportBtn = document.getElementById('copy-report-btn');
const errorResults = document.getElementById('error-results');
const apiKeyInput = document.getElementById('api-key-input');
const toggleKeyBtn = document.getElementById('toggle-key-btn');

// Pipeline step elements
const steps = ['step-upload', 'step-process', 'step-graph', 'step-report'];
const connectors = document.querySelectorAll('.step-connector');
const statusItems = ['status-ingest', 'status-pandas', 'status-graph', 'status-llm'];

let selectedFiles = [];

// ========== Upload Area Events ==========
browseLink.addEventListener('click', (e) => { e.preventDefault(); fileInput.click(); });
uploadArea.addEventListener('click', (e) => { if (e.target === browseLink) return; fileInput.click(); });

uploadArea.addEventListener('dragover', (e) => { e.preventDefault(); uploadArea.classList.add('drag-over'); });
uploadArea.addEventListener('dragleave', () => { uploadArea.classList.remove('drag-over'); });

uploadArea.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadArea.classList.remove('drag-over');
    const supported = ['.xer','.mpp','.mpt','.mpx','.xml','.pmxml','.pp','.ppx','.planner','.gan','.gnt','.cdpx','.cdpz','.sdef','.fts'];
    const files = Array.from(e.dataTransfer.files).filter(f => {
        const ext = '.' + f.name.split('.').pop().toLowerCase();
        return supported.includes(ext);
    });
    if (files.length === 0) {
        showToast('Unsupported file format', 'error');
        return;
    }
    addFiles(files);
});

fileInput.addEventListener('change', () => {
    const files = Array.from(fileInput.files);
    if (files.length > 0) addFiles(files);
    fileInput.value = '';
});

clearQueueBtn.addEventListener('click', clearQueue);
analyzeBtn.addEventListener('click', runAnalytics);

// Toggle API key visibility
toggleKeyBtn.addEventListener('click', () => {
    apiKeyInput.type = apiKeyInput.type === 'password' ? 'text' : 'password';
});

// Copy report
copyReportBtn.addEventListener('click', () => {
    const text = reportContent.innerText;
    navigator.clipboard.writeText(text).then(() => {
        showToast('Report copied to clipboard', 'success');
    });
});

// ========== File Queue ==========
function addFiles(files) {
    files.forEach(f => {
        if (!selectedFiles.some(sf => sf.name === f.name && sf.size === f.size)) {
            selectedFiles.push(f);
        }
    });
    renderQueue();
}

function removeFile(index) {
    selectedFiles.splice(index, 1);
    renderQueue();
}

function clearQueue() {
    selectedFiles = [];
    renderQueue();
}

function renderQueue() {
    if (selectedFiles.length === 0) {
        fileQueue.style.display = 'none';
        return;
    }
    fileQueue.style.display = 'block';
    queueCount.textContent = `${selectedFiles.length} file${selectedFiles.length > 1 ? 's' : ''} selected`;

    queueList.innerHTML = selectedFiles.map((f, i) => `
        <li class="queue-item">
            <div class="queue-file-info">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="file-icon">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                    <polyline points="14 2 14 8 20 8"/>
                </svg>
                <span class="queue-filename">${f.name}</span>
                <span class="queue-filesize">${formatSize(f.size)}</span>
            </div>
            <button class="btn-remove" onclick="removeFile(${i})" title="Remove">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <line x1="18" y1="6" x2="6" y2="18"/>
                    <line x1="6" y1="6" x2="18" y2="18"/>
                </svg>
            </button>
        </li>
    `).join('');
}

function formatSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / 1048576).toFixed(1) + ' MB';
}

// ========== Pipeline Visualization ==========
function resetPipeline() {
    steps.forEach(id => {
        const el = document.getElementById(id);
        el.classList.remove('active', 'done');
    });
    connectors.forEach(c => c.classList.remove('active'));
    statusItems.forEach(id => {
        const el = document.getElementById(id);
        if (el) { el.classList.remove('active', 'done'); }
    });
}

function setStepActive(index) {
    // Mark previous steps as done
    for (let i = 0; i < index; i++) {
        document.getElementById(steps[i]).classList.remove('active');
        document.getElementById(steps[i]).classList.add('done');
        if (connectors[i]) connectors[i].classList.add('active');
        const si = document.getElementById(statusItems[i]);
        if (si) { si.classList.remove('active'); si.classList.add('done'); }
    }
    // Mark current step as active
    const currentStep = document.getElementById(steps[index]);
    currentStep.classList.remove('done');
    currentStep.classList.add('active');
    const currentStatus = document.getElementById(statusItems[index]);
    if (currentStatus) { currentStatus.classList.remove('done'); currentStatus.classList.add('active'); }
}

function setAllStepsDone() {
    steps.forEach(id => {
        const el = document.getElementById(id);
        el.classList.remove('active');
        el.classList.add('done');
    });
    connectors.forEach(c => c.classList.add('active'));
    statusItems.forEach(id => {
        const el = document.getElementById(id);
        if (el) { el.classList.remove('active'); el.classList.add('done'); }
    });
}

// ========== Run Analytics ==========
async function runAnalytics() {
    if (selectedFiles.length === 0) return;

    // Reset UI
    resultsSection.style.display = 'none';
    metricsGrid.style.display = 'none';
    delayedCard.style.display = 'none';
    reportCard.style.display = 'none';
    errorResults.innerHTML = '';
    resetPipeline();

    // Show progress
    progressWrap.style.display = 'block';
    pipelineStatus.style.display = 'grid';
    progressBar.style.width = '0%';
    progressLabel.textContent = 'Uploading files...';
    progressPct.textContent = '0%';
    analyzeBtn.disabled = true;
    analyzeBtn.innerHTML = `
        <svg class="btn-icon spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 12a9 9 0 1 1-6.219-8.56"/>
        </svg>
        Processing Pipeline...
    `;

    // Simulate pipeline steps animation
    const stepTimers = [];
    const stepLabels = ['Ingesting via MPXJ...', 'Processing with Pandas...', 'Building CPM Graph...', 'Generating AI Report...'];
    const stepPcts = [15, 35, 55, 75];

    for (let i = 0; i < 4; i++) {
        stepTimers.push(setTimeout(() => {
            setStepActive(i);
            progressLabel.textContent = stepLabels[i];
            progressBar.style.width = stepPcts[i] + '%';
            progressPct.textContent = stepPcts[i] + '%';
        }, i * 2500));
    }

    // Build form data
    const fd = new FormData();
    selectedFiles.forEach(f => fd.append('files', f));
    const apiKey = apiKeyInput.value.trim();
    if (apiKey) fd.append('api_key', apiKey);

    try {
        const res = await fetch('/analyze', { method: 'POST', body: fd });
        const data = await res.json();

        // Clear step timers
        stepTimers.forEach(t => clearTimeout(t));

        if (data.error) {
            progressWrap.style.display = 'none';
            pipelineStatus.style.display = 'none';
            showToast(data.error, 'error');
            resetBtn();
            return;
        }

        // Complete progress
        setAllStepsDone();
        progressBar.style.width = '100%';
        progressPct.textContent = '100%';
        progressLabel.textContent = 'Pipeline complete!';

        setTimeout(() => {
            progressWrap.style.display = 'none';
            pipelineStatus.style.display = 'none';
            showResults(data);
        }, 800);

    } catch (err) {
        stepTimers.forEach(t => clearTimeout(t));
        progressWrap.style.display = 'none';
        pipelineStatus.style.display = 'none';
        showToast('Pipeline failed: ' + err.message, 'error');
    }

    resetBtn();
}

function resetBtn() {
    analyzeBtn.disabled = false;
    analyzeBtn.innerHTML = `
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="btn-icon">
            <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
        </svg>
        Run Full Analytics Pipeline
    `;
}

// ========== Show Results ==========
function showResults(data) {
    resultsSection.style.display = 'block';

    // Show errors
    const errors = data.results.filter(r => !r.success);
    if (errors.length > 0) {
        errorResults.innerHTML = errors.map(r => `
            <div class="error-item">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                    <circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/>
                </svg>
                <div>
                    <strong>${r.filename}</strong><br>
                    <span>${r.error}</span>
                </div>
            </div>
        `).join('');
    }

    // Show first successful result metrics
    const success = data.results.find(r => r.success);
    if (!success) return;

    const m = success.metrics;

    // Animate metrics
    metricsGrid.style.display = 'grid';
    animateCounter('m-tasks', m.total_tasks);
    animateCounter('m-relations', m.total_relations);
    animateCounter('m-critical', m.critical_path);
    animateCounter('m-delayed', m.delayed_tasks);
    animateCounter('m-nodes', m.graph_nodes);
    animateCounter('m-edges', m.graph_edges);

    // Delayed tasks table
    if (success.delayed_table && success.delayed_table.length > 0) {
        delayedCard.style.display = 'block';
        delayedTbody.innerHTML = success.delayed_table.map(t => `
            <tr>
                <td><code>${t.code}</code></td>
                <td>${t.name}</td>
                <td>${t.duration}</td>
                <td class="val-positive">${t.variance > 0 ? '+' : ''}${t.variance}</td>
                <td class="${t.float < 0 ? 'val-negative' : ''}">${t.float}</td>
            </tr>
        `).join('');
    }

    // Report
    if (success.report) {
        reportCard.style.display = 'block';
        reportContent.textContent = success.report;
        reportSource.textContent = success.report_file ? `Saved to: ${success.report_file}` : '';
        reportSavedInfo.textContent = success.report_path ? `📄 ${success.report_path}` : '';
    }

    clearQueue();
    showToast(`Pipeline complete! ${data.success_count} file(s) analyzed.`, 'success');
    metricsGrid.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// ========== Animate Counter ==========
function animateCounter(id, target) {
    const el = document.getElementById(id);
    if (!el) return;
    const duration = 1200;
    const start = performance.now();
    const startVal = 0;

    function tick(now) {
        const elapsed = now - start;
        const progress = Math.min(elapsed / duration, 1);
        const eased = 1 - Math.pow(1 - progress, 3);
        const current = Math.round(startVal + (target - startVal) * eased);
        el.textContent = current.toLocaleString();
        if (progress < 1) requestAnimationFrame(tick);
    }
    requestAnimationFrame(tick);
}

// ========== Toast ==========
function showToast(msg, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = msg;
    document.body.appendChild(toast);
    requestAnimationFrame(() => toast.classList.add('toast-visible'));
    setTimeout(() => {
        toast.classList.remove('toast-visible');
        setTimeout(() => toast.remove(), 300);
    }, 3500);
}

// ===== Spinner animation =====
const style = document.createElement('style');
style.textContent = `@keyframes spin { to { transform: rotate(360deg); } } .spin { animation: spin 1s linear infinite; }`;
document.head.appendChild(style);
