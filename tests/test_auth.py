"""认证接口测试"""


class TestLogin:
    def test_login_success(self, client):
        """成功登录应返回 token 和用户信息"""
        resp = client.post("/api/auth/login", json={"code": "test_code_123"})
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "token" in data
        assert len(data["token"]) > 0
        assert data["user"]["nickname"].startswith("用户")
        assert data["user"]["id"] > 0

    def test_login_returns_same_user_for_same_code(self, client):
        """相同 code 应返回同一个用户"""
        resp1 = client.post("/api/auth/login", json={"code": "same_code"})
        resp2 = client.post("/api/auth/login", json={"code": "same_code"})
        uid1 = resp1.json()["data"]["user"]["id"]
        uid2 = resp2.json()["data"]["user"]["id"]
        assert uid1 == uid2

    def test_login_creates_different_users_for_different_codes(self, client):
        """不同 code 应创建不同用户"""
        resp1 = client.post("/api/auth/login", json={"code": "code_a"})
        resp2 = client.post("/api/auth/login", json={"code": "code_b"})
        uid1 = resp1.json()["data"]["user"]["id"]
        uid2 = resp2.json()["data"]["user"]["id"]
        assert uid1 != uid2

    def test_login_with_empty_code(self, client):
        """空 code 应返回校验错误"""
        resp = client.post("/api/auth/login", json={"code": ""})
        assert resp.status_code == 422

    def test_login_creates_user_with_default_avatar(self, client):
        """新用户的头像应为空字符串"""
        resp = client.post("/api/auth/login", json={"code": "new_user"})
        assert resp.json()["data"]["user"]["avatar"] == ""
