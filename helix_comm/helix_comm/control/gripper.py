import roslibpy


class Gripper:
    def __init__(self, client, logger):
        self.client = client
        self.logger = logger

    def open(self):
        svc = roslibpy.Service(self.client, '/helix/gripper/open', 'std_srvs/srv/Trigger')
        res = svc.call(roslibpy.ServiceRequest({}))
        self.logger.info(f'  gripper open: {res}')

    def close(self):
        svc = roslibpy.Service(self.client, '/helix/gripper/close', 'std_srvs/srv/Trigger')
        res = svc.call(roslibpy.ServiceRequest({}))
        self.logger.info(f'  gripper close: {res}')

    def set_position(self, position):
        svc = roslibpy.Service(
            self.client, '/helix/gripper/set_position', 'helix_interfaces/srv/SetFloat32')
        res = svc.call(roslibpy.ServiceRequest({'data': float(position)}))
        self.logger.info(f'  gripper position ({position:.2f}): {res}')
