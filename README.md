# embedded-dev-mcp

让 Claude / OpenCode 等 AI 助手直接操作嵌入式设备和 MCU。自己跑命令、自己看输出、自己 debug。

支持**两种模式**、**三种传输方式**、**34 个 MCP 工具**：

| 模式 | Transport | 适用场景 | 后端 |
|------|-----------|---------|------|
| 嵌入式 Linux 板子 | `ssh` | 有 sshd 的板子（Renesas / TI / RK ...） | asyncssh |
| | `adb-usb` | USB adb gadget 的板子 | adb CLI |
| | `adb-wifi` | adb-over-tcp 的板子 | adb CLI |
| MCU 调试 | 本地 probe-rs | STM32 / ARM Cortex-M / RISC-V | probe-rs CLI + GDB |

---

## 项目结构

```
embedded_dev_mcp/
├── src/embedded_dev_mcp/
│   ├── server.py          # MCP server 入口（唯一入口点）
│   ├── config.py          # 配置管理（环境变量驱动）
│   ├── safety.py          # 命令白名单 / 路径安全检查
│   ├── audit.py           # 审计日志
│   ├── probe_manager.py   # probe-rs 命令行包装
│   ├── transports/        # 传输层
│   │   ├── base.py        #   抽象接口
│   │   ├── ssh.py         #   SSH 实现
│   │   └── adb.py         #   ADB 实现（USB / WiFi）
│   └── tools/             # 工具层
│       ├── __init__.py    #   嵌入式 Linux 板子工具
│       └── mcu_tools.py   #   MCU 调试工具
├── tests/                 # 45 个测试
│   ├── conftest.py
│   ├── test_safety.py
│   ├── test_config.py
│   └── test_probe_manager.py
├── examples/              # 配置示例 + 工作流示例
│   ├── mcp_configs/       #   SSH / ADB / ST-Link / i-jet 配置模板
│   ├── mcu_flash_workflow.py
│   └── linux_board_workflow.py
├── docs/
│   └── ARCHITECTURE.md    # 架构文档
├── .mcp.json              # 项目级 MCP 配置（OpenCode 自动发现）
├── create-mcp-config.sh   # 在其他项目中快速创建 .mcp.json
├── pyproject.toml
├── LICENSE
└── README.md
```

---

## 快速开始

```bash
# 克隆并安装
git clone <repo-url>
cd embedded_dev_mcp
uv sync

# 编辑 .mcp.json，配置目标设备
# OpenCode 在此目录下工作时自动加载 MCP 工具
```

---

## 工具全集（34 个）

### 嵌入式 Linux 板子 — 只读工具

| 工具 | 参数 | 说明 |
|------|------|------|
| `device_info` | — | 设备身份：transport、uname、uptime、hostname |
| `read_dmesg` | `lines=100`, `grep?` | 内核日志尾部，支持正则过滤 |
| `read_sysfs` | `path` | 读取 /sys/ 下的文件（路径白名单检查） |
| `read_proc` | `path` | 读取 /proc/ 下的文件 |
| `list_dir` | `path`, `long=False` | 列目录（路径白名单检查） |
| `lsmod` | — | 已加载内核模块列表 |
| `modinfo` | `module` | 内核模块元信息 |
| `read_gpio` | `gpio` | 读 GPIO 值（legacy sysfs） |
| `read_iio` | `device`, `channel` | 读 IIO 传感器通道值 |
| `run_shell` | `cmd` | 执行白名单内的 shell 命令 |

### 嵌入式 Linux 板子 — 写入工具

| 工具 | 参数 | 说明 |
|------|------|------|
| `install_module` | `ko_path`, `params=""` | 推送 .ko 到板子并 insmod |
| `remove_module` | `name` | rmmod 模块 |
| `write_sysfs` | `path`, `value` | 写入 sysfs 文件（路径白名单检查） |
| `set_gpio` | `gpio`, `value` | 设置 GPIO 输出（0 / 1） |
| `export_gpio` | `gpio` | 导出 GPIO 到 sysfs |
| `reboot_device` | — | 重启设备 |
| `pull_file` | `remote_path`, `local_path` | 从设备拉取文件 |

