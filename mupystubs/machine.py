"""dummy file to provide prototypes for vscode"""

class Pin:
    """IO Pin"""
    OUT = 3
    IN = 1
    def __init__(self, pin: int) -> None:
        pass

    def on(self):
        """Set Pin to high"""

    def off(self):
        """Set Pin to low"""
