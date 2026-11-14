import flet as ft
from api import API, ApiError

api = API()


def main(page: ft.Page):
    page.title = "AGRAM"
    page.padding = 0
    page.theme = ft.Theme(color_scheme_seed="#7C3AED")

    def toast(msg):
        page.snack_bar = ft.SnackBar(ft.Text(str(msg)))
        page.snack_bar.open = True
        page.update()

    # ---------------- Login ----------------
    def show_login():
        page.controls.clear()
        page.navigation_bar = None
        signup = {"on": False}
        username = ft.TextField(label="Username", visible=False)
        email = ft.TextField(label="Email", keyboard_type=ft.KeyboardType.EMAIL)
        password = ft.TextField(label="Password", password=True, can_reveal_password=True)
        submit = ft.ElevatedButton("Log in")
        switch = ft.TextButton("Naya account banayein")

        def toggle(e):
            signup["on"] = not signup["on"]
            username.visible = signup["on"]
            submit.text = "Sign up" if signup["on"] else "Log in"
            switch.text = "Pehle se account hai? Log in" if signup["on"] else "Naya account banayein"
            page.update()

        def go(e):
            submit.disabled = True
            page.update()
            try:
                if signup["on"]:
                    api.sign_up(email.value.strip(), password.value, username.value.strip())
                else:
                    api.sign_in(email.value.strip(), password.value)
                show_app()
                return
            except ApiError as ex:
                toast(ex)
            except Exception as ex:
                toast(f"Network error: {ex}")
            submit.disabled = False
            page.update()

        switch.on_click = toggle
        submit.on_click = go
        page.add(ft.Container(
            padding=24, alignment=ft.alignment.center,
            content=ft.Column(
                [ft.Text("AGRAM", size=42, weight=ft.FontWeight.W_800),
                 username, email, password, submit, switch],
                width=380, horizontal_alignment=ft.CrossAxisAlignment.CENTER, tight=True)))
        page.update()

    # ---------------- Main app ----------------
    def show_app():
        body = ft.Container(expand=True)
        picker = ft.FilePicker()
        page.overlay.append(picker)

        def post_card(p):
            likes = p.get("likes", [])
            liked = any(l["user_id"] == api.uid for l in likes)
            count = ft.Text(str(len(likes)))
            heart = ft.TextButton("❤️" if liked else "🤍")

            def toggle_like(e):
                nonlocal liked
                try:
                    if liked:
                        api.unlike(p["id"])
                        likes[:] = [l for l in likes if l["user_id"] != api.uid]
                    else:
                        api.like(p["id"])
                        likes.append({"user_id": api.uid})
                    liked = not liked
                    heart.text = "❤️" if liked else "🤍"
                    count.value = str(len(likes))
                    page.update()
                except ApiError as ex:
                    toast(ex)

            heart.on_click = toggle_like
            return ft.Column([
                ft.Container(ft.Text("@" + p["profiles"]["username"], weight=ft.FontWeight.BOLD),
                             padding=ft.padding.only(left=12, top=8)),
                ft.Image(src=p["image_url"], width=560, fit=ft.ImageFit.COVER),
                ft.Row([heart, count]),
                ft.Container(ft.Text(p.get("caption") or ""),
                             padding=ft.padding.only(left=12, bottom=16)),
            ], spacing=0)

        def load_feed(e=None):
            body.content = ft.ProgressRing()
            page.update()
            try:
                posts = api.feed()
                body.content = (ft.ListView([post_card(p) for p in posts], expand=True)
                                if posts else ft.Text("Abhi koi post nahi"))
            except Exception as ex:
                body.content = ft.Text(f"Error: {ex}")
            page.update()

        # ----- new post -----
        def show_new_post():
            chosen = {"path": None}
            label = ft.Text("Koi photo nahi chuni")
            caption = ft.TextField(label="Caption", multiline=True)
            share = ft.ElevatedButton("Share")

            def on_pick(e: ft.FilePickerResultEvent):
                if e.files:
                    chosen["path"] = e.files[0].path
                    label.value = e.files[0].name
                    page.update()

            picker.on_result = on_pick

            def do_share(e):
                if not chosen["path"]:
                    toast("Pehle photo chunein")
                    return
                share.disabled = True
                page.update()
                try:
                    with open(chosen["path"], "rb") as f:
                        url = api.upload_image(f.read())
                    api.create_post(url, caption.value.strip())
                    nav.selected_index = 0
                    load_feed()
                    return
                except Exception as ex:
                    toast(f"Upload fail: {ex}")
                share.disabled = False
                page.update()

            share.on_click = do_share
            body.content = ft.Column([
                ft.ElevatedButton("Photo chunein",
                                  on_click=lambda e: picker.pick_files(
                                      file_type=ft.FilePickerFileType.IMAGE)),
                label, caption, share], width=420, scroll=ft.ScrollMode.AUTO)
            body.padding = 16
            page.update()

        # ----- profile -----
        def show_profile():
            body.padding = 0
            try:
                posts = api.feed(api.uid)
            except Exception as ex:
                toast(ex)
                posts = []
            grid = ft.GridView(
                [ft.Image(src=p["image_url"], fit=ft.ImageFit.COVER) for p in posts],
                max_extent=180, spacing=2, run_spacing=2, expand=True)

            def logout(e):
                api.sign_out()
                show_login()

            body.content = ft.Column([
                ft.Container(height=16),
                ft.Text("@" + (api.username or "me"), size=20, weight=ft.FontWeight.BOLD),
                ft.Text(f"{len(posts)} posts"),
                ft.TextButton("Log out", on_click=logout),
                ft.Divider(), grid],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER, expand=True)
            page.update()

        def on_nav(e):
            i = e.control.selected_index
            body.padding = 0
            if i == 0:
                load_feed()
            elif i == 1:
                show_new_post()
            else:
                show_profile()

        nav = ft.NavigationBar(
            destinations=[
                ft.NavigationBarDestination(label="Feed", icon="home"),
                ft.NavigationBarDestination(label="Post", icon="add_box"),
                ft.NavigationBarDestination(label="Profile", icon="person"),
            ],
            on_change=on_nav)

        page.controls.clear()
        page.navigation_bar = nav
        page.add(ft.SafeArea(body, expand=True))
        load_feed()

    show_login()


ft.app(target=main)
      
