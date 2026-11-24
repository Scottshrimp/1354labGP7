"""Accounts, runs and leaderboards in server/rhythmhit_api.py."""

import http.client
import json
import os
import sqlite3
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORK = tempfile.mkdtemp()
ORIGIN = "http://127.0.0.1:1"


class FakeTurnstile(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_POST(self):
        form = self.rfile.read(int(self.headers["Content-Length"])).decode()
        ok = "response=good" in form
        body = json.dumps({"success": ok, "hostname": "rhythmhit.test"}).encode()
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


turnstile = ThreadingHTTPServer(("127.0.0.1", 0), FakeTurnstile)
threading.Thread(target=turnstile.serve_forever, daemon=True).start()

SONGS = Path(WORK, "songs.json")
SONGS.write_text(json.dumps([
    {"id": "short", "title": "SHORT", "duration": 1000, "notes": [[0, 0]] * 10, "audio": "x"},
    {"id": "long", "title": "LONG", "duration": 120000, "notes": [[0, 0]] * 20, "audio": "x"},
]))
os.environ.update({
    "RH_DB": str(Path(WORK, "api.sqlite3")), "RH_SONGS": str(SONGS), "RH_ORIGIN": ORIGIN,
    "RH_COOKIE_SECURE": "0", "RH_TURNSTILE_SECRET": "secret", "RH_TURNSTILE_SITEKEY": "site",
    "RH_TURNSTILE_HOSTNAME": "rhythmhit.test",
    "RH_TURNSTILE_URL": "http://127.0.0.1:%d/" % turnstile.server_address[1],
})
sys.path.insert(0, str(ROOT / "server"))
import rhythmhit_api as api  # noqa: E402

api.init_db()
server = ThreadingHTTPServer(("127.0.0.1", 0), api.Handler)
threading.Thread(target=server.serve_forever, daemon=True).start()


class Client:
    def __init__(self, ip="10.0.0.1"):
        self.cookie = ""
        self.ip = ip

    def call(self, method, path, body=None, origin=ORIGIN):
        connection = http.client.HTTPConnection("127.0.0.1", server.server_address[1], timeout=10)
        headers = {"X-Real-IP": self.ip, "Origin": origin}
        if self.cookie:
            headers["Cookie"] = self.cookie
        data = None
        if body is not None:
            data = json.dumps(body).encode()
            headers["Content-Type"] = "application/json"
        connection.request(method, path, data, headers)
        response = connection.getresponse()
        cookie = response.getheader("Set-Cookie")
        if cookie:
            self.cookie = cookie.split(";")[0] if "Max-Age=0" not in cookie else ""
        payload = json.loads(response.read())
        connection.close()
        return response.status, payload

    def signup(self, name, password="correct horse", token="good"):
        return self.call("POST", "/api/signup", {"username": name, "password": password, "turnstile": token})


def age_runs(seconds):
    db = sqlite3.connect(os.environ["RH_DB"])
    db.execute("UPDATE runs SET started_at = started_at - ?", (seconds,))
    db.commit()
    db.close()


class ApiTest(unittest.TestCase):
    def test_signup_login_logout(self):
        client = Client("10.0.1.1")
        self.assertEqual(client.call("GET", "/api/me")[1], {"user": None, "turnstile_site_key": "site"})
        self.assertEqual(client.signup("ab")[1]["error"], "bad_username")
        self.assertEqual(client.signup("alice", "short")[1]["error"], "bad_password")
        self.assertEqual(client.signup("alice", token="bad")[1]["error"], "captcha_failed")
        status, body = client.signup("alice")
        self.assertEqual((status, body), (201, {"user": {"name": "alice"}}))
        self.assertEqual(client.call("GET", "/api/me")[1]["user"], {"name": "alice"})
        self.assertEqual(Client("10.0.1.2").signup("ALICE")[1]["error"], "username_taken")

        client.call("POST", "/api/logout", {})
        self.assertIsNone(client.call("GET", "/api/me")[1]["user"])
        wrong = client.call("POST", "/api/login", {"username": "alice", "password": "nope nope", "turnstile": "good"})
        self.assertEqual(wrong, (401, {"error": "bad_credentials"}))
        ghost = client.call("POST", "/api/login", {"username": "ghost", "password": "nope nope", "turnstile": "good"})
        self.assertEqual(ghost, (401, {"error": "bad_credentials"}))
        status, body = client.call("POST", "/api/login",
                                   {"username": "Alice", "password": "correct horse", "turnstile": "good"})
        self.assertEqual((status, body["user"]["name"]), (200, "alice"))

    def test_posts_need_same_origin_json(self):
        client = Client("10.0.2.1")
        status, body = client.call("POST", "/api/signup", {"username": "mallory"}, origin="https://evil.example")
        self.assertEqual((status, body["error"]), (403, "bad_origin"))
        self.assertEqual(client.call("POST", "/api/runs/start", {"song_id": "short"})[1]["error"], "login_required")
        status, board = client.call("GET", "/api/leaderboard")
        self.assertEqual((status, board["user"], board["me"], board["recent"]), (200, None, None, []))

    def test_signup_rate_limit(self):
        client = Client("10.0.3.1")
        codes = [client.signup("spam%d" % i, token="bad")[1]["error"] for i in range(6)]
        self.assertEqual(codes, ["captcha_failed"] * 5 + ["rate_limited"])

    def test_runs_and_leaderboard(self):
        bob, cara = Client("10.0.4.1"), Client("10.0.4.2")
        bob.signup("bob")
        cara.signup("cara")

        def play(client, song, score, miss, best, wait=5):
            run = client.call("POST", "/api/runs/start", {"song_id": song})[1]["run_id"]
            age_runs(wait)
            return client.call("POST", "/api/runs/finish",
                               {"run_id": run, "score": score, "miss": miss, "best_combo": best})

        self.assertEqual(bob.call("POST", "/api/runs/start", {"song_id": "nope"})[1]["error"], "unknown_song")
        # Too fast for a 120 s song.
        self.assertEqual(play(bob, "long", 2000, 0, 20)[1]["error"], "run_rejected")
        # Impossible numbers: above max, combo larger than hits, combo too short for the misses.
        self.assertEqual(play(bob, "short", 1100, 0, 10)[1]["error"], "run_rejected")
        self.assertEqual(play(bob, "short", 900, 1, 10)[1]["error"], "run_rejected")
        self.assertEqual(play(bob, "short", 900, 1, 4)[1]["error"], "run_rejected")

        self.assertEqual(play(bob, "short", 850, 1, 6)[1], {"saved": True, "personal_best": True, "rank": 1})
        self.assertEqual(play(bob, "short", 600, 2, 4)[1], {"saved": True, "personal_best": False, "rank": 1})
        self.assertEqual(play(cara, "short", 1000, 0, 10)[1]["rank"], 1)

        run = bob.call("POST", "/api/runs/start", {"song_id": "short"})[1]["run_id"]
        age_runs(5)
        bob.call("POST", "/api/runs/finish", {"run_id": run, "score": 500, "miss": 5, "best_combo": 1})
        # A run is finished once; a stranger can't finish someone else's run.
        again = bob.call("POST", "/api/runs/finish", {"run_id": run, "score": 500, "miss": 5, "best_combo": 1})
        self.assertEqual(again[1]["error"], "unknown_run")

        status, board = bob.call("GET", "/api/leaderboard?song=short")
        self.assertEqual(status, 200)
        self.assertEqual([(e["rank"], e["name"], e["score"], e["you"]) for e in board["entries"]],
                         [(1, "cara", 1000, False), (2, "bob", 850, True)])
        self.assertEqual(board["me"]["accuracy"], 85.0)
        self.assertEqual([r["score"] for r in board["recent"]], [500, 600, 850])
        self.assertEqual([s["id"] for s in board["songs"]], ["short", "long"])
        self.assertEqual(bob.call("GET", "/api/leaderboard?song=zzz")[0], 404)
        # Logged-out visitors see the same board, without "you", "me" or recent runs.
        status, public = Client("10.0.4.3").call("GET", "/api/leaderboard?song=short")
        self.assertEqual(status, 200)
        self.assertEqual([(e["name"], e["you"]) for e in public["entries"]], [("cara", False), ("bob", False)])
        self.assertEqual((public["me"], public["recent"]), (None, []))

    def test_plausible(self):
        self.assertTrue(api.plausible(10, 1000, 0, 10))
        self.assertTrue(api.plausible(10, 0, 10, 0))
        self.assertFalse(api.plausible(10, 950, 0, 9))
        self.assertFalse(api.plausible(10, True, 0, 10))


if __name__ == "__main__":
    unittest.main()
