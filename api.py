import time
import httpx

SUPABASE_URL = "YOUR_SUPABASE_URL"      # e.g. https://abcd.supabase.co
SUPABASE_KEY = "YOUR_SUPABASE_ANON_KEY"


class ApiError(Exception):
    pass


class API:
    def __init__(self):
        self.token = None
        self.uid = None
        self.username = None
        self.c = httpx.Client(timeout=30)

    def _h(self, extra=None):
        h = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {self.token or SUPABASE_KEY}"}
        if extra:
            h.update(extra)
        return h

    def _check(self, r):
        if r.status_code >= 400:
            try:
                j = r.json()
                msg = j.get("msg") or j.get("message") or j.get("error_description") or r.text
            except Exception:
                msg = r.text
            raise ApiError(msg)
        return r

    # ---------- auth ----------
    def _set_session(self, j):
        self.token = j.get("access_token")
        user = j.get("user") or j
        self.uid = user.get("id")
        meta = user.get("user_metadata") or {}
        self.username = meta.get("username")
        if not self.token:
            raise ApiError("Account ban gaya. Email verify karke login karein.")

    def sign_up(self, email, password, username):
        r = self.c.post(f"{SUPABASE_URL}/auth/v1/signup", headers=self._h(),
                        json={"email": email, "password": password,
                              "data": {"username": username.lower()}})
        self._set_session(self._check(r).json())

    def sign_in(self, email, password):
        r = self.c.post(f"{SUPABASE_URL}/auth/v1/token?grant_type=password",
                        headers=self._h(), json={"email": email, "password": password})
        self._set_session(self._check(r).json())

    def sign_out(self):
        self.token = self.uid = self.username = None

    # ---------- posts ----------
    def feed(self, user_id=None):
        q = "select=*,profiles(username),likes(user_id)&order=created_at.desc&limit=30"
        if user_id:
            q += f"&user_id=eq.{user_id}"
        r = self.c.get(f"{SUPABASE_URL}/rest/v1/posts?{q}", headers=self._h())
        return self._check(r).json()

    def upload_image(self, data: bytes, content_type="image/jpeg"):
        path = f"{self.uid}/{int(time.time() * 1000)}.jpg"
        r = self.c.post(f"{SUPABASE_URL}/storage/v1/object/posts/{path}",
                        headers=self._h({"Content-Type": content_type}), content=data)
        self._check(r)
        return f"{SUPABASE_URL}/storage/v1/object/public/posts/{path}"

    def create_post(self, image_url, caption):
        r = self.c.post(f"{SUPABASE_URL}/rest/v1/posts", headers=self._h(),
                        json={"user_id": self.uid, "image_url": image_url, "caption": caption})
        self._check(r)

    # ---------- likes ----------
    def like(self, post_id):
        r = self.c.post(f"{SUPABASE_URL}/rest/v1/likes", headers=self._h(),
                        json={"user_id": self.uid, "post_id": post_id})
        self._check(r)

    def unlike(self, post_id):
        r = self.c.delete(
            f"{SUPABASE_URL}/rest/v1/likes?user_id=eq.{self.uid}&post_id=eq.{post_id}",
            headers=self._h())
        self._check(r)
                        
