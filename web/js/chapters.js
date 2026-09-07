/**
 * chapters.js - 章节管理
 * 
 * 包含章节目录树加载、卷/章节的增删改查、章节内容查看和编辑等功能。
 */

// ==================== 章节目录树 ====================

// 加载章节目录树
async function loadChapterTree() {
    if (!currentProject) return;
    
    try {
        const response = await fetch(`/api/projects/${currentProject}/chapter-tree`);
        const result = await response.json();
        
        if (result.success) {
            const chaptersDiv = document.getElementById('chaptersContent');
            const tree = result.data.tree;
            
            if (tree.length > 0) {
                chaptersDiv.innerHTML = tree.map(vol => `
                    <div class="volume-item">
                        <div class="volume-title">
                            <span class="volume-title-text">第${vol.volume}卷${vol.volume_name ? ' - ' + vol.volume_name : ''}</span>
                            <div class="volume-actions">
                                <button class="btn-volume-action" onclick="event.stopPropagation(); createChapterPrompt(${vol.volume})" title="新建章节">＋</button>
                                <button class="btn-volume-action" onclick="event.stopPropagation(); renameVolumePrompt(${vol.volume}, '${vol.volume_name}')" title="重命名卷">✏</button>
                                <button class="btn-volume-action" onclick="event.stopPropagation(); deleteVolumeConfirm(${vol.volume})" title="删除卷">✕</button>
                            </div>
                        </div>
                        ${vol.chapters.map(ch => `
                            <div class="chapter-item">
                                <span class="chapter-item-text" onclick="viewChapter('${ch.file}', '第${vol.volume}卷第${ch.chapter}章 ${ch.chapter_name}')">第${ch.chapter}章 ${ch.chapter_name || ''}</span>
                                <div class="chapter-actions">
                                    <button class="btn-chapter-action" onclick="event.stopPropagation(); renameChapterPrompt(${vol.volume}, ${ch.chapter}, '${ch.chapter_name}')" title="重命名">✏</button>
                                    <button class="btn-chapter-action" onclick="event.stopPropagation(); deleteChapterConfirm(${vol.volume}, ${ch.chapter})" title="删除">✕</button>
                                </div>
                            </div>
                        `).join('')}
                    </div>
                `).join('');
            } else {
                chaptersDiv.innerHTML = '<p style="color: #999;">暂无章节，请先新建卷</p>';
            }
        }
    } catch (error) {
        console.error('加载章节目录失败:', error);
    }
}

// ==================== 名称校验 ====================
// INVALID_CHARS 和 validateName 定义在 app.js 中

function validateName(name, nameType) {
    if (!name) return null; // 空名称允许（使用默认命名）
    for (const ch of INVALID_CHARS) {
        if (name.includes(ch)) {
            return `${nameType}不能包含特殊字符：/ \\ : * ? " < > | - _`;
        }
    }
    if (name.length > 50) {
        return `${nameType}长度不能超过50个字符`;
    }
    if (name.trim() === '') {
        return `${nameType}不能只包含空白字符`;
    }
    return null;
}

// ==================== 卷管理 ====================

// 新建卷（弹出输入框，支持自定义卷序号）
async function createVolumePrompt() {
    if (!currentProject) { alert('请先选择项目'); return; }
    
    // 弹出对话框：先输入卷序号，再输入卷名
    const volNumStr = prompt('请输入卷序号（阿拉伯数字，如 1, 2, 3）：\n\n留空则自动递增', '');
    if (volNumStr === null) return;  // 用户取消
    
    let volume = null;
    if (volNumStr.trim() !== '') {
        volume = parseInt(volNumStr.trim());
        if (isNaN(volume) || volume < 1) {
            alert('卷序号必须是正整数');
            return;
        }
    }
    
    const volName = prompt('请输入卷名（留空则使用默认名"第X卷"）：\n\n【格式】第x卷-yyyy（x为中文数字，由序号自动转换）\n【命名规则】\n• 不能包含特殊字符：/ \\ : * ? " < > | - _\n• 长度不超过50个字符\n• 示例：命运的邂逅、初入江湖', '');
    if (volName === null) return;  // 用户取消
    
    // 前端校验
    const error = validateName(volName.trim(), '卷名');
    if (error) {
        alert(error);
        return;
    }
    
    try {
        const body = { name: volName.trim() };
        if (volume !== null) body.volume = volume;
        
        const response = await fetch(`/api/projects/${currentProject}/volume`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });
        const result = await response.json();
        if (result.success) {
            await loadChapterTree();
        } else {
            alert('新建卷失败: ' + (result.error || '未知错误'));
        }
    } catch (error) {
        alert('新建卷失败: ' + error.message);
    }
}

