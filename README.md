# embedded-dev-mcp

让 Claude（或任何 MCP 客户端）直接操作嵌入式 Linux 板子和 Android 设备。自己跑命令、自己看输出、自己 debug。支持 SSH 和 ADB（USB/WiFi）三种连接方式。

## 功能特点

| Transport | 适用场景 | 后端 |
|-----------|---------|------|
| `ssh` | 嵌入式 Linux（i.MX、TI、RK 等有 sshd 的板子） | asyncssh |
| `adb-usb` | Android 设备 / RK 板子 USB adb gadget | adb CLI |
| `adb-wifi` | Android 设备 / adb-over-tcp | adb CLI |

### 支持的工具

**只读工具**（无需用户确认）：
- `device_info()` - 设备基本信息（transport、uname、uptime、hostname）
- `read_dmesg(lines, grep)` - 内核日志尾部
- `read_sysfs(path)` - 读取 /sys/ 文件
- `read_proc(path)` - 读取 /proc/ 文件
- `list_dir(path, long)` - 列目录内容
- `lsmod()` - 已加载内核模块列表
- `modinfo(module)` - 模块元信息
- `read_gpio(gpio)` - GPIO 值（legacy sysfs）
- `read_iio(device, channel)` - IIO 传感器值
- `run_shell(cmd)` - 白名单内的 shell 命令
- `adb_devices()` - ADB 设备列表（仅 ADB transport）

**写入工具**（需用户确认）：
- `install_module(ko_path, params)` - 推送到板子并 insmod
- `remove_module(name)` - rmmod 模块
- `write_sysfs(path, value)` - 写入 sysfs
- `set_gpio(gpio, value)` - 设置 GPIO 值
- `export_gpio(gpio)` - 导出 GPIO
- `reboot_device()` - 重启设备
- `pull_file(remote_path, local_path)` - 从设备拉取文件

## 安装

```bash
# 安装 uv（如果没有）
curl -LsSf https://astral.sh/uv/install.sh | sh

# 安装依赖
cd embedded-dev-mcp
uv sync
```

## 使用方式

项目根目录已包含 `.mcp.json` 文件。当 OpenCode 在此项目目录下工作时，会自动发现并加载 MCP server。

**只需修改 `.mcp.json` 中的环境变量**：

1. SSH 方式：修改 `SSH_HOST`、`SSH_USER`、`SSH_KEY`
2. ADB USB 方式：修改 `ADB_SERIAL`（可选）
3. ADB WiFi 方式：修改 `ADB_WIFI_HOST`

### 配置示例

编辑 `.mcp.json` 中对应 server 的 `env` 部分：

**SSH 方式**：
```json
"env": {
  "TRANSPORT": "ssh",
  "SSH_HOST": "192.168.1.100",
  "SSH_USER": "root",
  "SSH_KEY": "~/.ssh/id_rsa"
}
```

**ADB USB 方式**：
```json
"env": {
  "TRANSPORT": "adb-usb",
  "ADB_SERIAL": ""
}
```

**ADB WiFi 方式**：
```json
"env": {
  "TRANSPORT": "adb-wifi",
  "ADB_WIFI_HOST": "192.168.1.100",
  "ADB_WIFI_PORT": "5555"
}
```

## 安全机制

- **命令白名单**：只允许预定义的安全命令前缀
- **路径限制**：文件访问限制在安全目录内
- **审计日志**：所有操作记录到 audit.log
- **用户确认**：写入操作在 MCP 客户端需要用户显式批准

## 前置条件

- Python 3.10+
- `adb` 命令（ADB 方式需要）
- SSH 或 ADB 连接到目标设备

## 在其他项目中使用

当你在其他嵌入式开发项目目录下工作时，可以使用提供的脚本快速创建 `.mcp.json`：

```bash
# 在目标项目目录创建 MCP 配置
/path/to/embedded_dev_mcp/create-mcp-config.sh /path/to/your_project

# 或者直接在当前目录创建
cd /path/to/your_project
/path/to/embedded_dev_mcp/create-mcp-config.sh .
```

然后编辑生成的 `.mcp.json`，修改 `SSH_HOST` 或 `ADB_WIFI_HOST` 等配置。