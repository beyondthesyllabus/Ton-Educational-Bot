// Global state
let currentTab = 'dashboard';
let selectedFile = null;

// Backend URL - points directly to Render backend
const BASE_URL = 'https://ton-educational-bot.onrender.com';

// Quiz state
let quizQuestions = [
    {
        question: "What does TON stand for in the context of the blockchain?",
        options: [
            "Telegram Online Network",
            "The Open Network",
            "Trust Operating Node",
            "Token Optimization Network"
        ],
        correctIndex: 1
    },
    {
        question: "Which programming languages are used to write smart contracts on TON?",
        options: [
            "Solidity and Vyper",
            "Rust and Go",
            "FunC and Tact",
            "Python and JavaScript"
        ],
        correctIndex: 2
    },
    {
        question: "What is the name of the popular non-custodial wallet in the TON ecosystem?",
        options: [
            "Tonkeeper",
            "MetaMask",
            "Phantom",
            "WalletConnect"
        ],
        correctIndex: 0
    },
    {
        question: "How does the TON blockchain achieve massive scaling and transaction throughput?",
        options: [
            "Through off-chain state channels only",
            "By using a single high-performance supercomputer",
            "Using an infinite dynamic sharding paradigm",
            "By limiting transaction sizes to 1KB"
        ],
        correctIndex: 2
    },
    {
        question: "What is the primary use of Toncoin?",
        options: [
            "Paying transaction fees, network governance, and staking",
            "It has no utility and is just for trading",
            "To buy Telegram Premium subscriptions only",
            "To run Bitcoin nodes"
        ],
        correctIndex: 0
    }
];

let currentQuestionIndex = 0;
let quizScore = 0;
let selectedOptionIndex = null;

// Console log helper
function addLogLine(text, type = 'info') {
    const consoleEl = document.getElementById('log-console');
    if (!consoleEl) return;
    
    const timestamp = new Date().toLocaleTimeString();
    const line = document.createElement('span');
    line.className = `log-line ${type}`;
    line.textContent = `[${timestamp}] [${type.toUpperCase()}] ${text}`;
    
    consoleEl.appendChild(line);
    consoleEl.scrollTop = consoleEl.scrollHeight;
}

// Tab Switching Routing
function switchTab(tabId) {
    if (tabId === currentTab) return;
    
    // Deactivate current tab
    document.querySelector(`.nav-item[data-tab="${currentTab}"]`).classList.remove('active');
    document.getElementById(currentTab).classList.remove('active');
    
    // Activate new tab
    document.querySelector(`.nav-item[data-tab="${tabId}"]`).classList.add('active');
    document.getElementById(tabId).classList.add('active');
    
    currentTab = tabId;
    
    // Update Header Metadata
    const headerTitle = document.getElementById('active-tab-title');
    const headerDesc = document.getElementById('active-tab-desc');
    
    switch (tabId) {
        case 'dashboard':
            headerTitle.textContent = "Educational Dashboard";
            headerDesc.textContent = "Learn about the Open Network (TON) blockchain and ecosystem.";
            break;
        case 'chat':
            headerTitle.textContent = "AI Q&A Chatbot";
            headerDesc.textContent = "Ask OpenAI AI questions about TON, or upload images to verify them.";
            // Scroll chat to bottom
            const messagesContainer = document.getElementById('chat-messages');
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
            break;
        case 'quiz':
            headerTitle.textContent = "Quiz Center";
            headerDesc.textContent = "Test your skills and earn the TON Expert status.";
            break;
        case 'status':
            headerTitle.textContent = "Bot Control Panel";
            headerDesc.textContent = "Check health metrics, environment settings, and live system feeds.";
            break;
    }
    
    addLogLine(`Switched to view: ${tabId}`, 'system');
}

// Add click listeners to sidebar navigation items
document.querySelectorAll('.nav-item').forEach(button => {
    button.addEventListener('click', () => {
        const tabId = button.getAttribute('data-tab');
        switchTab(tabId);
    });
});

// File Upload Handler
function handleFileSelect(event) {
    const file = event.target.files[0];
    if (!file) return;
    
    selectedFile = file;
    document.getElementById('preview-filename').textContent = file.name;
    document.getElementById('upload-preview').style.display = 'flex';
    addLogLine(`Selected file: ${file.name} (${Math.round(file.size / 1024)} KB)`, 'info');
}

