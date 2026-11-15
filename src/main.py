"""AGRAM - Flet 1.x app (Android / Windows / iOS).

Features (Phase 1+2): signup/login, feed, photo post, like, comments,
search users, follow/unfollow, profiles, report post, logout, delete account.
"""
import asyncio
import inspect
from pathlib import Path

import flet as ft
from api import API, ApiError

api = API()

MUTED = "#9CA3AF"
RED = "#EF4444"
BG = "#0B0B12"
CARD = "#15151F"
PURPLE = "#8B5CF6"
CYAN = "#22D3EE"
WHITE = "#FFFFFF"
_FIT = getattr(ft, "BoxFit", None) or getattr(ft, "ImageFit", None)
COVER = _FIT.COVER if _FIT is not None else None


async def maybe(r):
    """Kuch Flet calls kisi version mein sync, kisi mein async hoti hain."""
    if inspect.isawaitable(r):
        await r


async def main(page: ft.Page):
    page.title = "AGRAM"
    page.padding = 0
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = BG
    page.theme = ft.Theme(color_scheme_seed=PURPLE)

    picker = ft.FilePicker()
    page.services.append(picker)

    body = ft.Container(expand=True)
    page.add(ft.SafeArea(content=body, expand=True))

    state = {"tab": 0}

    # ------------------------------------------------------------------ helpers
    async def toast(msg):
        await maybe(page.show_dialog(ft.SnackBar(content=ft.Text(str(msg)))))

    def safe(fn):
        async def wrapper(*a, **k):
            try:
                return await fn(*a, **k)
            except ApiError as ex:
                await toast(ex)
            except Exception as ex:
                await toast("Error: %s" % ex)
        return wrapper

    def set_body(control):
        body.content = control
        page.update()

    def loading():
        return ft.Column(
            controls=[ft.ProgressRing()],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            expand=True)

    def primary(label, on_click, solid=True):
        return ft.Button(label, on_click=on_click, style=ft.ButtonStyle(
            bgcolor=PURPLE if solid else CARD, color=WHITE,
            shape=ft.RoundedRectangleBorder(radius=14), padding=14))

    def avatar(name, radius=18):
        return ft.CircleAvatar(
            content=ft.Text((name or "?")[:1].upper(), weight=ft.FontWeight.BOLD, color=WHITE),
            bgcolor=PURPLE, radius=radius)

    def field(**kw):
        return ft.TextField(filled=True, bgcolor=CARD, border_radius=14,
                            border_color=ft.Colors.TRANSPARENT, **kw)

    def top_bar(title, back=None, action=None):
        row = []
        if back is not None:
            row.append(ft.IconButton(icon=ft.Icons.ARROW_BACK, on_click=back))
        if title == "AGRAM":
            row.append(ft.Image(src="icon.png", width=30, height=30))
        row.append(ft.Text(title, size=22, weight=ft.FontWeight.W_800, color=WHITE))
        if action is not None:
            row.append(ft.Container(expand=True))
            row.append(action)
        return ft.Container(content=ft.Row(controls=row), padding=10)

    def error_view(ex, retry):
        async def again(e):
            await retry()
        return ft.Column(
            controls=[ft.Text("Masla aaya: %s" % ex, color=RED, text_align=ft.TextAlign.CENTER),
                      primary("Dobara koshish karen", again)],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            expand=True)

    async def back_to_tab(e):
        await show_tab(state["tab"])

    # ------------------------------------------------------------------ login
    async def show_login(signup=False):
        page.navigation_bar = None
        username = field(label="Username (a-z, 0-9, _ .)", visible=signup)
        email = field(label="Email", keyboard_type=ft.KeyboardType.EMAIL)
        password = field(label="Password", password=True, can_reveal_password=True)

        async def go(e):
            submit.disabled = True
            page.update()
            ok = False
            try:
                if signup:
                    await api.sign_up(email.value or "", password.value or "", username.value or "")
                else:
                    await api.sign_in(email.value or "", password.value or "")
                ok = True
            except ApiError as ex:
                await toast(ex)
            except Exception as ex:
                await toast("Error: %s" % ex)
            submit.disabled = False
            if ok:
                await enter_app()
            else:
                page.update()

        async def toggle(e):
            await show_login(not signup)

        password.on_submit = go
        submit = primary("Sign up" if signup else "Log in", go)
        switch = ft.TextButton(
            "Pehle se account hai? Log in" if signup else "Naya account banayein",
            on_click=toggle)
        terms = ft.Text(
            "Sign up karke aap Terms of Service aur Privacy Policy se ittefaq karte hain. "
            "Kam az kam umar 13 saal.",
            size=11, color=MUTED, text_align=ft.TextAlign.CENTER)

        set_body(ft.Container(
            padding=24, expand=True,
            content=ft.Column(
                controls=[ft.Image(src="icon.png", width=120, height=120),
                          ft.Text("AGRAM", size=38, weight=ft.FontWeight.W_900, color=WHITE),
                          ft.Text("Apni kahani, poori duniya ke saath", size=13, color=CYAN),
                          ft.Container(height=8),
                          username, email, password, submit, switch, terms],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER,
                scroll=ft.ScrollMode.AUTO, spacing=12, expand=True)))

    async def enter_app():
        page.navigation_bar = nav
        nav.selected_index = 0
        await show_tab(0)

    async def logout_ui():
        api.sign_out()
        await show_login()

    # ------------------------------------------------------------------ tabs
    async def show_tab(i):
        state["tab"] = i
        nav.selected_index = i
        if i == 0:
            await show_feed()
        elif i == 1:
            await show_search()
        elif i == 2:
            await show_new_post()
        else:
            await show_profile(api.uid)

    @safe
    async def on_nav(e):
        await show_tab(int(e.control.selected_index))

    # ------------------------------------------------------------------ feed
    def post_card(p):
        likes = p.get("likes") or []
        liked = {"v": any(l.get("user_id") == api.uid for l in likes)}
        name = (p.get("profiles") or {}).get("username") or "user"
        count = ft.Text(str(len(likes)))
        heart = ft.IconButton(
            icon=ft.Icons.FAVORITE if liked["v"] else ft.Icons.FAVORITE_BORDER,
            icon_color=RED if liked["v"] else None)

        @safe
        async def toggle_like(e):
            if liked["v"]:
                await api.unlike(p["id"])
                likes[:] = [l for l in likes if l.get("user_id") != api.uid]
            else:
                await api.like(p["id"])
                likes.append({"user_id": api.uid})
            liked["v"] = not liked["v"]
            heart.icon = ft.Icons.FAVORITE if liked["v"] else ft.Icons.FAVORITE_BORDER
            heart.icon_color = RED if liked["v"] else None
            count.value = str(len(likes))
            page.update()

        @safe
        async def open_user(e):
            await show_profile(p["user_id"])

        @safe
        async def open_comments(e):
            await show_comments(p)

        @safe
        async def open_report(e):
            await ask_report(p["id"])

        heart.on_click = toggle_like
        caption = (p.get("caption") or "").strip()
        parts = [
            ft.Container(padding=10, content=ft.Row(controls=[
                avatar(name), ft.TextButton("@" + name, on_click=open_user)])),
            ft.Image(src=p["image_url"], fit=COVER, height=380),
            ft.Row(controls=[
                heart, count,
                ft.IconButton(icon=ft.Icons.CHAT_BUBBLE_OUTLINE, icon_color=CYAN,
                              on_click=open_comments),
                ft.Container(expand=True),
                ft.IconButton(icon=ft.Icons.FLAG, icon_color=MUTED, tooltip="Report",
                              on_click=open_report),
            ]),
        ]
        if caption:
            parts.append(ft.Container(content=ft.Text(caption), padding=12))
        return ft.Container(
            margin=10, bgcolor=CARD, border_radius=20,
            clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
            content=ft.Column(controls=parts, spacing=0,
                              horizontal_alignment=ft.CrossAxisAlignment.STRETCH))

    async def show_feed():
        set_body(loading())
        try:
            posts = await api.feed()
        except Exception as ex:
            set_body(error_view(ex, show_feed))
            return

        async def refresh(e):
            await show_feed()

        cards = [post_card(p) for p in posts]
        if not cards:
            cards = [ft.Container(
                padding=24,
                content=ft.Text("Abhi koi post nahi. Pehli post aap karen!", color=MUTED))]
        set_body(ft.Column(
            controls=[top_bar("AGRAM", action=ft.IconButton(icon=ft.Icons.REFRESH, on_click=refresh)),
                      ft.ListView(controls=cards, expand=True, spacing=0)],
            spacing=0, expand=True))

    # ------------------------------------------------------------------ report
    async def ask_report(post_id):
        def reason_button(label):
            async def pick_reason(e):
                await maybe(page.pop_dialog())
                try:
                    await api.report_post(post_id, label)
                    await toast("Report bhej di gayi. Shukriya.")
                except Exception as ex:
                    await toast(ex)
            return ft.TextButton(label, on_click=pick_reason)

        async def cancel(e):
            await maybe(page.pop_dialog())

        await maybe(page.show_dialog(ft.AlertDialog(
            title=ft.Text("Post report karen"),
            content=ft.Column(
                controls=[reason_button(r) for r in
                          ("Spam", "Nafrat ya dhamki", "Nange pan ka content", "Ghalat maloomat")],
                tight=True),
            actions=[ft.TextButton("Cancel", on_click=cancel)])))

    # ------------------------------------------------------------------ comments
    async def show_comments(post):
        set_body(loading())
        try:
            items = await api.comments(post["id"])
        except Exception as ex:
            async def retry():
                await show_comments(post)
            set_body(error_view(ex, retry))
            return

        rows = []
        for c in items:
            who = (c.get("profiles") or {}).get("username") or "user"
            rows.append(ft.Container(
                margin=6,
                padding=12, bgcolor=CARD, border_radius=16,
                content=ft.Row(controls=[
                    avatar(who, 14),
                    ft.Column(controls=[
                        ft.Text("@" + who, size=12, color=CYAN, weight=ft.FontWeight.BOLD),
                        ft.Text(c.get("body") or "")],
                        spacing=2, expand=True)])))
        if not rows:
            rows = [ft.Container(padding=16, content=ft.Text("Abhi koi comment nahi.", color=MUTED))]

        inp = field(hint_text="Comment likhen...", expand=True)

        async def send(e):
            text = (inp.value or "").strip()
            if not text:
                return
            try:
                await api.add_comment(post["id"], text)
            except Exception as ex:
                await toast(ex)
                return
            await show_comments(post)

        inp.on_submit = send
        set_body(ft.Column(
            controls=[top_bar("Comments", back=back_to_tab),
                      ft.ListView(controls=rows, expand=True, spacing=0),
                      ft.Container(padding=8, content=ft.Row(
                          controls=[inp, ft.IconButton(icon=ft.Icons.SEND, icon_color=PURPLE, on_click=send)]))],
            spacing=0, expand=True))

    # ------------------------------------------------------------------ search
    async def show_search(query="", results=None):
        box = field(hint_text="Username dhoondhen", value=query, expand=True)

        async def do_search(e):
            q = box.value or ""
            try:
                res = await api.search_users(q)
            except Exception as ex:
                await toast(ex)
                return
            await show_search(q, res)

        box.on_submit = do_search

        def tile(r):
            async def open_it(e):
                try:
                    await show_profile(r["id"])
                except Exception as ex:
                    await toast(ex)
            return ft.Container(
                margin=6, bgcolor=CARD, border_radius=16,
                content=ft.ListTile(leading=avatar(r["username"]),
                                    title=ft.Text("@" + r["username"], weight=ft.FontWeight.BOLD),
                                    on_click=open_it))

        if results is None:
            items = [ft.Container(padding=16, content=ft.Text("Naam likh kar search dabayen.", color=MUTED))]
        elif not results:
            items = [ft.Container(padding=16, content=ft.Text("Koi user nahi mila.", color=MUTED))]
        else:
            items = [tile(r) for r in results]

        set_body(ft.Column(
            controls=[top_bar("Search"),
                      ft.Container(padding=8, content=ft.Row(
                          controls=[box, ft.IconButton(icon=ft.Icons.SEARCH, icon_color=PURPLE, on_click=do_search)])),
                      ft.ListView(controls=items, expand=True)],
            spacing=0, expand=True))

    # ------------------------------------------------------------------ new post
    async def show_new_post():
        chosen = {"path": None, "name": None}
        label = ft.Text("Koi photo nahi chuni", color=MUTED)
        caption = field(label="Caption", multiline=True, min_lines=2, max_lines=5)

        async def pick(e):
            try:
                files = await picker.pick_files(file_type=ft.FilePickerFileType.IMAGE)
            except Exception as ex:
                await toast("Photo chunne mein masla: %s" % ex)
                return
            if not files:
                return
            f = files[0]
            if not f.path:
                await toast("Is device par photo ka path nahi mila.")
                return
            chosen["path"], chosen["name"] = f.path, f.name
            label.value = f.name
            page.update()

        async def share(e):
            if not chosen["path"]:
                await toast("Pehle photo chunein.")
                return
            share_btn.disabled = True
            page.update()
            ok = False
            try:
                data = await asyncio.to_thread(Path(chosen["path"]).read_bytes)
                url = await api.upload_image(data, chosen["name"] or chosen["path"])
                await api.create_post(url, (caption.value or "").strip())
                ok = True
            except ApiError as ex:
                await toast(ex)
            except Exception as ex:
                await toast("Upload nahi hui: %s" % ex)
            share_btn.disabled = False
            if ok:
                await toast("Post share ho gayi!")
                await show_tab(0)
            else:
                page.update()

        share_btn = primary("Share", share)
        set_body(ft.Column(
            controls=[top_bar("Nayi post"),
                      ft.Container(padding=16, content=ft.Column(
                          controls=[primary("Photo chunein", pick, solid=False),
                                    label, caption, share_btn],
                          spacing=12))],
            spacing=0, expand=True, scroll=ft.ScrollMode.AUTO))

    # ------------------------------------------------------------------ profile
  async def show_profile(user_id):
    set_body(loading())
    is_me = user_id == api.uid
    own_tab = is_me and state["tab"] == 0

    async def retry():
        await show_profile(user_id)

    try:
        prof, posts, followers, following, followed = await asyncio.gather(
            api.profile(user_id),
            api.user_posts(user_id),
            api.follower_count(user_id),
            api.following_count(user_id),
            api.is_following(user_id) if not is_me else asyncio.sleep(0, result=False),
        )
    except Exception as ex:
        set_body(error_view(ex, retry))
        return

    if not prof:
        set_body(error_view("Profile nahi mili.", retry))
        return

    name = prof.get("username") or "user"
    bio = prof.get("bio") or ""

    def stat(n, label):
        return ft.Column(
            controls=[
                ft.Text(str(n), weight=ft.FontWeight.BOLD, size=16),
                ft.Text(label, color=MUTED, size=12),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=0,
        )

    header = [
        ft.Row(
            controls=[
                avatar(name, 28),
                stat(len(posts), "Posts"),
                stat(followers, "Followers"),
                stat(following, "Following"),
            ],
            alignment=ft.MainAxisAlignment.SPACE_AROUND,
        ),
        ft.Text(name, weight=ft.FontWeight.BOLD, size=16),
    ]
    if bio:
        header.append(ft.Text(bio, color=MUTED))

    if not is_me:
        async def toggle_follow(e):
            try:
                if followed:
                    await api.unfollow(user_id)
                else:
                    await api.follow(user_id)
            except Exception as ex:
                await toast(ex)
                return
            await show_profile(user_id)

        header.append(
            primary("Unfollow" if followed else "Follow", toggle_follow, solid=not followed)
        )

    if own_tab:
        async def do_logout(e):
            await logout_ui()

        async def ask_delete(e):
            async def cancel(e2):
                await maybe(page.pop_dialog())

            async def yes(e2):
                await maybe(page.pop_dialog())
                try:
                    await api.delete_account()
                except Exception as ex:
                    await toast(ex)
                    return
                await logout_ui()

            await maybe(
                page.show_dialog(
                    ft.AlertDialog(
                        modal=True,
                        title=ft.Text("Account delete karen?"),
                        content=ft.Text(
                            "Aapki profile, posts, likes aur comments hamesha ke liye delete ho jayenge."
                        ),
                        actions=[
                            ft.TextButton("Cancel", on_click=cancel),
                            ft.TextButton("Delete", on_click=yes),
                        ],
                    )
                )
            )

        header.append(
            ft.Row(
                controls=[
                    ft.TextButton("Log out", on_click=do_logout),
                    ft.TextButton("Account delete karen", on_click=ask_delete),
                ]
            )
        )

    if posts:
        grid = ft.GridView(
            controls=[
                ft.Container(
                    border_radius=12,
                    clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                    content=ft.Image(src=x["image_url"], fit=COVER),
                )
                for x in posts
            ],
            max_extent=160,
            spacing=4,
            run_spacing=4,
            expand=True,
        )
    else:
        grid = ft.Container(padding=16, content=ft.Text("Abhi koi post nahi.", color=MUTED))

    set_body(
        ft.Column(
            controls=[
                top_bar("@" + name, back=None if own_tab else back_to_tab),
                ft.Container(
                    padding=16,
                    content=ft.Column(controls=header, spacing=8),
                ),
                ft.Divider(),
                grid,
            ],
            spacing=0,
            expand=True,
        )
      )
            
