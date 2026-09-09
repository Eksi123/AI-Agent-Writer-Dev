/**
 * skill-manager.js - Skill 管理功能
 * 
 * 处理 Skill 的导入、删除、列表展示等功能
 */

// 全局状态
let skillDeleteMode = false;
let currentSkillToDelete = null;
let installedSkills = [];
let skillHoverTimer = null; // 悬停延迟定时器

// ==================== 弹窗控制 ====================

function openSkillManager() {
    document.getElementById('skillManagerModal').classList.add('show');
    loadSkillList();
}

function closeSkillManager() {
    document.getElementById('skillManagerModal').classList.remove('show');
    skillDeleteMode = false;
    updateDeleteButton();
}

// ==================== Skill 列表 ====================

async function loadSkillList() {
    try {
        const response = await fetch('/api/skills');
        const result = await response.json();
        
        if (result.success) {
            installedSkills = result.data.skills;
            renderSkillList();
        } else {
            showError('加载 Skill 列表失败: ' + result.error);
        }
    } catch (error) {
        console.error('加载 Skill 列表失败:', error);
        showError('加载 Skill 列表失败: ' + error.message);
    }
}

function renderSkillList() {
    const skillList = document.getElementById('skillList');
    
    if (installedSkills.length === 0) {
        skillList.innerHTML = '<div class="skill-list-empty">暂无自定义 Skill</div>';
        return;
    }
    
    skillList.innerHTML = installedSkills.map(skill => `
        <div class="skill-list-item" data-skill-name="${skill.name}"
             onmouseenter="onSkillItemMouseEnter('${skill.name}', this)"
             onmouseleave="onSkillItemMouseLeave()">
            <div class="skill-list-item-content">
                <span class="skill-list-item-name">${skill.name}</span>
            </div>
            ${skillDeleteMode ? `<button class="skill-list-item-delete" onclick="event.stopPropagation(); requestDeleteSkill('${skill.name}')">×</button>` : ''}
        </div>
    `).join('');
}

// ==================== 悬停显示详情 ====================

function onSkillItemMouseEnter(skillName, element) {
    if (skillDeleteMode) return;
    
    // 清除之前的定时器
    if (skillHoverTimer) {
        clearTimeout(skillHoverTimer);
    }
    
    // 延迟 500ms 后显示详情弹窗
    skillHoverTimer = setTimeout(() => {
        showSkillDetail(skillName, element);
    }, 500);
}

function onSkillItemMouseLeave() {
    // 清除定时器
    if (skillHoverTimer) {
        clearTimeout(skillHoverTimer);
        skillHoverTimer = null;
    }
    
    // 隐藏详情弹窗
    closeSkillDetail();
}

// ==================== Skill 详情 ====================

function showSkillDetail(skillName, element) {
    if (skillDeleteMode) return;
    
    const skill = installedSkills.find(s => s.name === skillName);
    if (!skill) return;
    
    const popover = document.getElementById('skillDetailPopover');
    const nameEl = document.getElementById('skillDetailName');
    const descEl = document.getElementById('skillDetailDescription');
    
    nameEl.textContent = skill.name;
    descEl.textContent = skill.description || '无描述';
    
    // 定位到悬停元素右侧
    const rect = element.getBoundingClientRect();
    
    popover.style.top = `${rect.top}px`;
    popover.style.left = `${rect.right + 10}px`;
    popover.style.display = 'block';
}

function closeSkillDetail() {
    document.getElementById('skillDetailPopover').style.display = 'none';
}

// ==================== 删除功能 ====================

function toggleDeleteMode() {
    skillDeleteMode = !skillDeleteMode;
    updateDeleteButton();
    renderSkillList();
}

function updateDeleteButton() {
    const btn = document.getElementById('btnToggleDelete');
    if (skillDeleteMode) {
        btn.textContent = '✓ 完成';
        btn.classList.add('active');
    } else {
        btn.textContent = '🗑 删除';
        btn.classList.remove('active');
    }
}

