/**
 * project.js - 项目管理
 * 
 * 包含项目的增删改查、导入导出、切换等功能。
 */

// 加载项目列表
async function loadProjects() {
    try {
        const response = await fetch('/api/projects');
        const result = await response.json();
        
        if (result.success) {
            renderProjectList(result.data.projects, result.data.current);
        }
    } catch (error) {
        console.error('加载项目失败:', error);
    }
}

// 渲染项目列表
function renderProjectList(projects, currentProjectName) {
    const list = document.getElementById('projectList');
    list.innerHTML = '';
    
    projects.forEach(project => {
        const li = document.createElement('li');
        li.className = 'project-item' + (project === currentProjectName ? ' active' : '');
        li.innerHTML = `
            <span class="project-icon">📖</span>
            <span class="project-name">${project}</span>
            <button class="btn-more" onclick="event.stopPropagation(); toggleProjectMenu(event, '${project}')">⋮</button>
        `;
        li.onclick = () => switchProject(project);
        list.appendChild(li);
    });

    // 更新当前项目显示
    if (currentProjectName) {
        currentProject = currentProjectName;
        document.getElementById('currentProject').textContent = currentProjectName;
        loadOutline();
        loadChapterTree();
    }
}

// 切换项目菜单
function toggleProjectMenu(event, projectName) {
    event.stopPropagation();
    
    // 关闭已打开的菜单
    const existingMenu = document.querySelector('.project-menu');
    if (existingMenu) {
        existingMenu.remove();
        return;
    }
    
    // 创建新菜单
    const menu = document.createElement('div');
    menu.className = 'project-menu';
    menu.innerHTML = `
        <div class="project-menu-item" onclick="exportProject('${projectName}')">📤 导出项目</div>
        <div class="project-menu-item danger" onclick="deleteProject('${projectName}')">🗑️ 删除项目</div>
    `;
    
    // 定位菜单
    const rect = event.target.getBoundingClientRect();
    menu.style.left = rect.left + 'px';
    menu.style.top = (rect.bottom + 5) + 'px';
    menu.style.position = 'fixed';
    
    document.body.appendChild(menu);
    
    // 点击其他地方关闭菜单
    setTimeout(() => {
        document.addEventListener('click', function closeMenu() {
            menu.remove();
            document.removeEventListener('click', closeMenu);
        }, { once: true });
    }, 0);
}

// 导出项目
async function exportProject(projectName) {
    try {
        const response = await fetch(`/api/projects/${projectName}/export`);
        
        if (!response.ok) {
            throw new Error('导出失败');
        }
        
        // 获取ZIP文件并下载
        const blob = await response.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${projectName}.zip`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        
        addMessage('info', `✓ 项目 ${projectName} 已导出为ZIP`);
    } catch (error) {
        console.error('导出项目失败:', error);
        alert('导出失败: ' + error.message);
    }
}

// 删除项目
async function deleteProject(projectName) {
    if (!confirm(`确定要删除项目 "${projectName}" 吗？\n此操作不可恢复，所有数据将被永久删除！`)) {
        return;
    }
    
    try {
        const response = await fetch(`/api/projects/${projectName}`, {
            method: 'DELETE'
        });
        const result = await response.json();
        
        if (result.success) {
            addMessage('info', `✓ 项目 ${projectName} 已删除`);
            
            // 如果删除的是当前项目，清空显示
            if (currentProject === projectName) {
                currentProject = null;
                document.getElementById('currentProject').textContent = '未选择项目';
                document.getElementById('outlinePreview').innerHTML = '请先选择项目';
                document.getElementById('chaptersContent').innerHTML = '请先选择项目';
            }
            
            await loadProjects();
        } else {
            alert('删除失败: ' + result.error);
        }
    } catch (error) {
        console.error('删除项目失败:', error);
        alert('删除失败: ' + error.message);
    }
}

// 刷新大纲
async function refreshOutline() {
    if (!currentProject) return;
    await loadOutline();
    addMessage('info', '✓ 大纲已刷新');
}

// 刷新章节
async function refreshChapters() {
    if (!currentProject) return;
    await loadChapterTree();
    addMessage('info', '✓ 章节列表已刷新');
}

// 创建新小说
async function createProject() {
    const name = prompt('请输入小说名称:');
    if (!name) return;

    try {
        const response = await fetch('/api/projects', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name })
        });
        
        const result = await response.json();
        
        if (result.success) {
            await loadProjects();
            addMessage('info', `✓ 小说 ${name} 已创建（大纲已用模板初始化）`);
        } else {
            alert('创建失败: ' + result.error);
        }
    } catch (error) {
        console.error('创建小说失败:', error);
        alert('创建失败: ' + error.message);
    }
}

// 导入大纲
function importProject() {
    document.getElementById('fileInput').click();
}

// 处理文件上传
async function handleFileUpload(event) {
    const file = event.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await fetch('/api/projects/import', {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (result.success) {
            await loadProjects();
            addMessage('info', `✓ 大纲 ${result.data.name} 已导入`);
        } else {
            alert('导入失败: ' + result.error);
        }
    } catch (error) {
        console.error('导入大纲失败:', error);
        alert('导入失败: ' + error.message);
    }

    // 清空文件输入
    event.target.value = '';
}

// 切换项目
async function switchProject(projectName) {
    try {
        const response = await fetch(`/api/projects/${projectName}/switch`, {
            method: 'POST'
        });

        const result = await response.json();
        
        if (result.success) {
            currentProject = projectName;
            document.getElementById('currentProject').textContent = projectName;
            await loadProjects(); // 刷新列表
            loadOutline();
            loadChapterTree();
            addMessage('info', `✓ 已切换到项目: ${projectName}`);
        }
    } catch (error) {
        console.error('切换项目失败:', error);
    }
}
