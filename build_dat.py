#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Extract a trimmed geosite category from v2fly dlc.dat.

Reads the compiled community dlc.dat (release asset), pulls category
SOURCE_CATEGORY (default category-ai-!cn), removes every domain entry whose
code also appears in EXCLUDE_CATEGORIES (default: xai, google-deepmind),
and re-emits a minimal GeoSiteList dat containing just the trimmed category.

Domain sub-messages are preserved byte-for-byte (matcher type, attributes),
so semantics stay identical to the community build.

Usage: build_dat.py <dlc.dat> <out.dat> [--category NAME] [--exclude a,b]
Outputs out.dat, out.sha256, out.list (kept codes), out.removed (dropped codes).
Stdlib only.
"""
import sys, hashlib, argparse

def rv(buf, i):
    t = s = 0
    while True:
        b = buf[i]; i += 1
        t |= (b & 0x7f) << s; s += 7
        if not b & 0x80:
            break
    return t, i

def subs(buf):
    """Yield (field, wiretype, payload_or_value) for length-delimited/varint."""
    i = 0
    while i < len(buf):
        t, i = rv(buf, i)
        fn, wt = t >> 3, t & 7
        if wt == 0:
            v, i = rv(buf, i)
            yield fn, wt, v
        elif wt == 2:
            ln, i = rv(buf, i)
            yield fn, wt, buf[i:i + ln]
            i += ln
        else:
            raise ValueError(f"unsupported wiretype {wt}")

def category_blob(buf, name):
    want = name.lower()
    for fn, wt, p in subs(buf):
        if fn != 1 or wt != 2:
            continue
        # GeoSite: field1 code string, field2.. domains
        code = None
        for f2, k2, v2 in subs(p):
            if f2 == 1 and k2 == 2:
                code = v2.decode("utf-8", "replace")
                break
        if code and code.lower() == want:
            return p
    raise SystemExit(f"category '{name}' not found in dlc.dat")

def domain_entries(blob):
    return [p for f, wt, p in subs(blob) if f == 2 and wt == 2]

def domain_code(d):
    for f, wt, v in subs(d):
        if f == 2 and wt == 2:
            return v.decode("utf-8", "replace")
    return None

def varint(v):
    out = b""
    while True:
        b = v & 0x7F; v >>= 7
        out += bytes([b | (0x80 if v else 0)])
        if not v:
            return out

def tag(fn, wt):
    return varint((fn << 3) | wt)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dlc")
    ap.add_argument("out")
    ap.add_argument("--category", default="category-ai-!cn")
    ap.add_argument("--out-category", default=None,
                    help="category name in output dat (default: same as source)")
    ap.add_argument("--exclude", default="xai,google-deepmind")
    args = ap.parse_args()

    dlc = open(args.dlc, "rb").read()
    src = category_blob(dlc, args.category)
    excl_codes = set()
    for ex in [e.strip() for e in args.exclude.split(",") if e.strip()]:
        blob = category_blob(dlc, ex)
        excl_codes |= {c for c in map(domain_code, domain_entries(blob)) if c}

    doms = domain_entries(src)
    keep, removed = [], []
    for d in doms:
        (removed if domain_code(d) in excl_codes else keep).append(d)

    # re-emit: GeoSiteList{ geoSite=1: GeoSite{ code=1, domain=2* } }
    outcat = (args.out_category or args.category).encode()
    geosite = tag(1, 2) + varint(len(outcat)) + outcat
    for d in keep:
        geosite += tag(2, 2) + varint(len(d)) + d
    dat = tag(1, 2) + varint(len(geosite)) + geosite

    open(args.out, "wb").write(dat)
    h = hashlib.sha256(dat).hexdigest()
    open(args.out + ".sha256", "w").write(h + "  " + args.out.split("/")[-1] + "\n")
    open(args.out + ".list", "w").write("\n".join(domain_code(d) for d in keep) + "\n")
    open(args.out + ".removed", "w").write("\n".join(domain_code(d) for d in removed) + "\n")
    print(f"source={args.category} kept={len(keep)} removed={len(removed)} "
          f"(exclude codes total={len(excl_codes)}) sha256={h}")

if __name__ == "__main__":
    main()
