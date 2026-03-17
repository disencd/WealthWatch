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
    return data["token"], data["user"]


async def _register_secondary(client):
    """Register a secondary user and return (token, user_dict)."""
    data = await register_user(
        client,
        email="bob@example.com",
        password="Secret456!",
        first_name="Bob",
        last_name="Jones",
    )
    return data["token"], data["user"]


# ------------------------------------------------ 1. list families after register
async def test_list_families_after_register(client):
    token, _ = await _register_main(client)

    resp = await client.get("/api/v1/families", headers=auth_header(token))
    assert resp.status_code == 200

    families = resp.json()
    assert isinstance(families, list)
    assert len(families) >= 1  # auto-created during registration


# ------------------------------------------------ 2. create a new family
async def test_create_family(client):
    token, _ = await _register_main(client)

    resp = await client.post(
        "/api/v1/families",
        json={"name": "Vacation Fund", "currency": "EUR"},
        headers=auth_header(token),
    )
    assert resp.status_code == 201

    body = resp.json()
    assert body["name"] == "Vacation Fund"
    assert body["currency"] == "EUR"


# ------------------------------------------------ 3. list members (should have 1 - self)
async def test_list_members_self(client):
    token, user = await _register_main(client)

    resp = await client.get("/api/v1/families/members", headers=auth_header(token))
    assert resp.status_code == 200

    members = resp.json()
    assert isinstance(members, list)
    assert len(members) == 1
    # the sole member should be the registering user
    assert members[0]["user"]["email"] == user["email"]


# ------------------------------------------------ 4. add member
async def test_add_member(client):
    token, _ = await _register_main(client)
    _, second_user = await _register_secondary(client)

    resp = await client.post(
        "/api/v1/families/members",
        json={"email": second_user["email"], "role": "member"},
        headers=auth_header(token),
    )
    assert resp.status_code == 201

    body = resp.json()
    assert body["user_id"] == second_user["id"]


# ------------------------------------------------ 5. update member role
async def test_update_member_role(client):
    token, _ = await _register_main(client)
    _, second_user = await _register_secondary(client)

    # add the second user first
    add_resp = await client.post(
        "/api/v1/families/members",
        json={"email": second_user["email"], "role": "member"},
        headers=auth_header(token),
    )
    assert add_resp.status_code == 201
    member_id = add_resp.json()["id"]

    # update role to admin
    resp = await client.put(
        f"/api/v1/families/members/{member_id}/role",
        json={"role": "admin"},
        headers=auth_header(token),
    )
    assert resp.status_code == 200

    body = resp.json()
    assert body["role"] == "admin"


# ------------------------------------------------ 6. remove member
async def test_remove_member(client):
    token, _ = await _register_main(client)
    _, second_user = await _register_secondary(client)

    # add the second user
    add_resp = await client.post(
        "/api/v1/families/members",
        json={"email": second_user["email"], "role": "member"},
        headers=auth_header(token),
    )
    assert add_resp.status_code == 201
    member_id = add_resp.json()["id"]

    # remove them
    resp = await client.delete(
        f"/api/v1/families/members/{member_id}",
        headers=auth_header(token),
    )
    assert resp.status_code == 204

    # verify they are gone
    members_resp = await client.get("/api/v1/families/members", headers=auth_header(token))
    member_emails = [m["user"]["email"] for m in members_resp.json()]
    assert second_user["email"] not in member_emails


# ------------------------------------------------ 7. add nonexistent user (404)
async def test_add_nonexistent_user(client):
    token, _ = await _register_main(client)

    resp = await client.post(
        "/api/v1/families/members",
        json={"email": "ghost@nowhere.com", "role": "member"},
        headers=auth_header(token),
    )
    assert resp.status_code == 404
