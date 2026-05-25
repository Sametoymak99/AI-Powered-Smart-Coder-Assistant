let socket;
let sysChart;
const maxChartPoints = 20;
const cpuData = [];
const ramData = [];
const chartLabels = [];

for (let i = 0; i < maxChartPoints; i++) {
    cpuData.push(0);
    ramData.push(0);
    chartLabels.push("");
}

function initWebSocket() {
    const statusBadge = document.getElementById("conn-status");
    
    // Connect to local WebSocket server running in main.py
    socket = new WebSocket("ws://localhost:8765");

    socket.onopen = () => {
        statusBadge.innerText = "BAĞLANDI";
        statusBadge.className = "status-badge connected";
        addLog("NEXUS WebSocket bağlantısı kuruldu.", "success");
        // Request initial plugins
        socket.send(JSON.stringify({ type: "get_plugins" }));
    };

    socket.onclose = () => {
        statusBadge.innerText = "BAĞLANTI KESİLDİ";
        statusBadge.className = "status-badge disconnected";
        addLog("Bağlantı koptu. 5 saniye sonra tekrar denenecek...", "danger");
        setTimeout(initWebSocket, 5000);
    };

    socket.onerror = (err) => {
        console.error("WS error: ", err);
    };

    socket.onmessage = (event) => {
        try {
            const msg = JSON.parse(event.data);
            handleMessage(msg);
        } catch (e) {
            console.error("Failed parsing message: ", e);
        }
    };
}

function handleMessage(msg) {
    switch (msg.type) {
        case "system_status":
            updateSystemStatus(msg.data);
            break;
        case "agent_status":
            updateAgentStatus(msg.data);
            break;
        case "ai_log":
            addLog(msg.data.message, msg.data.level);
            break;
        case "plugins_list":
            updatePluginsList(msg.data);
            break;
        case "memory_update":
            updateMemory(msg.data);
            break;
        case "security_audit":
            updateAudit(msg.data);
            break;
        case "brain_status":
            updateBrainStatus(msg.data);
            break;
    }
}

function updateSystemStatus(data) {
    document.getElementById("cpu-val").innerText = `${data.cpu}%`;
    document.getElementById("cpu-bar").style.width = `${data.cpu}%`;
    
    document.getElementById("ram-val").innerText = `${data.ram}%`;
    document.getElementById("ram-bar").style.width = `${data.ram}%`;
    
    document.getElementById("disk-val").innerText = `${data.disk}%`;
    document.getElementById("disk-bar").style.width = `${data.disk}%`;

    // Update Chart
    cpuData.shift();
    cpuData.push(data.cpu);
    ramData.shift();
    ramData.push(data.ram);
    
    sysChart.update();
}

function updateAgentStatus(agents) {
    const container = document.getElementById("agents-container");
    container.innerHTML = "";
    
    for (const [name, status] of Object.entries(agents)) {
        const item = document.createElement("div");
        item.className = "agent-item";
        
        const dot = document.createElement("span");
        dot.className = `status-dot ${status.running ? 'active' : 'inactive'}`;
        
        const nameSpan = document.createElement("span");
        nameSpan.className = "agent-name";
        nameSpan.innerText = `${name} Agent`;
        
        const lastEv = document.createElement("span");
        lastEv.className = "agent-event";
        const evType = status.last_event ? status.last_event.event_type : "Boşta";
        lastEv.innerText = evType;
        
        item.appendChild(dot);
        item.appendChild(nameSpan);
        item.appendChild(lastEv);
        container.appendChild(item);
    }
}

function updatePluginsList(plugins) {
    const container = document.getElementById("plugins-container");
    container.innerHTML = "";
    
    plugins.forEach(p => {
        const item = document.createElement("div");
        item.className = "plugin-item";
        
        const nameSpan = document.createElement("span");
        nameSpan.className = "plugin-name";
        nameSpan.innerText = `${p.name} v${p.version}`;
        
        const label = document.createElement("label");
        label.className = "switch";
        
        const input = document.createElement("input");
        input.type = "checkbox";
        input.checked = p.enabled;
        input.onchange = () => togglePlugin(p.name, input.checked);
        
        const slider = document.createElement("span");
        slider.className = "slider";
        
        label.appendChild(input);
        label.appendChild(slider);
        
        item.appendChild(nameSpan);
        item.appendChild(label);
        container.appendChild(item);
    });
}

function togglePlugin(name, enabled) {
    socket.send(JSON.stringify({
        type: "toggle_plugin",
        data: { name: name, enabled: enabled }
    }));
}

function updateBrainStatus(data) {
    document.getElementById("model-provider").innerText = data.provider;
    document.getElementById("model-name").innerText = data.model;
    document.getElementById("personality-mode").innerText = data.personality;
    document.getElementById("improvement-score").innerText = `${data.self_improvement}/100`;
}

function updateMemory(memoryText) {
    const container = document.getElementById("memory-container");
    container.innerHTML = "";
    
    const lines = memoryText.split("\n");
    lines.forEach(line => {
        if (line.trim()) {
            const div = document.createElement("div");
            div.className = "log-entry info";
            div.innerText = line;
            container.appendChild(div);
        }
    });
}

function updateAudit(auditLogs) {
    const container = document.getElementById("audit-container");
    container.innerHTML = "";
    
    auditLogs.forEach(log => {
        const div = document.createElement("div");
        const risk = log.risk_level === "high" ? "danger" : (log.risk_level === "medium" ? "warning" : "info");
        div.className = `log-entry ${risk}`;
        div.innerText = `[${log.tool}] ${log.action} -> ${log.result}`;
        container.appendChild(div);
    });
}

function addLog(message, level = "info") {
    const container = document.getElementById("log-stream-container");
    const entry = document.createElement("div");
    entry.className = `log-entry ${level}`;
    
    const now = new Date();
    const timeStr = now.toTimeString().split(' ')[0];
    
    entry.innerText = `[${timeStr}] ${message}`;
    container.insertBefore(entry, container.firstChild);
    
    if (container.childNodes.length > 100) {
        container.removeChild(container.lastChild);
    }
}

function sendCommand(cmd) {
    socket.send(JSON.stringify({
        type: "quick_command",
        data: { command: cmd }
    }));
    addLog(`Hızlı komut gönderildi: ${cmd}`, "info");
}

function initClock() {
    setInterval(() => {
        const now = new Date();
        document.getElementById("clock").innerText = now.toTimeString().split(' ')[0];
    }, 1000);
}

function initChart() {
    const ctx = document.getElementById('sys-chart').getContext('2d');
    sysChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: chartLabels,
            datasets: [
                {
                    label: 'CPU',
                    data: cpuData,
                    borderColor: '#00d4ff',
                    borderWidth: 1.5,
                    pointRadius: 0,
                    fill: false,
                    tension: 0.4
                },
                {
                    label: 'RAM',
                    data: ramData,
                    borderColor: '#7c3aed',
                    borderWidth: 1.5,
                    pointRadius: 0,
                    fill: false,
                    tension: 0.4
                }
            ]
        },
        options: {
            responsive: true,
            plugins: { legend: { display: false } },
            scales: {
                x: { display: false },
                y: { min: 0, max: 100, ticks: { color: '#6272a4', font: { size: 10 } } }
            }
        }
    });
}

window.onload = () => {
    initClock();
    initChart();
    initWebSocket();
    
    document.getElementById("memory-search").oninput = (e) => {
        socket.send(JSON.stringify({
            type: "search_memory",
            data: { query: e.target.value }
        }));
    };
};
