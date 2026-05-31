"""日历接口测试"""

import pytest


class TestCreateCalendar:
    def test_create_success(self, client, auth_headers):
        """创建日历应返回日历详情且包含邀请码"""
        resp = client.post(
            "/api/calendars",
            json={"name": "和闺蜜的小窝"},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()["data"]
        assert data["name"] == "和闺蜜的小窝"
        assert len(data["invite_code"]) == 6
        assert data["member_count"] == 1
        assert data["max_members"] == 4
        assert data["is_owner"] is True
        assert len(data["members"]) == 1
        assert data["members"][0]["role"] == "creator"

    def test_create_with_empty_name(self, client, auth_headers):
        """空名称应返回校验错误"""
        resp = client.post(
            "/api/calendars", json={"name": ""}, headers=auth_headers
        )
        assert resp.status_code == 422

    def test_create_with_long_name(self, client, auth_headers):
        """超长名称应返回校验错误"""
        resp = client.post(
            "/api/calendars", json={"name": "这是一个超过十个字的日历名称"}, headers=auth_headers
        )
        assert resp.status_code == 422

    def test_create_without_auth(self, client):
        """未登录应返回 401"""
        resp = client.post("/api/calendars", json={"name": "测试日历"})
        assert resp.status_code == 401


class TestListCalendars:
    def test_list_empty(self, client, auth_headers):
        """新用户应返回空列表"""
        resp = client.get("/api/calendars", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["data"] == []

    def test_list_after_create(self, client, auth_headers):
        """创建日历后列表应包含该日历"""
        client.post("/api/calendars", json={"name": "我的日历"}, headers=auth_headers)
        resp = client.get("/api/calendars", headers=auth_headers)
        assert len(resp.json()["data"]) == 1
        assert resp.json()["data"][0]["name"] == "我的日历"


class TestJoinCalendar:
    def test_join_success(self, client, auth_headers, another_headers, another_user):
        """通过邀请码加入日历"""
        # 创建日历
        create_resp = client.post(
            "/api/calendars", json={"name": "好友圈"}, headers=auth_headers
        )
        invite_code = create_resp.json()["data"]["invite_code"]

        # 另一个用户加入
        join_resp = client.post(
            "/api/calendars/join",
            json={"invite_code": invite_code},
            headers=another_headers,
        )
        assert join_resp.status_code == 200
        data = join_resp.json()["data"]
        assert data["member_count"] == 2
        assert len(data["members"]) == 2

    def test_join_invalid_code(self, client, auth_headers):
        """无效邀请码应返回错误"""
        resp = client.post(
            "/api/calendars/join",
            json={"invite_code": "XXXXXX"},
            headers=auth_headers,
        )
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "INVALID_INVITE_CODE"

    def test_join_wrong_length_code(self, client, auth_headers):
        """邀请码长度不对应返回校验错误"""
        resp = client.post(
            "/api/calendars/join",
            json={"invite_code": "ABC"},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_join_own_calendar_twice(self, client, auth_headers):
        """创建者不能再次加入自己的日历"""
        create_resp = client.post(
            "/api/calendars", json={"name": "我的"}, headers=auth_headers
        )
        code = create_resp.json()["data"]["invite_code"]

        resp = client.post(
            "/api/calendars/join",
            json={"invite_code": code},
            headers=auth_headers,
        )
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "ALREADY_MEMBER"

    def test_join_when_full(self, client, auth_headers, another_headers, another_user, db):
        """满员时返回错误"""
        from app.models.calendar import Calendar, CalendarMember
        from app.models.user import User

        # 创建日历
        create_resp = client.post(
            "/api/calendars", json={"name": "满员测试"}, headers=auth_headers
        )
        cal_id = create_resp.json()["data"]["id"]
        invite_code = create_resp.json()["data"]["invite_code"]

        # 手动塞满额外成员（共 4 人）
        for i in range(3, 6):
            u = User(openid=f"test_fill_{i}", nickname=f"用户{i}", avatar="")
            db.add(u)
            db.flush()
            m = CalendarMember(calendar_id=cal_id, user_id=u.id, role="member")
            db.add(m)
            cal = db.query(Calendar).filter(Calendar.id == cal_id).first()
            cal.member_count += 1
        db.commit()

        # 第 5 人加入应失败
        resp = client.post(
            "/api/calendars/join",
            json={"invite_code": invite_code},
            headers=another_headers,
        )
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "CALENDAR_FULL"


class TestCalendarDetail:
    def test_get_detail(self, client, auth_headers):
        """获取日历详情应返回完整信息"""
        create_resp = client.post(
            "/api/calendars", json={"name": "我的日历"}, headers=auth_headers
        )
        cal_id = create_resp.json()["data"]["id"]

        resp = client.get(f"/api/calendars/{cal_id}", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["name"] == "我的日历"
        assert data["is_owner"] is True

    def test_get_nonexistent(self, client, auth_headers):
        """不存在的日历应返回 404"""
        resp = client.get("/api/calendars/99999", headers=auth_headers)
        assert resp.status_code == 404

    def test_get_without_permission(self, client, auth_headers, another_headers):
        """非成员访问应返回 403"""
        create_resp = client.post(
            "/api/calendars", json={"name": "私密日历"}, headers=auth_headers
        )
        cal_id = create_resp.json()["data"]["id"]

        resp = client.get(f"/api/calendars/{cal_id}", headers=another_headers)
        assert resp.status_code == 403


class TestUpdateCalendar:
    def test_update_name(self, client, auth_headers):
        """创建者可修改日历名称"""
        create_resp = client.post(
            "/api/calendars", json={"name": "旧名称"}, headers=auth_headers
        )
        cal_id = create_resp.json()["data"]["id"]

        resp = client.patch(
            f"/api/calendars/{cal_id}",
            json={"name": "新名称"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["name"] == "新名称"

    def test_non_creator_cannot_update(self, client, auth_headers, another_headers):
        """非创建者不能修改日历名称"""
        create_resp = client.post(
            "/api/calendars", json={"name": "固定名称"}, headers=auth_headers
        )
        cal_id = create_resp.json()["data"]["id"]

        resp = client.patch(
            f"/api/calendars/{cal_id}",
            json={"name": "想改名"},
            headers=another_headers,
        )
        assert resp.status_code == 403


class TestDisbandCalendar:
    def test_creator_can_disband(self, client, auth_headers):
        """创建者可解散日历"""
        create_resp = client.post(
            "/api/calendars", json={"name": "待解散"}, headers=auth_headers
        )
        cal_id = create_resp.json()["data"]["id"]

        resp = client.delete(f"/api/calendars/{cal_id}", headers=auth_headers)
        assert resp.status_code == 204

    def test_non_creator_cannot_disband(self, client, auth_headers, another_headers):
        """非创建者不能解散日历"""
        create_resp = client.post(
            "/api/calendars", json={"name": "我的日历"}, headers=auth_headers
        )
        cal_id = create_resp.json()["data"]["id"]
        code = create_resp.json()["data"]["invite_code"]

        # 另一个用户加入
        client.post(
            "/api/calendars/join",
            json={"invite_code": code},
            headers=another_headers,
        )

        # 尝试解散
        resp = client.delete(f"/api/calendars/{cal_id}", headers=another_headers)
        assert resp.status_code == 403


class TestMembers:
    def test_list_members(self, client, auth_headers):
        """获取成员列表"""
        create_resp = client.post(
            "/api/calendars", json={"name": "团队"}, headers=auth_headers
        )
        cal_id = create_resp.json()["data"]["id"]

        resp = client.get(
            f"/api/calendars/{cal_id}/members", headers=auth_headers
        )
        assert resp.status_code == 200
        assert len(resp.json()["data"]) == 1
        assert resp.json()["data"][0]["role"] == "creator"

    def test_list_members_non_member_forbidden(self, client, auth_headers, another_headers):
        """非成员不能查看成员列表"""
        create_resp = client.post(
            "/api/calendars", json={"name": "私密"}, headers=auth_headers
        )
        cal_id = create_resp.json()["data"]["id"]

        resp = client.get(
            f"/api/calendars/{cal_id}/members", headers=another_headers
        )
        assert resp.status_code == 403

    def test_remove_member(self, client, auth_headers, another_headers, another_user):
        """创建者可移除成员"""
        create_resp = client.post(
            "/api/calendars", json={"name": "团队"}, headers=auth_headers
        )
        cal_id = create_resp.json()["data"]["id"]
        code = create_resp.json()["data"]["invite_code"]

        client.post(
            "/api/calendars/join",
            json={"invite_code": code},
            headers=another_headers,
        )

        resp = client.delete(
            f"/api/calendars/{cal_id}/members/{another_user.id}",
            headers=auth_headers,
        )
        assert resp.status_code == 204

    def test_creator_cannot_remove_self(self, client, auth_headers, test_user):
        """创建者不能移除自己"""
        create_resp = client.post(
            "/api/calendars", json={"name": "我的"}, headers=auth_headers
        )
        cal_id = create_resp.json()["data"]["id"]

        resp = client.delete(
            f"/api/calendars/{cal_id}/members/{test_user.id}",
            headers=auth_headers,
        )
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "SELF_REMOVE_NOT_ALLOWED"
