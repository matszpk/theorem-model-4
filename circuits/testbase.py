def revbits(n,width):
    return int(('{:0{width}b}'.format(n, width=width))[::-1], 2)

def gen_testsuite(testname, funcname, inwidth, outwidth, cases, func, infunc = lambda x: x):
    for c in cases:
        inmask = (1<<inwidth)-1
        outmask = (1<<outwidth)-1
        wc = infunc(c) & inmask
        rc = revbits(wc, inwidth)
        res=revbits(func(wc), outwidth) & outmask
        print("{}_test_{} {} {:0{iw}b} {:0{ow}b}" \
                .format(testname, c, funcname, rc, res, iw=inwidth, ow=outwidth))

def bin_decomp(listname, v):
    pos = 0
    dic_out = dict()
    for (name, ilen) in listname:
        mask = (1<<ilen)-1
        dic_out[name] = (v >> pos) & mask
        pos += ilen
    return dic_out

def bin_comp(listname, dic):
    pos, v = 0, 0
    for (name, ilen) in listname:
        mask = (1<<ilen)-1
        v |= (dic_in[name] & mask) << pos
        pos += ilen
    return v
