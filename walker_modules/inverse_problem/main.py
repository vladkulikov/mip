import sys
import json

from inverse_optimizer import InverseOptimizer

from util_container.util_container import UtilContainer as utils
from error_handler import error_handler


def main(config_file):
    with open(config_file, 'r') as file:
        config = json.loads(file.read())['internal']
    optim = InverseOptimizer()
    optim.init(config)
    # Первый вызов оптимизатора с формированием файла конфигурации
    if not optim.initialized():
        return optim.first(config)
    # Вызов оптимизатора с обработкой целевых функций
    else:
        return optim.next()


# Блок корректной очистки Singletons (эмуляция деструкторов) во время выхода из скрипта
from pool_context_container.pool_context_container import PoolContextContainer
import atexit


@atexit.register
def main_exit():
    PoolContextContainer().clear()


if __name__ == '__main__':
    try:
        if len(sys.argv) != 2:
            raise RuntimeError('a config_file is waiting in the command line')
        sys.exit(main(sys.argv[1]))
    except Exception:
        error_handler.log_exception()
        sys.exit(utils.exception)
