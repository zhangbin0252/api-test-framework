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

---

## 关于缺陷用例的标记策略

对应上面两个缺陷的 3 条用例，代码里用了 `@pytest.mark.xfail(strict=True)` 标记：

| 文件 | 用例 | 对应缺陷 |
|---|---|---|
| `testcases/test_auth.py` | `test_unauthorized_read_user` | BUG-002 |
| `testcases/test_login.py` | `test_login[异常-密码错误...]` | BUG-001 |
| `ui/test_login_ui.py` | `test_login_wrong_password_bug001` | BUG-001（用户视角） |

**为什么不直接删掉，也不改成「断言缺陷行为」？**

1. **不能删**：这三条用例是缺陷存在的证据，删了就没法证明「测试能发现问题」。
2. **不能改成断言 500 / 断言显示"系统异常"**：那等于把 bug 写成了预期行为，
   缺陷修好之后用例反而会失败——这是最坏的做法，会把缺陷永久固化在代码里。
3. **不能放任它一直报红**：CI 长期是红的，团队就会习惯性忽略红色，
   真正的失败被淹没，流水线失去意义。

**`strict=True` 的关键作用**：

| 服务端状态 | 用例结果 | 含义 |
|---|---|---|
| 缺陷仍存在 | `xfailed` | 已知问题，不计入失败，流水线保持绿色 |
| 缺陷被修复 | **`XPASS` → 判定为失败** | 强制提醒：这个缺陷修好了，请删掉 xfail 标记 |

也就是说，标记会「自动到期」——缺陷一修，CI 立刻变红逼人处理。
这比单纯加个注释靠谱得多，因为注释不会有人看。

**当前执行结果**：

```
pytest                      →  60 passed, 2 xfailed
pytest -c ui/pytest.ini     →  18 passed, 1 xfailed
```

