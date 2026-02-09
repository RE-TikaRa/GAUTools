# GSAU 登录获取课表脚本

## TL;DR

> **Quick Summary**: 编写一个 Python 脚本，通过 GSAU 统一身份认证（CAS）自动登录，然后获取并打印学期课表。参考 nbu_logintest.py 的 AES 加密登录流程和 kbtest.py 的课表解析逻辑。
> 
> **Deliverables**:
> - `gsau_schedule.py` — 完整的登录+获取课表脚本
> 
> **Estimated Effort**: Short
> **Parallel Execution**: NO - sequential
> **Critical Path**: 编写脚本 → 验证登录 → 验证课表获取

---

## Context

### Original Request
参考 kbtest.py（课表解析）和 nbu_logintest.py（CAS 登录流程），基于请求样本3（从登录到查看课表的完整流程），编写一个完整的 Python 脚本实现 GSAU 系统从登录到获取课表。UA 随机，不需要压力测试，只需正常登录并打印结果。脚本保持简洁。

### 关键发现：完整登录流程（从请求样本3分析）

GSAU 使用与 NBU 相同的 wisedu CAS 认证系统，但有一个关键的二次认证流程：

**Phase 1: CAS 登录**
1. GET `https://jwgl.gsau.edu.cn/` → 302 到 `web.gsau.edu.cn/wengine-auth/login?id=9&path=/&from=...`
2. → 302 到 `authserver.gsau.edu.cn/authserver/login?service=https://web.gsau.edu.cn/wengine-auth/login?cas_login=true`（同时 Set-Cookie: `wengine_new_ticket`）
3. GET 登录页面 → 200，HTML 中包含 `pwdEncryptSalt`、`execution` 等表单参数
4. POST 登录（AES 加密密码）→ 302，Set-Cookie: `CASTGC`，Location 带 ticket 到 web.gsau.edu.cn

**Phase 2: wengine-auth 回调**
5. GET `web.gsau.edu.cn/wengine-auth/login?cas_login=true&ticket=ST-...` → 302 到 `jwgl.gsau.edu.cn/`
6. GET `jwgl.gsau.edu.cn/` → 302 到 `web.gsau.edu.cn/wengine-auth/login?id=9&...`
7. → 302 到 `jwgl.gsau.edu.cn/wengine-auth/token-login?wengine-ticket=...`（Set-Cookie: 新的 `wengine_new_ticket`）

**Phase 3: jwgl 二次认证（关键！）**
8. GET `jwgl.gsau.edu.cn/` → 200，但返回的是 JS 重定向：
   `window.location.href='https://authserver.gsau.edu.cn/authserver/login?service=http%3A%2F%2Fjwgl.gsau.edu.cn%2F'`
   （注意 service 是 **http://** 不是 https://）
9. 由于已有 CASTGC cookie，authserver 自动 302 发放新 ticket
10. GET `jwgl.gsau.edu.cn/?ticket=ST-...` → 302 → GET `/` → 302 到 `/jsxsd/xk/LoginToXk?method=jwxt&ticket1=...`
11. → 302 到 `/jsxsd/framework/xsMain.jsp`（Set-Cookie: `JSESSIONID` for `/jsxsd/`）

**Phase 4: 获取课表**
12. GET `https://jwgl.gsau.edu.cn/jsxsd/xskb/xskb_list.do` → 200，课表 HTML

### 密码加密
与 NBU 完全相同的 AES-CBC 加密：
- 从登录页 HTML 提取 `pwdEncryptSalt`（16字符 key）
- 生成 64 字符随机前缀 + 16 字符随机 IV
- AES-CBC(key=salt, iv=random_iv, data=random_prefix+password) → Base64

### 测试账号
- 账号: `<REDACTED>`
- 密码: `<REDACTED>`

---

## Work Objectives

### Core Objective
编写一个简洁的 Python 脚本，自动完成 GSAU CAS 登录并获取打印课表。

### Concrete Deliverables
- `D:\Lib\gsautools\gsau_schedule.py`

### Definition of Done
- [ ] 脚本能成功登录并打印课表
- [ ] 运行 `python gsau_schedule.py` 输出课表内容

### Must Have
- 随机 UA（参考 kbtest.py 的 `random_uagent()`）
- AES 密码加密（参考 nbu_logintest.py）
- 完整的登录重定向链处理（包括 JS 重定向解析）
- 课表 HTML 解析和格式化打印（复用 kbtest.py 的解析逻辑）
- `session.trust_env = False`（禁用系统代理，与现有脚本一致）

### Must NOT Have
- 不要压力测试/多线程
- 不要过度结构化（不要不必要的类、框架、过多的函数拆分和变量提取）
- 不要交互式输入（账号密码直接写在脚本顶部配置区）
- 不要冗余注释

---

## Verification Strategy

### Test Decision
- **Infrastructure exists**: NO
- **Automated tests**: None
- **Agent-Executed QA**: YES

