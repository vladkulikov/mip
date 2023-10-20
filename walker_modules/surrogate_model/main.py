import sys
import json

from surrogate_model import SurrogateModel

from error_handler import error_handler
from interrupter.interrupter import Interrupter

try:
    from localization.localization import *
    tr = LocaleHelper().set_locale(__file__)
except:
    tr = lambda msg : msg

from pool_helper import PoolHelper

def main(config_file):
    # Загружаем конфигурационный файл
    with open(config_file, 'r') as file:
        config = json.loads(file.read())['internal']
    # Запускаем решатель
    approx = SurrogateModel(config)
    approx.process()

# Блок корректной очистки Singletons (эмуляция деструкторов) во время выхода из скрипта
from pool_context_container import PoolContextContainer
import atexit
@atexit.register
def main_exit():
    PoolContextContainer().clear()


if __name__ == '__main__':
    try:
        if len(sys.argv) != 2:
            raise RuntimeError(tr('an config_file is waiting in the command line'))
        main(sys.argv[1])
    except Exception:
        error_handler.log_exception()
        Interrupter().terminate()
    else:
        sys.exit(0)
