#!/usr/bin/env python3
"""Synthetic validation of TLS diagnostic contract, not a network test."""
import importlib.util
from pathlib import Path
p=Path(__file__).with_name("report_create_maven_tls.py")
s=importlib.util.spec_from_file_location("tls",p)
m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
def fixture():
    return {name:{"http_code":200,"curl_exit":0,"ca_verified":True,
                  "url":"https://maven.createmod.net/a.pom"} for name in m.EXPECTED}
def main():
    data=fixture()
    assert m.classify(data)["all_endpoints_reachable"]
    cases=[
        ("tls",{"curl_exit":60,"ca_verified":False,"http_code":0},"TLS_OR_TRANSPORT_FAILURE"),
        ("http",{"http_code":404},"HTTP_ERROR"),
        ("network",{"curl_exit":28,"ca_verified":False,"http_code":0},"TLS_OR_TRANSPORT_FAILURE"),
    ]
    for _,change,expected in cases:
        test=fixture()
        test["create_pom"].update(change)
        result=m.classify(test)
        assert not result["all_endpoints_reachable"]
        assert result["endpoints"]["create_pom"]["status"]==expected
    for field,value in (("url","http://maven.createmod.net/a.pom"),
                        ("ca_verified","true"),("curl_exit",True),("http_code",-1)):
        bad=fixture()
        bad["create_pom"][field]=value
        try:m.classify(bad)
        except ValueError:pass
        else:raise AssertionError("Invalid TLS evidence accepted: "+field)
    bad=fixture();del bad["ponder_pom"]
    try:m.classify(bad)
    except ValueError:pass
    else:raise AssertionError("Missing Maven dependency accepted")
    print("PASS 9 Create Maven trust and transport diagnostic contract checks")
if __name__=="__main__":main()
