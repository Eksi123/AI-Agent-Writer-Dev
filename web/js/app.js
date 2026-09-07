/**
 * app.js - 全局状态、初始化和工具函数
 * 
 * 必须最先加载的 JS 文件，定义全局状态和公共工具函数。
 */

// ==================== 全局状态 ====================

let currentProject = null;
let currentPanel = 'outline';
let currentAgentName = 'chat';
let currentOutlineRaw = '';

// 设置相关
let currentMaskedKey = '';
let apiKeyModified = false;
let apiKeyVisible = false;

// 名称校验：禁止包含的特殊字符
const INVALID_CHARS = ['/', '\\', ':', '*', '?', '"', '<', '>', '|', '-', '_'];

// ==================== 初始化 ====================

// 页面加载时初始化
window.addEventListener('DOMContentLoaded', async () => {
    // 先检查配置状态
    await checkConfigStatus();
    
    loadProjects();
    loadSettings();
    setupInputHandlers();
    
    // 初始化大纲预览模式
    switchOutlineMode('preview');
});

// 设置输入框事件
function setupInputHandlers() {
    const input = document.getElementById('chatInput');
    
    // Enter 发送，Shift+Enter 换行
    input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    // 自动调整高度
    input.addEventListener('input', () => {
        input.style.height = 'auto';
        input.style.height = Math.min(input.scrollHeight, 150) + 'px';
    });

    // 拖动分隔条调整对话框大小
    setupResizeHandle();
}

// 设置可拖动分隔条
function setupResizeHandle() {
    const resizeHandle = document.getElementById('resizeHandle');
    const chatInputArea = document.querySelector('.chat-input-area');
    const chatPanel = document.querySelector('.chat-panel');
    
    let isResizing = false;
    let startY = 0;
    let startHeight = 0;

    resizeHandle.addEventListener('mousedown', (e) => {
        isResizing = true;
        startY = e.clientY;
        startHeight = chatInputArea.offsetHeight;
        document.body.style.cursor = 'ns-resize';
        document.body.style.userSelect = 'none';
        e.preventDefault();
    });

    document.addEventListener('mousemove', (e) => {
        if (!isResizing) return;
        
        // 向上拖动时deltaY为负，输入区域应该变大
        // 向下拖动时deltaY为正，输入区域应该变小
        const deltaY = e.clientY - startY;
        const newHeight = startHeight - deltaY;
        
        // 限制最小和最大高度
        const minHeight = 60;
        const maxHeight = chatPanel.offsetHeight - 150;
        
        if (newHeight >= minHeight && newHeight <= maxHeight) {
            chatInputArea.style.height = newHeight + 'px';
            chatInputArea.style.flex = 'none';
        }
    });

    document.addEventListener('mouseup', () => {
        if (isResizing) {
            isResizing = false;
            document.body.style.cursor = '';
            document.body.style.userSelect = '';
        }
    });
}

// ==================== 工具函数 ====================

// 简单的 Markdown 渲染
function renderMarkdown(text) {
    if (!text) return '';
    
    // 转义 HTML
    text = text.replace(/&/g, '&amp;')
              .replace(/</g, '&lt;')
              .replace(/>/g, '&gt;');
    
    // 标题
    text = text.replace(/^### (.*$)/gim, '<h3>$1</h3>');
    text = text.replace(/^## (.*$)/gim, '<h2>$1</h2>');
    text = text.replace(/^# (.*$)/gim, '<h1>$1</h1>');
    
    // 粗体
    text = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    
    // 斜体
    text = text.replace(/\*(.*?)\*/g, '<em>$1</em>');
    
    // 代码块
    text = text.replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>');
    
    // 行内代码
    text = text.replace(/`(.*?)`/g, '<code>$1</code>');
    
    // 列表
    text = text.replace(/^\s*[-*] (.*$)/gim, '<li>$1</li>');
    text = text.replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>');
    
    // 换行
    text = text.replace(/\n/g, '<br>');
    
    return text;
}

// HTML 转义
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
