# embedded-dev-mcp

嵌入式 Linux 和 Android 开发的 MCP 服务器。让 AI 助手（如 Claude）直接操作嵌入式设备，支持 SSH 和 ADB（USB/WiFi）两种连接方式。

## 功能特点

| 传输方式 | 适用设备 | 实现方式 |
|-----------|---------------|---------|
| `ssh` | 嵌入式 Linux（i.MX、TI、RK 等） | asyncssh |
| `adb-usb` | Android 设备 / RK 板子 USB adb | adb CLI |
| `adb-wifi` | Android 设备 / adb-over-tcp | adb CLI |

### 支持的工具

**只读工具**（无需用户确认）：
- `device_info()` - 设备基本信息（传输方式、uname、uptime）
- `read_dmesg(lines, grep)` - 内核日志尾部
- `read_sysfs(path)` - 读取 /sys/ 文件
- `read_proc(path)` - 读取 /proc/ 文件
- `list_dir(path, long)` - 列出目录内容
- `lsmod()` - 已加载的内核模块
- `modinfo(module)` - 模块元数据
- `read_gpio(gpio)` - GPIO 值（传统 sysfs 接口）
- `read_iio(device, channel)` - IIO 传感器值
- `run_shell(cmd)` - 执行白名单内的 shell 命令
- `adb_devices()` - 列出 ADB 设备（仅 ADB 传输）

**写入工具**（需要用户确认）：
- `install_module(ko_path, params)` - 上传并 insmod .ko 文件
- `remove_module(name)` - rmmod 模块
- `write_sysfs(path, value)` - 写入 sysfs
- `set_gpio(gpio, value)` - 设置 GPIO 值
- `export_gpio(gpio)` - 导出 GPIO
- `reboot_device()` - 重启设备
- `pull_file(remote_path, local_path)` - 从设备拉取文件

## 安装步骤

```bash
# 安装 uv（如果未安装）
curl -LsSf https://astral.sh/uv/install.sh | sh

# 安装依赖
cd embedded-dev-mcp
uv sync

# 从模板生成 mcp.json
sed "s|{{PROJECT_DIR}}|$PWD|g" mcp.template.json > mcp.json
```

## 配置说明

编辑 `mcp.json` 配置传输方式：

### SSH 传输

```json
{
  "mcpServers": {
    "embedded-dev-ssh": {
      "env": {
        "TRANSPORT": "ssh",
        "SSH_HOST": "192.168.1.100",
        "SSH_PORT": "22",
        "SSH_USER": "root",
        "SSH_KEY": "~/.ssh/id_rsa",
        "DEVICE_TIMEOUT": "15"
      }
    }
  }
}
```

### ADB USB 传输

```json
{
  "mcpServers": {
    "embedded-dev-adb-usb": {
      "env": {
        "TRANSPORT": "adb-usb",
        "ADB_SERIAL": "",  // 可选：指定设备序列号
        "DEVICE_TIMEOUT": "15"
      }
    }
  }
}
```

### ADB WiFi 传输

```json
{
  "mcpServers": {
    "embedded-dev-adb-wifi": {
      "env": {
        "TRANSPORT": "adb-wifi",
        "ADB_WIFI_HOST": "192.168.1.100",
        "ADB_WIFI_PORT": "5555",
        "DEVICE_TIMEOUT": "15"
      }
    }
  }
}
```

## 安全机制

- **命令白名单**：只允许预定义的安全命令前缀
- **路径限制**：文件访问仅限于安全目录
- **审计日志**：所有操作记录到 audit.log
- **用户确认**：写入工具在 MCP 客户端需要用户显式批准

## 系统要求

- Python 3.10+
- `adb` 命令行工具（用于 ADB 传输方式）
- 目标设备的 SSH 访问或 ADB 连接

## 使用方法

在 Claude Code 或其他 MCP 客户端中，将 `mcp.json` 的配置添加到客户端设置即可使用。

### 环境变量配置

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `TRANSPORT` | 传输方式：ssh / adb-usb / adb-wifi | ssh |
| `SSH_HOST` | SSH 服务器地址 | 192.168.1.100 |
| `SSH_PORT` | SSH 端口 | 22 |
| `SSH_USER` | SSH 用户名 | root |
| `SSH_KEY` | SSH 私钥路径 | ~/.ssh/id_rsa |
| `SSH_PASSWORD` | SSH 密码（可选） | - |
| `ADB_SERIAL` | ADB 设备序列号（可选） | - |
| `ADB_WIFI_HOST` | ADB WiFi 主机地址 | - |
| `ADB_WIFI_PORT` | ADB WiFi 端口 | 5555 |
| `DEVICE_TIMEOUT` | 命令超时秒数 | 15 |
| `AUDIT_LOG` | 审计日志路径 | ~/.embedded_dev_mcp/audit.log |
| `EXTRA_SHELL_PREFIXES` | 额外允许的命令前缀（逗号分隔） | - |