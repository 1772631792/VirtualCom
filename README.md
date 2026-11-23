# VirtualCom 虚拟串口工作台

## 先说缺点 / 已知限制

- 底层用的是 **com0com v3.0** 老驱动。它带签名，但**不是 WHQL**。在开启「内存完整性 / HVCI」或严格 Secure Boot 策略的 Windows 10/11 上，系统可能拒绝加载，设备管理器出现黄色感叹号（常见 Code 52）。这不是界面能修的问题。
- 创建 / 删除 COM 端口必须管理员权限，exe 启动时会弹 UAC。
- 免费开源驱动的兼容性、稳定性和售后都不如商业虚拟串口软件。要真正省心，需要购买 WHQL 签名驱动的商业软件。
- 本软件只创建**成对互联**的虚拟 COM 口；波特率、校验位等由两端程序自行约定，软件本身不转发数据。
- 配置只保存在本机 `%APPDATA%`，不跨设备同步。
- 当前这台机器已开启 HVCI。若创建端口后设备管理器黄感叹号，只能选择关闭内存完整性（有安全代价）或改用商业驱动。

## 简介

一个带图形界面的 Windows 虚拟串口管理工具：基于 **com0com** 创建真实的成对 COM 端口，提供新增、编辑、删除、自检和本地配置管理。

## Python 环境

本工程固定使用本机 Python 3.10：

```text
D:\Python310\python.exe
```

IDE 中请也把项目解释器设置为该路径。不要用机器上另外安装的 Python 3.14 来装依赖，否则 PySide6 / PyInstaller 可能不兼容。

## 运行

在 `VirtualCom` 工程目录下执行：

```powershell
D:\Python310\python.exe -m pip install -r requirements.txt
D:\Python310\python.exe main.py
```

> `dist/VirtualCom.exe` 已带管理员权限清单，双击运行会自动弹出 UAC 提示，点「是」即可。

## 使用前准备

VirtualCom 通过 `com0com` 的 `setupc.exe` 管理驱动。首次打开时，如果检测到没有驱动，会弹窗询问是否「一键安装驱动」；也可以随时在左侧状态卡片或「系统设置 → com0com 驱动」里点同一个按钮。

安装包是官方签名的 com0com v3.0，原始安装包放在工程根目录 `Setup_com0com_v3.0.0.0_W7_x64_signed.exe`（同时也有 x86 版），并且会打包进 exe，**全程不需要联网**。安装时会请求管理员权限；软件还会自动把官方 INF/CAT/SYS 文件补齐到 `C:\Windows\System32`，修复部分电脑上安装包漏复制 INF 导致 `SetupOpenInfFile ... ERROR 2` 的问题。完成后会自动重新检测，并继续创建已有配置。

推荐端口范围默认为 `COM10 ~ COM64`，避免占用 COM1 / COM2 这类系统常见串口。如果驱动没装，软件仍可管理配置，但端口状态会显示「未创建」。

## 功能

- 新建 / 编辑 / 删除串口对，端口卡片式展示，名称可留空自动生成
- 「推荐空闲端口」会调用 `setupc busynames`，避开系统和 COMDB 残留占用
- 「自检」在两个端口间互发数据，验证双向连通
- 配置自动保存在 `%APPDATA%\\VirtualCom\\config.json`
- 支持午夜蓝 / 云雾白主题、可选托盘驻留（默认关闭时直接退出）、启动自动创建
- 导出配置、恢复默认设置、清空全部配置
- 内置 com0com 官方签名驱动包，支持一键静默安装
- 内置离线生成的二次元风格 ico，无 AI 云端依赖

## 关闭软件后配置还在吗

还在。配置保存在 `%APPDATA%\VirtualCom\config.json`，关闭 exe 不会删除；com0com 创建的真实 COM 端口也由驱动保留，其他程序仍可继续使用。

只有在软件里执行「删除」并确认移除虚拟端口，或者手动卸载 com0com / 用 `setupc.exe remove 0` 删除端口时，它们才会消失。

「删除配置并移除虚拟端口」只会删除这一对 COM 端口，不会卸载 com0com 驱动本身。

## 打包

```powershell
D:\Python310\python.exe build.py
```

产物位于 `dist/VirtualCom.exe`。打包脚本会自动生成图标、把 com0com 安装包打进 exe，并为 Windows 添加管理员权限清单。

## 重新生成图标

```powershell
D:\Python310\python.exe tools/make_icon.py
```

图标资源输出到 `assets/logo.png` 和 `assets/app.ico`。
