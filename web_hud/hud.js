/* ==========================================================================
   F.R.I.D.A.Y. WEB HUD — CLIENT CONTROLLER MODULE
   ========================================================================== */

const API_BASE = window.location.origin;

let isConnected = false;
let lastLogs = [];
let speechRecognizer = null;
let isListening = false;

// DOM Elements
const connBadge = document.getElementById('conn-badge');
const connText = document.getElementById('conn-text');
const stateBadge = document.getElementById('state-badge');
const cpuGauge = document.getElementById('cpu-gauge');
const cpuVal = document.getElementById('cpu-val');
const ramGauge = document.getElementById('ram-gauge');
const ramVal = document.getElementById('ram-val');
const batGauge = document.getElementById('bat-gauge');
const batVal = document.getElementById('bat-val');
const terminalLog = document.getElementById('terminal-log');
const aiReactor = document.getElementById('ai-reactor');
const emotionLabel = document.getElementById('emotion-label');
const btnSentinel = document.getElementById('btn-sentinel');
const sentinelStatus = document.getElementById('sentinel-status');
const btnGesture = document.getElementById('btn-gesture');
const gestureStatus = document.getElementById('gesture-status');
const cmdInput = document.getElementById('cmd-input');
const btnMic = document.getElementById('btn-mic');
const cameraViewport = document.getElementById('camera-viewport');
const hudCameraFeed = document.getElementById('hud-camera-feed');
const aiCoreContainer = document.getElementById('ai-core-container');

// 1. POLL SYSTEM STATUS
async function pollStatus() {
    try {
        const response = await fetch(`${API_BASE}/api/status`);
        if (!response.ok) throw new Error("API unreachable");
        
        const data = await response.json();
        
        // Update connection state
        if (!isConnected) {
            isConnected = true;
            connBadge.className = "badge badge-connected";
            connText.innerText = "BAĞLANDI";
            addTerminalLine("SYS: F.R.I.D.A.Y. Protokol Köprüsü bağlandı.", "sys-line");
        }
        
        // Update state badge
        stateBadge.innerText = data.state;
        
        // Update Gauges (dasharray size is 251)
        updateCircularGauge(cpuGauge, cpuVal, data.sys_stats.cpu);
        updateCircularGauge(ramGauge, ramVal, data.sys_stats.ram);
        updateCircularGauge(batGauge, batVal, data.sys_stats.battery);
        
        // Update Empathy Core colors
        updateEmpathyCore(data.user_emotion);
        
        // Update Active Badges
        updateBadges(data.sentinel_active, data.gesture_active);
        
        // Update Terminal logs if updated
        updateTerminalLogs(data.recent_logs);
        
    } catch (error) {
        if (isConnected) {
            isConnected = false;
            connBadge.className = "badge badge-disconnected";
            connText.innerText = "BAĞLANTI KESİLDİ";
            addTerminalLine("ERR: Sunucu bağlantısı kesildi. Yeniden deneniyor...", "err-line");
        }
    }
}

// UPDATE CIRCULAR DASH METRICS
function updateCircularGauge(circleElement, textElement, value) {
    const val = Math.round(value || 0);
    textElement.innerText = `${val}%`;
    
    // Circle path calculations (251 dasharray limit)
    const offset = 251 - (251 * val) / 100;
    circleElement.style.strokeDashoffset = offset;
}

// UPDATE CORE THEMES
function updateEmpathyCore(emotion) {
    const activeEmotion = emotion ? emotion.toLowerCase() : 'calm';
    
    // Clear dynamic classes
    aiReactor.className = `emotion-${activeEmotion}`;
    
    // Map text labels
    const emotionLabels = {
        'calm': 'EMPATHY CORE // STANDBY (CYAN)',
        'tired': 'EMPATHY CORE // UYKULU / DİNLENME (BLUE)',
        'energetic': 'EMPATHY CORE // HİPERAKTİF / COŞKULU (GOLD)',
        'stressed': 'EMPATHY CORE // GERGİN / YATIŞTIRMA (VIOLET)'
    };
    
    emotionLabel.innerText = emotionLabels[activeEmotion] || `EMPATHY CORE // ${activeEmotion.toUpperCase()}`;
}

// UPDATE BADGE BUTTONS ACTIVE STATE
function updateBadges(sentinelActive, gestureActive) {
    if (sentinelActive) {
        btnSentinel.classList.add('active');
        sentinelStatus.innerText = "ACTIVE RADAR";
    } else {
        btnSentinel.classList.remove('active');
        sentinelStatus.innerText = "STANDBY";
    }
    
    if (gestureActive) {
        btnGesture.classList.add('active');
        gestureStatus.innerText = "ACTIVE DETECTOR";
    } else {
        btnGesture.classList.remove('active');
        gestureStatus.innerText = "STANDBY";
    }

    // Handle Camera Viewport Visibility
    if (sentinelActive || gestureActive) {
        if (cameraViewport.classList.contains('viewport-hidden')) {
            cameraViewport.classList.remove('viewport-hidden');
            aiCoreContainer.classList.add('hidden');
            hudCameraFeed.src = `${API_BASE}/api/video_feed`;
            addTerminalLine("SYS: Canlı kamera akışı başlatıldı.", "sys-line");
        }
    } else {
        if (!cameraViewport.classList.contains('viewport-hidden')) {
            cameraViewport.classList.add('viewport-hidden');
            aiCoreContainer.classList.remove('hidden');
            hudCameraFeed.src = ""; // Stop stream
            addTerminalLine("SYS: Canlı kamera akışı durduruldu.", "sys-line");
        }
    }
}

