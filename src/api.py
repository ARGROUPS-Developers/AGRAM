"""AGRAM <-> Supabase REST API (sirf Python standard library + certifi).

Flet 1.x mein UI ka event-loop ek hi hota hai, is liye har network call
asyncio.to_thread() ke andar chalti hai taake app freeze na ho.
"""
import asyncio
import json
import mimetypes
import re
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request

try:
    import certifi

    _CTX = ssl.create_default_context(cafile=certifi.where())
except Exception:  # certifi na mile to system certificates
    _CTX = ssl.create_default_context()

# ====== YAHAN APNI SUPABASE VALUES LAGAYEN ======
SUPABASE_URL = "YOUR_SUPABASE_URL"        # https://abcd.supabase.co
SUPABASE_KEY = "YOUR_SUPABASE_ANON_KEY"   # eyJ... wali anon key
# =================================================

USERNAME_RE = re.compile(r"^[a-z0-9_.]{3,20}$")
ALLOWED_IMAGES = {".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                  ".png": "image/png", ".webp": "image/webp"}


class ApiError(Exception):
    pass


def _error_text(raw: str) -> str:
    try:
        j = json.loads(raw)
        if isinstance(j, dict):
            return (j.get("msg") or j.get("message") or j.get("error_description")
                    or j.get("error") or raw)
    except Exception:
        pass
    return raw or "Unknown error"


class API:
    def __init__(self):
        self.token = None
        self.refresh_token = None
        self.expires_at = 0
        self.uid = None
        self.username = None

    # ------------------------------------------------------------------
    # low level
    # ------------------------------------------------------------------
    def _request(self, method, path, body=None, raw=None, headers=None, use_token=True):
        if "YOUR_SUPABASE" in SUPABASE_URL or "YOUR_SUPABASE" in SUPABASE_KEY:
            raise ApiError("api.py mein SUPABASE_URL aur SUPABASE_KEY lagayen.")
        bearer = self.token if (use_token and self.token) else SUPABASE_KEY
        h = {"apikey": SUPABASE_KEY, "Authorization": "Bearer " + bearer}
        data = None
        if raw is not None:
            data = raw
        elif body is not None:
            data = json.dumps(body).encode()
            h["Content-Type"] = "application/json"
        if headers:
            h.update(headers)
        req = urllib.request.Request(SUPABASE_URL.rstrip("/") + path,
                                     data=data, method=method, headers=h)
        try:
            with urllib.request.urlopen(req, timeout=30, context=_CTX) as r:
                txt = r.read().decode("utf-8", errors="ignore")
                return json.loads(txt) if txt.strip() else None
        except urllib.error.HTTPError as e:
            raise ApiError(_error_text(e.read().decode("utf-8", errors="ignore")))
        except urllib.error.URLError as e:
            raise ApiError("Internet ka masla: %s" % (e.reason,))
        except TimeoutError:
            raise ApiError("Internet slow hai, dobara koshish karen.")

    def _ensure_token(self):
        if self.refresh_token and self.expires_at and time.time() > self.expires_at - 60:
            j = self._request("POST", "/auth/v1/token?grant_type=refresh_token",
                              body={"refresh_token": self.refresh_token}, use_token=False)
            self._set_session(j)

    def _call(self, method, path, **kw):
        self._ensure_token()
        return self._request(method, path, **kw)

    async def call(self, method, path, **kw):
        return await asyncio.to_thread(self._call, method, path, **kw)

    # ------------------------------------------------------------------
    # auth
    # ------------------------------------------------------------------
    def _set_session(self, j):
        if not isinstance(j, dict) or not j.get("access_token"):
            raise ApiError("Account ban gaya hai. Agar email verify mangi jaye to "
                           "Supabase mein 'Confirm email' band karen, phir log in karen.")
        self.token = j["access_token"]
        self.refresh_token = j.get("refresh_token")
        self.expires_at = time.time() + int(j.get("expires_in") or 3600)
        user = j.get("user") or {}
        self.uid = user.get("id") or self.uid
        meta = user.get("user_metadata") or {}
        self.username = meta.get("username") or self.username

    async def sign_up(self, email, password, username):
        username = username.strip().lower()
        if not USERNAME_RE.match(username):
            raise ApiError("Username 3-20 harf ka ho: a-z, 0-9, _ ya .")
        if len(password) < 6:
            raise ApiError("Password kam az kam 6 harf ka rakhen.")
        j = await asyncio.to_thread(
            self._request, "POST", "/auth/v1/signup", body={
                "email": email.strip(), "password": password,
                "data": {"username": username}}, use_token=False)
        self._set_session(j)
        self.username = username

    async def sign_in(self, email, password):
        j = await asyncio.to_thread(
            self._request, "POST", "/auth/v1/token?grant_type=password",
            body={"email": email.strip(), "password": password}, use_token=False)
        self._set_session(j)
        if not self.username:
            p = await self.profile(self.uid)
            self.username = p.get("username") if p else None

    def sign_out(self):
        self.token = self.refresh_token = self.uid = self.username = None
        self.expires_at = 0

    async def delete_account(self):
        await self.call("POST", "/rest/v1/rpc/delete_my_account", body={})
        self.sign_out()

    # ------------------------------------------------------------------
    # profiles / search
    # ------------------------------------------------------------------
    async def profile(self, user_id):
        r = await self.call("GET", "/rest/v1/profiles?select=*&id=eq.%s" % user_id)
        return r[0] if r else None

    async def search_users(self, text):
        q = re.sub(r"[^a-z0-9_.]", "", text.strip().lower().lstrip("@"))
        if not q:
            return []
        return await self.call(
            "GET", "/rest/v1/profiles?select=id,username,full_name&limit=20"
                   "&username=ilike.*%s*&order=username.asc" % q) or []

    # ------------------------------------------------------------------
    # posts
    # ------------------------------------------------------------------
    _POST_SELECT = "select=id,user_id,image_url,caption,created_at,profiles(username),likes(user_id)"

    async def feed(self):
        return await self.call(
            "GET", "/rest/v1/posts?%s&order=created_at.desc&limit=30" % self._POST_SELECT) or []

    async def user_posts(self, user_id):
        return await self.call(
            "GET", "/rest/v1/posts?%s&user_id=eq.%s&order=created_at.desc&limit=60"
                   % (self._POST_SELECT, user_id)) or []

    async def upload_image(self, data: bytes, filename: str):
        ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        ctype = ALLOWED_IMAGES.get(ext)
        if not ctype:
            raise ApiError("Sirf JPG, PNG ya WEBP photo chunen.")
        if len(data) > 15 * 1024 * 1024:
            raise ApiError("Photo 15MB se choti honi chahiye.")
        path = "%s/%d%s" % (self.uid, int(time.time() * 1000), ext)
        await self.call("POST", "/storage/v1/object/posts/" + path, raw=data,
                        headers={"Content-Type": ctype})
        return "%s/storage/v1/object/public/posts/%s" % (SUPABASE_URL.rstrip("/"), path)

    async def create_post(self, image_url, caption):
        await self.call("POST", "/rest/v1/posts", body={
            "user_id": self.uid, "image_url": image_url, "caption": caption})

    # ------------------------------------------------------------------
    # likes / comments
    # ------------------------------------------------------------------
    async def like(self, post_id):
        await self.call("POST", "/rest/v1/likes", body={"user_id": self.uid, "post_id": post_id})

    async def unlike(self, post_id):
        await self.call("DELETE", "/rest/v1/likes?user_id=eq.%s&post_id=eq.%s" % (self.uid, post_id))

    async def comments(self, post_id):
        return await self.call(
            "GET", "/rest/v1/comments?select=id,body,user_id,created_at,profiles(username)"
                   "&post_id=eq.%s&order=created_at.asc&limit=200" % post_id) or []

    async def add_comment(self, post_id, text):
        text = text.strip()
        if not text:
            raise ApiError("Comment khali hai.")
        await self.call("POST", "/rest/v1/comments", body={
            "post_id": post_id, "user_id": self.uid, "body": text[:1000]})

    # ------------------------------------------------------------------
    # follow
    # ------------------------------------------------------------------
    async def follower_count(self, user_id):
        r = await self.call("GET", "/rest/v1/follows?select=follower_id&following_id=eq.%s" % user_id)
        return len(r or [])

    async def following_count(self, user_id):
        r = await self.call("GET", "/rest/v1/follows?select=following_id&follower_id=eq.%s" % user_id)
        return len(r or [])

    async def is_following(self, user_id):
        r = await self.call(
            "GET", "/rest/v1/follows?select=follower_id&follower_id=eq.%s&following_id=eq.%s"
                   % (self.uid, user_id))
        return bool(r)

    async def follow(self, user_id):
        await self.call("POST", "/rest/v1/follows", body={
            "follower_id": self.uid, "following_id": user_id})

    async def unfollow(self, user_id):
        await self.call("DELETE", "/rest/v1/follows?follower_id=eq.%s&following_id=eq.%s"
                        % (self.uid, user_id))

    # ------------------------------------------------------------------
    # safety (store requirement)
    # ------------------------------------------------------------------
    async def report_post(self, post_id, reason):
        await self.call("POST", "/rest/v1/reports", body={
            "reporter_id": self.uid, "post_id": post_id, "reason": reason})
        
