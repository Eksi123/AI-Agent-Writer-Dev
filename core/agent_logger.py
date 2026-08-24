import logging
import time
import os

BASE_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

LOG_PATH = os.path.join(BASE_PATH, "log")
if not os.path.exists(LOG_PATH):
    os.mkdir(LOG_PATH)

class Logger():
    def __init__(self):
        self.logname = os.path.join(LOG_PATH, "{}.log".format(time.strftime("%Y%m%d")))
        self.logger = logging.getLogger("log")
        self.logger.setLevel(logging.DEBUG)
        self.formater = logging.Formatter(
            '[%(asctime)s][%(filename)s %(lineno)d][%(levelname)s]: %(message)s')

        # 同时输出到文件和控制台
        self.filelogger = logging.FileHandler(self.logname, mode='a', encoding="UTF-8")
        self.filelogger.setLevel(logging.DEBUG)
        self.filelogger.setFormatter(self.formater)
        self.console = logging.StreamHandler()
        self.console.setLevel(logging.DEBUG)
        self.console.setFormatter(self.formater)

        self.logger.addHandler(self.filelogger)
        self.logger.addHandler(self.console)


# 全局 logger 实例，其他模块直接 import 使用
logger = Logger().logger

if __name__ == '__main__':
    logger.info("---日志采集开始---")
    logger.debug("---日志采集结束---")
