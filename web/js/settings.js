/**
 * settings.js - 设置和配置向导
 * 
 * 包含 LLM 设置面板和首次配置引导弹窗的功能。
 */

// ==================== 设置面板 ====================

// 打开设置
async function openSettings() {
    document.getElementById('settingsModal').classList.add('show');
    await loadSettings();
}

// 关闭设置
function closeSettings() {
    document.getElementById('settingsModal').classList.remove('show');
}

// 切换 API Key 显示/隐藏
function toggleApiKeyVisibility() {
    const input = document.getElementById('apiKey');
    const btn = document.querySelector('.btn-toggle-visibility');
    
    if (apiKeyVisible) {
        // 当前可见，切换为隐藏
        input.type = 'password';
        btn.textContent = '👁';
        btn.title = '显示';
        apiKeyVisible = false;
    } else {
        // 当前隐藏，切换为可见
        input.type = 'text';
        btn.textContent = '👁‍🗨';
        btn.title = '隐藏';
        apiKeyVisible = true;
    }
}

// 加载设置
async function loadSettings() {
    try {
        const response = await fetch('/api/settings');
        const result = await response.json();
        
        if (result.success) {
            const data = result.data;
            document.getElementById('baseUrl').value = data.api_url || '';
            document.getElementById('modelName').value = data.model_name || '';
            document.getElementById('temperature').value = data.temperature || 0.7;
            
            // API Key：预填掩码值，用户可清空后输入新值
            currentMaskedKey = data.api_key_masked || '';
            const apiKeyInput = document.getElementById('apiKey');
            apiKeyInput.value = currentMaskedKey;
            apiKeyInput.readOnly = false; // 允许编辑
            apiKeyModified = false; // 重置修改标记
            
            // 根据 provider 判断模型类型
            if (data.provider === 'ollama') {
                document.getElementById('modelType').value = 'local';
            } else {
                document.getElementById('modelType').value = 'online';
            }
            
            // 同步 API Key 区域显隐
            onModelTypeChange();
        }
    } catch (error) {
        console.error('加载设置失败:', error);
    }
}

// 模型类型切换（不硬编码 URL，保持当前配置值）
function onModelTypeChange() {
    const modelType = document.getElementById('modelType').value;
    const baseUrlInput = document.getElementById('baseUrl');
    const apiKeyGroup = document.getElementById('apiKeyGroup');
    const apiKeyInput = document.getElementById('apiKey');
    
    if (modelType === 'local') {
        // 仅更新 placeholder，不改变当前 value
        baseUrlInput.placeholder = 'http://localhost:11434/v1';
        // 本地模型不需要 API Key，隐藏并禁用
        apiKeyGroup.classList.add('hidden');
        apiKeyInput.disabled = true;
        // 加载 Ollama 可用模型列表
        loadOllamaModels();
    } else {
        // 仅更新 placeholder，不改变当前 value
        baseUrlInput.placeholder = 'https://api.openai.com/v1';
        // 在线模型显示 API Key
        apiKeyGroup.classList.remove('hidden');
        apiKeyInput.disabled = false;
    }
}

// 加载 Ollama 本地可用模型列表
async function loadOllamaModels() {
    try {
        const response = await fetch('/api/llm/ollama/models');
        const result = await response.json();
        const datalist = document.getElementById('ollamaModelList');
        if (result.success && result.data.models.length > 0) {
            datalist.innerHTML = result.data.models.map(m =>
                `<option value="${m}">`
            ).join('');
        } else {
            datalist.innerHTML = '';
        }
    } catch (error) {
        console.error('加载 Ollama 模型失败:', error);
    }
}

