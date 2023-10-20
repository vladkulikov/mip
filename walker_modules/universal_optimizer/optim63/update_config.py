def nelder_mead(config, cfg_config, x_values):

    simplex = config['simplex'].split(',')
    simplex = [item.strip().strip('[').strip(']').strip() for item in simplex]
    result_simplex = []
    count = int(len(simplex) / len(x_values))
    for i in range(count):
        result_simplex.append([float(simplex[i * len(x_values)]), float(simplex[i * len(x_values) + 1])])
            
    cfg_config['NelderMead']['initial_simplex'] = result_simplex
    return cfg_config
    
def basin_hopping(config, cfg_config):

    cfg_config['BasinHopping']['method'] = config['method_local']
    cfg_config['BasinHopping']['interval'] = config['interval']
    cfg_config['BasinHopping']['step_size'] = config['step_size']
    return cfg_config
    
def sego(config, cfg_config, y_values):

    method = cfg_config['optimization_method']
    cfg_config[method]['current_iteration'] = 0
    cfg_config[method]['method_local'] = config['method_local']
    cfg_config[method]['max_count_clusters'] = config['max_count_clusters']
    cfg_config[method]['soft'] = 0
    cfg_config[method]['min_distance_between_points'] = config['min_distance_between_points']
    cfg_config[method]['n_sampling'] = 1
    cfg_config[method]['criterion'] = config['criterion']
    cfg_config[method]['constraints'] = [{'name': y_value.name, 'min': 0, 'max': None} for y_value in y_values if y_value.type == 1]
    return cfg_config

def update_config(config, cfg_config, x_values, y_values):

    method = cfg_config['optimization_method']
    if method == 'NelderMead':
        return nelder_mead(config, cfg_config, x_values)
    if (method == 'SEGO') or (method == 'SEGOVAE'):
        return sego(config, cfg_config, y_values)
    if (method == 'CG') or (method == 'SLSQP'):
        return cfg_config
    if method == 'BasinHopping':
        return basin_hopping(config, cfg_config)