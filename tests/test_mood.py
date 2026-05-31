"""心情记录接口测试"""

from datetime import date


class TestCreateMoodEntry:
    def _create_calendar(self, client, headers):
        """辅助：创建日历并返回 ID"""
        resp = client.post("/api/calendars", json={"name": "心情簿"}, headers=headers)
        return resp.json()["data"]["id"]

    def test_create_entry_success(self, client, auth_headers):
        """成功创建心情记录"""
        cal_id = self._create_calendar(client, auth_headers)

        resp = client.post(
            f"/api/calendars/{cal_id}/entries",
            json={
                "date": "2026-05-20",
                "mood_type": "happy",
                "text": "今天很开心！",
                "image_urls": [],
            },
            headers=auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()["data"]
        assert data["mood_type"] == "happy"
        assert data["text"] == "今天很开心！"
        assert data["image_urls"] == []
        assert data["user"]["nickname"] == "测试用户"

    def test_create_duplicate_entry(self, client, auth_headers):
        """同一天不能重复记录"""
        cal_id = self._create_calendar(client, auth_headers)
        payload = {"date": "2026-05-20", "mood_type": "happy", "text": "开心"}

        client.post(
            f"/api/calendars/{cal_id}/entries", json=payload, headers=auth_headers
        )
        resp = client.post(
            f"/api/calendars/{cal_id}/entries", json=payload, headers=auth_headers
        )
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "ENTRY_ALREADY_EXISTS"

    def test_different_calendar_same_day_allowed(self, client, auth_headers):
        """不同日历同一天可以分别记录"""
        cal1 = self._create_calendar(client, auth_headers)
        cal2 = self._create_calendar(client, auth_headers)
        payload = {"date": "2026-05-20", "mood_type": "calm", "text": "平静"}

        resp1 = client.post(
            f"/api/calendars/{cal1}/entries", json=payload, headers=auth_headers
        )
        resp2 = client.post(
            f"/api/calendars/{cal2}/entries", json=payload, headers=auth_headers
        )
        assert resp1.status_code == 201
        assert resp2.status_code == 201

    def test_invalid_mood_type(self, client, auth_headers):
        """无效的心情类型应返回校验错误"""
        cal_id = self._create_calendar(client, auth_headers)
        resp = client.post(
            f"/api/calendars/{cal_id}/entries",
            json={"date": "2026-05-20", "mood_type": "angry", "text": "测试"},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_mood_types_accepted(self, client, auth_headers):
        """所有心情类型都可接受"""
        cal_id = self._create_calendar(client, auth_headers)
        for i, mood in enumerate(["happy", "calm", "sad"], start=1):
            resp = client.post(
                f"/api/calendars/{cal_id}/entries",
                json={"date": f"2026-06-{i:02d}", "mood_type": mood},
                headers=auth_headers,
            )
            assert resp.status_code == 201

    def test_text_too_long(self, client, auth_headers):
        """文字超过 500 字应返回校验错误"""
        cal_id = self._create_calendar(client, auth_headers)
        resp = client.post(
            f"/api/calendars/{cal_id}/entries",
            json={"date": "2026-05-20", "mood_type": "happy", "text": "字" * 501},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_too_many_images(self, client, auth_headers):
        """超过 3 张图片应返回校验错误"""
        cal_id = self._create_calendar(client, auth_headers)
        resp = client.post(
            f"/api/calendars/{cal_id}/entries",
            json={
                "date": "2026-05-20",
                "mood_type": "happy",
                "text": "开心",
                "image_urls": [f"https://example.com/img{i}.jpg" for i in range(4)],
            },
            headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_without_auth(self, client):
        """未登录不可创建"""
        resp = client.post(
            "/api/calendars/1/entries",
            json={"date": "2026-05-20", "mood_type": "happy"},
        )
        assert resp.status_code == 401

    def test_non_member_cannot_create(self, client, auth_headers, another_headers):
        """非成员不可创建"""
        cal_id = self._create_calendar(client, auth_headers)
        resp = client.post(
            f"/api/calendars/{cal_id}/entries",
            json={"date": "2026-05-20", "mood_type": "happy"},
            headers=another_headers,
        )
        assert resp.status_code == 403


class TestListEntries:
    def _create_calendar(self, client, headers):
        resp = client.post("/api/calendars", json={"name": "心情簿"}, headers=headers)
        return resp.json()["data"]["id"]

    def test_list_empty_month(self, client, auth_headers):
        """空月份应返回空列表"""
        cal_id = self._create_calendar(client, auth_headers)
        resp = client.get(
            f"/api/calendars/{cal_id}/entries",
            params={"year": 2026, "month": 5},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["year"] == 2026
        assert data["month"] == 5
        assert data["entries"] == []

    def test_list_entries_non_member_forbidden(self, client, auth_headers, another_headers):
        """非成员不能查看心情列表"""
        cal_id = self._create_calendar(client, auth_headers)
        resp = client.get(
            f"/api/calendars/{cal_id}/entries",
            params={"year": 2026, "month": 5},
            headers=another_headers,
        )
        assert resp.status_code == 403

    def test_list_with_entries(self, client, auth_headers):
        """有记录时返回该月所有心情"""
        cal_id = self._create_calendar(client, auth_headers)

        # 创建两条记录
        client.post(
            f"/api/calendars/{cal_id}/entries",
            json={"date": "2026-05-20", "mood_type": "happy", "text": "开心"},
            headers=auth_headers,
        )
        client.post(
            f"/api/calendars/{cal_id}/entries",
            json={"date": "2026-05-21", "mood_type": "sad", "text": "难过"},
            headers=auth_headers,
        )

        resp = client.get(
            f"/api/calendars/{cal_id}/entries",
            params={"year": 2026, "month": 5},
            headers=auth_headers,
        )
        assert len(resp.json()["data"]["entries"]) == 2


class TestGetEntry:
    def _create_entry(self, client, headers):
        """辅助：创建一条心情记录并返回其 ID"""
        resp = client.post("/api/calendars", json={"name": "心情簿"}, headers=headers)
        cal_id = resp.json()["data"]["id"]

        resp = client.post(
            f"/api/calendars/{cal_id}/entries",
            json={"date": "2026-05-20", "mood_type": "happy", "text": "超开心！"},
            headers=headers,
        )
        return resp.json()["data"]["id"]

    def test_get_entry(self, client, auth_headers):
        """获取心情详情"""
        entry_id = self._create_entry(client, auth_headers)

        resp = client.get(f"/api/entries/{entry_id}", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["mood_type"] == "happy"
        assert data["text"] == "超开心！"

    def test_get_nonexistent(self, client, auth_headers):
        """不存在的心情记录应返回 404"""
        resp = client.get("/api/entries/99999", headers=auth_headers)
        assert resp.status_code == 404

    def test_get_entry_non_member_forbidden(self, client, auth_headers, another_headers):
        """非成员不能查看心情详情"""
        entry_id = self._create_entry(client, auth_headers)
        resp = client.get(f"/api/entries/{entry_id}", headers=another_headers)
        assert resp.status_code == 403


class TestDeleteEntry:
    def _create_entry(self, client, headers):
        resp = client.post("/api/calendars", json={"name": "心情簿"}, headers=headers)
        cal_id = resp.json()["data"]["id"]
        resp = client.post(
            f"/api/calendars/{cal_id}/entries",
            json={"date": "2026-05-20", "mood_type": "happy"},
            headers=headers,
        )
        return resp.json()["data"]["id"]

    def test_delete_own_entry(self, client, auth_headers):
        """删除自己的心情记录"""
        entry_id = self._create_entry(client, auth_headers)
        resp = client.delete(f"/api/entries/{entry_id}", headers=auth_headers)
        assert resp.status_code == 204

    def test_delete_others_entry(self, client, auth_headers, another_headers):
        """不能删除别人的记录"""
        entry_id = self._create_entry(client, auth_headers)
        resp = client.delete(f"/api/entries/{entry_id}", headers=another_headers)
        assert resp.status_code == 403
