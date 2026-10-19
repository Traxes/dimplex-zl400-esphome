"""Minimal ngspice (KiCad DLL) runner: run(netlist_lines, probes) -> dict of operating-point values."""
import ctypes, os, re
BIN = r"C:\Program Files\KiCad\10.0\bin"
os.add_dll_directory(BIN)
os.environ["PATH"] = BIN + ";" + os.environ["PATH"]
ng = ctypes.CDLL(os.path.join(BIN, "ngspice.dll"))
OUT = []
CB = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_void_p)
EX = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_int, ctypes.c_bool, ctypes.c_bool, ctypes.c_int, ctypes.c_void_p)
BG = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_bool, ctypes.c_int, ctypes.c_void_p)
_cb = [CB(lambda s, i, p: OUT.append(s.decode(errors="replace")) or 0), CB(lambda s, i, p: 0),
       EX(lambda a, b, c, d, e: 0), BG(lambda a, b, c: 0)]
ng.ngSpice_Init(_cb[0], _cb[1], _cb[2], None, None, _cb[3], None)


def run(lines, probes):
    OUT.clear()
    net = ["wcca"] + [l for l in lines if l.strip()] + [".end"]
    arr = (ctypes.c_char_p * (len(net) + 1))(*[l.encode() for l in net], None)
    ng.ngSpice_Circ(arr)
    ng.ngSpice_Command(b"op")
    log = " ".join(OUT)
    res = {}
    for p in probes:
        OUT.clear()
        ng.ngSpice_Command(("print " + p).encode())
        m = re.search(r"=\s*([-+0-9.eE]+)", " ".join(OUT))
        res[p] = float(m.group(1)) if m else float("nan")
    ng.ngSpice_Command(b"destroy all")
    if any(k in log.lower() for k in ("singular", "no convergence", "error")):
        res["_log"] = log[-400:]
    return res
