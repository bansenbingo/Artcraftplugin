import json
import os
import socket
import sys
import tempfile
import threading
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "servers"))
from craft_runtime import CraftError, NativeSession, Runtime, private_text


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.old_home = os.environ.get("CRAFT_AGENT_HOME")
        os.environ["CRAFT_AGENT_HOME"] = str(self.root / "runtime")
        self.config = self.root / "config.json"

    def tearDown(self):
        if self.old_home is None:
            os.environ.pop("CRAFT_AGENT_HOME", None)
        else:
            os.environ["CRAFT_AGENT_HOME"] = self.old_home
        self.temp.cleanup()

    def runtime(self, apps):
        self.config.write_text(json.dumps({"workspace": str(self.root / "work"), "apps": apps}))
        return Runtime(self.config)

    def control_peer(self, auth_name=None, pdf=False):
        listener = socket.socket()
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        port = listener.getsockname()[1]
        seen = []

        def serve():
            try:
                with listener:
                    conn, _ = listener.accept()
                    with conn, conn.makefile("rb") as stream:
                        for line in stream:
                            req = json.loads(line)
                            seen.append(req)
                            ok = req["method"] != "auth" or req["params"] == {auth_name: "test-secret"}
                            if pdf:
                                reply = {"jsonrpc": "2.0", "id": req["id"], "result": {"document": "live"}} if ok else {"id": req["id"], "error": {"message": "unauthorized"}}
                            else:
                                reply = {"id": req["id"], "ok": ok, "result": {"document": "live"}} if ok else {"id": req["id"], "ok": False, "error": "unauthorized"}
                            conn.sendall((json.dumps(reply) + "\n").encode())
                            if not ok or req["method"] != "auth":
                                return
            except OSError:
                pass

        thread = threading.Thread(target=serve, daemon=True)
        thread.start()
        return port, seen, thread

    def secret(self, name, value):
        path = self.root / name
        path.write_text(value)
        path.chmod(0o600)
        return str(path)

    def test_photo_authentication_before_control(self):
        port, seen, thread = self.control_peer("token")
        r = self.runtime({"photocraft": {"port": port, "token_file": self.secret("token", "test-secret")}})
        self.assertEqual(r.control("photocraft", "ui.inspect"), {"document": "live"})
        thread.join(2)
        self.assertEqual([x["method"] for x in seen], ["auth", "ui.inspect"])

    def test_wordcraft_key_authentication(self):
        port, seen, thread = self.control_peer("key")
        r = self.runtime({"wordcraft": {"port": port, "key_file": self.secret("key", "test-secret")}})
        r.command("wordcraft", "text.insert", {"text": "中文"})
        thread.join(2)
        self.assertEqual(seen[0]["params"], {"key": "test-secret"})
        self.assertEqual(seen[1]["params"]["params"]["text"], "中文")

    def test_pdf_control_file_and_jsonrpc(self):
        port, seen, thread = self.control_peer("token", pdf=True)
        path = self.secret("control.json", json.dumps({"port": port, "token": "test-secret"}))
        r = self.runtime({"pdfcraft": {"control_file": path}})
        r.command("pdfcraft", "page.rotate")
        thread.join(2)
        self.assertEqual(seen[1]["method"], "ui.command")
        self.assertEqual(seen[1]["params"], {"id": "page.rotate"})

    def test_failed_auth_does_not_send_edit(self):
        port, seen, thread = self.control_peer("token")
        r = self.runtime({"photocraft": {"port": port, "token_file": self.secret("token", "wrong")}})
        with self.assertRaises(CraftError):
            r.command("photocraft", "file.new", {})
        thread.join(2)
        self.assertEqual(len(seen), 1)

    def test_shared_and_symlink_credentials_rejected(self):
        path = Path(self.secret("secret", "abc"))
        path.chmod(0o644)
        with self.assertRaises(CraftError):
            private_text(path)
        path.chmod(0o600)
        link = self.root / "link"
        link.symlink_to(path)
        with self.assertRaises(OSError):
            private_text(link)

    def test_edit_timeout_is_reported_without_replay(self):
        import time
        listener = socket.socket()
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        port = listener.getsockname()[1]
        seen = []

        def slow():
            with listener:
                conn, _ = listener.accept()
                with conn, conn.makefile("rb") as stream:
                    seen.append(json.loads(stream.readline()))
                    time.sleep(0.2)

        thread = threading.Thread(target=slow, daemon=True)
        thread.start()
        r = self.runtime({"gridcraft": {"port": port}})
        with self.assertRaisesRegex(CraftError, "may have completed"):
            r.control("gridcraft", "engine.execute", {"command": "cell.set", "params": {"input": "2"}}, timeout=0.05)
        thread.join(2)
        self.assertEqual(len(seen), 1)

    def test_native_document_state_persists_and_schema_is_enforced(self):
        script = self.root / "fake-cli"
        script.write_text('''#!/usr/bin/env python3
import json,sys
count=0
for line in sys.stdin:
 m=json.loads(line)
 if 'id' not in m:continue
 method=m['method']
 if method=='initialize':r={'protocolVersion':'2025-06-18','capabilities':{},'serverInfo':{'name':'fixture','version':'1'}}
 elif method=='tools/list':r={'tools':[{'name':'increment','inputSchema':{'type':'object','properties':{'amount':{'type':'integer'}},'required':['amount'],'additionalProperties':False}}]}
 else:
  count+=m['params']['arguments']['amount'];r={'content':[{'type':'text','text':str(count)}],'structuredContent':{'count':count},'isError':False}
 print(json.dumps({'jsonrpc':'2.0','id':m['id'],'result':r}),flush=True)
''')
        script.chmod(0o755)
        r = self.runtime({"gridcraft": {"cli": str(script)}})
        s = NativeSession(r, "gridcraft")
        try:
            self.assertEqual(s.call("increment", {"amount": 2})["structuredContent"]["count"], 2)
            self.assertEqual(s.call("increment", {"amount": 3})["structuredContent"]["count"], 5)
            with self.assertRaises(Exception):
                s.call("increment", {"amount": "3"})
            self.assertEqual(s.call("increment", {"amount": 1})["structuredContent"]["count"], 6)
        finally:
            s.close()


if __name__ == "__main__":
    unittest.main()
