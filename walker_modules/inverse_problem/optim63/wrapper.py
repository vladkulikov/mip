import os
import subprocess
import json
import sys
import glob
import shutil
import psutil
import numpy as np
from time import sleep
from xml.etree import ElementTree as et

from values import X_Value, Y_Value, indent
from pipe_maker.pipe_maker import PipeMaker
from table_helper.table_helper import TableReader, TableWriter


# проверка существования процесса оптимизатора
def check_opt():
    with open("pid_optimizer.txt", 'r') as file:
        pid = file.readline()
    if psutil.pid_exists(int(pid)):
        return True
        

class CurrentVariants:
    cfg_file_name = 'inverse_problem_config.json'
    input_name = 'input.csv'
    output_name = 'output.csv'
    history_name = 'history.csv'
    optimum_name = 'opt_step.csv'
    finish_name = 'finish_state.txt'

    def __init__(self):
        self.x_values = []
        self.y_values = []

        self.adapter_path = ''

        self.direct_pipe = None
        self.reverse_pipe = None

        self.max_count = 0
        self.current_pointnum = 0

        self.point_name = 'points.csv'
        self.metric = ''
        self.method = ''
        self.tunnel_name = ''

    # Конфигурация оптимизатора        
    def init(self, config):
        options = config['options']
        self.max_count = options['max_count']

        self.method = options['selection_method']
        self.metric = options['metric']
        self.adapter_path = options['adapter_path']

        self.tunnel_name = options['tunnel_name']
        self.direct_pipe = PipeMaker(self.tunnel_name, 'direct')
        self.reverse_pipe = PipeMaker(self.tunnel_name, 'reverse')

        self.x_values = self.get_x_values(config['x_ranges'])
        self.y_values = self.get_y_values(options['count_crit'], options['count_lim'])

    # Получение строк от оптимизатора
    def receive(self):
        with self.direct_pipe.sender() as conn:
            with open('log.txt', 'a') as file:
                file.write('\n\nrecv opt ')
            input = json.loads(conn.recv())['input']
        return input

    # Отправка строк оптимизатору
    def send(self, input):
        with self.reverse_pipe.receiver() as conn:
            with open('log.txt', 'a') as file:
                file.write('\n\nsend opt ')
            conn.send(json.dumps(input, ensure_ascii=False))

    def get_x_values(self, ranges):
        if len(ranges) < 1:
            raise RuntimeError('the range list size is not valid')
        result = []
        for ind, item in enumerate(ranges):
            x = X_Value(ind)
            x.init(item)
            result.append(x)
        return result

    def get_y_values(self, count_crit, count_lim):
        if count_crit < 1:
            raise RuntimeError('the function is not valid')
        result = []

        for i in range(count_crit):
            y = Y_Value(i, str(i))
            y.init(0)
            result.append(y)

        for i in range(count_lim):
            y = Y_Value(i + count_crit, str(i))
            y.init(1)
            result.append(y)

        return result

    # Получение X из файла оптимизатора
    def create_current_variant(self):
        current_x_values = TableReader(self.point_name)._table_to_tuple(-1)
        current_x_values = [float(current_x_value) for current_x_value in current_x_values]

        with open(self.input_name, 'a') as file:
            file.write(';'.join([str(value) for value in current_x_values]) + '\n')
        os.remove(self.point_name)

        for ind, x_value in enumerate(self.x_values):
            x_value.value = current_x_values[ind]

    # Формирование строки с X
    def create_response(self):
        values = []
        for x_value in self.x_values:
            values.append({x_value.name: {"value": x_value.value}})
        output = {
            'output': {
                'status': 'process',
                'evaluations': {
                    'evaluation_index': int(self.current_pointnum),
                    'variables': values
                }
            }
        }
        return output

    # Обработка строки с Y
    def get_current_variant(self, input):
        current_y_values = input['evaluations']['functions']
        current_constraints = input['evaluations']['constraints']

        for current_y_value in current_y_values:
            name = list(current_y_value.keys())[0]
            for y_value in self.y_values:
                if (name == y_value.name) and (y_value.type == 0):
                    y_value.value = current_y_value[name]['value']
                    break

        for current_constraint in current_constraints:
            name = list(current_constraint.keys())[0]
            for y_value in self.y_values:
                if (name == y_value.name) and (y_value.type == 1):
                    y_value.value = current_constraint[name]['value']
                    break

    # Запись файла конфигурации
    def create_config(self, config):
        budget = self.max_count
        if budget < 1:
            budget = 1
        x_bounds = [[x_value.begin, x_value.end] for x_value in self.x_values]
        p_bounds = x_bounds[-int(config['p_count']):]

        cfg_config = {
            'model': {
                'x_dim': len(self.x_values),
                'y_dim': len(self.y_values),
                'x_bounds': x_bounds,
                'y_names': [y_value.name for y_value in self.y_values if y_value.type == 0]
            },
            'p_count': config['p_count'],
            'p_bounds': p_bounds,
            'true_data': config['points_path'],
            'metric': self.metric,
            "optimization_method": {
                'optimization_method': self.method,
                self.method: {
                    'model': {
                        'x_dim': len(p_bounds),
                        'y_dim': 1,
                        'x_bounds': p_bounds,
                        'y_names': [self.metric]
                    },
                    'evaluate_file_path': self.point_name,
                    'out_file_path': self.input_name,
                    'data_file_path': self.output_name,
                    'max_iteration': budget,
                    'accuracy_x': 0,
                    'accuracy_y': 0,
                    'sampling_method': config['sampling_method'],
                    'number_of_ineffective_steps': config['count_ineff']
                }
            }
        }
        with open(self.cfg_file_name, 'w') as file:
            file.write(json.dumps({'inverse_problem': cfg_config}, indent=4))

    # Запись Y в файл оптимизатора
    def create_out(self):
        output = [x_value.value for x_value in self.x_values] + [y_value.value for y_value in self.y_values]
        with open(self.history_name, 'a') as file:
            file.write(';'.join([str(value) for value in output]) + '\n')
        with open(self.output_name, 'w') as file:
            file.write(';'.join([str(value) for value in output]) + '\n')

    # Проверка условий завершения
    def finished(self):
        # Нормальный выход по количеству итераций
        if self.current_pointnum + 1 > self.max_count:
            sleep(3)
            return True
           
        # Нормальный выход по нахождению оптимума
        while os.path.exists(self.output_name):
            if not check_opt():
                return True
            sleep(1)

        while not os.path.exists(self.point_name):
            if not check_opt():
                return True
            sleep(1)
        with open(self.point_name, 'r') as file:
            lines = file.readlines()
        if len(lines) == 0:
            sleep(3)
            return True
        return False

    # Формирование сообщения о нормальном завершении
    def create_finish_message(self):
        with open(self.optimum_name, 'r') as file:
            best_steps = file.read().strip('\n')
        output = {
            'output': {
                'status': 'finish',
                'best_evaluation': [int(best_steps)]
            }
        }
        return output

    # Вызов оптимизатора
    def call_optimizer(self):
        command = '"{}" "{}" "{}"'.format(
            sys.executable,
            os.path.join(self.adapter_path, 'main_inverse_problem.py'),
            os.path.join(os.getcwd(), self.cfg_file_name)
        )

        proc = subprocess.Popen(
            command,
            creationflags=subprocess.CREATE_NO_WINDOW,
            close_fds=True
        )
        pid = proc.pid
        with open("pid_optimizer.txt", 'a') as file:
            file.write(str(pid) + '\n' + str(os.getpid()))

    # Обработка входных и выходных файлов оптимизатора
    def process(self):
        while True:
            if self.finished():
                self.send(self.create_finish_message())
                break
            self.create_current_variant()
            self.send(self.create_response())
            self.get_current_variant(self.receive())
            self.create_out()
            self.current_pointnum += 1


def main(config):
    current_variant = CurrentVariants()
    current_variant.init(config)
    current_variant.create_config(config['options'])
    current_variant.call_optimizer()
    current_variant.process()


if __name__ == '__main__':
    try:
        if len(sys.argv) != 2:
            raise RuntimeError('config is waiting in the command line')
        sys.exit(main(eval(sys.argv[1])))
    except Exception:
        sys.exit(-1)
