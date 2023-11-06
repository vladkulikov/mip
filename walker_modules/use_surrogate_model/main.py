import sys
import json

from use_surrogate_model import UseSurrogateModel

from error_handler import error_handler
from interrupter.interrupter import Interrupter

from pool_helper import PoolHelper

def main(config_file):
    # Загружаем конфигурационный файл
    with open(config_file, 'r') as file:
        config = json.loads(file.read())['internal']
    # Запускаем решатель
    calc = UseSurrogateModel(config)
    calc.process()

# Блок корректной очистки Singletons (эмуляция деструкторов) во время выхода из скрипта
from pool_context_container import PoolContextContainer
import atexit
@atexit.register
def main_exit():
    PoolContextContainer().clear()


if __name__ == '__main__':
    try:
        main(sys.argv[1])
    except Exception:
        error_handler.log_exception()
        Interrupter().terminate()
    else:
        sys.exit(0)
