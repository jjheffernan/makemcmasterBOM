c.ServerApp.token = ""
c.ServerApp.password = ""
c.ServerApp.base_url = "/jupyter"
c.ServerApp.allow_origin = "*"
c.ServerApp.disable_check_xsrf = True
c.ServerApp.root_dir = ".."
c.ServerApp.tornado_settings = {
    "headers": {
        "Content-Security-Policy": (
            "frame-ancestors 'self' http://localhost:5173 http://127.0.0.1:5173"
        ),
    },
}
