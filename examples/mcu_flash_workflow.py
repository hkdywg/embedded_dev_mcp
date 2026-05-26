"""MCU flash workflow example.

Demonstrates the complete flash-then-debug workflow:
  erase_flash → program_flash → verify_flash → reset → set_breakpoint → run

This is a reference script showing the expected tool call sequence.
The actual tools are invoked by the MCP client (Claude/OpenCode), not this script.
"""

from __future__ import annotations

FIRMWARE_PATH = "build/firmware.elf"
ENTRY_POINT = 0x08000000

WORKFLOW = [
    ("erase_flash", {}),
    ("program_flash", {"firmware_path": FIRMWARE_PATH}),
    ("verify_flash", {"firmware_path": FIRMWARE_PATH}),
    ("reset_target", {"halt": True}),
    ("set_breakpoint", {"address": ENTRY_POINT, "hw": True}),
    ("run_target", {}),
    ("halt_target", {}),
    ("read_memory", {"address": ENTRY_POINT, "size": 256, "format": "hex"}),
    ("clear_all_breakpoints", {}),
    ("run_target", {}),
]

if __name__ == "__main__":
    print("MCU flash-debug workflow:")
    for i, (tool, args) in enumerate(WORKFLOW, 1):
        print(f"  {i}. {tool}({args})")