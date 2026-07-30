import os
import openai
import configparser

BASE_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

config = configparser.ConfigParser()
config.read(os.path.join(BASE_PATH, "config.ini"),encoding="utf-8-sig")

llm_base_url = config.get("llllm_api_aliyun","base_url")
llm_api_key = config.get("llllm_api_aliyun","api_key")
llm_model = config.get("llllm_api_aliyun","model")

# 自定义大模型客户端
class AgentLLM():
    def __init__(self,base_url,api_key,model):
        self.client = openai.OpenAI(
            api_key = api_key,
            base_url = base_url,
            timeout = 30
        )
        self.model = model

    def chat(self,prompt, max_tokens=1000, temperature=0.5):
        try:
            response = self.client.chat.completions.create(
                model=self.model,      # 当前大模型厂商可选model
                messages=[{"role": "user", "content": prompt}],  # role通常分为user和assistant两种类型
                max_tokens=max_tokens,    # 最大输出长度
                temperature=temperature   # temperature越高，模型输出越随机化
            )
            return response.choices[0].message.content
        except Exception as error:
            self.handle_error(error)

    def handle_error(self, error: Exception):
        if isinstance(error, openai.APITimeoutError):
            logger.info("错误！大模型请求超时".format(self.timeout))
        elif isinstance(error, openai.APIConnectionError):
            logger.info("错误！大模型连接失败")
        elif isinstance(error, openai.AuthenticationError):
            logger.info("错误！大模型api_key错误")
        else:
            logger.info("错误!详情为{} ".format(error))

agent_llm = AgentLLM(base_url=llm_base_url,
                      api_key=llm_api_key,
                      model=llm_model)


if __name__ == '__main__':
    prompt = """
    当前车况：{主驾座椅通风(打开);主驾座椅加热(关闭)}
    下发指令："主驾座椅按摩(打开)"
    车主query："我的腿好冷"
    
    根据query评估一下这个指令下发的合理吗，10分给几分（直接说分数值，不用带‘分’）
    """
    response = agent_llm.chat(prompt)
    print(response)