import subprocess, json, sys
K=r"<HOME>\Documents\KiCad\10.0\3rdparty\plugins\com_github_mixelpixx_konnect\bin\konnect.exe"
def run(calls, cwd=r"<PROJEKT>"):
    p=subprocess.Popen([K],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,cwd=cwd,text=True,encoding='utf8')
    def send(o): p.stdin.write(json.dumps(o)+"\n"); p.stdin.flush()
    def recv(i):
        while True:
            l=p.stdout.readline()
            if not l: raise SystemExit("EOF")
            d=json.loads(l)
            if d.get('id')==i: return d
    send({"jsonrpc":"2.0","id":0,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"probe","version":"0.1"}}}); recv(0)
    send({"jsonrpc":"2.0","method":"notifications/initialized"})
    out=[]
    for n,(m,params) in enumerate(calls,1):
        if m=="tools/list": send({"jsonrpc":"2.0","id":n,"method":m})
        else: send({"jsonrpc":"2.0","id":n,"method":"tools/call","params":{"name":m,"arguments":params}})
        out.append(recv(n))
    p.stdin.close(); p.wait(timeout=10)
    return out
if __name__=="__main__":
    calls=json.loads(sys.stdin.read())
    lim=int(sys.argv[1]) if len(sys.argv)>1 else 3000
    for (m,_),r in zip(calls,run(calls)):
        print("=== ",m)
        res=r.get('result',r)
        if 'tools' in res: print(len(res['tools']),'tools:',', '.join(t['name'] for t in res['tools']))
        elif 'content' in res:
            for c in res['content']: print(c.get('text','')[:lim])
        else: print(json.dumps(res)[:lim])
