import os
import sys
import glob
import json
import subprocess

# from pathlib import Path

try:
    from localization.localization import *
    tr = LocaleHelper().set_locale(__file__)
except:
    tr = lambda msg : msg
from pool_helper.pool_helper import PoolHelper, CurrentTask, InitTask


## Класс запуска аппроксиматора.
class SurrogateModel:
    def __init__(self, config):
        self._config = config
        ## Имя файла с результатами, полученными расчетным модулем.
        self._res_file_name = 'results.csv'
        ## Стартовая позиция для каждой строки, с который извлекаются данные из файла результатов. 
        self._offset_in_res = 0
        ## Имя файла с входными данными для аппроксиматора
        self._in_file_name = 'MtoAData.csv'
        ## Имя файла с выходными данными от аппроксиматора
        self._out_file_name = 'AtoMData.csv'
        ## Имя файла конфигурации аппроксиматора.
        self._cfg_file_name = 'config.json'
        ## Имя файла суррогатной модели.
        self._archive_file_name = 'surrogate_model.zip'
        ## Имя входного файла вариатора.
        self._variator_file_name = 'variator_context.json'
        ## Хранит порядок следования входных переменных в init_pool.
        self._x_order_init = [val['name'] if val['name'] in self._config['x_values'] else float(val['begin']) for val in
                              PoolHelper().x_ranges]
        ## Хранит порядок следования входных переменных во входном файле аппроксиматора.
        self._x_order_opt = list()
        ## Имя файла, которых хранит количество шагов, выполненное расчетным модулем.
        self._steps_file_name = 'steps_per_stage.csv'
        ## Номера шагов расчета на текущей стадии, начальный и следующий за последним
        self._steps_in_stage = self._get_steps_in_stage()

    def _get_steps_in_stage(self):
        try:
            # читаем из контекста вариатора индекс следующего элемента,
            # с этого индекса начнется счет на следующей стадии
            with open(self._variator_file_name, 'r') as fh:
                next_step = json.loads(fh.read())['index']
            # вычисляем номер первого шага на текущей стадии
            if not os.access(self._steps_file_name, os.R_OK):
                first_step = 0
            else:
                with open(self._steps_file_name, 'r') as fh:
                    first_step = fh.readlines()[-1]
            return first_step, next_step
        except Exception:
            raise RuntimeError(tr("Can't to get steps in stage."))

    @staticmethod
    def _get_targets_name():
        # проверяем конфигурационные файлы всех модулей и находим
        # конфиг модуля table_y_extractor, из которого извелкаем значения
        t = None
        for file_name in glob.glob(os.path.join(PoolHelper().walker_data, '*.json')):
            try:
                with open(file_name, 'r') as fh:
                    params = json.loads(fh.read())
                if params['external']['module_name'] == 'table_y_extractor':
                    t = [item['name'] for item in params['internal']['items']]
                    break
            except Exception:
                pass
        if t:
            return t
        raise RuntimeError(tr("Target values not exist."))

    def _parse_vars(self, vars_str):
        names = []
        markers = []
        indexes = []
        # targets = self._get_targets_name()
        targets = self._config['y_values']
        for n, var_name in enumerate(vars_str):
            for var_x in PoolHelper().x_ranges:
                # if var_x['name'] == var_name and var_x['type'] == 'void': #len(var_x['values']) > 1:
                if var_x['name'] == var_name and var_x['name'] in self._config['x_values']:  # len(var_x['values']) > 1:
                    names.append(var_name)
                    markers.append('C')
                    indexes.append(n)
                    self._x_order_opt.append(var_name)
                    break
            if var_name in targets:
                names.append(var_name)
                markers.append('F')
                indexes.append(n)
        return names, markers, indexes

    def _create_input_file(self, fin, idx):
        with open(self._in_file_name, 'w') as fout:
            for row in fin:
                if not row.strip():
                    continue
                row_split = row.strip().split(';')
                fout.write(';'.join([str(row_split[_ + self._offset_in_res]) for _ in idx]) + '\n')

    def _create_cfg_file(self):
        if self._config['method'] == 'KrigingSampler':
            config = {'surrogate_method': self._config['method'],
                self._config['method'] : {
                    'max_iteration': self._config['attempt'],
                    'current_iteration': self._get_attempt_count(self._steps_file_name),
                    'out_file_path': self._get_absolute_path(self._out_file_name),
                    'data_file_path': self._get_absolute_path(self._in_file_name),
                    'archive_path': self._get_absolute_path('kriging_model.zip'),
                    'model': {
                        'x_dim': len(self._config['x_values']),
                        'y_dim': len(self._config['y_values']),
                        'x_name': self._config['x_values'],
                        'y_name': self._config['y_values'],
                        'x_bounds': [[x_range['begin'], x_range['end']] for x_range in PoolHelper().x_ranges]
                    },
                    'count_start_points': self._config['start_points'],
                    'count_request_points': self._config['request_points'],
                    'count_of_grid_nodes': self._config['grid_nodes'],
                    'min_distance_between_points': self._config['min_distance'],
                    'sparsity_weight': self._config['sparsity_weight'],
                    'distanceX_weight': self._config['distanceX_weight'],
                    'deltaF_weight': self._config['deltaF_weight'],
                    'min_error': self._config['min_error'],
                    'sampling_method': self._config['sampling_method'],
                    'surrogate_type': self._config['surrogate_type'],
                    'x_limits': [{
                        'name': x_range['name'],
                        'min': x_range['begin'],
                        'max': x_range['end']
                    } for x_range in PoolHelper().x_ranges],
                }
            }
        if self._config['method'] == 'VAE':
            config = {'surrogate_method': self._config['method'],
                self._config['method'] : {
                    'max_iteration': self._config['attempt'],
                    'current_iteration': self._get_attempt_count(self._steps_file_name),
                    'out_file_path': self._get_absolute_path(self._out_file_name),
                    'data_file_path': self._get_absolute_path(self._in_file_name),
                    'surrogate_model_paths': self._config['old_model'],
                    'model': {
                        'x_dim': len(self._config['x_values']),
                        'y_dim': len(self._config['y_values']),
                        'x_name': self._config['x_values'],
                        'y_name': self._config['y_values'],
                        'x_bounds': [[x_range['begin'], x_range['end']] for x_range in PoolHelper().x_ranges]
                    },
                    'n_sampling': self._config['n_sampling'],
                    'vae_path': self._config['vae_path'],
                    'save_vae_path': self._get_absolute_path('vae.zip'),
                    'save_surrogate_model_path': self._get_absolute_path('vae_model.zip'),
                    'sampling_method': self._config['sampling_method'],
                    'model_type': 'small',
                }
            }
        with open(self._cfg_file_name, 'w') as fh:
            fh.write(json.dumps({'surrogate': config}, indent = 4))

    def _create_configuration(self):
        with open(self._res_file_name, 'r') as fh:
            names, markers, indexes = \
                self._parse_vars(fh.readline().strip().split(';')[self._offset_in_res:])
            self._create_input_file(fh, indexes)
            self._create_cfg_file()

    @staticmethod
    def _get_absolute_path(relative_path):
        return PoolHelper().ppool.root_path() + '/' + relative_path

    def _run(self):
        config_file_path = self._get_absolute_path(self._cfg_file_name)
        module_path = os.path.join(PoolHelper().walker_util_path, 'approximation-py', 'src', 'adapter')
        if sys.platform.startswith('linux'):
            command = '"{}" "{}" "{}"'.format(
                PoolHelper().python_app,
                os.path.join(module_path, 'main_surrogate.py'),
                config_file_path
            )
        elif sys.platform.startswith('win32'):
            path_python = PoolHelper().walker_util_path.replace('walker_utils', 'integrator')
            command = '"{}" "{}" "{}" '.format(
                os.path.join(path_python, 'python37', PoolHelper().python_app),
                os.path.join(module_path, r'main_surrogate.py'),
                config_file_path
            )
        else:
            raise RuntimeError(
                tr("Approximator error: file {} not exist.").format(self._out_file_name)
            )
        process = subprocess.Popen(
            command,
            creationflags=0x08,
            close_fds=True,
            shell=True
        )
        process.wait()
        if process.returncode != 0:
            raise RuntimeError(tr('command "{}" launch complete with error').format(command))

        try:
            # если выходной файл аппроксиматора пустой, нормально завершаем работу
            if os.path.getsize(self._out_file_name) == 0:
                sys.exit(1)
        except OSError:
            raise RuntimeError(
                tr("Approximator error: file {} not exist.").format(self._out_file_name)
            )

    def _modify_variator(self):
        try:
            # Читаем содержимое контекста вариатора в переменную.
            with open(self._variator_file_name, 'r') as fh:
                var_params = json.loads(fh.read())
            # Если нет вариантов, ничего не делаем
            if 'variants' not in var_params:
                var_params['variants'] = []
            # Добавляем к переменной, содержащей контекст
            # вариатора новые варианты.
            with open(self._out_file_name, 'r') as fh:
                for line in fh:
                    new_param = line.strip().split(';')[:len(self._x_order_opt)]
                    tmp_params = list(self._x_order_init)
                    for name, val in zip(self._x_order_opt, new_param):
                        tmp_params[self._x_order_init.index(name)] = float(val)
                    var_params['variants'].append(tmp_params)
            # Записываем в файл число запускв расчетного модуля на на конкретной стадии.
            with open(self._steps_file_name, 'a') as fh:
                fh.write(str(var_params['index']) + '\n')
            # Записываем в файл расширенный контекст вариатора.
            with open(self._variator_file_name, 'w') as fh:
                fh.write(json.dumps(var_params, indent = 4))
        except Exception:
            raise RuntimeError(tr("Can't modify variator parameters"))

    def _check_attempt(self):
        if int(self._config['attempt']) == self._get_attempt_count(self._steps_file_name) - 1:
            sys.exit(1)

    @staticmethod
    def _get_attempt_count(steps_file):
        if os.path.exists(steps_file):
            with open(steps_file, 'r') as file:
                return len(file.readlines())
        else:
            return 0
                
    def process(self):
        self._check_attempt()
        self._create_configuration()
        self._run()
        self._modify_variator()
        PoolHelper().ppool.dict['variants'] = {}
        PoolHelper().variants_total = 0
