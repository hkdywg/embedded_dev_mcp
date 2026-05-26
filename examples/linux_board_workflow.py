"""Embedded Linux board debug workflow example.

Demonstrates kernel module install & GPIO debug workflow:
  device_info → lsmod → install_module → read_dmesg → read_gpio

This is a reference script showing the expected tool call sequence.
The actual tools are invoked by the MCP client, not this script.
"""

from __future__ import annotations

KO_PATH = "/home/user/build/driver.ko"
GPIO_NUM = 42

WORKFLOW = [
    ("device_info", {}),
    ("lsmod", {}),
    ("read_dmesg", {"lines": 50, "grep": "error"}),
    ("install_module", {"ko_path": KO_PATH, "params": "debug=1"}),
    ("read_dmesg", {"lines": 20, "grep": "driver"}),
    ("lsmod", {}),
    ("read_sysfs", {"path": "/sys/class/driver/version"}),
    ("read_gpio", {"gpio": GPIO_NUM}),
    ("set_gpio", {"gpio": GPIO_NUM, "value": 1}),
    ("read_gpio", {"gpio": GPIO_NUM}),
    ("remove_module", {"name": "driver"}),
]

if __name__ == "__main__":
    print("Linux board debug workflow:")
    for i, (tool, args) in enumerate(WORKFLOW, 1):
        print(f"  {i}. {tool}({args})")