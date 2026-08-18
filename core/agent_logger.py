import logging
import time
import os

BASE_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

LOG_PATH = os.path.join(BASE_PATH, "log") # 定义日志文件路径
if not os.path.exists(LOG_PATH):
    os.mkdir(LOG_PATH)

class Logger():
    def __init__(self):
        self.logname = os.path.join(LOG_PATH, "{}.log".format(time.strftime("%Y%m%d"))) #日志名
        self.logger = logging.getLogger("log") #日志采集器
        self.logger.setLevel(logging.DEBUG) #日志等级
        self.formater = logging.Formatter( #日志格式
            '[%(asctime)s][%(filename)s %(lineno)d][%(levelname)s]: %(message)s')

        # 文件日志
        self.filelogger = logging.FileHandler(self.logname, mode='a', encoding="UTF-8")
        self.filelogger.setLevel(logging.DEBUG)
        self.filelogger.setFormatter(self.formater)
        # 终端日志
        self.console = logging.StreamHandler()
        self.console.setLevel(logging.DEBUG)
        self.console.setFormatter(self.formater)

        self.logger.addHandler(self.filelogger)
        self.logger.addHandler(self.console)


logger = Logger().logger

if __name__ == '__main__':
    logger.info("---日志采集开始---")
    logger.debug("---日志采集结束---")
