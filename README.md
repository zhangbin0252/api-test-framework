# 接口 + UI 自动化测试框架（Python + pytest + Requests + Playwright + Allure）

> 一个可以直接跑起来、可以讲清楚的自动化测试项目。
> 不依赖任何外部测试站，自带 Mock 服务（含 Web 前端），测试结果 **100% 可复现**。

## 项目背景

做这个项目的原因很直接：想系统练一遍接口自动化。

所以最后决定：**自己写一个 Mock 服务当被测系统**。

这样做反而带来三个好处：

1. 测试可以稳定复现，不会因为外部服务抽风导致流水线变红
2. 可以**故意埋缺陷**，让「发现 Bug」变成真的发现，而不是编的
3. 真实工作中本来就要用 Mock 隔离第三方依赖，这套思路可以直接迁移

后来在这个基础上又补了一层 **Playwright UI 自动化**，形成「接口 + UI」两层测试：
同一个被测系统，接口层测协议与业务逻辑，UI 层测用户真实操作路径，两层互相印证。

## 项目结构

```
api_test_framework/
├── config/
│   └── config.yaml            # base_url、超时、账号、UI 开关等全局配置
├── data/
│   ├── login.yaml             # 登录模块测试数据（10 条）
│   └── user.yaml              # 用户模块测试数据（18 条）
├── api/
│   ├── base_api.py            # 请求基类：统一发请求、带 token、记日志、挂 Allure 附件
│   └── user_api.py            # 用户/登录接口封装
├── business/
│   └── user_business.py       # 业务层：登录→访问、创建→查询 等跨接口组合
├── testcases/                 # 接口用例（62 条）
│   ├── conftest.py            # fixture：启动 Mock、登录复用、用例间数据隔离
│   ├── test_login.py          # 登录模块 13 条
│   ├── test_user.py           # 用户模块 19 条
│   ├── test_auth.py           # 鉴权与安全 6 条
│   ├── test_business_flow.py  # 业务流串联 4 条
│   └── test_httpbin.py        # HTTP 协议层 20 条（外部 httpbin，不通自动 skip）
├── ui/                        # UI 用例（19 条，Playwright）
│   ├── pytest.ini             # UI 测试独立配置
│   ├── conftest.py            # fixture：浏览器复用、上下文隔离、失败截图
│   ├── browser.py             # 浏览器管理（单例 + 独立上下文）
│   ├── base_page.py           # 页面对象基类：通用操作与断言封装
│   ├── login_page.py          # 登录页 PO
│   ├── user_list_page.py      # 用户列表页 PO
│   ├── test_login_ui.py       # 登录页用例 9 条
│   └── test_user_list_ui.py   # 用户列表页用例 10 条
├── mock_server/
│   ├── mock_server.py         # 被测系统：本地 Mock 服务（含 2 个已知缺陷）
│   └── static/                # 被测系统前端页面
│       ├── login.html         # 登录页
│       └── index.html         # 用户列表页
├── utils/
│   ├── yaml_util.py           # YAML 读取
│   ├── logger_util.py         # 日志（控制台 + 按天切分文件）
│   └── assert_util.py         # 断言工具：状态码/字段/嵌套/类型/响应时间
├── logs/                      # 运行日志
├── report/                    # Allure 结果与报告
├── pytest.ini                 # 接口测试配置
└── requirements.txt
```

## 分层设计

```
用例层 testcases/     只写业务逻辑与断言，不关心请求怎么发
        ↓
业务层 business/      把多个接口组合成一个业务动作（登录→访问受保护接口）
        ↓
接口层 api/           封装单个接口，统一处理 token、日志、异常
        ↓
数据层 data/          测试数据外置为 YAML，实现数据驱动
```

**为什么要分层？**
新增用例只改数据文件和用例文件，底层不用动；接口变了只改 api 层，用例不用动。
这是「可维护性」，也是面试官最常追问的点。

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt
playwright install chromium      # 首次运行 UI 用例前需要下载浏览器

# 2. 跑接口用例（Mock 服务会自动启动）
pytest

# 3. 跑 UI 用例
pytest -c ui/pytest.ini

