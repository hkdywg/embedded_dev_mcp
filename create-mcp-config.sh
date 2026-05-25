#!/bin/bash
# 在指定项目目录创建 .mcp.json，引用 embedded_dev_mcp

MCP_DIR="/home/yinwg/ywg_workspace/prj/embedded_dev_mcp"
TARGET_DIR="${1:-.}"

if [ ! -d "$TARGET_DIR" ]; then
    echo "Error: Directory $TARGET_DIR not found"
    exit 1
fi

cd "$TARGET_DIR"

cat > .mcp.json << EOF
{
  "mcpServers": {
    "embedded-dev-ssh": {
      "command": "uv",
      "args": ["--directory", "$MCP_DIR", "run", "embedded-dev-mcp"],
      "env": {
        "TRANSPORT": "ssh",
        "SSH_HOST": "192.168.1.100",
        "SSH_PORT": "22",
        "SSH_USER": "root",
        "SSH_KEY": "~/.ssh/id_rsa",
        "DEVICE_TIMEOUT": "15"
      }
    },
    "embedded-dev-adb-usb": {
      "command": "uv",
      "args": ["--directory", "$MCP_DIR", "run", "embedded-dev-mcp"],
      "env": {
        "TRANSPORT": "adb-usb",
        "ADB_SERIAL": "",
        "DEVICE_TIMEOUT": "15"
      }
    },
    "embedded-dev-adb-wifi": {
      "command": "uv",
      "args": ["--directory", "$MCP_DIR", "run", "embedded-dev-mcp"],
      "env": {
        "TRANSPORT": "adb-wifi",
        "ADB_WIFI_HOST": "192.168.1.100",
        "ADB_WIFI_PORT": "5555",
        "DEVICE_TIMEOUT": "15"
      }
    }
  }
}
EOF

echo "Created .mcp.json in $TARGET_DIR"
echo "Edit .mcp.json to configure SSH_HOST, ADB_WIFI_HOST, etc."