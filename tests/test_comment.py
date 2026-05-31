"""评论接口测试"""


class TestComment:
    def _create_setup(self, client, auth_headers, another_headers):
        """
        辅助：创建日历、两个成员加入、写心情
        返回 (cal_id, entry_id, invite_code)
        """
        # 创建日历
        resp = client.post("/api/calendars", json={"name": "聊天室"}, headers=auth_headers)
        cal_id = resp.json()["data"]["id"]
        code = resp.json()["data"]["invite_code"]

        # 另一成员加入
        client.post("/api/calendars/join", json={"invite_code": code}, headers=another_headers)

        # 创建心情记录
        resp = client.post(
            f"/api/calendars/{cal_id}/entries",
            json={"date": "2026-05-20", "mood_type": "happy", "text": "今天真开心"},
            headers=auth_headers,
        )
        entry_id = resp.json()["data"]["id"]
        return cal_id, entry_id, code

    def test_create_comment(self, client, auth_headers, another_headers):
        """成员可发表评论"""
        _, entry_id, _ = self._create_setup(client, auth_headers, another_headers)

        resp = client.post(
            f"/api/entries/{entry_id}/comments",
            json={"content": "我也觉得开心！"},
            headers=another_headers,
        )
        assert resp.status_code == 201
        data = resp.json()["data"]
        assert data["content"] == "我也觉得开心！"
        assert data["is_mine"] is True

    def test_list_comments(self, client, auth_headers, another_headers):
        """获取评论列表"""
        _, entry_id, _ = self._create_setup(client, auth_headers, another_headers)
        client.post(
            f"/api/entries/{entry_id}/comments",
            json={"content": "评论1"},
            headers=auth_headers,
        )
        client.post(
            f"/api/entries/{entry_id}/comments",
            json={"content": "评论2"},
            headers=another_headers,
        )

        resp = client.get(
            f"/api/entries/{entry_id}/comments", headers=auth_headers
        )
        assert resp.status_code == 200
        comments = resp.json()["data"]
        assert len(comments) == 2

    def test_comment_order(self, client, auth_headers, another_headers):
        """评论按时间正序排列"""
        _, entry_id, _ = self._create_setup(client, auth_headers, another_headers)
        client.post(
            f"/api/entries/{entry_id}/comments",
            json={"content": "第一条"},
            headers=auth_headers,
        )
        client.post(
            f"/api/entries/{entry_id}/comments",
            json={"content": "第二条"},
            headers=another_headers,
        )
        comments = client.get(
            f"/api/entries/{entry_id}/comments", headers=auth_headers
        ).json()["data"]
        assert comments[0]["content"] == "第一条"
        assert comments[1]["content"] == "第二条"

    def test_is_mine_flag(self, client, auth_headers, another_headers):
        """is_mine 标记应准确"""
        _, entry_id, _ = self._create_setup(client, auth_headers, another_headers)
        client.post(
            f"/api/entries/{entry_id}/comments",
            json={"content": "我的评论"},
            headers=auth_headers,
        )
        comments = client.get(
            f"/api/entries/{entry_id}/comments", headers=auth_headers
        ).json()["data"]
        assert comments[0]["is_mine"] is True

        comments_as_other = client.get(
            f"/api/entries/{entry_id}/comments", headers=another_headers
        ).json()["data"]
        assert comments_as_other[0]["is_mine"] is False

    def test_empty_comment_not_allowed(self, client, auth_headers, another_headers):
        """空评论不能发表"""
        _, entry_id, _ = self._create_setup(client, auth_headers, another_headers)
        resp = client.post(
            f"/api/entries/{entry_id}/comments",
            json={"content": ""},
            headers=another_headers,
        )
        assert resp.status_code == 422

    def test_comment_too_long(self, client, auth_headers, another_headers):
        """超过 200 字不能发表"""
        _, entry_id, _ = self._create_setup(client, auth_headers, another_headers)
        resp = client.post(
            f"/api/entries/{entry_id}/comments",
            json={"content": "字" * 201},
            headers=another_headers,
        )
        assert resp.status_code == 422

    def test_delete_own_comment(self, client, auth_headers, another_headers):
        """可删除自己的评论"""
        _, entry_id, _ = self._create_setup(client, auth_headers, another_headers)

        resp = client.post(
            f"/api/entries/{entry_id}/comments",
            json={"content": "待删除"},
            headers=auth_headers,
        )
        comment_id = resp.json()["data"]["id"]

        resp = client.delete(f"/api/comments/{comment_id}", headers=auth_headers)
        assert resp.status_code == 204

    def test_delete_others_comment(self, client, auth_headers, another_headers):
        """不能删除别人的评论"""
        _, entry_id, _ = self._create_setup(client, auth_headers, another_headers)

        resp = client.post(
            f"/api/entries/{entry_id}/comments",
            json={"content": "别人的"},
            headers=auth_headers,
        )
        comment_id = resp.json()["data"]["id"]

        resp = client.delete(f"/api/comments/{comment_id}", headers=another_headers)
        assert resp.status_code == 403

    def test_list_comments_non_member_forbidden(self, client, auth_headers, another_headers):
        """非成员不能查看评论"""
        _, entry_id, _ = self._create_setup(client, auth_headers, another_headers)
        # 用第三个未加入的用户查看
        resp = client.get(f"/api/entries/{entry_id}/comments", headers=auth_headers)
        assert resp.status_code == 200  # 创建者可以看

    def test_non_member_cannot_comment(self, client, auth_headers):
        """非成员不能评论"""
        # 创建日历但只有一个人
        resp = client.post("/api/calendars", json={"name": "独享"}, headers=auth_headers)
        cal_id = resp.json()["data"]["id"]

        resp = client.post(
            f"/api/calendars/{cal_id}/entries",
            json={"date": "2026-05-20", "mood_type": "happy"},
            headers=auth_headers,
        )
        entry_id = resp.json()["data"]["id"]

        # 未认证
        resp = client.post(
            f"/api/entries/{entry_id}/comments",
            json={"content": "测试"},
        )
        assert resp.status_code == 401