// UPDATE LOG CONSOLE FLOW
function updateTerminalLogs(logs) {
    if (!logs || logs.length === 0) return;
    
    let isNew = false;
    if (logs.length !== lastLogs.length) {
        isNew = true;
    } else {
        for (let i = 0; i < logs.length; i++) {
            if (logs[i] !== lastLogs[i]) {
                isNew = true;
                break;
            }
        }
    }
    
    if (isNew) {
        lastLogs = logs;
        terminalLog.innerHTML = ""; // Clear and rebuild
        logs.forEach(line => {
            let className = "sys-line";
            if (line.startsWith("Siz:")) className = "user-line";
            else if (line.startsWith("Siz (Mobil):")) className = "user-line";
            else if (line.startsWith("JARVIS:")) className = "jarvis-line";
            else if (line.startsWith("ERR:")) className = "err-line";
            
            addTerminalLine(line, className);
        });
    }
}

function addTerminalLine(text, className) {
    const p = document.createElement('div');
    p.className = `log-line ${className}`;
    p.innerText = text;
    terminalLog.appendChild(p);
    terminalLog.scrollTop = terminalLog.scrollHeight;
}

// 2. TRIGGER ACTIONS
async function triggerControl(action) {
    try {
        addTerminalLine(`SYS: Komut gönderiliyor: ${action}...`, "sys-line");
        const response = await fetch(`${API_BASE}/api/control?action=${action}`, {
            method: 'POST'
        });
        const data = await response.json();
        if (data.success) {
            addTerminalLine(`SYS: Başarılı: ${data.message}`, "sys-line");
        } else {
            addTerminalLine(`ERR: Hata oluştu: ${data.error}`, "err-line");
        }
    } catch (err) {
        addTerminalLine(`ERR: Bağlantı hatası: ${err.message}`, "err-line");
    }
}

// 3. SEND TEXT COMMANDS
async function sendCommand(overrideCmd = null) {
    const text = overrideCmd || cmdInput.value.trim();
    if (!text) return;
    
    if (!overrideCmd) cmdInput.value = "";
    
    try {
        addTerminalLine(`Siz (Mobil): ${text}`, "user-line");
        const response = await fetch(`${API_BASE}/api/command`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ command: text })
        });
        const data = await response.json();
        if (!data.success) {
            addTerminalLine(`ERR: Komut gönderilemedi: ${data.error}`, "err-line");
        }
    } catch (err) {
        addTerminalLine(`ERR: Bağlantı hatası: ${err.message}`, "err-line");
    }
}

function handleInputKey(event) {
    if (event.key === 'Enter') {
        sendCommand();
    }
}

// 4. WEB SPEECH RECOGNITION (REMOTE MIC OVER WIFI)
function initSpeechRecognition() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
        console.warn("Speech recognition not supported on this browser.");
        btnMic.style.display = "none";
        return;
    }
    
    speechRecognizer = new SpeechRecognition();
    speechRecognizer.continuous = false;
    speechRecognizer.interimResults = false;
    speechRecognizer.lang = 'tr-TR';
    
    speechRecognizer.onstart = () => {
        isListening = true;
        btnMic.classList.add('listening');
        addTerminalLine("🎙️ Dinliyorum... Konuşun.", "sys-line");
    };
    
    speechRecognizer.onresult = (event) => {
        const resultText = event.results[0][0].transcript;
        addTerminalLine(`🎙️ Algılanan Ses: "${resultText}"`, "user-line");
        sendCommand(resultText);
    };
    
    speechRecognizer.onerror = (event) => {
        addTerminalLine(`🎙️ Ses Hatası: ${event.error}`, "err-line");
    };
    
    speechRecognizer.onend = () => {
        isListening = false;
        btnMic.classList.remove('listening');
        addTerminalLine("🎙️ Mikrofon kapatıldı.", "sys-line");
    };
}

function toggleRemoteMic() {
    if (!speechRecognizer) {
        alert("Tarayıcınız ses tanımayı desteklemiyor. (Safari, Chrome veya modern mobil tarayıcılar önerilir)");
        return;
    }
    
    if (isListening) {
        speechRecognizer.stop();
    } else {
        speechRecognizer.start();
    }
}

// START SERVICE IN LOOPS
window.addEventListener('DOMContentLoaded', () => {
    initSpeechRecognition();
    
    // Poll immediately then every 1200ms
    pollStatus();
    setInterval(pollStatus, 1200);
});
