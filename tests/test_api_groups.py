from tests.conftest import auth_header, register_user


# ------------------------------------------------------------------ helpers
async def _register_main(client):
    """Register the primary user and return (token, user_dict)."""
    data = await register_user(
        client,
        email="alice@example.com",
        password="Secret123!",
        first_name="Alice",
        last_name="Smith",
    )
    return data["access_token"], data["user"]


async def _register_secondary(client):
    """Register a secondary user and return (token, user_dict)."""
    data = await register_user(
        client,
        email="bob@example.com",
        password="Secret456!",
        first_name="Bob",
        last_name="Jones",
    )
    return data["access_token"], data["user"]


# ------------------------------------------------ 1. create group
async def test_create_group(client):
    token, _ = await _register_main(client)

    resp = await client.post(
        "/api/v1/groups",
        json={"name": "Household", "description": "Shared expenses"},
        headers=auth_header(token),
    )
    assert resp.status_code == 201

    body = resp.json()
    assert body["name"] == "Household"
    assert body["description"] == "Shared expenses"
    assert "id" in body


# ------------------------------------------------ 2. list groups
async def test_list_groups(client):
    token, _ = await _register_main(client)

    # create two groups
    await client.post(
        "/api/v1/groups",
        json={"name": "Group A"},
        headers=auth_header(token),
    )
    await client.post(
        "/api/v1/groups",
        json={"name": "Group B"},
        headers=auth_header(token),
    )

    resp = await client.get("/api/v1/groups", headers=auth_header(token))
    assert resp.status_code == 200

    groups = resp.json()
    assert isinstance(groups, list)
    assert len(groups) >= 2
    names = [g["name"] for g in groups]
    assert "Group A" in names
    assert "Group B" in names


# ------------------------------------------------ 3. get group by id
async def test_get_group_by_id(client):
    token, _ = await _register_main(client)

    create_resp = await client.post(
        "/api/v1/groups",
        json={"name": "Travel Fund"},
        headers=auth_header(token),
    )
    group_id = create_resp.json()["id"]

    resp = await client.get(f"/api/v1/groups/{group_id}", headers=auth_header(token))
    assert resp.status_code == 200

    body = resp.json()
    assert body["id"] == group_id
    assert body["name"] == "Travel Fund"


# ------------------------------------------------ 4. add member
async def test_add_member(client):
    token, _ = await _register_main(client)
    _, second_user = await _register_secondary(client)

    # create a group
    create_resp = await client.post(
        "/api/v1/groups",
        json={"name": "Shared"},
        headers=auth_header(token),
    )
    group_id = create_resp.json()["id"]

    # add second user
    resp = await client.post(
        f"/api/v1/groups/{group_id}/members",
        json={"user_id": second_user["id"]},
        headers=auth_header(token),
    )
    assert resp.status_code == 201

    # verify via group detail
    detail = await client.get(f"/api/v1/groups/{group_id}", headers=auth_header(token))
    member_ids = [m["id"] for m in detail.json().get("members", [])]
    assert second_user["id"] in member_ids


# ------------------------------------------------ 5. remove member
async def test_remove_member(client):
    token, _ = await _register_main(client)
    _, second_user = await _register_secondary(client)

    # create a group and add second user
    create_resp = await client.post(
        "/api/v1/groups",
        json={"name": "Temp Group"},
        headers=auth_header(token),
    )
    group_id = create_resp.json()["id"]

    await client.post(
        f"/api/v1/groups/{group_id}/members",
        json={"user_id": second_user["id"]},
        headers=auth_header(token),
    )

    # remove the second user (member_id is user_id)
    resp = await client.delete(
        f"/api/v1/groups/{group_id}/members/{second_user['id']}",
        headers=auth_header(token),
    )
    assert resp.status_code == 204

    # verify removal
    detail = await client.get(f"/api/v1/groups/{group_id}", headers=auth_header(token))
    member_ids = [m["id"] for m in detail.json().get("members", [])]
    assert second_user["id"] not in member_ids


# ------------------------------------------------ 6. get nonexistent group
async def test_get_nonexistent_group(client):
    token, _ = await _register_main(client)

    resp = await client.get("/api/v1/groups/999999", headers=auth_header(token))
    assert resp.status_code == 404