function clearSelectedFile() {
    selectedFile = null;
    document.getElementById('image-upload').value = '';
    document.getElementById('upload-preview').style.display = 'none';
    addLogLine(`Cleared file selection`, 'info');
}

// Chat API Integrations
async function handleChatSubmit(event) {
    event.preventDefault();
    
    const textInput = document.getElementById('chat-input');
    const userText = textInput.value.trim();
    
    // Need at least text or a file
    if (!userText && !selectedFile) return;
    
    const messagesContainer = document.getElementById('chat-messages');
    
    // 1. Render User Message
    const userMessageDiv = document.createElement('div');
    userMessageDiv.className = 'message user';
    
    let messageContent = '';
    if (selectedFile) {
        messageContent += `📷 [Image: ${selectedFile.name}]<br>`;
    }
    if (userText) {
        messageContent += escapeHTML(userText);
    }
    
    userMessageDiv.innerHTML = `<div class="message-bubble">${messageContent}</div>`;
    messagesContainer.appendChild(userMessageDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
    
    // Clear inputs and preview
    textInput.value = '';
    const fileToSend = selectedFile;
    clearSelectedFile();
    
    // Disable send button temporarily
    const sendBtn = document.getElementById('send-button');
    sendBtn.disabled = true;
    
    // 2. Render Typing Indicator
    const typingIndicator = document.createElement('div');
    typingIndicator.className = 'typing-indicator';
    typingIndicator.id = 'typing-indicator';
    typingIndicator.innerHTML = `
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
    `;
    messagesContainer.appendChild(typingIndicator);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
    
    try {
        let responseText = "";
        
        if (fileToSend) {
            // Send file to Pillow upload endpoint
            addLogLine(`Uploading image '${fileToSend.name}' to server...`, 'info');
            const formData = new FormData();
            formData.append('file', fileToSend);
            if (userText) {
                formData.append('prompt', userText);
            }
            
            const response = await fetch(`${BASE_URL}/api/upload`, {
                method: 'POST',
                body: formData
            });
            
            const data = await response.json();
            if (response.ok) {
                responseText = `🖼️ **Pillow Verification Result:**<br>`;
                responseText += `• File: ${escapeHTML(data.filename)}<br>`;
                responseText += `• Format: **${escapeHTML(data.format)}**<br>`;
                responseText += `• Size: ${data.size[0]} x ${data.size[1]} pixels<br>`;
                responseText += `• Mode: ${escapeHTML(data.mode)}<br><br>`;
                if (data.ai_response) {
                    responseText += `🤖 **AI Response:** ${escapeHTML(data.ai_response)}`;
                } else {
                    responseText += `Bot verified image formatting successfully.`;
                }
                addLogLine(`Image verified successfully format=${data.format}`, 'success');
            } else {
                responseText = `⚠️ Error: ${escapeHTML(data.detail || 'Could not verify image')}`;
                addLogLine(`Image upload failed: ${data.detail || 'unknown error'}`, 'error');
            }
        } else {
            // Send text to Chatbot OpenAI endpoint
            addLogLine(`Sending prompt to OpenAI API...`, 'info');
            const response = await fetch(`${BASE_URL}/api/chat`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ message: userText })
            });
            
            const data = await response.json();
            if (response.ok) {
                responseText = data.reply;
                addLogLine(`Received AI response from OpenAI`, 'success');
            } else {
                responseText = `⚠️ Error: ${escapeHTML(data.detail || 'Failed to reach AI API')}`;
                addLogLine(`Chatbot API failed: ${data.detail || 'unknown error'}`, 'error');
            }
        }
        
        // 3. Remove Typing Indicator
        typingIndicator.remove();
        
        // 4. Render Assistant Bubble
        const assistantMessageDiv = document.createElement('div');
        assistantMessageDiv.className = 'message assistant';
        assistantMessageDiv.innerHTML = `<div class="message-bubble">${formatMarkdown(responseText)}</div>`;
        messagesContainer.appendChild(assistantMessageDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
        
    } catch (err) {
        typingIndicator.remove();
        const errorDiv = document.createElement('div');
        errorDiv.className = 'message assistant';
        errorDiv.innerHTML = `<div class="message-bubble">⚠️ Network Error: Unable to communicate with the backend. Make sure server.py is running.</div>`;
        messagesContainer.appendChild(errorDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
        addLogLine(`Network error: ${err.message}`, 'error');
    } finally {
        sendBtn.disabled = false;
    }
}