function requestDeleteSkill(skillName) {
    currentSkillToDelete = skillName;
    document.getElementById('deleteSkillName').textContent = skillName;
    document.getElementById('skillDeleteConfirmModal').classList.add('show');
}

function cancelDelete() {
    document.getElementById('skillDeleteConfirmModal').classList.remove('show');
    currentSkillToDelete = null;
}

async function confirmDelete() {
    if (!currentSkillToDelete) return;
    
    try {
        const response = await fetch(`/api/skills/${currentSkillToDelete}`, {
            method: 'DELETE'
        });
        
        const result = await response.json();
        
        if (result.success) {
            // 删除成功，刷新列表
            await loadSkillList();
            cancelDelete();
        } else {
            showError('删除失败: ' + result.error);
        }
    } catch (error) {
        console.error('删除 Skill 失败:', error);
        showError('删除失败: ' + error.message);
    }
}

// ==================== 导入功能 ====================

function triggerSkillImport() {
    document.getElementById('skillFolderInput').click();
}

async function handleSkillFolderSelect(event) {
    const files = event.target.files;
    if (!files || files.length === 0) {
        return;
    }
    
    // 计算总大小
    let totalSize = 0;
    for (let file of files) {
        totalSize += file.size;
    }
    
    // 检查大小限制 (5MB)
    if (totalSize > 5 * 1024 * 1024) {
        showError('文件夹大小超过 5MB 限制');
        event.target.value = ''; // 清空选择
        return;
    }
    
    // 查找 SKILL.md 文件
    let skillMdFile = null;
    let skillMdContent = null;
    let scripts = [];
    
    for (let file of files) {
        if (file.name === 'SKILL.md') {
            skillMdFile = file;
            skillMdContent = await file.text();
        } else if (file.webkitRelativePath.includes('scripts/') && file.name.endsWith('.py')) {
            scripts.push({
                filename: file.name,
                content: await file.text()
            });
        }
    }
    
    // 验证 SKILL.md 存在
    if (!skillMdFile) {
        showError('文件夹中必须包含 SKILL.md 文件');
        event.target.value = '';
        return;
    }
    
    // 验证 frontmatter
    const frontmatterRegex = /^---\s*\n([\s\S]*?)\n---/;
    const match = skillMdContent.match(frontmatterRegex);
    
    if (!match) {
        showError('SKILL.md 必须包含 YAML frontmatter (--- 包裹的内容)');
        event.target.value = '';
        return;
    }
    
    const frontmatter = match[1];
    const hasName = /^name:\s*.+/m.test(frontmatter);
    const hasDescription = /^description:\s*.+/m.test(frontmatter);
    
    if (!hasName || !hasDescription) {
        showError('SKILL.md 的 frontmatter 中必须包含 name 和 description 字段');
        event.target.value = '';
        return;
    }
    
    // 提取 skill name
    const nameMatch = frontmatter.match(/^name:\s*(.+)/m);
    const skillName = nameMatch ? nameMatch[1].trim() : null;
    
    if (!skillName) {
        showError('无法从 SKILL.md 中提取 skill 名称');
        event.target.value = '';
        return;
    }
    
    // 检查是否同名已存在
    if (installedSkills.some(s => s.name === skillName)) {
        showError(`Skill "${skillName}" 已存在，无法重复导入`);
        event.target.value = '';
        return;
    }
    
    // 提交导入
    try {
        const response = await fetch('/api/skills/import', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                skillName: skillName,
                skillContent: skillMdContent,
                scripts: scripts
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            // 导入成功，刷新列表
            await loadSkillList();
            // 清空文件选择
            event.target.value = '';
        } else {
            showError('导入失败: ' + result.error);
        }
    } catch (error) {
        console.error('导入 Skill 失败:', error);
        showError('导入失败: ' + error.message);
    }
}

// ==================== 错误提示 ====================

function showError(message) {
    document.getElementById('skillErrorMessage').textContent = message;
    document.getElementById('skillErrorModal').classList.add('show');
}

function closeErrorModal() {
    document.getElementById('skillErrorModal').classList.remove('show');
}
