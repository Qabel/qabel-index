def test_superuser(admin_user):
    assert admin_user.is_staff