### Agent-Executed QA Scenarios (MANDATORY)

```
Scenario: 脚本成功登录并获取课表
  Tool: Bash
  Preconditions: Python 环境可用，pycryptodome 已安装
  Steps:
    1. 运行: python D:\Lib\gsautools\gsau_schedule.py
    2. 观察输出中是否包含登录成功的指示（如 302 重定向到课表页面）
    3. 观察输出中是否包含课表内容（"学期理论课表" 或课程数据表格）
    4. 如果输出包含 "登录" 或 "Session 已过期" 则表示登录失败
  Expected Result: 输出包含格式化的课表（星期一到星期日的课程安排）
  Failure Indicators: 输出包含 "登录失败"、"密码错误"、"Session 已过期"、或 Python 异常
  Evidence: 终端输出截取

Scenario: 验证密码加密正确性
  Tool: Bash
  Preconditions: 同上
  Steps:
    1. 如果登录失败，检查是否能成功获取登录页面（pwdEncryptSalt 和 execution 参数）
    2. 检查 POST 登录后的响应状态码是否为 302
    3. 检查 302 Location 是否包含 ticket=
  Expected Result: CAS 登录返回 302 带 ticket
  Failure Indicators: 返回 200（登录页面重新显示，说明密码错误或加密有误）
  Evidence: 终端输出截取
```

---

## Execution Strategy

### Sequential (Single Task)

只有一个任务，无需并行。

---

## TODOs