// 重命名卷（弹出输入框）
async function renameVolumePrompt(volume, currentName) {
    const newName = prompt(`请输入第${volume}卷的新卷名：\n\n【命名规则】\n• 不能包含特殊字符：/ \\ : * ? " < > | - _\n• 长度不超过50个字符\n• 示例：命运的邂逅、初入江湖`, currentName);
    if (newName === null || newName.trim() === '') return;
    
    // 前端校验
    const error = validateName(newName.trim(), '卷名');
    if (error) {
        alert(error);
        return;
    }
    
    try {
        const response = await fetch(`/api/projects/${currentProject}/volume/${volume}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: newName.trim() })
        });
        const result = await response.json();
        if (result.success) {
            await loadChapterTree();
        } else {
            alert('重命名失败: ' + (result.error || '未知错误'));
        }
    } catch (error) {
        alert('重命名失败: ' + error.message);
    }
}

// 删除卷（确认对话框）
async function deleteVolumeConfirm(volume) {
    if (!confirm(`确定要删除第${volume}卷及其所有章节吗？此操作不可撤销！`)) return;
    try {
        const response = await fetch(`/api/projects/${currentProject}/volume/${volume}`, { method: 'DELETE' });
        const result = await response.json();
        if (result.success) {
            await loadChapterTree();
        } else {
            alert('删除失败: ' + (result.error || '未知错误'));
        }
    } catch (error) {
        alert('删除失败: ' + error.message);
    }
}

// ==================== 章节管理 ====================

// 新建章节（弹出输入框，支持自定义章节序号）
async function createChapterPrompt(volume) {
    // 弹出对话框：先输入章节序号，再输入章节名
    const chNumStr = prompt('请输入章节序号（阿拉伯数字，如 1, 2, 3）：\n\n留空则自动递增', '');
    if (chNumStr === null) return;  // 用户取消
    
    let chapter = null;
    if (chNumStr.trim() !== '') {
        chapter = parseInt(chNumStr.trim());
        if (isNaN(chapter) || chapter < 1) {
            alert('章节序号必须是正整数');
            return;
        }
    }
    
    const chapterName = prompt('请输入章节名（留空则使用默认名"第X章"）：\n\n【格式】第x章-yyyy（x为阿拉伯数字）\n【命名规则】\n• 不能包含特殊字符：/ \\ : * ? " < > | - _\n• 长度不超过50个字符\n• 示例：命运的邂逅、初入江湖', '');
    if (chapterName === null) return;
    
    // 前端校验
    const error = validateName(chapterName.trim(), '章节名');
    if (error) {
        alert(error);
        return;
    }
    
    try {
        const body = { volume: volume, name: chapterName.trim() };
        if (chapter !== null) body.chapter = chapter;
        
        const response = await fetch(`/api/projects/${currentProject}/chapter/create`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });
        const result = await response.json();
        if (result.success) {
            await loadChapterTree();
        } else {
            alert('新建章节失败: ' + (result.error || '未知错误'));
        }
    } catch (error) {
        alert('新建章节失败: ' + error.message);
    }
}

// 重命名章节（弹出输入框）
async function renameChapterPrompt(volume, chapter, currentName) {
    const newName = prompt(`请输入第${volume}卷第${chapter}章的新章节名：\n\n【命名规则】\n• 不能包含特殊字符：/ \\ : * ? " < > | - _\n• 长度不超过50个字符\n• 示例：命运的邂逅、初入江湖`, currentName);
    if (newName === null || newName.trim() === '') return;
    
    // 前端校验
    const error = validateName(newName.trim(), '章节名');
    if (error) {
        alert(error);
        return;
    }
    
    try {
        const response = await fetch(`/api/projects/${currentProject}/chapter/${volume}/${chapter}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: newName.trim() })
        });
        const result = await response.json();
        if (result.success) {
            await loadChapterTree();
        } else {
            alert('重命名失败: ' + (result.error || '未知错误'));
        }
    } catch (error) {
        alert('重命名失败: ' + error.message);
    }
}

// 删除章节（确认对话框）
async function deleteChapterConfirm(volume, chapter) {
    if (!confirm(`确定要删除第${volume}卷第${chapter}章吗？此操作不可撤销！`)) return;
    try {
        const response = await fetch(`/api/projects/${currentProject}/chapter/${volume}/${chapter}`, { method: 'DELETE' });
        const result = await response.json();
        if (result.success) {
            await loadChapterTree();
        } else {
            alert('删除失败: ' + (result.error || '未知错误'));
        }
    } catch (error) {
        alert('删除失败: ' + error.message);
    }
}

// ==================== 章节内容查看/编辑 ====================

// 查看章节内容
async function viewChapter(filePath, chapterName) {
    try {
        const response = await fetch(`/api/projects/${currentProject}/chapter?file=${encodeURIComponent(filePath)}`);
        const result = await response.json();
        
        if (result.success) {
            const chaptersDiv = document.getElementById('chaptersContent');
            const content = result.data.content || '';
            
            chaptersDiv.innerHTML = `
                <div class="chapter-preview">
                    <div class="chapter-preview-header">
                        <h3>${chapterName}</h3>
                        <div style="display: flex; gap: 6px; align-items: center;">
                            <button class="btn-mode-toggle" id="btnChapterPreview" onclick="switchChapterMode('preview', '${filePath}')">预览</button>
                            <button class="btn-mode-toggle" id="btnChapterEdit" onclick="switchChapterMode('edit', '${filePath}')">编辑</button>
                            <button class="btn-save" id="btnChapterSave" onclick="saveChapter('${filePath}')">💾 保存</button>
                            <button class="btn-back" onclick="loadChapterTree()">← 返回列表</button>
                        </div>
                    </div>
                    <div id="chapterPreview" class="markdown-content">${renderMarkdown(content)}</div>
                    <textarea id="chapterEdit" class="edit-textarea chapter-edit-fill" style="display: none;" placeholder="在此编辑章节内容...">${content}</textarea>
                </div>
            `;
            
            // 默认显示预览模式
            switchChapterMode('preview', filePath);
        }
    } catch (error) {
        console.error('加载章节内容失败:', error);
        alert('加载失败: ' + error.message);
    }
}

// 切换章节预览/编辑模式
function switchChapterMode(mode, filePath) {
    const previewDiv = document.getElementById('chapterPreview');
    const editArea = document.getElementById('chapterEdit');
    const btnPreview = document.getElementById('btnChapterPreview');
    const btnEdit = document.getElementById('btnChapterEdit');
    const btnSave = document.getElementById('btnChapterSave');
    
    if (mode === 'preview') {
        // 使用空字符串清除 inline style，让 CSS class (.markdown-content) 的 display 生效
        previewDiv.style.display = '';
        editArea.style.display = 'none';
        btnPreview.classList.add('active');
        btnEdit.classList.remove('active');
        btnSave.classList.remove('visible');
    } else {
        previewDiv.style.display = 'none';
        // 清除 inline style，让 CSS class (.edit-textarea) 的 display 生效
        editArea.style.display = '';
        btnPreview.classList.remove('active');
        btnEdit.classList.add('active');
        btnSave.classList.add('visible');
    }
}

// 保存章节
async function saveChapter(filePath) {
    const editArea = document.getElementById('chapterEdit');
    const newContent = editArea.value;
    
    try {
        const response = await fetch(`/api/projects/${currentProject}/chapter`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ file: filePath, content: newContent })
        });
        
        const result = await response.json();
        
        if (result.success) {
            const previewDiv = document.getElementById('chapterPreview');
            previewDiv.innerHTML = renderMarkdown(newContent);
            
            // 切换到预览模式
            switchChapterMode('preview', filePath);
            alert('✓ 章节已保存');
        } else {
            alert('保存失败: ' + result.error);
        }
    } catch (error) {
        console.error('保存章节失败:', error);
        alert('保存失败: ' + error.message);
    }
}
