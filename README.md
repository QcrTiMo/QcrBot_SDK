# QcrBot_SDK (OneBot v11 Python SDK)

<!-- 在这里可以放一个 Logo 或者简短的 Slogan -->

**QcrBot_SDK** 是一个基于 Python `asyncio` 的 OneBot v11 SDK，旨在提供一个 **简洁、轻量、易于理解和使用** 的机器人开发框架。它封装了与 OneBot v11 实现端 (如 go-cqhttp, NapCat 等) 的 WebSocket 通信、事件处理和 API 调用，让开发者可以专注于机器人应用逻辑的实现。

[![LICENSE](https://img.shields.io/badge/license-AGPL--3.0-blue.svg)](https://github.com/你的GitHub用户名/QcrBot_SDK/blob/main/LICENSE) <!-- 替换链接 -->
<!-- 你还可以添加其他徽章，例如 PyPI 版本、构建状态等 -->

## ✨ 特性

*   **简洁易用:** 提供直观的 API 和面向对象的接口，降低开发门槛。
*   **异步优先:** 基于 `asyncio`，性能良好，适合处理高并发场景。
*   **事件驱动:** 使用装饰器 `@bot.on_event()` 和 `@bot.on_command()` 轻松注册事件和命令处理器。
*   **便捷消息处理:**
    *   支持使用**列表**混合**字符串**和**消息段对象** (`Text`, `Image`, `At` 等) 构建和发送消息。
    *   自动将接收到的 OneBot v11 消息 (CQ 码或数组) 解析为 `MessageChain` 对象，方便处理。
    *   提供了 `MessageChain` 对象的常用操作方法 (`extract_plain_text`, `get`, `get_all`, `__contains__` 等)。
*   **丰富的 API 封装:** 覆盖了大部分常用的 OneBot v11 API，并提供类型提示。
*   **自动重连:** 内置 WebSocket 自动重连机制，提高稳定性。
*   **类型安全:** 大量使用类型提示和 Pydantic 模型，减少运行时错误。
*   **清晰结构:** SDK 内部模块化，易于理解和扩展。