- [ ] 1. 编写 gsau_schedule.py 并验证运行

  **What to do**:
  
  编写 `D:\Lib\gsautools\gsau_schedule.py`，实现从登录到获取课表的完整流程。脚本结构保持简洁扁平，参考现有脚本风格。
  
  具体实现要点：
  
  1. **配置区**：USERNAME、PASSWORD 常量（与 nbu_logintest.py 风格一致）
  2. **random_uagent()**：复用 kbtest.py 的实现（Windows Chrome UA）
  3. **AES 加密**：复用 nbu_logintest.py 的 `encrypt_password()` 逻辑（AES_CHARS、random_string、AES-CBC + Base64）
  4. **登录流程**（使用 `requests.Session`，`trust_env=False`）：
     - GET `https://jwgl.gsau.edu.cn/` 让 session 自动跟随重定向到 authserver 登录页
     - 从 HTML 提取 `pwdEncryptSalt`（id="pwdEncryptSalt" value="..."）和 `execution`（在 pwdLoginDiv 内的 execution）
     - 注意：登录页有多个 form（qrLogin、fidoLogin、dynamicLogin、pwdLogin），需要从 `pwdLoginDiv` 区域提取正确的 `execution` 值
     - POST 到 `https://authserver.gsau.edu.cn/authserver/login?service=https%3A%2F%2Fweb.gsau.edu.cn%2Fwengine-auth%2Flogin%3Fcas_login%3Dtrue`
     - POST data: `username`, `password`(加密后), `captcha`(空), `_eventId=submit`, `cllt=userNameLogin`, `dllt=generalLogin`, `lt`(空), `execution`
     - 跟随重定向链
  5. **处理 JS 重定向**：
     - jwgl 首次访问返回 200 但内容是 JS 重定向：`window.location.href='https://authserver.gsau.edu.cn/authserver/login?service=http%3A%2F%2Fjwgl.gsau.edu.cn%2F'`
     - 用正则提取 URL，再 GET 该 URL（由于 session 已有 CASTGC cookie，authserver 会自动发 ticket）
     - 跟随后续重定向直到 jwgl 返回 302 到 `/jsxsd/xk/LoginToXk?method=jwxt&ticket1=...`
     - 最终到达 `/jsxsd/framework/xsMain.jsp`
  6. **获取课表**：
     - GET `https://jwgl.gsau.edu.cn/jsxsd/xskb/xskb_list.do`
     - 使用 kbtest.py 的 `parse_schedule()` 和 `print_schedule()` 解析打印
  
  **关键注意事项**：
  - 请求样本显示 authserver 登录页 HTML 中有**多个** execution 值（分别在 qrLoginForm、fidoLogin form、phoneFromId、pwdFromId 中），需要提取 `pwdLoginDiv` 内的那个
  - `pwdEncryptSalt` 也在 `pwdLoginDiv` 内：`<input type="hidden" id="pwdEncryptSalt" value="LwWkCGY5yajlPueU" />`
  - 登录 POST 的 service URL 是 `https://web.gsau.edu.cn/wengine-auth/login?cas_login=true`（从请求样本 line 1395 确认）
  - JS 重定向中的 service URL 是 `http://jwgl.gsau.edu.cn/`（注意是 http 不是 https，从 line 2144 确认）
  - 需要在每一步打印关键信息（状态码、重定向地址等）以便调试
  
  **编写完成后必须实际运行验证**：
  - 运行脚本，确认能成功登录
  - 确认能获取到课表 HTML（包含 "学期理论课表"）
  - 确认课表能正确解析和打印
  - 如果遇到问题，根据输出调试修复，直到完全正常工作

  **Must NOT do**:
  - 不要创建类或过度封装
  - 不要把每个小步骤都拆成单独函数
  - 不要添加不必要的错误处理和兜底逻辑
  - 不要添加命令行参数解析
  - 不要添加与任务相关的说明注释

  **Recommended Agent Profile**:
  - **Category**: `unspecified-low`
    - Reason: 单文件 Python 脚本，逻辑清晰，参考充分
  - **Skills**: []
    - 无需特殊技能

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential
  - **Blocks**: None
  - **Blocked By**: None

  **References**:

  **Pattern References**:
  - `D:\Lib\gsautools\nbu_logintest.py:8-57` — AES 加密实现（AES_CHARS、random_string、encrypt_password），直接复用
  - `D:\Lib\gsautools\nbu_logintest.py:60-103` — CAS 登录页参数提取（get_login_params），GSAU 使用相同的 wisedu CAS 系统，正则模式可复用
  - `D:\Lib\gsautools\nbu_logintest.py:106-230` — 登录流程结构（session 管理、重定向处理），参考整体流程但 GSAU 的重定向链不同
  - `D:\Lib\gsautools\kbtest.py:9-11` — random_uagent() 实现，直接复用（Windows Chrome UA 风格）
  - `D:\Lib\gsautools\kbtest.py:26-43` — fetch() 中的 session.trust_env = False 模式
  - `D:\Lib\gsautools\kbtest.py:46-116` — parse_cell、parse_schedule、print_schedule 课表解析和打印逻辑，直接复用
  - `D:\Lib\gsautools\kbtest.py:119-131` — handle_response 判断响应类型

  **请求流程参考（请求样本3）**:
  - `D:\Lib\gsautools\请求样本3_完整:1-36` — 初始 GET jwgl → 302 到 web.gsau.edu.cn
  - `D:\Lib\gsautools\请求样本3_完整:39-67` — web.gsau.edu.cn → 302 到 authserver（Set-Cookie: wengine_new_ticket）
  - `D:\Lib\gsautools\请求样本3_完整:70-453` — authserver 登录页 HTML（包含 pwdEncryptSalt、execution 等）
  - `D:\Lib\gsautools\请求样本3_完整:1352-1391` — checkNeedCaptcha 接口（返回 `{"isNeed":false}`，可选）
  - `D:\Lib\gsautools\请求样本3_完整:1395-1441` — POST 登录请求和响应（302 + ticket）
  - `D:\Lib\gsautools\请求样本3_完整:1444-1577` — 登录后重定向链（web.gsau.edu.cn → jwgl token-login → 新 wengine_new_ticket）
  - `D:\Lib\gsautools\请求样本3_完整:2111-2144` — jwgl 返回 JS 重定向（"该帐号不存在或密码错误" + JS redirect 到 authserver）
  - `D:\Lib\gsautools\请求样本3_完整:2148-2185` — 二次 authserver 认证（自动发 ticket，service=http://jwgl.gsau.edu.cn/）
  - `D:\Lib\gsautools\请求样本3_完整:2189-2271` — ticket 验证 → LoginToXk → xsMain.jsp（Set-Cookie: JSESSIONID for /jsxsd/）

  **Acceptance Criteria**:

  **Agent-Executed QA Scenarios:**

  ```
  Scenario: 完整登录并获取课表
    Tool: Bash
    Preconditions: Python 可用，pycryptodome 已安装
    Steps:
      1. python D:\Lib\gsautools\gsau_schedule.py
      2. Assert: 输出中包含登录过程的状态信息
      3. Assert: 输出中包含课表数据（"星期一" 或课程名称）或 "未解析到课程数据"（假期无课时）
      4. Assert: 不包含 "登录失败" 或 Python traceback
    Expected Result: 成功打印课表或提示当前无课程
    Evidence: 终端输出

  Scenario: 登录失败时的错误提示
    Tool: Bash（仅在上一场景失败时执行）
    Steps:
      1. 检查输出中的状态码和重定向信息
      2. 如果 POST 登录返回 200 而非 302，说明密码加密有误
      3. 如果 JS 重定向未被正确处理，说明正则提取有误
    Expected Result: 根据错误信息定位并修复问题
    Evidence: 终端输出
  ```

  **Commit**: NO

---

## Success Criteria

### Verification Commands
```bash
python D:\Lib\gsautools\gsau_schedule.py  # Expected: 打印课表内容
```

### Final Checklist
- [ ] 脚本能成功通过 CAS 登录
- [ ] 脚本能正确处理 JS 重定向（二次认证）
- [ ] 脚本能获取并打印课表
- [ ] 代码风格简洁，与现有脚本一致
