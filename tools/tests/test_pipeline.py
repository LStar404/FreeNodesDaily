#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""不依赖网络的回归测试：把这次修掉的几个「静默发死节点 / 导出错误」钉住。

    python -m unittest discover -s tools/tests -v
"""

import json
import os
import sys
import types
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import daily_auto as DA  # noqa: E402
import export_formats as EF  # noqa: E402


def args(**kw):
    base = dict(quick=False, top=40, min_speed=0.2)
    base.update(kw)
    return types.SimpleNamespace(**base)


class ChooseFinalTest(unittest.TestCase):
    def test_drops_unmeasured_and_zero_speed(self):
        results = [
            {"name": "dead", "delay": 80, "speed": None},
            {"name": "stalled", "delay": 90, "speed": 0.0},
            {"name": "slow", "delay": 120, "speed": 0.5},
            {"name": "fast", "delay": 60, "speed": 1.2},
        ]
        final, tested, qualified = DA.choose_final(results, args())
        self.assertEqual([r["name"] for r in final], ["fast", "slow"])
        self.assertEqual(qualified, 2)
        self.assertEqual(len(tested), 2)

    def test_returns_none_when_nothing_measured(self):
        results = [
            {"name": "dead", "delay": 80, "speed": None},
            {"name": "stalled", "delay": 90, "speed": 0.0},
        ]
        final, tested, qualified = DA.choose_final(results, args())
        self.assertIsNone(final)
        self.assertEqual(tested, [])
        self.assertEqual(qualified, 0)

    def test_slow_but_measured_is_kept(self):
        results = [{"name": "slow", "delay": 200, "speed": 0.05}]
        final, _, qualified = DA.choose_final(results, args(min_speed=0.2))
        self.assertEqual([r["name"] for r in final], ["slow"])  # 实测能跑，好过发空
        self.assertEqual(qualified, 0)

    def test_quick_mode_sorts_by_delay(self):
        results = [
            {"name": "b", "delay": 200, "speed": None},
            {"name": "a", "delay": 50, "speed": None},
        ]
        final, _, _ = DA.choose_final(results, args(quick=True))
        self.assertEqual([r["name"] for r in final], ["a", "b"])


class ExportTest(unittest.TestCase):
    def test_hysteria_v1_uri_has_no_userinfo(self):
        p = {"type": "hysteria", "server": "1.2.3.4", "port": 443,
             "auth-str": "secret", "sni": "example.com"}
        uri = EF.v2ray_uri(p)
        self.assertTrue(uri.startswith("hysteria://1.2.3.4:443?"), uri)
        self.assertIn("auth=secret", uri)
        self.assertNotIn("@", uri)

    def test_hysteria2_uri_keeps_password(self):
        p = {"type": "hysteria2", "server": "1.2.3.4", "port": 443, "password": "pw"}
        uri = EF.v2ray_uri(p)
        self.assertTrue(uri.startswith("hysteria2://pw@1.2.3.4:443"), uri)

    def test_singbox_keeps_hysteria_v1_type(self):
        v1 = {"type": "hysteria", "server": "h1.com", "port": 443, "auth-str": "x"}
        v2 = {"type": "hysteria2", "server": "h2.com", "port": 443, "password": "y"}
        out = {o["type"]: o for o in json.loads(EF.singbox_outbounds([v1, v2]))
               if o.get("type") in ("hysteria", "hysteria2")}
        self.assertEqual(out["hysteria"]["auth_str"], "x")
        self.assertEqual(out["hysteria2"]["password"], "y")

    def test_sip008_ids_unique_for_same_endpoint(self):
        proxies = [
            {"type": "ss", "server": "1.1.1.1", "port": 443, "cipher": "aes-128-gcm", "password": "p1"},
            {"type": "ss", "server": "1.1.1.1", "port": 443, "cipher": "aes-128-gcm", "password": "p2"},
        ]
        data = __import__("json").loads(EF.sip008(proxies))
        ids = [s["id"] for s in data["servers"]]
        self.assertEqual(len(ids), 2)
        self.assertNotEqual(ids[0], ids[1])

    def test_export_dedupe_keeps_different_passwords(self):
        proxies = [
            {"type": "ss", "server": "1.1.1.1", "port": 443, "cipher": "aes-128-gcm", "password": "p1"},
            {"type": "ss", "server": "1.1.1.1", "port": 443, "cipher": "aes-128-gcm", "password": "p2"},
        ]
        self.assertEqual(len(EF._by_type(proxies, ("ss",), 10)), 2)


class MirrorTest(unittest.TestCase):
    def test_raw_github_url_gets_mirrors(self):
        url = "https://raw.githubusercontent.com/a/b/main/c/yaml"
        out = DA.mirrors(url)
        self.assertEqual(out[0], url)
        self.assertTrue(any("jsdelivr.net" in u for u in out))
        self.assertTrue(any("gh-proxy.com" in u for u in out))


if __name__ == "__main__":
    unittest.main()
