import roslibpy


class Calibrate:
    def __init__(self, client, logger):
        self.client = client
        self.logger = logger

    def _get_param(self, node, name):
        svc = roslibpy.Service(
            self.client, f'{node}/get_parameters', 'rcl_interfaces/srv/GetParameters')
        res = svc.call(roslibpy.ServiceRequest({'names': [name]}))
        return res['values'][0]

    def _set_param(self, node, name, value, ptype=3):
        svc = roslibpy.Service(
            self.client, f'{node}/set_parameters', 'rcl_interfaces/srv/SetParameters')
        req = roslibpy.ServiceRequest({
            'parameters': [{
                'name': name,
                'value': {'type': ptype, 'double_value': float(value)}
            }]
        })
        res = svc.call(req)
        return res['results'][0]['successful']

    def status(self):
        self.logger.info('\n========== CALIBRATION STATUS ==========')
        v = self._get_param('/helix/tendon_calibration_node', 'calibration_current_ma')
        self.logger.info(f'  calibration_current_ma = {v["double_value"]} mA')
        for dxl_id in range(9):
            try:
                v = self._get_param(
                    '/helix/dynamixel_driver_node', f'motor_{dxl_id}/current_limit')
                self.logger.info(f'  motor_{dxl_id}/current_limit = {v["double_value"]} mA')
            except Exception:
                pass
        self.logger.info('========================================\n')

    def set_current(self, milliamps):
        ok = self._set_param('/helix/tendon_calibration_node',
                             'calibration_current_ma', milliamps)
        if ok:
            self.logger.info(f'  calibration_current_ma {milliamps} mA')
        else:
            self.logger.error('  failed to set calibration_current_ma')

    def start(self):
        svc = roslibpy.Service(self.client, '/helix/start_calibration', 'std_srvs/srv/Empty')
        res = svc.call(roslibpy.ServiceRequest({}))
        self.logger.info(f'  {res}')

    def finish(self):
        svc = roslibpy.Service(self.client, '/helix/finish_calibration', 'std_srvs/srv/Empty')
        res = svc.call(roslibpy.ServiceRequest({}))
        self.logger.info(f'  {res}')

    def compression_limits(self):
        svc = roslibpy.Service(
            self.client, '/helix/calibrate_compression_limits', 'std_srvs/srv/Empty')
        res = svc.call(roslibpy.ServiceRequest({}))
        self.logger.info(f'  {res}')
