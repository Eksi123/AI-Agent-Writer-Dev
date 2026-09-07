/**
 * outline.js - 大纲管理
 * 
 * 包含大纲的加载、编辑、保存、目录解析等功能。
 */

// ==================== 面板切换 ====================

// 切换面板
function switchPanel(panel, event) {
    currentPanel = panel;
    
    // 更新标签样式
    document.querySelectorAll('.panel-tab').forEach(tab => {
        tab.classList.remove('active');
    });
    if (event) {
        event.target.classList.add('active');
    }
    
    // 显示对应面板 —— 必须用 'flex' 而非 'block'，
    // 因为 .outline-content / .chapters-content 是 flex 容器，
    // 用 'block' 会破坏整个 flex 布局链条
    document.getElementById('outlinePanel').style.display = 
        panel === 'outline' ? 'flex' : 'none';
    document.getElementById('chaptersPanel').style.display = 
        panel === 'chapters' ? 'flex' : 'none';
}

// ==================== 大纲功能 ====================

// currentOutlineRaw 定义在 app.js 中

// 加载大纲
async function loadOutline() {
    if (!currentProject) return;
    
    try {
        const response = await fetch(`/api/projects/${currentProject}/outline`);
        const result = await response.json();
        
        if (result.success) {
            currentOutlineRaw = result.data.outline || '';
            const outlinePreview = document.getElementById('outlinePreview');
            const outlineEdit = document.getElementById('outlineEdit');
            
            if (currentOutlineRaw) {
                outlinePreview.innerHTML = renderMarkdown(currentOutlineRaw);
                outlineEdit.value = currentOutlineRaw;
                
                // 解析并显示目录
                parseOutlineToc(currentOutlineRaw);
            } else {
                outlinePreview.innerHTML = '<p style="color: #999;">暂无大纲</p>';
                outlineEdit.value = '';
                document.getElementById('outlineToc').style.display = 'none';
            }
        }
    } catch (error) {
        console.error('加载大纲失败:', error);
    }
}

// 解析大纲目录
function parseOutlineToc(markdown) {
    const tocList = document.getElementById('tocList');
    const outlineToc = document.getElementById('outlineToc');
    
    // 匹配标题：# 一级标题，## 二级标题，### 三级标题
    const headingRegex = /^(#{1,3})\s+(.+)$/gm;
    const headings = [];
    let match;
    
    while ((match = headingRegex.exec(markdown)) !== null) {
        const level = match[1].length;
        const text = match[2].trim();
        const id = 'heading-' + headings.length;
        headings.push({ level, text, id });
    }
    
    if (headings.length === 0) {
        outlineToc.style.display = 'none';
        return;
    }
    
    // 生成目录列表
    tocList.innerHTML = headings.map(h => 
        `<li class="toc-item level-${h.level}" onclick="scrollToHeading('${h.id}')" title="${h.text}">${h.text}</li>`
    ).join('');
    
    // 为标题添加ID用于跳转
    const outlinePreview = document.getElementById('outlinePreview');
    let headingIndex = 0;
    outlinePreview.innerHTML = outlinePreview.innerHTML.replace(
        /<h([1-3])>(.*?)<\/h\1>/g,
        (match, level, text) => {
            const id = 'heading-' + headingIndex;
            headingIndex++;
            return `<h${level} id="${id}">${text}</h${level}>`;
        }
    );
    
    outlineToc.style.display = 'block';
}

// 跳转到指定标题
function scrollToHeading(id) {
    const element = document.getElementById(id);
    if (element) {
        element.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
}

// 切换目录显示/隐藏
function toggleToc() {
    const tocList = document.getElementById('tocList');
    const toggleBtn = document.querySelector('.toc-toggle');
    
    if (tocList.classList.contains('collapsed')) {
        tocList.classList.remove('collapsed');
        toggleBtn.textContent = '收起';
    } else {
        tocList.classList.add('collapsed');
        toggleBtn.textContent = '展开';
    }
}

// 切换大纲预览/编辑模式
function switchOutlineMode(mode) {
    const previewDiv = document.getElementById('outlinePreview');
    const editArea = document.getElementById('outlineEdit');
    const tocNav = document.getElementById('outlineToc');
    const btnPreview = document.getElementById('btnOutlinePreview');
    const btnEdit = document.getElementById('btnOutlineEdit');
    const btnSave = document.getElementById('btnOutlineSave');
    
    if (mode === 'preview') {
        // 使用空字符串清除 inline style，让 CSS class 生效
        previewDiv.style.display = '';
        editArea.style.display = 'none';
        tocNav.style.display = '';
        btnPreview.classList.add('active');
        btnEdit.classList.remove('active');
        btnSave.classList.remove('visible');
    } else {
        previewDiv.style.display = 'none';
        // textarea 不需要 flex，保持 block 即可
        editArea.style.display = '';
        tocNav.style.display = 'none';
        btnPreview.classList.remove('active');
        btnEdit.classList.add('active');
        btnSave.classList.add('visible');
    }
}

// 保存大纲
async function saveOutline() {
    const editArea = document.getElementById('outlineEdit');
    const newContent = editArea.value;
    
    try {
        const response = await fetch(`/api/projects/${currentProject}/outline`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ content: newContent })
        });
        
        const result = await response.json();
        
        if (result.success) {
            currentOutlineRaw = newContent;
            const outlinePreview = document.getElementById('outlinePreview');
            outlinePreview.innerHTML = renderMarkdown(newContent);
            parseOutlineToc(newContent);
            
            // 切换到预览模式
            switchOutlineMode('preview');
            alert('✓ 大纲已保存');
        } else {
            alert('保存失败: ' + result.error);
        }
    } catch (error) {
        console.error('保存大纲失败:', error);
        alert('保存失败: ' + error.message);
    }
}
