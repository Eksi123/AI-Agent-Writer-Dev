"""
AI Agent Writer - 主入口
"""
from core.agent_llm import create_llm_client
from core.logger import logger


def main():
    """主函数"""
    # 创建 LLM 客户端
    llm = create_llm_client()
    
    # 设置系统提示词
    llm.set_system_prompt("你是一个智能车辆助手，可以帮助用户控制车辆设备和查询车辆状态。")
    
    print("\n欢迎使用 AI Agent Writer！输入 'quit' 或 'exit' 退出。")
    print("-" * 50)
    
    while True:
        try:
            user_input = input("\n请输入: ").strip()
            if not user_input:
                continue
            if user_input.lower() in ("quit", "exit", "q"):
                print("再见！")
                break
            
            # 添加用户消息
            llm.add_message("user", user_input)
            
            # 调用大模型
            response = llm.chat(llm.messages)
            
            # 添加助手回复到历史
            llm.add_message("assistant", response["content"])
            
            print(f"\nAgent: {response['content']}")
            
        except KeyboardInterrupt:
            print("\n再见！")
            break
        except Exception as e:
            logger.error(f"运行出错: {str(e)}")
            print(f"\n出错了: {str(e)}")


if __name__ == "__main__":
    main()
