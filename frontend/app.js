const API_BASE = window.location.origin; // Using relative path for robustness

let sessionId = null;

const configPanel = document.getElementById('config-panel');
const interfacePanel = document.getElementById('interface-panel');
const messageLog = document.getElementById('messagelog');
const userInput = document.getElementById('user-input');
const micBtn = document.getElementById('mic-btn');
const speakerBtn = document.getElementById('speaker-btn');

// --- AUDIO CONFIG ---
let recognition = null;
let isRecording = false;
let isSpeakerOn = true;
let synthesis = window.speechSynthesis;
let auditorVoice = null;

// Initialize Speech Recognition
if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.lang = 'en-US';
    recognition.interimResults = false;

    recognition.onstart = () => {
        isRecording = true;
        micBtn.classList.add('recording');
        userInput.placeholder = "Listening...";
    };

    recognition.onend = () => {
        isRecording = false;
        micBtn.classList.remove('recording');
        userInput.placeholder = "// Describe your safety concept... (or click Mic to speak)";
    };

    recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        userInput.value += transcript + " ";
    };

    recognition.onerror = (event) => {
        console.error("Speech Error:", event.error);
        stopMic();
    };
} else {
    micBtn.style.display = 'none'; // Hide if not supported
    console.warn("Web Speech API not supported in this browser.");
}

// Load Voices for TTS
function loadVoices() {
    const voices = synthesis.getVoices();
    // Try to find a German or British voice for that "Strict Auditor" vibe
    auditorVoice = voices.find(v => v.lang === 'de-DE') ||
        voices.find(v => v.lang === 'en-GB') ||
        voices.find(v => v.name.includes('Google Deutsch')) ||
        voices[0];
}
if (speechSynthesis.onvoiceschanged !== undefined) {
    speechSynthesis.onvoiceschanged = loadVoices;
}

function toggleMic() {
    if (!recognition) return;
    if (isRecording) {
        recognition.stop();
    } else {
        recognition.start();
    }
}

function toggleSpeaker() {
    isSpeakerOn = !isSpeakerOn;
    speakerBtn.classList.toggle('active', isSpeakerOn);
    speakerBtn.innerText = isSpeakerOn ? '🔊' : '🔇';
    if (!isSpeakerOn) synthesis.cancel();
}

function speakText(text) {
    if (!isSpeakerOn) return;

    // Clean text (remove markdown like **bold** or *italic*)
    const cleanText = text.replace(/[*#]/g, '');

    const utterance = new SpeechSynthesisUtterance(cleanText);
    utterance.voice = auditorVoice;
    utterance.rate = 0.9; // Slightly slower, more deliberate
    utterance.pitch = 0.9; // Lower pitch, serious tone
    synthesis.speak(utterance);
}

function addMessage(role, content) {
    const div = document.createElement('div');
    div.className = `message ${role}`;
    // Industrial formatting
    const prefix = role === 'interviewer' ? 'AUDITOR: ' : 'ME: ';
    div.innerText = prefix + content;
    messageLog.appendChild(div);
    messageLog.scrollTop = messageLog.scrollHeight;
}

async function startAudit() {
    const role = document.getElementById('role').value;
    const level = document.getElementById('level').value;
    const topic = document.getElementById('topic').value;
    const exp = parseInt(document.getElementById('exp').value);

    // Initial UI switch
    configPanel.style.display = 'none';
    interfacePanel.style.display = 'flex';
    interfacePanel.style.flexDirection = 'column';

    try {
        const response = await fetch(`${API_BASE}/audit/start`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                target_role: role,
                target_level: level,
                experience_years: exp,
                topic_focus: topic
            })
        });

        if (!response.ok) {
            throw new Error(`Connection Error: ${response.status}`);
        }

        const data = await response.json();
        sessionId = data.session_id;

        addMessage('interviewer', data.interviewer_message);
        speakText(data.interviewer_message);

    } catch (e) {
        addMessage('system', `CRITICAL ERROR: ${e.message}. REVERTING TO OFFLINE PROTOCOLS.`);
        // Fallback or retry logic could go here
    }
}

async function sendResponse() {
    const content = userInput.value.trim();
    if (!content) return;

    addMessage('candidate', content);
    userInput.value = '';

    try {
        const response = await fetch(`${API_BASE}/audit/${sessionId}/respond`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(content)
        });

        if (!response.ok) {
            throw new Error(`Transmission Failed: ${response.status}`);
        }

        const data = await response.json();
        addMessage('interviewer', data.interviewer_message);
        speakText(data.interviewer_message);

    } catch (e) {
        addMessage('system', `LINK LOST: ${e.message}`);
    }
}
