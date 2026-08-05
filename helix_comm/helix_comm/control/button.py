import roslibpy

BUTTON_COLORS = {
    "white": (1.0, 1.0, 1.0),
    "red": (1.0, 0.0, 0.0),
    "green": (0.0, 1.0, 0.0),
    "blue": (0.0, 0.0, 1.0),
    "yellow": (1.0, 1.0, 0.0),
    "cyan": (0.0, 1.0, 1.0),
    "magenta": (1.0, 0.0, 1.0),
    "purple": (0.5, 0.0, 0.5),
    "pink": (1.0, 0.4, 0.7),
    "orange": (1.0, 0.5, 0.0),
    "off": (0.0, 0.0, 0.0),
}


class Button:
    def __init__(self, client, logger):
        self.client = client
        self.logger = logger

    def set_color(self, r, g, b, a=1.0):
        pub = roslibpy.Topic(
            self.client, "/helix/command/button", "std_msgs/msg/ColorRGBA"
        )
        pub.publish({"r": float(r), "g": float(g), "b": float(b), "a": float(a)})
        self.logger.info(f"  button: R{r} G{g} B{b}")
