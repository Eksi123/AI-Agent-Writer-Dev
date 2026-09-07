/**
 * chat.js - 对话功能和 Agent 切换
 * 
 * 包含消息发送、消息渲染、Agent 切换、配置状态检查等功能。
 */

// ==================== 配置检查 ====================

// 检查配置状态，若未配置则显示强制设置弹窗
async function checkConfigStatus() {
    try {
        const response = await fetch('/api/settings/status');
        const result = await response.json();
        
        if (result.success && !result.data.configured) {
            // 配置不完整，显示强制设置弹窗
            showSetupModal();
        }
    } catch (error) {
        console.error('检查配置状态失败:', error);
    }
}

// 显示强制设置弹窗
function showSetupModal() {
    const modal = document.getElementById('setupModal');
    modal.classList.add('show');
    
    // 预填默认值
    document.getElementById('wizardBaseUrl').value = 'https://dashscope.aliyuncs.com/compatible-mode/v1';
    document.getElementById('wizardModelName').value = 'qwen-plus';
    document.getElementById('wizardTemperature').value = '0.7';
    document.getElementById('wizardModelType').value = 'online';
    onWizardModelTypeChange();
}

// ==================== Agent 切换 ====================

// 切换 Agent
function switchAgent(agentName) {
    currentAgentName = agentName;
    
    // 更新按钮样式
    document.querySelectorAll('.agent-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    event.target.classList.add('active');
    
    // 更新顶部显示
    const agentNames = {
        'chat': 'ChatAgent',
        'writer': 'NovelWriter',
        'outline_polisher': 'OutlinePolisher',
        'content_polisher': 'ContentPolisher',
        'summary': 'SummaryGenerator',
        'info_query': 'InfoQuery'
    };
    document.getElementById('currentAgent').textContent = 
        `当前 Agent: ${agentNames[agentName]}`;
}

// ==================== 对话功能 ====================

// 发送消息
async function sendMessage() {
    const input = document.getElementById('chatInput');
    let message = input.value.trim();
    
    if (!message) return;

    // 如果不是 chat agent，自动添加 @指令
    if (currentAgentName !== 'chat' && !message.startsWith('@')) {
        const agentCommands = {
            'writer': '@写作',
            'outline_polisher': '@大纲润色',
            'content_polisher': '@小说润色',
            'summary': '@汇总说明',
            'info_query': '@信息查询'
        };
        message = `${agentCommands[currentAgentName]} ${message}`;
    }

    // 添加用户消息
    addMessage('user', message);
    input.value = '';
    input.style.height = 'auto';

    // 禁用发送按钮
    const btnSend = document.getElementById('btnSend');
    btnSend.disabled = true;
    btnSend.innerHTML = '<span class="loading"></span>';

    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message })
        });
        
        const result = await response.json();
        
        if (result.success) {
            const data = result.data;
            // 添加 AI 回复，包含思考过程
            const thoughtProcess = data.thought_process || [];
            
            if (data.error) {
                // 大模型返回了错误，使用 system 样式显示
                addMessage('system', data.response, thoughtProcess);
            } else {
                addMessage('assistant', data.response, thoughtProcess);
            }
            
            // 如果是写作工作流，刷新章节列表
            if (data.workflow) {
                loadChapterTree();
            }
        } else {
            // 显示错误信息（使用 system 类型，会有醒目的样式）
            addMessage('system', result.error);
        }
    } catch (error) {
        console.error('发送消息失败:', error);
        addMessage('system', '发送失败: ' + error.message);
    } finally {
        // 恢复发送按钮
        btnSend.disabled = false;
        btnSend.textContent = '发送';
    }
}

// 添加消息到聊天区域
function addMessage(role, content, thoughtProcess = []) {
    const messagesDiv = document.getElementById('chatMessages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;
    
    const avatar = role === 'user' ? '你' : (role === 'system' ? '⚠' : (role === 'info' ? '⚙' : 'AI'));
    
    // 构建思考过程 HTML
    let thoughtHtml = '';
    if (role === 'assistant' && thoughtProcess.length > 0) {
        const thoughtId = 'thought-' + Date.now();
        thoughtHtml = `
            <div class="thought-process">
                <div class="thought-header" onclick="toggleThought('${thoughtId}')">
                    <span class="thought-icon">💭</span>
                    <span class="thought-title">思考过程</span>
                    <span class="thought-toggle" id="${thoughtId}-toggle">▼</span>
                </div>
                <div class="thought-content" id="${thoughtId}">
                    ${renderThoughtProcess(thoughtProcess)}
                </div>
            </div>
        `;
    }
    
    messageDiv.innerHTML = `
        <div class="message-avatar">${avatar}</div>
        <div class="message-content">
            ${thoughtHtml}
            <div class="markdown-content">${renderMarkdown(content)}</div>
        </div>
    `;
    
    messagesDiv.appendChild(messageDiv);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

// 切换思考过程展开/折叠
function toggleThought(thoughtId) {
    const content = document.getElementById(thoughtId);
    const toggle = document.getElementById(thoughtId + '-toggle');
    
    if (content.classList.contains('expanded')) {
        content.classList.remove('expanded');
        toggle.textContent = '▼';
    } else {
        content.classList.add('expanded');
        toggle.textContent = '▲';
    }
}

// 渲染思考过程
function renderThoughtProcess(thoughtProcess) {
    return thoughtProcess.map(item => {
        if (item.type === 'thinking') {
            return `<div class="thought-item thinking">
                <div class="thought-item-header">🧠 思考</div>
                <div class="thought-item-content">${escapeHtml(item.content)}</div>
            </div>`;
        } else if (item.type === 'tool_call') {
            return `<div class="thought-item tool-call">
                <div class="thought-item-header">🔧 调用工具: ${escapeHtml(item.tool)}</div>
                <div class="thought-item-content"><pre>${escapeHtml(JSON.stringify(item.args, null, 2))}</pre></div>
            </div>`;
        } else if (item.type === 'tool_result') {
            return `<div class="thought-item tool-result">
                <div class="thought-item-header">✅ 工具结果: ${escapeHtml(item.tool)}</div>
                <div class="thought-item-content"><pre>${escapeHtml(item.result)}</pre></div>
            </div>`;
        } else if (item.type === 'tool_error') {
            return `<div class="thought-item tool-error">
                <div class="thought-item-header">❌ 工具错误: ${escapeHtml(item.tool)}</div>
                <div class="thought-item-content"><pre>${escapeHtml(item.error)}</pre></div>
            </div>`;
        }
        return '';
    }).join('');
}
