# 接口自动化测试框架（Python + Requests + pytest + Allure）

> 一个可以直接跑起来、可以讲清楚的接口自动化测试项目。
> 不依赖任何外部测试站，自带 Mock 服务，测试结果 **100% 可复现**。

## 项目背景

做这个项目的原因很直接：想系统练一遍接口自动化。

所以最后决定：**自己写一个 Mock 服务当被测系统**。

这样做反而带来三个好处：

1. 测试可以稳定复现，不会因为外部服务抽风导致流水线变红
2. 可以**故意埋缺陷**，让「发现 Bug」变成真的发现，而不是编的
3. 真实工作中本来就要用 Mock 隔离第三方依赖，这套思路可以直接迁移

## 项目结构

```
api_test_framework/
├── config/
│   └── config.yaml            # base_url、超时、账号等全局配置
├── data/
│   ├── login.yaml             # 登录模块测试数据（10 条）
│   └── user.yaml              # 用户模块测试数据（18 条）
├── api/
│   ├── base_api.py            # 请求基类：统一发请求、带 token、记日志、挂 Allure 附件
│   └── user_api.py            # 用户/登录接口封装
├── business/
│   └── user_business.py       # 业务层：登录→访问、创建→查询 等跨接口组合
├── testcases/
│   ├── conftest.py            # fixture：启动 Mock、登录复用、用例间数据隔离
│   ├── test_login.py          # 登录模块 13 条
│   ├── test_user.py           # 用户模块 19 条
│   ├── test_auth.py           # 鉴权与安全 6 条
│   ├── test_business_flow.py  # 业务流串联 4 条
│   └── test_httpbin.py        # HTTP 协议层 20 条（外部 httpbin，不通自动 skip）
├── mock_server/
│   └── mock_server.py         # 被测系统：本地 Mock 服务（含 2 个已知缺陷）
├── utils/
│   ├── yaml_util.py           # YAML 读取
│   ├── logger_util.py         # 日志（控制台 + 按天切分文件）
│   └── assert_util.py         # 断言工具：状态码/字段/嵌套/类型/响应时间
├── logs/                      # 运行日志
├── report/                    # Allure 结果与报告
├── pytest.ini
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

# 2. 跑全部用例（Mock 服务会自动启动）
pytest

# 3. 生成 Allure 报告
allure generate report/allure-results -o report/allure-report --clean
allure open report/allure-report
```

也可以单独启动 Mock 服务，方便用 Postman 手工调试：

```bash
python mock_server/mock_server.py
# 服务地址 http://127.0.0.1:8899
```

## 测试结果

| 模块 | 用例数 | 通过 | 失败 | 说明 |
|---|---|---|---|---|
| 登录模块 | 13 | 12 | 1 | 正常/异常/参数缺失/边界/敏感信息 |
| 用户管理 | 19 | 19 | 0 | 列表分页/详情/创建/更新/删除 |
| 鉴权与安全 | 6 | 5 | 1 | 未认证/伪造 token/越权/权限控制 |
| 业务流串联 | 4 | 4 | 0 | 登录鉴权链路/写后读/幂等/删除后查询 |
| HTTP 协议层 | 20 | 20 | 0 | 参数回显/鉴权/状态码/重定向（外部 httpbin） |
| **合计** | **62** | **60** | **2** | 2 条失败对应 2 个真实缺陷，见下 |

> 执行命令：`pytest`　|　耗时约 9.3 秒　|　代码规模：13 个 Python 文件、1304 行

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

## 过程中踩到并解决的坑

1. **公开测试站不可靠**：黑马商城 410 下线、reqres.in 每日 40 次限流 → 改为自建 Mock
2. **用例之间状态污染**：删除用例改了内存数据，导致列表分页用例时好时坏
   → 用 session 级快照 + function 级恢复，保证用例相互独立
3. **HTTP keep-alive 请求体未读完**：服务端在 401/403 分支直接返回、没读请求体，
   残留字节被当成下一个请求的起始行，报 `Bad request syntax`
   → 所有提前返回的分支统一先 drain body

## 技术栈

| 技术 | 用途 |
|---|---|
| Python 3.8+ | 编程语言 |
| requests | 发 HTTP 请求，Session 支持会话保持 |
| pytest | 测试框架：fixture、参数化、标记 |
| allure-pytest | 可视化报告：步骤、附件、失败定位 |
| PyYAML | 测试数据外置，数据与代码分离 |
| http.server | 自建 Mock 被测系统（标准库，零依赖） |