// 保存设置 —— 将表单中的值写入 config.ini 和环境变量
async function saveSettings(event) {
    event.preventDefault();
    
    const apiKeyInput = document.getElementById('apiKey');
    const apiKeyValue = apiKeyInput.value.trim();
    const modelType = document.getElementById('modelType').value;
    
    const data = {
        api_url: document.getElementById('baseUrl').value,
        model_name: document.getElementById('modelName').value,
        provider: modelType === 'local' ? 'ollama' : 'openai_compatible',
        temperature: parseFloat(document.getElementById('temperature').value)
    };
    
    // 在线模型且用户输入了新的 Key（不是掩码值）时才发送给后端
    if (modelType === 'online' && apiKeyValue && apiKeyValue !== currentMaskedKey) {
        data.api_key = apiKeyValue;
    }

    try {
        const response = await fetch('/api/settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        
        if (result.success) {
            alert('✓ 设置已保存到 config.ini 或环境变量');
            // 重新加载设置，刷新掩码值
            await loadSettings();
        } else {
            alert('保存失败: ' + result.error);
        }
    } catch (error) {
        console.error('保存设置失败:', error);
        alert('保存失败: ' + error.message);
    }
}

// 测试连接 —— 根据表单中当前的值进行测试
async function testConnection() {
    const modelType = document.getElementById('modelType').value;
    const apiKeyInput = document.getElementById('apiKey');
    
    // 读取表单中当前填写的值
    const data = {
        api_url: document.getElementById('baseUrl').value,
        model_name: document.getElementById('modelName').value,
        provider: modelType === 'local' ? 'ollama' : 'openai_compatible'
    };
    
    // 在线模型：把 API Key 输入框当前的值发过去
    if (modelType === 'online') {
        data.api_key = apiKeyInput.value;
        // 标记用户是否修改了 Key（输入框的值不等于加载时的掩码值）
        data.use_input_key = apiKeyModified || (apiKeyInput.value !== currentMaskedKey);
    }

    try {
        const response = await fetch('/api/settings/test', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        
        if (result.success) {
            alert(`✓ 连接成功\n\n模型响应: ${result.data.response}`);
        } else {
            alert(`✗ 连接失败\n\n${result.error}`);
        }
    } catch (error) {
        console.error('测试连接失败:', error);
        alert('测试失败: ' + error.message);
    }
}

// ==================== 首次配置向导 ====================

// 切换向导模型类型
function onWizardModelTypeChange() {
    const modelType = document.getElementById('wizardModelType').value;
    const baseUrlInput = document.getElementById('wizardBaseUrl');
    const apiKeyGroup = document.getElementById('wizardApiKeyGroup');
    const modelNameInput = document.getElementById('wizardModelName');
    
    if (modelType === 'local') {
        baseUrlInput.value = 'http://localhost:11434/v1';
        baseUrlInput.placeholder = 'http://localhost:11434/v1';
        apiKeyGroup.style.display = 'none';
        document.getElementById('wizardApiKey').value = '';
        modelNameInput.placeholder = 'qwen2.5';
        // 加载 Ollama 模型列表
        loadWizardOllamaModels();
    } else {
        baseUrlInput.value = 'https://dashscope.aliyuncs.com/compatible-mode/v1';
        baseUrlInput.placeholder = 'https://api.openai.com/v1';
        apiKeyGroup.style.display = 'block';
        modelNameInput.placeholder = 'qwen-plus';
    }
}

// 加载 Ollama 模型列表（向导用）
async function loadWizardOllamaModels() {
    try {
        const response = await fetch('/api/llm/ollama/models');
        const result = await response.json();
        const datalist = document.getElementById('wizardOllamaModelList');
        if (result.success && result.data.models.length > 0) {
            datalist.innerHTML = result.data.models.map(m =>
                `<option value="${m}">`
            ).join('');
            // 自动选择第一个模型
            document.getElementById('wizardModelName').value = result.data.models[0];
        } else {
            datalist.innerHTML = '';
        }
    } catch (error) {
        console.error('加载 Ollama 模型失败:', error);
    }
}

// 测试向导连接
async function testWizardConnection() {
    const modelType = document.getElementById('wizardModelType').value;
    const data = {
        api_url: document.getElementById('wizardBaseUrl').value,
        model_name: document.getElementById('wizardModelName').value,
        provider: modelType === 'local' ? 'ollama' : 'openai_compatible'
    };
    
    if (modelType === 'online') {
        const apiKey = document.getElementById('wizardApiKey').value;
        if (!apiKey) {
            alert('请先填写 API Key');
            return;
        }
        data.api_key = apiKey;
        data.use_input_key = true;
    }

    try {
        const response = await fetch('/api/settings/test', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        
        if (result.success) {
            alert(`✓ 连接成功\n\n模型响应: ${result.data.response}`);
        } else {
            alert(`✗ 连接失败\n\n${result.error}`);
        }
    } catch (error) {
        console.error('测试连接失败:', error);
        alert('测试失败: ' + error.message);
    }
}

// 保存向导配置
async function saveWizardConfig(event) {
    event.preventDefault();
    
    const modelType = document.getElementById('wizardModelType').value;
    const data = {
        api_url: document.getElementById('wizardBaseUrl').value,
        model_name: document.getElementById('wizardModelName').value,
        provider: modelType === 'local' ? 'ollama' : 'openai_compatible',
        temperature: parseFloat(document.getElementById('wizardTemperature').value)
    };
    
    if (modelType === 'online') {
        const apiKey = document.getElementById('wizardApiKey').value;
        if (!apiKey) {
            alert('API Key 不能为空');
            return;
        }
        data.api_key = apiKey;
    }

    try {
        const response = await fetch('/api/settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        
        if (result.success) {
            // 再次检查配置状态
            const statusResponse = await fetch('/api/settings/status');
            const statusResult = await statusResponse.json();
            
            if (statusResult.success && statusResult.data.configured) {
                // 配置完整，关闭弹窗并刷新页面
                document.getElementById('setupModal').classList.remove('show');
                alert('✓ 配置已保存，页面即将刷新');
                location.reload();
            } else {
                // 仍不完整，显示缺失字段
                const missing = statusResult.data.missing || [];
                const fieldNames = {
                    'api_url': 'API URL',
                    'model_name': '模型名称',
                    'api_key': 'API Key'
                };
                const missingNames = missing.map(f => fieldNames[f] || f).join('、');
                alert(`✗ 配置仍不完整，缺少：${missingNames}`);
            }
        } else {
            alert('保存失败: ' + result.error);
        }
    } catch (error) {
        console.error('保存配置失败:', error);
        alert('保存失败: ' + error.message);
    }
}
