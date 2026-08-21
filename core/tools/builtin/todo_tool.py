"""
任务清单工具
"""
import json
import os
from typing import List, Dict
from langchain_core.tools import tool


# 任务清单存储文件
TODO_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "todo.json")


def _load_todos() -> List[Dict]:
    """加载任务清单"""
    if not os.path.exists(TODO_FILE):
        return []
    
    try:
        with open(TODO_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return []


def _save_todos(todos: List[Dict]) -> None:
    """保存任务清单"""
    with open(TODO_FILE, 'w', encoding='utf-8') as f:
        json.dump(todos, f, ensure_ascii=False, indent=2)


@tool
def manage_todo(action: str, task_id: int = -1, title: str = "", status: str = "") -> str:
    """
    管理任务清单：创建、更新、删除或查看任务
    
    Args:
        action: 操作类型 - "add"(添加), "update"(更新状态), "delete"(删除), "list"(列出所有)
        task_id: 任务 ID（update/delete 时必需）
        title: 任务标题（add 时必需）
        status: 任务状态 - "pending"(待办), "in_progress"(进行中), "completed"(已完成)
    
    Returns:
        操作结果信息
    """
    try:
        todos = _load_todos()
        
        if action == "add":
            if not title:
                return "错误: 添加任务时必须提供 title"
            
            # 生成新 ID
            new_id = max([t["id"] for t in todos], default=0) + 1
            
            new_todo = {
                "id": new_id,
                "title": title,
                "status": "pending"
            }
            todos.append(new_todo)
            _save_todos(todos)
            
            return f"成功: 添加任务 #{new_id} - {title}"
        
        elif action == "update":
            if task_id < 0:
                return "错误: 更新任务时必须提供有效的 task_id"
            
            if status not in ["pending", "in_progress", "completed"]:
                return "错误: status 必须是 pending, in_progress, completed 之一"
            
            for todo in todos:
                if todo["id"] == task_id:
                    todo["status"] = status
                    _save_todos(todos)
                    return f"成功: 更新任务 #{task_id} 状态为 {status}"
            
            return f"错误: 任务 #{task_id} 不存在"
        
        elif action == "delete":
            if task_id < 0:
                return "错误: 删除任务时必须提供有效的 task_id"
            
            original_count = len(todos)
            todos = [t for t in todos if t["id"] != task_id]
            
            if len(todos) == original_count:
                return f"错误: 任务 #{task_id} 不存在"
            
            _save_todos(todos)
            return f"成功: 删除任务 #{task_id}"
        
        elif action == "list":
            if not todos:
                return "任务清单为空"
            
            lines = ["任务清单:"]
            for todo in todos:
                status_icon = {
                    "pending": "○",
                    "in_progress": "◐",
                    "completed": "●"
                }.get(todo["status"], "?")
                
                lines.append(f"  #{todo['id']} [{status_icon}] {todo['title']}")
            
            return '\n'.join(lines)
        
        else:
            return f"错误: 未知的 action - {action}，必须是 add, update, delete, list 之一"
    
    except Exception as e:
        return f"错误: 操作任务清单失败 - {str(e)}"