# 4. 生成 Allure 报告
allure generate report/allure-results -o report/allure-report --clean
allure open report/allure-report
```

也可以单独启动 Mock 服务，用浏览器或 Postman 手工体验被测系统：

```bash
python mock_server/mock_server.py
# 登录页   http://127.0.0.1:8899/
# 用户列表 http://127.0.0.1:8899/app
```

## 测试结果

### 接口层（62 条）

| 模块 | 用例数 | 通过 | 失败 | 说明 |
|---|---|---|---|---|
| 登录模块 | 13 | 12 | 1 | 正常/异常/参数缺失/边界/敏感信息 |
| 用户管理 | 19 | 19 | 0 | 列表分页/详情/创建/更新/删除 |
| 鉴权与安全 | 6 | 5 | 1 | 未认证/伪造 token/越权/权限控制 |
| 业务流串联 | 4 | 4 | 0 | 登录鉴权链路/写后读/幂等/删除后查询 |
| HTTP 协议层 | 20 | 20 | 0 | 参数回显/鉴权/状态码/重定向（外部 httpbin） |
| **合计** | **62** | **60** | **2** | 2 条失败对应 2 个真实缺陷，见下 |

> 执行命令：`pytest`　|　耗时约 9.3 秒

### UI 层（19 条）

| 模块 | 用例数 | 通过 | 失败 | 说明 |
|---|---|---|---|---|
| 登录页 | 9 | 8 | 1 | 元素渲染/前端校验/登录成功/登录失败/密码掩码 |
| 用户列表页 | 10 | 10 | 0 | 列表渲染/表头/分页/新建用户/表单校验/退出/访问控制 |
| **合计** | **19** | **18** | **1** | 失败对应用户视角的 BUG-001，见下 |

> 执行命令：`pytest -c ui/pytest.ini`　|　耗时约 24 秒　|　技术栈：Playwright + Page Object 模式

### 代码规模

13 个接口相关 Python 文件 1304 行 + UI 层 9 个文件约 700 行，合计 **1800+ 行**。

## 发现的缺陷

### BUG-001｜登录接口密码错误时返回 500，应返回 401

- **严重程度**：中
- **优先级**：高
- **复现步骤**：
  1. `POST /api/login`
  2. 请求体 `{"username": "alice", "password": "wrong_password"}`
- **预期结果**：HTTP 401，`{"error": "invalid_credentials"}`
- **实际结果**：HTTP 500，`{"error": "internal_error", "message": "服务器内部错误"}`
- **影响**：密码错误属于正常的业务校验失败，返回 500 会让前端无法区分「密码错」和「服务挂了」，
  用户看到的是系统错误而不是「密码错误」提示；监控上也会产生大量无效告警。
- **用例**：`testcases/test_login.py::TestLogin::test_login[异常-密码错误...]`

### BUG-002｜用户详情接口未鉴权，未登录可查询任意用户（水平越权）

- **严重程度**：高
- **优先级**：高
- **复现步骤**：
  1. 不携带任何 `Authorization` 头
  2. `GET /api/users/1`
- **预期结果**：HTTP 401
- **实际结果**：HTTP 200，返回完整用户信息（含邮箱）
- **影响**：属于水平越权漏洞。攻击者遍历 id 即可批量拉取全部用户数据，是安全类缺陷。
- **用例**：`testcases/test_auth.py::TestAuth::test_unauthorized_read_user`

> 这两个缺陷是 Mock 服务里**故意保留**的，用来演示「接口测试如何发现页面点不出来的问题」。
> 真实项目里，这类缺陷往往就是接口测试最大的价值所在。

### 同一个缺陷，两个视角（面试可以重点讲）

BUG-001 在接口层和 UI 层的表现完全不同，这正好说明**为什么要做两层测试**：

| 视角 | 现象 | 断言 |
|---|---|---|
| 接口层 | `POST /api/login` 返回 500 | 期望 401，实际 500 → 失败 |
| UI 层 | 用户看到「系统异常，请稍后重试」 | 期望「用户名或密码错误」→ 失败 |

接口测试能精确定位到「状态码错了」，UI 测试能说明「用户实际看到什么」。
两者结合，缺陷单才完整——这是只做一层测试拿不到的信息。

## 过程中踩到并解决的坑

1. **用例之间状态污染**：删除用例改了内存数据，导致列表分页用例时好时坏
   → 用 session 级快照 + function 级恢复，保证用例相互独立
2. **HTTP keep-alive 请求体未读完**：服务端在 401/403 分支直接返回、没读请求体，
   残留字节被当成下一个请求的起始行，报 `Bad request syntax`
   → 所有提前返回的分支统一先 drain body
3. **UI 分页陷阱**：新建用户后断言「第 1 页应出现新用户」一直失败，
   实际是新用户 id 递增排到了最后一页
   → 用例改为翻到最后一页查找，而不是死盯第 1 页
4. **UI 用例互相污染登录态**：一开始所有用例共享一个浏览器上下文，
   退出登录的用例把后续用例全带崩了
   → 每个用例用独立的 context，Cookie / localStorage 完全隔离

## 技术栈

| 技术 | 用途 |
|---|---|
| Python 3.12 | 编程语言 |
| requests | 发 HTTP 请求，Session 支持会话保持 |
| pytest | 测试框架：fixture、参数化、标记 |
| allure-pytest | 可视化报告：步骤、附件、失败定位 |
| PyYAML | 测试数据外置，数据与代码分离 |
| http.server | 自建 Mock 被测系统（标准库，零依赖） |
| **Playwright** | **UI 自动化：驱动 Chromium，支持等待、截图、多上下文隔离** |
| **Page Object** | **UI 分层模式：页面元素与操作封装在页面类，用例只写业务逻辑** |

## UI 自动化设计说明

### Page Object 分层

```
用例层 ui/test_*_ui.py     只写业务逻辑与断言
        ↓
页面层 ui/*_page.py        封装页面元素定位与操作
        ↓
基类 ui/base_page.py       通用操作：点击/输入/等待/断言/截图
        ↓
驱动 ui/browser.py         浏览器生命周期与上下文管理
```


