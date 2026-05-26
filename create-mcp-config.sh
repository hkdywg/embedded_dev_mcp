#!/bin/bash
# 在指定项目目录创建 .mcp.json，引用 embedded_dev_mcp
#
# 用法:
#   ./create-mcp-config.sh                    # 当前目录
#   ./create-mcp-config.sh /path/to/project    # 指定目录
#
# 支持的模式（可同时启用多个 server）:
#   SSH     — 嵌入式 Linux 板子（有 sshd）
#   ADB     — Android 设备 / adb gadget 板子
#   MCU     — MCU 调试（probe-rs + IAR 编译）

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
MCP_DIR="${EMBEDDED_DEV_MCP_DIR:-$SCRIPT_DIR}"
TARGET_DIR="${1:-.}"

if [ ! -d "$TARGET_DIR" ]; then
    echo "Error: Directory $TARGET_DIR not found"
    exit 1
fi

TARGET_DIR="$(cd "$TARGET_DIR" && pwd)"

cat > "$TARGET_DIR/.mcp.json" << 'EOF'
{
  "_comment": "embedded-dev-mcp config — edit env values for your target device",
  "mcpServers": {
    "embedded-dev-ssh": {
      "command": "uv",
      "args": ["--directory", "__MCP_DIR__", "run", "embedded-dev-mcp"],
      "env": {
        "SERVER_NAME": "embedded-dev-ssh",
        "TRANSPORT": "ssh",
        "SSH_HOST": "192.168.1.100",
        "SSH_PORT": "22",
        "SSH_USER": "root",
        "SSH_KEY": "~/.ssh/id_rsa",
        "SSH_PASSWORD": "",
        "TIMEOUT": "15",
        "AUDIT_LOG": "audit.log",
        "EXTRA_SHELL_PREFIXES": ""
      }
    },
    "embedded-dev-adb-usb": {
      "command": "uv",
      "args": ["--directory", "__MCP_DIR__", "run", "embedded-dev-mcp"],
      "env": {
        "SERVER_NAME": "embedded-dev-adb-usb",
        "TRANSPORT": "adb-usb",
        "ADB_BINARY": "adb",
        "ADB_SERIAL": "",
        "TIMEOUT": "15",
        "AUDIT_LOG": "audit.log"
      }
    },
    "embedded-dev-adb-wifi": {
      "command": "uv",
      "args": ["--directory", "__MCP_DIR__", "run", "embedded-dev-mcp"],
      "env": {
        "SERVER_NAME": "embedded-dev-adb-wifi",
        "TRANSPORT": "adb-wifi",
        "ADB_BINARY": "adb",
        "ADB_WIFI_HOST": "192.168.1.100",
        "ADB_WIFI_PORT": "5555",
        "TIMEOUT": "15",
        "AUDIT_LOG": "audit.log"
      }
    },
    "embedded-dev-mcu": {
      "command": "uv",
      "args": ["--directory", "__MCP_DIR__", "run", "embedded-dev-mcp"],
      "env": {
        "SERVER_NAME": "embedded-dev-mcu",
        "TRANSPORT": "ssh",
        "SSH_HOST": "127.0.0.1",
        "SSH_USER": "root",
        "MCU_DEBUG_ENABLED": "true",
        "PROBE_TYPE": "stlink",
        "TARGET_CHIP": "stm32f4",
        "PROBE_RS_BINARY": "probe-rs",
        "IAR_BUILD_BINARY": "iarbuild",
        "GDB_BINARY": "arm-none-eabi-gdb",
        "TIMEOUT": "30",
        "AUDIT_LOG": "audit.log"
      }
    }
  }
}
EOF

sed -i "s|__MCP_DIR__|$MCP_DIR|g" "$TARGET_DIR/.mcp.json"

# ── 输出帮助 ──
echo ""
echo "=========================================="
echo " Created $TARGET_DIR/.mcp.json"
echo "=========================================="
echo ""
echo "  包含 4 个 server 配置:"
echo ""
echo "  Server                    模式         需配置"
echo "  ─────────────────────────────────────────────"
echo "  embedded-dev-ssh          SSH 板子     SSH_HOST / SSH_USER / SSH_KEY"
echo "  embedded-dev-adb-usb      ADB USB      ADB_SERIAL (可选)"
echo "  embedded-dev-adb-wifi     ADB WiFi     ADB_WIFI_HOST"
echo "  embedded-dev-mcu          MCU 调试     PROBE_TYPE / TARGET_CHIP"
echo ""
echo "  MCU 模式额外支持:"
echo "    - 调试器: stlink / jlink / i-jet"
echo "    - 烧录:   erase_flash → program_flash → verify_flash"
echo "    - 编译:   iar_build(project.ewp, Debug)"
echo "    - 断点:   set_breakpoint / step_target / read_memory"
echo ""
echo "  编辑 $TARGET_DIR/.mcp.json 配置目标设备后重启 OpenCode 即可。"
echo ""