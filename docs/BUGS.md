# 缺陷记录

测试过程中发现的真实问题。每条都可用 `pytest` 复现。

| 编号 | 标题 | 严重程度 | 优先级 | 状态 | 对应用例 |
|---|---|---|---|---|---|
| BUG-001 | 登录接口密码错误时返回 500，应返回 401 | 中 | 高 | 待修复 | `test_login.py::test_login[异常-密码错误...]` |
| BUG-002 | 用户详情接口未鉴权，未登录可查询任意用户 | 高 | 高 | 待修复 | `test_auth.py::test_unauthorized_read_user` |

---

## BUG-001｜登录接口密码错误时返回 500

- **模块**：登录模块
- **接口**：`POST /api/login`
- **严重程度**：中　**优先级**：高
- **发现版本**：mock_server v1.0
- **状态**：待修复

### 复现步骤
1. 启动 Mock 服务：`python mock_server/mock_server.py`
2. 发送请求：
   ```bash
   curl -X POST http://127.0.0.1:8899/api/login \
        -H "Content-Type: application/json" \
        -d '{"username":"alice","password":"wrong_password"}'
   ```

### 预期结果
```
HTTP 401
{"error": "invalid_credentials", "message": "用户名或密码错误"}
```

### 实际结果
```
HTTP 500
{"error": "internal_error", "message": "服务器内部错误"}
```

### 影响分析
密码错误是**正常的业务校验失败**，不属于服务端异常。
返回 500 会带来三个问题：
1. 前端无法区分「密码错」和「服务挂了」，只能统一提示「系统错误」，用户体验差
2. 监控系统会把这类请求计入 5xx 错误率，产生大量无效告警
3. 掩盖了真实的服务器异常，增加排查成本

### 修复建议
在密码比对失败的分支返回 401，而不是抛出未捕获异常：
```python
if ACCOUNTS[username] != password:
    return self._send(401, {"error": "invalid_credentials", "message": "用户名或密码错误"})
```

---

## BUG-002｜用户详情接口未鉴权（水平越权）

- **模块**：用户管理
- **接口**：`GET /api/users/{id}`
- **严重程度**：高　**优先级**：高
- **发现版本**：mock_server v1.0
- **状态**：待修复
- **缺陷类型**：安全漏洞 / 权限控制缺失

### 复现步骤
1. **不携带任何** `Authorization` 请求头
2. 直接请求任意用户 id：
   ```bash
   curl http://127.0.0.1:8899/api/users/1
   ```

### 预期结果
```
HTTP 401
{"error": "unauthorized", "message": "请先登录"}
```

### 实际结果
```
HTTP 200
{"data": {"id": 1, "username": "alice", "email": "alice@example.com", "role": "admin", "status": "active"}}
```

### 影响分析
这是典型的**水平越权**（IDOR）漏洞：
- 攻击者无需登录，遍历 `id` 即可批量拉取全部用户数据
- 返回内容包含 `email`、`role` 等敏感字段，`role=admin` 还暴露了管理员身份
- 如果线上存在同类问题，属于需要立即修复的安全缺陷

### 修复建议
在 `_get_user` 入口增加鉴权校验：
```python
def _get_user(self, uid):
    user = self._auth_user()
    if user is None:
        return self._send(401, {"error": "unauthorized", "message": "请先登录"})
    ...
```

---

## 说明

这两个缺陷是 Mock 服务里**故意保留**的，目的是演示接口测试的价值：
**页面点不出来的问题，接口测试能测出来。**

真实项目中的缺陷单还应包含：截图/录屏附件、日志片段、关联需求编号、修复人、修复版本、回归结果。
本文件为了便于阅读做了精简。
