#!/usr/bin/env python3
#
# check_hpe_raid.py - Nagios/Icinga plugin for monitoring HPE Smart Array RAID health via ssacli.
#
# Copyright (c) 2026 Csanaki Csaba <cscsanaki@gmail.com>
# SPDX-License-Identifier: MIT
#
# Requires HPE Smart Storage Administrator CLI (ssacli).
#
# Nagios exit codes:
#   0 OK
#   1 WARNING
#   2 CRITICAL
#   3 UNKNOWN
#
import argparse, os, re, shutil, subprocess, sys
VERSION = "1.0.0"
OK, WARNING, CRITICAL, UNKNOWN = 0, 1, 2, 3
TEXT = {OK:"OK", WARNING:"WARNING", CRITICAL:"CRITICAL", UNKNOWN:"UNKNOWN"}
CANDIDATES=("/usr/sbin/ssacli","/usr/bin/ssacli","/usr/local/bin/ssacli")
class CheckError(Exception): pass

def resolve(path):
    if path:
        if os.path.isfile(path) and os.access(path, os.X_OK): return path
        raise CheckError(f"ssacli executable not found or not executable: {path}")
    p=shutil.which("ssacli")
    if p: return p
    for p in CANDIDATES:
        if os.path.isfile(p) and os.access(p,os.X_OK): return p
    raise CheckError("ssacli executable not found")

def run(cmd, timeout):
    try: r=subprocess.run(cmd,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=timeout)
    except subprocess.TimeoutExpired: raise CheckError(f"command exceeded timeout ({timeout}s): {' '.join(cmd)}")
    if r.returncode:
        d=re.sub(r"\s+"," ",(r.stderr or r.stdout).strip())
        raise CheckError(f"command exited with code {r.returncode}: {' '.join(cmd)}"+(f": {d}" if d else ""))
    return r.stdout

def controllers(text):
    out=[]; cur=None
    for line in text.splitlines():
        m=re.match(r"^\s*(.+?)\s+in\s+Slot\s+(\S+)(?:\s+\(.+\))?\s*$",line,re.I)
        if m:
            cur={"model":m.group(1).strip(),"slot":m.group(2),"status":None}; out.append(cur); continue
        if cur:
            m=re.match(r"^\s*Controller Status:\s*(.+?)\s*$",line,re.I)
            if m: cur["status"]=m.group(1).strip()
    return out

def arrays(text):
    out=[]; cur=None
    for line in text.splitlines():
        m=re.match(r"^\s*array\s+(\S+)(?:\s+\(([^)]+)\))?\s*$",line,re.I)
        if m:
            cur={"name":m.group(1),"status":(m.group(2) or "OK").strip(),"lds":[]}; out.append(cur); continue
        m=re.match(r"^\s*logicaldrive\s+(\d+)\s+\((.+)\)\s*$",line,re.I)
        if m and cur:
            parts=[x.strip() for x in m.group(2).split(",")]
            cur["lds"].append({"id":m.group(1),"status":parts[-1] if parts else "UNKNOWN"})
    return out

def ldsev(s):
    s=s.lower()
    if s in ("ok","disabled"): return OK
    if s in ("rebuild","recover","rebuilding","recovering"): return WARNING
    return CRITICAL

def main():
    p=argparse.ArgumentParser(description="Nagios/Icinga plugin for monitoring HPE Smart Array RAID health via ssacli.")
    p.add_argument("-t","--timeout",type=int,default=30,help="ssacli command timeout in seconds (default: 30)")
    p.add_argument("--ssacli",help="Path to ssacli executable")
    p.add_argument("-V","--version",action="version",version=f"%(prog)s {VERSION}")
    a=p.parse_args()
    try:
        b=resolve(a.ssacli); cs=controllers(run([b,"controller","all","show","status"],a.timeout))
        if not cs: raise CheckError("no HPE Smart Array controllers found")
        state=OK; summaries=[]; na=nl=problems=0
        for c in cs:
            if not c["status"]: state=max(state,UNKNOWN); problems+=1
            elif c["status"].upper()!="OK": state=max(state,CRITICAL); problems+=1
            raw=run([b,"controller",f"slot={c['slot']}","logicaldrive","all","show"],a.timeout)
            aa=arrays(raw)
            if not aa: state=max(state,UNKNOWN); problems+=1
            parts=[]
            for ar in aa:
                na+=1
                if ar["status"].upper()!="OK": state=max(state,CRITICAL); problems+=1
                ls=[]
                for ld in ar["lds"]:
                    nl+=1; s=ldsev(ld["status"]); state=max(state,s); problems += s!=OK
                    ls.append(f"LUN{ld['id']}:{ld['status']}")
                parts.append(f"Array {ar['name']}({ar['status']})"+(f"[{','.join(ls)}]" if ls else ""))
            summaries.append(f"{c['model']}[{c['status'] or 'UNKNOWN'}]"+(f": {', '.join(parts)}" if parts else ""))
        print(f"HPE RAID {TEXT[state]}: {'; '.join(summaries)} | controllers={len(cs)} arrays={na} logical_drives={nl} problems={problems}")
        return state
    except CheckError as e:
        print(f"HPE RAID UNKNOWN: {e}"); return UNKNOWN

if __name__ == "__main__": sys.exit(main())