// Helpers
function escapeHTML(text) {
    const div = document.createElement('div');
    div.innerText = text;
    return div.innerHTML;
}

function formatMarkdown(text) {
    // Basic formatting for presentation
    let formatted = escapeHTML(text);
    // Replace **bold** with <strong>bold</strong>
    formatted = formatted.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    // Replace *bullet with list item
    formatted = formatted.replace(/\n• (.*?)/g, '<br>• $1');
    formatted = formatted.replace(/\n- (.*?)/g, '<br>• $1');
    // Convert newlines to breaks
    formatted = formatted.replace(/\n/g, '<br>');
    return formatted;
}

// Interactive Quiz Logic
function startQuiz() {
    currentQuestionIndex = 0;
    quizScore = 0;
    selectedOptionIndex = null;
    
    document.getElementById('quiz-start-view').style.display = 'none';
    document.getElementById('quiz-result-view').style.display = 'none';
    document.getElementById('quiz-active-view').style.display = 'block';
    
    renderQuestion();
    addLogLine(`Started a new Quiz Challenge`, 'system');
}

function renderQuestion() {
    const question = quizQuestions[currentQuestionIndex];
    selectedOptionIndex = null;
    
    // Disable submit button
    const submitBtn = document.getElementById('quiz-submit-btn');
    submitBtn.disabled = true;
    submitBtn.textContent = "Confirm Answer";
    
    // Update question metadata
    document.getElementById('question-counter').textContent = `Question ${currentQuestionIndex + 1} of ${quizQuestions.length}`;
    
    // Update progress bar
    const progressPercent = ((currentQuestionIndex) / quizQuestions.length) * 100;
    document.getElementById('quiz-progress-bar').style.width = `${progressPercent}%`;
    
    // Set Question Text
    document.getElementById('quiz-question-text').textContent = question.question;
    
    // Clear and build options buttons
    const optionsContainer = document.getElementById('quiz-options-list');
    optionsContainer.innerHTML = '';
    
    question.options.forEach((option, idx) => {
        const btn = document.createElement('button');
        btn.className = 'quiz-option-btn';
        btn.innerHTML = `${idx + 1}. ${escapeHTML(option)}`;
        btn.onclick = () => selectOption(idx);
        optionsContainer.appendChild(btn);
    });
}

function selectOption(index) {
    selectedOptionIndex = index;
    
    // Remove selected class from all buttons
    const buttons = document.querySelectorAll('.quiz-option-btn');
    buttons.forEach((btn, idx) => {
        if (idx === index) {
            btn.classList.add('selected');
        } else {
            btn.classList.remove('selected');
        }
    });
    
    // Enable submit button
    const submitBtn = document.getElementById('quiz-submit-btn');
    submitBtn.disabled = false;
}

async function submitAnswer() {
    const currentQuestion = quizQuestions[currentQuestionIndex];
    const isCorrect = (selectedOptionIndex === currentQuestion.correctIndex);
    
    if (isCorrect) {
        quizScore++;
        addLogLine(`Question ${currentQuestionIndex + 1} Answered Correctly!`, 'success');
    } else {
        addLogLine(`Question ${currentQuestionIndex + 1} Answered Incorrectly.`, 'info');
    }
    
    // Move to next question or show results
    currentQuestionIndex++;
    
    if (currentQuestionIndex < quizQuestions.length) {
        renderQuestion();
    } else {
        // Complete the quiz
        showQuizResults();
    }
}

function showQuizResults() {
    document.getElementById('quiz-active-view').style.display = 'none';
    document.getElementById('quiz-result-view').style.display = 'block';
    
    const percentage = Math.round((quizScore / quizQuestions.length) * 100);
    document.getElementById('score-percentage').textContent = `${percentage}%`;
    document.getElementById('score-fraction').textContent = `${quizScore} out of ${quizQuestions.length} Correct`;
    
    const badgeGraphic = document.getElementById('result-badge-graphic');
    const resultTitle = document.getElementById('result-title');
    const resultText = document.getElementById('result-text');
    
    if (percentage >= 80) {
        badgeGraphic.textContent = "🏆";
        resultTitle.textContent = "TON Expert!";
        resultText.textContent = "Incredible! You have passed the quiz and proved a comprehensive understanding of the TON Blockchain architecture. You are ready to build on TON!";
        addLogLine(`Quiz completed: PASSED with ${percentage}% score`, 'success');
    } else {
        badgeGraphic.textContent = "📚";
        resultTitle.textContent = "Keep Learning!";
        resultText.textContent = "Good try, but you need 80% or higher to earn the expert badge. Read the dashboard materials or consult the AI assistant and try again!";
        addLogLine(`Quiz completed: FAILED with ${percentage}% score`, 'info');
    }
}

