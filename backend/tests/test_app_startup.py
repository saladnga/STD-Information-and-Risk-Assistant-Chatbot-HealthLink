def test_app_imports_and_registers_routes():
    import main
    
    paths = {route.path for route in main.app.routes}
    for expected in [
        "/auth/signup",
        "/auth/login",
        "/auth/forgot-password",
        "/auth/reset-password",
        "/predict",
        "/ws/chat"
    ]:
        assert expected in paths, f"missing route: {expected}"