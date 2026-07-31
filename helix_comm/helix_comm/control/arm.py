import roslibpy


class Arm:
    def __init__(self, client, logger):
        self.client = client
        self.logger = logger
        self.cart_pub = roslibpy.Topic(
            client, '/helix/command/cartesian', 'geometry_msgs/msg/Pose')
        self.config_pub = roslibpy.Topic(
            client, '/helix/command/configuration', 'control_msgs/msg/InterfaceValue')
        self.tendon_pub = roslibpy.Topic(
            client, '/helix/command/tendon_lengths', 'control_msgs/msg/InterfaceValue')

    def move_to_pose(self, x, y, z, qx=0.0, qy=0.0, qz=0.0, qw=1.0):
        msg = {
            'position': {'x': x, 'y': y, 'z': z},
            'orientation': {'x': qx, 'y': qy, 'z': qz, 'w': qw},
        }
        self.cart_pub.publish(msg)
        self.logger.debug(
            f'  cartesian: ({x:.3f}, {y:.3f}, {z:.3f})  '
            f'quat: ({qx:.3f}, {qy:.3f}, {qz:.3f}, {qw:.3f})'
        )

    def set_configuration(self, joint_names, joint_values):
        msg = {
            'interface_names': joint_names,
            'values': joint_values,
        }
        self.config_pub.publish(msg)
        self.logger.debug('  configuration set')

    def set_tendon_lengths(self, names, lengths):
        msg = {
            'interface_names': names,
            'values': lengths,
        }
        self.tendon_pub.publish(msg)
        pairs = ', '.join(f'{n}: {length:.3f}' for n, length in zip(names, lengths))
        self.logger.debug(f'  tendon lengths -> {pairs}')

    def cleanup(self):
        self.cart_pub.unadvertise()
        self.config_pub.unadvertise()
        self.tendon_pub.unadvertise()