### MCU 调试工具（`MCU_DEBUG_ENABLED=true` 时启用）

**探针管理**

| 工具 | 参数 | 说明 |
|------|------|------|
| `list_probes` | — | 列出连接的调试探针 |
| `connect_probe` | `probe_index?` | 连接调试探针 |

**烧录**

| 工具 | 参数 | 说明 |
|------|------|------|
| `erase_flash` | — | 擦除全部 Flash |
| `program_flash` | `firmware_path` | 烧录固件（ELF / HEX / BIN） |
| `verify_flash` | `firmware_path` | 校验 Flash 内容 |

**执行控制**

| 工具 | 参数 | 说明 |
|------|------|------|
| `reset_target` | `halt=False` | 复位目标 MCU，可选 halt |
| `halt_target` | — | 停止执行 |
| `resume_target` | — | 恢复执行 |
| `run_target` | — | 运行目标 MCU |
| `step_target` | — | 单步执行 |

**内存操作**

| 工具 | 参数 | 说明 |
|------|------|------|
| `read_memory` | `address`, `size`, `format="hex"` | 读内存（hex / bin / ascii） |
| `write_memory` | `address`, `data`, `format="hex"` | 写内存 |

**断点管理**

| 工具 | 参数 | 说明 |
|------|------|------|
| `set_breakpoint` | `address`, `hw=True` | 设置断点（hw=硬件断点） |
| `clear_breakpoint` | `address` | 清除断点 |
| `list_breakpoints` | — | 列出所有断点 |
| `clear_all_breakpoints` | — | 清除全部断点 |

**信息**

| 工具 | 参数 | 说明 |
|------|------|------|
| `target_info` | — | 获取目标芯片信息 |

---

## 配置

### 嵌入式 Linux 板子（SSH）

```json
{
  "mcpServers": {
    "embedded-dev-ssh": {
      "command": "uv",
      "args": ["--directory", ".", "run", "embedded-dev-mcp"],
      "env": {
        "TRANSPORT": "ssh",
        "SSH_HOST": "192.168.1.100",
        "SSH_PORT": "22",
        "SSH_USER": "root",
        "SSH_KEY": "~/.ssh/id_rsa",
        "TIMEOUT": "15",
        "AUDIT_LOG": "./audit.log"
      }
    }
  }
}
```

### ADB USB

```json
{
  "env": {
    "TRANSPORT": "adb-usb",
    "ADB_SERIAL": "5c5ec7023ef0356e"
  }
}
```

### ADB WiFi

```json
{
  "env": {
    "TRANSPORT": "adb-wifi",
    "ADB_WIFI_HOST": "192.168.1.100",
    "ADB_WIFI_PORT": "5555"
  }
}
```

### MCU 调试（ST-Link + STM32F4）

```json
{
  "env": {
    "MCU_DEBUG_ENABLED": "true",
    "PROBE_TYPE": "stlink",
    "TARGET_CHIP": "stm32f407",
    "PROBE_RS_BINARY": "probe-rs"
  }
}
```

### MCU 调试（i-jet + STM32H7）

```json
{
  "env": {
    "MCU_DEBUG_ENABLED": "true",
    "PROBE_TYPE": "i-jet",
    "TARGET_CHIP": "stm32h743",
    "GDB_BINARY": "arm-none-eabi-gdb"
  }
}
```

### 在多个项目中复用

```bash
# 在其他嵌入式项目目录下创建 .mcp.json
/home/yinwg/ywg_workspace/prj/embedded_dev_mcp/create-mcp-config.sh /path/to/your_project

# 编辑生成的 .mcp.json，修改 SSH_HOST 或 ADB_WIFI_HOST
```

### 扩展 run_shell 命令白名单

```json
{
  "env": {
    "EXTRA_SHELL_PREFIXES": "i2cdetect,nvcc,make,cmake"
  }
}
```

这样 `run_shell` 即可执行 `i2cdetect -y 1`、`make -j4` 等额外命令。

---

## 完整环境变量参考

