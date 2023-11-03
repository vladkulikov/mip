from pool_helper.pool_helper import PoolHelper, CurrentVariant
from util_container.util_container import UtilContainer as utils
from time import sleep
from pipe_maker import PipeMaker
from copy import deepcopy
from table_helper import TableReader, TableWriter

import os
import subprocess
import json
import sys
import pathlib

class UniversalOptimizer:

    def __init__(self):

        self.x_ranges = [] 
        self.max_count = 0
        self.tunnel_name = ''
        self.direct_pipe = None
        self.reverse_pipe = None
        self.walker_modules_path = ''

    # Инициализация параметров МЭС
    def init(self, config):

        self.x_ranges = PoolHelper().x_ranges
            
        self.max_count = config['max_count']
        if self.max_count < 1:
            raise RuntimeError('invalid max count of steps')
        self.tunnel_name = config['tunnel_name']
        self.walker_modules_path = os.path.join(os.path.dirname(PoolHelper().walker_util_path), 
            'walker_modules')

    # Проверка первого запуска оптимизатора
    @staticmethod
    def initialized():

        return 'optimizer_type' in PoolHelper().ppool.dict

    # Запуск туннеля с задержкой
    def tunnel_starter(self, delay):

        tunnel_path = os.path.join(self.walker_modules_path, 'pipe_tunnel_starter', 'pipe_tunnel.py')
        command = f'"{sys.executable}" "{tunnel_path}" {self.tunnel_name}'
        process = subprocess.Popen(
            command,
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW,
            start_new_session=True
        )
        sleep(delay)
        self.direct_pipe = PipeMaker(self.tunnel_name, 'direct')
        self.reverse_pipe = PipeMaker(self.tunnel_name, 'reverse')

    # Формирование строки со значениями целевых функций и ограничений       
    def get_y_values_string(self, current_step):

        y_values = CurrentVariant().y_values
        values =[]
        constraints = []
        for y_value in y_values:
            if y_value['type'] == 'objective':
                values.append({"value": y_value['value']})
            if y_value['type'] == 'limit_le':
                constraints.append({"value": y_value['value']})

        output = {
            'input': {
                'status': 'process',
                'evaluations': {
                    'evaluation_index': current_step,
                    'functions': [{str(i): values[i]} for i in range(len(values))],
                    'constraints': [{str(i): constraints[i]} for i in range(len(constraints))]
                }
            }
        }
        return output

    # Запись списка лучших шагов в process_pool
    @staticmethod       
    def write_best_steps(best_steps):
    
        for best_step in best_steps:
            PoolHelper().selected_steps.append(best_step)

    # Запись новых варьируемых параметров и шага оптимизации в process_pool         
    def create_current_variant(self, input):

        x_values = input['variables']
        if len(self.x_ranges) != len(x_values):
            raise RuntimeError(
                'the X range list size "{}" does not correspond with X value list one {}'.format(
                    len(self.x_ranges), len(x_values)
                )
            )
            
        current_variant = CurrentVariant()
        current_variant.clear()
        current_variant.step = input['evaluation_index']
        
        for ind, variable in enumerate(x_values):
            x_value = {}
            x_range = self.x_ranges[ind]
            name = list(variable.keys())[0]
            x_value['name'] = name

            if 'type' in x_range:
                x_value['type'] = x_range['type']
            if 'ext_data' in x_range:
                x_value['ext_data'] = x_range['ext_data']
            x_value['value'] = float(variable[name]['value'])
            current_variant.x_values.append(x_value)

    # Проверка статуса оптимизации          
    def check_status(self, status):

        # Если исключение   
        if status == 'exception':
            return utils.exception

        # Если найден оптимум
        if status == 'finish':
            return utils.fail

        # Если получены варьируемые параметры           
        return utils.success
        
    def treat_retcode(self, retcode, input):
    
        if retcode == utils.success:
            self.create_current_variant(input['evaluations'])
            
        if retcode == utils.fail:
            self.write_best_steps(input['best_evaluation'])
            
        if retcode == utils.exception:
            raise RuntimeError('Optimizer error: {}'.format(input['error']))

    # Получение строк от оптимизатора       
    def receive(self): 
    
        with self.reverse_pipe.sender() as conn:
            with open('log.txt', 'a') as file:
                file.write('\n\nrecv mes ')
            output = json.loads(conn.recv())['output']
        return output

    # Отправка строк оптимизатору       
    def send(self, input): 
    
        with self.direct_pipe.receiver() as conn:
            with open('log.txt', 'a') as file:
                file.write('\nsend mes ')
            conn.send(json.dumps(input, ensure_ascii = False))

    # Формирование параметров конфигурации            
    def get_config(self, config):

        x_ranges = deepcopy(self.x_ranges)
        for x_range in x_ranges:
            del x_range['ext_data']
            del x_range['type']        
        output = {
            'options': config,
            'x_ranges': x_ranges,
        }
        return output

    # Выбор и запуск драйвера оптимизатора       
    def run_optimizer_driver(self, config):

        PoolHelper().ppool.dict['optimizer_type'] = config['type']
        options = self.get_config(config)
        
        wrapper_path = os.path.join(pathlib.Path(__file__).resolve().parent, config['type'], 'wrapper.py')
        
        environments = os.environ.copy()
        command = f'"{sys.executable}" "{wrapper_path}" "{str(options)}"'
        process = subprocess.Popen(
            command,
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW,
            start_new_session=True,
            env = environments
        )
			
    # Проверка лимита шагов         
    def check_steps_limit(self, current_step):
    
        return current_step + 1 > self.max_count

    # Первый вызов оптимизатора
    def first(self, config):

        # Открытие туннеля
        self.tunnel_starter(config['delay'])
        # Запуск оптимизатора
        self.run_optimizer_driver(config)

        # Получение строки с варьируемыми параметрами
        input = self.receive()       
        # Обработка кода завершения
        retcode = self.check_status(input['status'])
        self.treat_retcode(retcode, input)
        return retcode

    # Следующие вызовы оптимизатора     
    def next(self):
    
        current_step = CurrentVariant().step
        # Проверка лимита шагов
        if self.check_steps_limit(current_step):
            return utils.fail
        
        type = PoolHelper().ppool.dict['optimizer_type']
        self.direct_pipe = PipeMaker(self.tunnel_name, 'direct')
        self.reverse_pipe = PipeMaker(self.tunnel_name, 'reverse')

        # Формирование и отправка строки со значениями целевых функций      
        self.send(self.get_y_values_string(current_step))
        # Получение строки с варьируемыми параметрами
        input = self.receive()
        
        # Обработка кода завершения
        retcode = self.check_status(input['status'])
        self.treat_retcode(retcode, input)
        return retcode