// Status Updates Polling
async function checkBotStatus() {
    try {
        const response = await fetch(`${BASE_URL}/api/status`);
        const data = await response.json();
        
        if (response.ok) {
            // Update status tab indicators
            const statusIndicator = document.getElementById('bot-status-indicator');
            const statusText = document.getElementById('bot-status-text');
            const badgeIndicator = document.querySelector('.sidebar-footer .pulse-indicator');
            const badgeText = document.querySelector('.sidebar-footer span:last-child');
            
            if (data.bot_active) {
                statusIndicator.className = 'pulse-indicator online';
                statusText.textContent = 'ONLINE';
                statusText.style.color = 'var(--color-success)';
                
                badgeIndicator.className = 'pulse-indicator online';
                badgeText.textContent = 'Bot: Live Polling';
            } else {
                statusIndicator.className = 'pulse-indicator';
                statusIndicator.style.backgroundColor = 'var(--text-muted)';
                statusText.textContent = 'OFFLINE';
                statusText.style.color = 'var(--text-secondary)';
                
                badgeIndicator.className = 'pulse-indicator';
                badgeIndicator.style.backgroundColor = 'var(--text-muted)';
                badgeText.textContent = 'Bot: Stopped';
            }
            
            // Credentials indicators
            const botTokenPill = document.getElementById('status-bot-token');
            const openaiKeyPill = document.getElementById('status-openai-key');
            
            if (data.credentials.BOT_TOKEN === 'configured') {
                botTokenPill.className = 'status-pill success';
                botTokenPill.textContent = 'Configured';
            } else {
                botTokenPill.className = 'status-pill error';
                botTokenPill.textContent = 'Missing';
            }
            
            if (data.credentials.OPENAI_API_KEY === 'configured') {
                openaiKeyPill.className = 'status-pill success';
                openaiKeyPill.textContent = 'Configured';
            } else {
                openaiKeyPill.className = 'status-pill error';
                openaiKeyPill.textContent = 'Missing';
            }

            // Sync console logs
            const consoleEl = document.getElementById('log-console');
            if (consoleEl && data.logs) {
                consoleEl.innerHTML = '';
                data.logs.forEach(log => {
                    const line = document.createElement('span');
                    line.className = `log-line ${log.type}`;
                    line.textContent = `[${log.timestamp}] [${log.type.toUpperCase()}] ${log.message}`;
                    consoleEl.appendChild(line);
                });
                consoleEl.scrollTop = consoleEl.scrollHeight;
            }
        }
    } catch (err) {
        // Silent catch during periodic poll
    }
}

// Theme Toggle
function initTheme() {
    const themeToggleBtn = document.getElementById('theme-toggle');
    if (!themeToggleBtn) return;
    
    const sunIcon = themeToggleBtn.querySelector('.sun-icon');
    const moonIcon = themeToggleBtn.querySelector('.moon-icon');
    
    // Check local storage or default to dark
    const savedTheme = localStorage.getItem('theme') || 'dark';
    
    if (savedTheme === 'light') {
        document.body.classList.add('light-theme');
        sunIcon.style.display = 'none';
        moonIcon.style.display = 'block';
    } else {
        document.body.classList.remove('light-theme');
        sunIcon.style.display = 'block';
        moonIcon.style.display = 'none';
    }
    
    themeToggleBtn.addEventListener('click', () => {
        const isLight = document.body.classList.toggle('light-theme');
        if (isLight) {
            localStorage.setItem('theme', 'light');
            sunIcon.style.display = 'none';
            moonIcon.style.display = 'block';
            addLogLine("Theme switched to Light Mode", "system");
        } else {
            localStorage.setItem('theme', 'dark');
            sunIcon.style.display = 'block';
            moonIcon.style.display = 'none';
            addLogLine("Theme switched to Dark Mode", "system");
        }
    });
}

// Initial Setup
document.addEventListener('DOMContentLoaded', () => {
    addLogLine("Educational SPA layout initialised successfully.", "system");
    initTheme();
    checkBotStatus();
    // Poll status every 8 seconds
    setInterval(checkBotStatus, 8000);
});