### 通用

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `SERVER_NAME` | `embedded-dev` | MCP server 名称 |
| `TRANSPORT` | `ssh` | `ssh` / `adb-usb` / `adb-wifi` |
| `TIMEOUT` | `15` | 命令超时（秒） |
| `AUDIT_LOG` | `~/.embedded_dev_mcp/audit.log` | 审计日志路径 |
| `EXTRA_SHELL_PREFIXES` | — | 额外命令前缀（逗号分隔） |

### SSH

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `SSH_HOST` | `192.168.7.2` | SSH 主机 |
| `SSH_PORT` | `22` | SSH 端口 |
| `SSH_USER` | `root` | SSH 用户 |
| `SSH_KEY` | — | 私钥路径 |
| `SSH_PASSWORD` | — | 密码（可选） |

### ADB

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `ADB_BINARY` | `adb` | adb 命令路径 |
| `ADB_SERIAL` | — | 设备序列号（USB 模式） |
| `ADB_WIFI_HOST` | — | WiFi 主机（WiFi 模式） |
| `ADB_WIFI_PORT` | `5555` | WiFi 端口 |

### MCU 调试（probe-rs）

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `MCU_DEBUG_ENABLED` | `false` | 启用 MCU 调试 |
| `PROBE_TYPE` | `stlink` | 调试器：`stlink` / `jlink` / `i-jet` |
| `TARGET_CHIP` | `stm32f4` | 目标芯片 |
| `PROBE_RS_BINARY` | `probe-rs` | probe-rs 命令行路径 |
| `PROBE_INDEX` | — | 调试器索引（多探针时指定） |
| `GDB_BINARY` | `arm-none-eabi-gdb` | GDB 路径（断点管理用） |

---

## 支持的调试器

| 调试器 | 状态 | 协议 |
|--------|------|------|
| ST-Link V2/V3 | ✅ | stlink |
| J-Link | ✅ | jlink |
| i-jet | ✅ | CMSIS-DAP |

**i-jet 说明**：i-jet 是 IAR 的调试器，在 CMSIS-DAP 兼容模式下工作。配置 `PROBE_TYPE=i-jet`，内部映射为 `cmsisdap` 协议。

---

## 支持的芯片

- ARM Cortex-M（M0 / M0+ / M3 / M4 / M7）
- RISC-V
- STM32 全系列（实机验证 STM32G431CBTx）

---

## 安全机制

| 机制 | 说明 |
|------|------|
| 命令白名单 | `run_shell` 只允许预定义的安全命令前缀（`ALLOW_SHELL_PREFIXES`） |
| 拒绝模式 | 禁止 `rm`、`dd`、`reboot`、`sudo`、命令替换等（`DENY_PATTERNS`） |
| 路径限制 | `read_sysfs` / `write_sysfs` 只允许在安全目录内操作 |
| 审计日志 | 所有操作记录到 JSON Lines 格式的 audit.log |
| 用户确认 | 写入工具需 MCP 客户端显式批准 |

---

## 典型工作流

### MCU 烧录 + 调试

```
list_probes → connect_probe → erase_flash → program_flash(firmware.elf)
→ verify_flash(firmware.elf) → reset_target(halt=true)
→ set_breakpoint(0x08000100) → run_target → [命中断点]
→ read_memory(0x08000100, 256) → step_target → clear_all_breakpoints → run_target
```

### 嵌入式 Linux 板子调试

```
device_info → lsmod → read_dmesg(grep="error")
→ install_module(driver.ko, params="debug=1")
→ read_sysfs("/sys/class/driver/version") → read_gpio(42)
→ set_gpio(42, 1) → read_gpio(42) → remove_module("driver")
```

完整示例见 `examples/` 目录。

---

## 前置条件

| 模式 | 依赖 |
|------|------|
| SSH | Python 3.10+, asyncssh |
| ADB | Python 3.10+, adb 命令 |
| MCU 调试 | Python 3.10+, probe-rs CLI, arm-none-eabi-gdb |
| MCU 硬件 | 调试探针（ST-Link / J-Link / i-jet），目标板 USB 连接 |

---

## 测试

```bash
uv run pytest tests/ -v        # 45 个测试
uv run ruff check src/         # 代码检查
```

---

## 许可证

MIT
