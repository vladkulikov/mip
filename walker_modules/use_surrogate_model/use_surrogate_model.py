import os
import sys
import glob
import json
import subprocess
from pathlib import Path

from util_container.util_container import UtilContainer as utils
from pool_helper.pool_helper import PoolHelper, CurrentTask, InitTask


## Класс запуска
class UseSurrogateModel:
    def __init__(self, config):
        self._config = config
        ## Имя файла с результатами, полученными расчетным модулем.
        self._res_file_name = 'results.csv'
        ## Стартовая позиция для каждой строки, с который извлекаются данные из файла результатов. 
        self._offset_in_res = 2
        ## Путь к файлу суррогатной модели
        self._surrogate_model_path = 'surrogate.zip'
        ## Имя файла с входными данными 
        self._in_file_name = 'MtoAData.csv'
        ## Имя файла с выходными данными
        self._out_file_name = 'AtoMData.csv'
        ## Имя файла конфигурации
        self._cfg_file_name = 'config.json'
        ## Имя входного файла вариатора.
        self._variator_file_name = 'variator_context.json'

    def _create_input_file(self):
        with open(self._variator_file_name, 'r') as fh:
            steps = json.loads(fh.read())['variants']
        with open(self._in_file_name, 'w') as fout:
            for step in steps:
                fout.write(';'.join([str(step[i]) for i in range(len(step))]) + '\n')

    def _create_cfg_file(self):

        config = {
            'surrogate_model_path': self._surrogate_model_path,
            'action': 'evaluate_point',
            'out_file_path': self._out_file_name,
            'data_file_path': self._in_file_name
        }
        with open(self._cfg_file_name, 'w') as fh:
            fh.write(json.dumps(config, indent=4))


    def _create_configuration(self):
        # self._create_input_file()
        self._create_cfg_file()

    def _check_options(self):
        if not ((self._config['surrogate_model_path'].__contains__('/')) | (
                self._config['surrogate_model_path'].__contains__('\\'))):
            self._surrogate_model_path = self._get_absolute_path(self._config['surrogate_model_path'])
        else:
            self._surrogate_model_path = self._config['surrogate_model_path']
        if not ((self._config['in_file_name'].__contains__('/')) | (self._config['in_file_name'].__contains__('\\'))):
            self._in_file_name = self._get_absolute_path(self._config['in_file_name'])
        else:
            self._in_file_name = self._config['in_file_name']
        if not ((self._config['out_file_name'].__contains__('/')) | (self._config['out_file_name'].__contains__('\\'))):
            self._out_file_name = self._get_absolute_path(self._config['out_file_name'])
        else:
            self._out_file_name = self._config['out_file_name']

        if not os.path.exists(self._surrogate_model_path):
            sys.exit(1)
        if not os.path.exists(self._in_file_name):
            sys.exit(1)

        line_count = 0
        with open(self._in_file_name, 'r') as fh:
            line_count = len(fh.readlines())
        if line_count == 0:
            sys.exit(1)

    @staticmethod
    def _get_absolute_path(relative_path):
        return PoolHelper().ppool.root_path() + '/' + relative_path

    def _run(self):
        config_file_path = self._get_absolute_path(self._cfg_file_name)
        module_path = os.path.join(PoolHelper().walker_util_path, 'approximation-py', 'src', 'adapter', 'use_surrogate')
        if sys.platform.startswith('linux'):
            command = '"{}" "{}" "{}"'.format(
                PoolHelper().python_app,
                os.path.join(module_path, 'main.py'),
                config_file_path,
            )
        elif sys.platform.startswith('win32'):
            path_python = PoolHelper().walker_util_path.replace('walker_utils', 'integrator')

            command = '"{}" "{}" "{}"'.format(
                os.path.join(path_python, 'python37', PoolHelper().python_app),
                os.path.join(module_path, r'main.py'),
                config_file_path,
            )
        else:
            raise RuntimeError(
                LC("Error: file {} not exist.").format(self._out_file_name)
            )
        process = subprocess.Popen(
            command,
            creationflags=0x08,
            close_fds=True
        )
        process.wait()
        if process.returncode != 0:
            raise RuntimeError(LC('command "{}" launch complete with error').format(command))

        try:
            # если выходной файл аппроксиматора пустой, нормально завершаем работу
            if os.path.getsize(self._out_file_name) == 0:
                sys.exit(1)
        except OSError:
            raise RuntimeError(
                LC("Error: file {} not exist.").format(self._out_file_name)
            )

    def process(self):
        self._check_options()
        self._create_configuration()
        self._run()
