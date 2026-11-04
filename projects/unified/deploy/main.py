# Unified RAM2: bounded compilation, one deployment file.
import gc

def _rh_boot():
    with open('main.py') as _rh_file:
        _rh_code = ''
        while True:
            _rh_line = _rh_file.readline()
            if _rh_line == '#~BEGIN\n':
                break
            if not _rh_line:
                raise ValueError('Missing payload')
        while True:
            _rh_line = _rh_file.readline()
            if not _rh_line:
                break
            if _rh_line in ('#~\n', '#~END\n'):
                if _rh_line == '#~END\n':
                    _rh_file.close()
                gc.collect()
                exec(_rh_code, globals())
                _rh_code = ''
                gc.collect()
            elif _rh_line.startswith('#'):
                _rh_code += _rh_line[1:]

_rh_boot()
#~BEGIN
#aV='standalone'
#Q='pc'
#ci=('menu','loading','ready','playing','paused','results')
#cG=500
#bv=2500
#def cO(O,de):
# return O-de
#def cP(u):
# return isinstance(u,str)and len(u)==16 and all((aX in '0123456789abcdef' for aX in u))
#class cN:
# def __init__(b,aS=bv,ticks_diff=None):
#  if aS<=0:
#   raise ValueError('Lease timeout must be positive')
#  b.dC=aS
#  b.dl=ticks_diff or cO
#  b.clear()
# def clear(b):
#  b.di=None
#  b.dA=None
# def dD(b,O):
#  if b.di is None:
#   return False
#  F=b.dl(O,b.dA)
#  return 0<=F<b.dC
# def dU(b,u,O):
#  if not cP(u):
#   raise ValueError('Session must contain 16 lowercase hexadecimal characters')
#  if b.di is not None:
#   return u==b.di and b.dD(O)
#  b.di=u
#  b.dA=O
#  return True
# def dQ(b,u,O):
#  if u!=b.di or not b.dD(O):
#   return False
#  b.dA=O
#  return True
#class cK:
# def __init__(b,aS=bv,ticks_diff=None):
#  b.dk=cN(aS,ticks_diff)
#  b.dm=aV
#  b.dr='menu'
#  b.dv=False
# def dV(b,u,O):
#  return b.dk.dU(u,O)
# def dQ(b,u,O):
#  return b.dk.dQ(u,O)
# def dY(b,u,O):
#  if u!=b.dk.di or not b.dk.dD(O):
#   return()
#  b.dv=True
#  return b.dK(O)
# def dS(b):
#  b.dk.clear()
#  b.dv=False
#  if b.dm!=Q:
#   return()
#  V=()
#  if b.dr in('loading','ready','playing','paused'):
#   V=('abort_pc_round',)
#  b.dm=aV
#  b.dr='menu'
#  return V+('enter_standalone',)
# def dK(b,O):
#  if b.dk.di is not None and(not b.dk.dD(O)):
#   return b.dS()
#  if b.dv and b.dm==aV and(b.dr=='menu'):
#   b.dm=Q
#   return('enter_pc',)
#  return()
# def du(b,af,O):
#  if af not in ci:
#   raise ValueError('Unknown game phase')
#  b.dr=af
#  return b.dK(O)
#'Bounded ASCII line framing for the RH1 serial protocol.\n\nCommand validation, handshakes, acknowledgments and serial I/O are handled by\nthe board adapter and pc_host.py.\n'
#cM='RH1'
#bw=60
#class cI:
# def __init__(b,bj=bw):
#  if not 1<=bj<=bw:
#   raise ValueError('Line limit must be between 1 and 60 bytes')
#  b.dG=bj
#  b.dL()
# def dL(b):
#  b.ds=bytearray()
#  b.dz=False
#  b.dE=False
# def dX(b,ar):
#  bU=[]
#  for E in ar or b'':
#   if E==10:
#    if not b.dz and b.ds:
#     bU.append(b.ds.decode('ascii'))
#    b.dL()
#   elif b.dz:
#    continue
#   elif E==13:
#    if b.dE:
#     b.ds=bytearray()
#     b.dz=True
#    b.dE=True
#   elif b.dE or E<32 or E>126 or(len(b.ds)>=b.dG):
#    b.ds=bytearray()
#    b.dz=True
#   else:
#    b.ds.append(E)
#  return bU
#from microbit import*
#import music
#import gc
#from utime import ticks_ms,ticks_diff,ticks_add
#~
#from random import getrandbits
#def cQ(text):
# ck='ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/'
# ar=bytearray()
# E=am=0
# for aX in text:
#  E=E<<6|ck.index(aX)
#  am+=6
#  if am>=8:
#   am-=8
#   ar.append(E>>am&255)
#   E&=(1<<am)-1
# return ar
#def cD(text):
# aB=cQ(text)
# aA=bytearray()
# H=0
# while H<len(aB):
#  E=aB[H]
#  H+=1
#  if E:
#   aA.append(E)
#  else:
#   bT=aB[H]
#   H+=1
#   if bT==0:
#    aA.append(0)
#   else:
#    cn=aB[H]|aB[H+1]<<8
#    H+=2
#    for bz in range(bT):
#     aA.append(aA[-cn])
# return aA
#cH=3000
#cL=220
#cF=400
#aU=20
#by=True
#bx=159196
#cg='AAAAAHUAAD6CAAB2AAA+gwAA6wAASgUBYAFFhwHrAABEBQHrAABDAAQFAEEFAQAHIwBBgwAAdQAAQ4IAAHUAADwABA8APAAgMgB1AABBAAQoAEMABDcAOwAECgA7ACwyADoABAoAOgAsMgAAHMgA6gAAQQQBAAUeAAAMMgAAHMgAABYyAAAcyAAAFjIAAAjIAOoAAEoEAWEBRYgAITIASgAECgBKAAQyAFYABDIAUQAEMgBQAAQtAE8EAesAAE0FAQAFHgB1AABNAAQoAE8ABAoASAAECgBIACwyAEcABDsBR4IAAOsAAFYFACYyAEYABDIARgAMMgDqAABQAAQtAE8ABM0AABQyAEoABDIASgAlMgB1AABPAAfDAAAFzQAAKjIARwAHzQAABTIAYAFRAASQAVAABC0AABkyAEYAB80AABkyAAAHgQFNAAQoAAAFMgAABUYATQAE9AFNAAQiAU0AByIBAAUDAksCSowCAAdpAE0ABIEBAAUeAAAFSwBQAAQUAAAFCQEABRMBAAiHAGABT4cABC0AABYyAOsAAFEABIIAVAAJmwBWAAQUAFYABBQAVgAERgBRAARGAFaCAAAhBFSWBHYABC0AAAUUAOoAAFEABEYAUQAHQQAABVAASwJPjAIABSMAdQAAUQAE8AAADR4AAAcKAAAFWgAABR4AAAUUAAAFbgAACiMAAAXwAFQADIEB6wAATAAEBQBGAAQ3AAAFdgJKAAcZACEEVKoIAAdoAQAPQAFQAApKAQAHFwI6AABQQQAAOgAAT0EAADsAAE1CAAA6AABKQQAEHQEFAasDT5YEAAUJAQAFlgAABQkBAAUKAAAURgB1AABMAAS5AAAFlgAACtIAVAAEBQBVAAdPAXUAAFAACY8CTQAENgEABV8AQQAJfwNFAAfMAdYBTAoC1gFKAAQFAEwKAtUBTQkC1gFPAAcPAKsDURMABG0BAARGAAAKUABOAASCAAAF2wFMAAQPAEsAB+UBNgNJkQMhBEupCAAKqgAACg4BAA+RAAAFMgAACg4BOgAATQAEEwFKQgAEHgAEAawACQ4BAAd9AAAIDgEAFEYAABkOAeoAAFUABOYAAAVGAAANRQEABQ4BAAWDBAAHVQVFAAfMAQAKDgHVAUwABAkBTQAEDwBPAAcPAKwDURQEABGVAU4ACYwAAAgOAQAF+gAACA4BlgSBBToeBtUBQQAEQQBAFASrAz4TBFYHQU4QgAU6HQbWAUEKAA0ZAD5OEAAHGQU+AATXAABOmgYADDIAACaaBgAyMgAAKJoGABYyAAAuYgeIAbAAAE2wAARNA1UABAgCAAQtAEgABCMATAAE/gFKAARjBkUACScGSgAtLQAABIIARgAJ8gMABTcFAAgPAAAFBQDqAABGAAQyAEYACSgASAAEFABIAAQUAEgABBQASAAHFAAAFhkASgAJcwAABWkAAAVMBEkABBQASQAElAJJAASyAkkABBkASQAYQQBHAAQUAEcABC0ARwAELQBHAAQZAAAFFABGAAQUAEYABBQAAAqbAAAIrwAADxkAAAVVAAAFUAAACloAAAoUAAARGQBKAAQZAEoAB1kGAArDAAAHvgAACBkAABQUAAAgLQAACKUAAAWbAAAKqgAAFhkAAA2bAAAPrwAAB9EBAAVJBwAIaAEAEW4AAAVUAQAFBQBJAAQtAEkABC0AAAhoAQARQQBHAAdtAQAFBQAAB3EHAAUPAAAcHAIAERkAABRaAAAXtAAAMvwDADIyAAAFlwkABaEJACoyADwAB50DACouBAAyXgsALjIA'
#~
#aT=cD('JwgAABMEAAAUBAETBAEUBAITBAIUBAMTBAMUBAAKGABiFAAWGAAABRUAAgAFFQADYRQAAAAFGwABAAUbAAAKGAAABS0AAAcYAGEAF0gAAAx4AGIUAByQAAAJSAAAFWAAABWQAAAz2AAADDAAACfYAAAMGAATBAAA')
#cf={58:233,59:247,60:262,62:294,64:330,65:349,67:392,68:415,69:440,70:466,71:494,72:523,73:554,74:587,75:622,76:659,77:698,78:740,79:784,80:831,81:880,84:1047,85:1109,86:1175}
#L=None
#def cX():
# global L
# if L is None:
#  gc.collect()
#  L=cD(cg)
#  gc.collect()
#bt=(pin13,pin11,pin15,pin5)
#bu='0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ-: >/'
#ce='7555726227717477171755711747177475771111757577571725755656563444365556746477464434553557557222711152556554444757755577752555265644255736565534216722225555755552557755525555222712470070002020000004212411244'
#~
#class ch:
# def __init__(b,aF):
#  b.dw=aF
#  b.do=bytearray(1024)
#  b.dp=bytearray(1024)
#  b.dF=True
#  for an in(174,213,128,168,63,211,0,64,141,20,32,2,161,200,218,18,129,207,217,241,219,64,164,166,175):
#   i2c.write(aF,bytes((0,an)))
# def clear(b):
#  for H in range(1024):
#   b.do[H]=0
# def dq(b,f,v):
#  if 0<=f<128 and 0<=v<64:
#   b.do[f+(v>>3)*128]|=1<<(v&7)
# def dj(b,S,al,P,cc):
#  bb=abs(P-S)
#  bq=1 if S<P else-1
#  bc=-abs(cc-al)
#  br=1 if al<cc else-1
#  X=bb+bc
#  while True:
#   b.dq(S,al)
#   if S==P and al==cc:
#    break
#   bH=2*X
#   if bH>=bc:
#    X+=bc
#    S+=bq
#   if bH<=bb:
#    X+=bb
#    al+=br
# def dN(b,p,q,bY):
#  f=bY
#  v=0
#  bd=1-bY
#  while f>=v:
#   b.dq(p+f,q+v)
#   b.dq(p+v,q+f)
#   b.dq(p-v,q+f)
#   b.dq(p-f,q+v)
#   b.dq(p-f,q-v)
#   b.dq(p-v,q-f)
#   b.dq(p+v,q-f)
#   b.dq(p+f,q-v)
#   v+=1
#   if bd<0:
#    bd+=2*v+1
#   else:
#    f-=1
#    bd+=2*(v-f)+1
# def dT(b,p,q,D,bY=8):
#  t=bY
#  if D==0:
#   b.dj(p,q-t,p-t,q+3)
#   b.dj(p,q-t,p+t,q+3)
#   b.dj(p,q-t,p,q+t)
#  elif D==1:
#   b.dj(p+t,q,p-3,q-t)
#   b.dj(p+t,q,p-3,q+t)
#   b.dj(p-t,q,p+t,q)
#  elif D==2:
#   b.dj(p,q+t,p-t,q-3)
#   b.dj(p,q+t,p+t,q-3)
#   b.dj(p,q-t,p,q+t)
#  else:
#   b.dj(p-t,q,p+3,q-t)
#   b.dj(p-t,q,p+3,q+t)
#   b.dj(p-t,q,p+t,q)
# def dn(b,cY,f,v,aO=1):
#  for an in str(cY).upper():
#   w=bu.find(an)
#   if w<0:
#    w=bu.find(' ')
#   for cd in range(5):
#    cA=ord(ce[w*5+cd])-48
#    for cb in range(3):
#     if cA&1<<2-cb:
#      for br in range(aO):
#       for bq in range(aO):
#        b.dq(f+cb*aO+bq,v+cd*aO+br)
#   f+=4*aO
# def show(b):
#  b.dI(0,127,0,7)
#  b.dF=False
# def dZ(b,S,P):
#  if S<=P:
#   b.dI(S,P,3,5)
# def dI(b,S,P,dc,dd):
#  S=max(0,S)
#  P=min(127,P)
#  for ai in range(dc,dd+1):
#   I=ai*128
#   f=S
#   while f<=P:
#    while f<=P and(not b.dF)and(b.do[I+f]==b.dp[I+f]):
#     f+=1
#    if f>P:
#     break
#    aC=f
#    bg=f
#    f+=1
#    while f<=P and f-aC<28:
#     if b.dF or b.do[I+f]!=b.dp[I+f]:
#      bg=f
#     elif f-bg>6:
#      break
#     f+=1
#    aH=bg+1
#    i2c.write(b.dw,bytes((0,176|ai,aC&15,16|aC>>4)))
#    i2c.write(b.dw,b'@'+b.do[I+aC:I+aH])
#    for ah in range(aC,aH):
#     b.dp[I+ah]=b.do[I+ah]
#    if f<aH:
#     f=aH
# def dO(b,S,P,da,db):
#  for ai in range(da,db+1):
#   I=ai*128
#   for f in range(S,P+1):
#    b.do[I+f]=0
# def dW(b):
#  for ai in(3,4,5):
#   I=ai*128
#   for f in range(128):
#    b.do[I+f]=0
#~
#def bi():
# if by:
#  pin9.write_digital(1)
#  pin14.write_digital(1)
#  pin16.write_digital(1)
#def cW(cz):
# if not by:
#  return
# pin9.write_digital(0 if cz in(1,2)else 1)
# pin14.write_digital(0 if cz in(0,1)else 1)
# pin16.write_digital(1)
#z=[]
#C='MENU'
#def bs(ar,cu):
# return ar[cu]|ar[cu+1]<<8
#class cJ:
# def __init__(b):
#  cX()
#  b.index=0
#  b.dH=bs(L,0)if L else bx
#  b.dJ=-1
#  b.pitch=0
#  b.dB=False
# def stop(b):
#  music.stop(pin12)
#  b.dB=False
# def update(b,F):
#  if F<0:
#   return
#  bB=False
#  while b.index<len(L)and F>=b.dH:
#   b.dJ=b.dH+bs(L,b.index+2)
#   b.pitch=L[b.index+4]
#   b.index+=5
#   if b.index<len(L):
#    b.dH+=bs(L,b.index)
#   bB=True
#  if F<b.dJ:
#   if bB or not b.dB:
#    music.pitch(cf[b.pitch],duration=-1,pin=pin12,wait=False)
#    b.dB=True
#  elif b.dB:
#   b.stop()
#class cE:
# def __init__(b):
#  b.index=0
#  b.dM=0
# def dP(b):
#  while len(z)<12 and b.index<len(aT):
#   b.dM+=bs(aT,b.index)
#   z.append([b.dM,aT[b.index+2],0,None])
#   b.index+=3
#def ag(p,q):
# f=pin0.read_analog()-p
# v=pin1.read_analog()-q
# if abs(f)<230 and abs(v)<230:
#  return-1
# if abs(f)>=abs(v):
#  return 1 if f>0 else 3
# return 0 if v>0 else 2
#def cV(cZ,al,cT):
# for v in range(al,al+cT):
#  cj=(v>>3)*128
#  cr=1<<(v&7)
#  for f in range(6,122):
#   cZ.do[cj+f]^=cr
#def ax(m,cU,aN,w,cS):
# m.hud_combo=None
# m.clear()
# m.dn(cU[:18],4,2)
# for H in range(min(4,len(aN))):
#  cC=max(0,min(w-2,len(aN)-4))if len(aN)>4 else 0
#  ah=cC+H
#  if ah>=len(aN):
#   break
#  v=16+H*9
#  m.dn(aN[ah][:25],10,v)
#  if ah==w:
#   cV(m,v-1,8)
# m.dn(cS[:28],3,57)
# m.show()
#def bF(m,M,R):
# if getattr(m,'hud_combo',None)is None:
#  m.clear()
#  m.dn('COMBO',23,3,2)
#  m.dj(8,39,119,39)
#  m.dn('SCORE',8,48)
#  m.dn(str(M),max(0,(128-(4*len(str(M))-1)*2)//2),22,2)
#  m.dn(str(R),40,48)
#  m.show()
# else:
#  if M!=m.hud_combo:
#   m.dO(0,127,2,3)
#   bD=str(M)
#   m.dn(bD,max(0,(128-(4*len(bD)-1)*2)//2),22,2)
#   m.dI(0,127,2,3)
#  if R!=m.dR:
#   m.dO(40,127,6,6)
#   m.dn(str(R),40,48)
#   m.dI(40,127,6,6)
# m.hud_combo=M
# m.dR=R
#def cq(ad,g):
# cW(ad)
# pin8.write_digital(1 if ad==2 else 0)
# return(ticks_add(g,130),0)
#def ct():
# return '%04x%04x'%(getrandbits(16),getrandbits(16))
#o=cK(ticks_diff=ticks_diff)
#bJ=cI()
#aL=ct()
#bN=ticks_add(ticks_ms(),-1000)
#au=0
#T=[]
#ao=0
#Z=0
#K=0
#bo=0
#aM=0
#ae=0
#ap=False
#aQ=False
#ca=0
#at=0
#bR=0
#Y=''
#N=[]
#aI=0
#bI=0
#bm=-1
#bM=ticks_ms()
#~
#def aE(*cR):
# line=','.join((str(E)for E in cR))
# if len(line)<=60:
#  uart.write(line+'\n')
#def aa(bC,*dh):
# global aI
# if o.dk.di:
#  if bC=='NEED' and any((X[1]=='NEED' for X in N)):
#   return
#  N.append((aI,bC)+dh)
#  aI=(aI+1)%65536
#def bV():
# global L
# music.stop(pin12)
# L=None
# bi()
# pin8.write_digital(0)
#def ak(stop):
# global C,z,Y
# if stop and o.dm==Q:
#  aa('STOP',K)
# bV()
# z=[]
# o.du('menu',ticks_ms())
# C='MENU'
# Y=''
#def cl(V):
# global aL,T,z,C,Y,Z
# if 'enter_standalone' in V or 'enter_pc' in V:
#  bV()
#  z=[]
#  C='MENU'
#  Y=''
#  Z=0
# if 'enter_standalone' in V:
#  T=[]
# if o.dk.di is None:
#  bJ.dL()
#  N[:]=[]
#  aL=ct()
#def bC(l,g):
# global T,ao,bo,aM,ae
# global ap,C,aQ,ca,at,Y
# J=l[0]
# if J=='EA' and len(l)==2:
#  if N and int(l[1])==N[0][0]:
#   N.pop(0)
#  return
# if J=='HB' and len(l)==1:
#  return
# if J=='CATBEGIN' and len(l)==2 and(not o.dv):
#  aq=int(l[1])
#  if not 1<=aq<=12:
#   raise ValueError()
#  T=[]
#  ao=aq
#  return
# if J=='CAT' and len(l)==3 and(not o.dv):
#  w=int(l[1])
#  if w!=len(T)or w>=ao:
#   raise ValueError()
#  T.append((w,l[2][:18]))
#  return
# if J=='READY' and len(l)==1 and(len(T)==ao)and ao:
#  cl(o.dY(o.dk.di,g))
#  return
# if J=='BYE' and len(l)==1:
#  o.dk.dA=ticks_add(g,-3000)
#  return
# if o.dm!=Q or len(l)<2:
#  raise ValueError()
# if int(l[1])!=K or C=='MENU' or o.dr=='results':
#  return
# if J=='BEGIN' and len(l)==4 and(C=='LOADING'):
#  duration,aq=(int(l[2]),int(l[3]))
#  if not 0<duration<=3600000 or not 0<aq<=10000:
#   raise ValueError()
#  bo,aM,ae=(duration,aq,0)
#  ap=False
#  at=g
# elif J=='N' and len(l)==5 and(C in('LOADING','ARMED','PLAY')):
#  w,bp,D=(int(l[2]),int(l[3]),int(l[4]))
#  if w!=ae or w>=aM or len(z)>=48 or(not 0<=bp<bo)or(not 0<=D<4)or(z and bp<z[-1][0]):
#   raise ValueError()
#  z.append([bp,D,0,None])
#  ae+=1
#  at=g
# elif J=='END' and len(l)==2 and(ae==aM):
#  ap=True
# elif J=='ARM' and len(l)==2 and(C=='LOADING')and ae:
#  C='ARMED'
#  o.du('ready',g)
# elif J=='SYNC' and len(l)==2 and(C=='PLAY')and(not aQ):
#  ca=ticks_add(g,2700)
#  aQ=True
#  aa('SYNCED',K)
# elif J=='ERROR' and len(l)==2:
#  ak(True)
# else:
#  raise ValueError()
#~
#def df(line,g):
# global au,aI,bm,T,ao,Z
# l=line.split(',')
# if len(l)==4 and l[:2]==['RH1','ATTACH']and(l[2]==aL)and(len(l[3])==8)and all((an in '0123456789abcdef' for an in l[3])):
#  u=aL+l[3]
#  co=o.dk.di is None
#  if o.dV(u,g):
#   if co:
#    au=aI=0
#    bm=-1
#    T=[]
#    ao=0
#    Z=0
#    N[:]=[]
#   aE('RH1','ACCEPT',u)
#  return
# if len(l)<4 or l[0]!='RH1' or l[1]!=o.dk.di:
#  return
# try:
#  aP=int(l[2])
#  if aP==(au-1)%65536:
#   aE('RH1',l[1],'A',aP,'OK')
#   return
#  if aP!=au:
#   return
#  bC(l[3:],g)
#  o.dQ(l[1],g)
#  au=(au+1)%65536
#  aE('RH1',l[1],'A',aP,'OK')
# except(ValueError,IndexError):
#  aE('RH1',l[1],'A',l[2],'BAD')
#def bn():
# global aL,bN,bI,bm,bM
# g=ticks_ms()
# cp=o.dk.di is not None
# V=o.dK(g)
# if V or(cp and o.dk.di is None):
#  cl(V)
# if ticks_diff(g,bM)>=1000:
#  gc.collect()
#  bM=g
# if uart.any():
#  for line in bJ.dX(uart.read(64)):
#   df(line,g)
# if N and(N[0][0]!=bm or ticks_diff(g,bI)>=600):
#  aE('RH1',o.dk.di,'E',*N[0])
#  bm=N[0][0]
#  bI=g
# if o.dk.di is None and ticks_diff(g,bN)>=800:
#  aE('RH1','HELLO',aL)
#  bN=g
#def dg(g):
# global bR
# if not ap and len(z)<32 and(ticks_diff(g,bR)>=500):
#  aa('NEED',K,ae,44-len(z))
#  bR=g
#~
#def cw(B,m):
# global C,z,L
# G=o.dm==Q
# o.du('playing',ticks_ms())
# bS,cv,bK=(1700,100,210)if G else(3000,220,400)
# duration=bo if G else bx
# C='PLAY'
# M=0
# R=0
# aW=0
# bX=0
# bf=0
# ay=0
# if not G:
#  z=[]
# aY=None if G else cE()
# if aY:
#  aY.dP()
# bk=None if G else cJ()
# bW=0
# aj=False
# bO=[False]*4
# be=ticks_ms()
# bh=ticks_add(ticks_ms(),-aU)
# bP=ag(ab,ac)
# aJ=False
# bQ=-1
# B.clear()
# B.dj(1,18,126,18)
# B.dj(1,52,126,52)
# B.dN(32,35,10)
# B.show()
# m.hud_combo=None
# bF(m,0,0)
# if G:
#  aa('START',K)
#  cm=ticks_add(ticks_ms(),8000)
#  while not aQ:
#   bn()
#   if o.dm!=Q or ticks_diff(ticks_ms(),cm)>=0:
#    ak(True)
#    return
#   sleep(2)
#  aR=ca
# else:
#  aR=ticks_add(ticks_ms(),3500)
# display.show('3')
# aG=3
# while True:
#  bn()
#  if G and o.dm!=Q:
#   return
#  g=ticks_ms()
#  W=ag(ab,ac)
#  if W!=-1 and bP==-1:
#   if not aj and W==3:
#    aj=True
#    bW=g
#    o.du('paused',g)
#    if G:
#     aa('PAUSE',K)
#    else:
#     bk.stop()
#    bi()
#    pin8.write_digital(0)
#    ax(m,'PAUSED',('LS RIGHT RESUME','LS DOWN EXIT'),0,'LS R / LS DOWN')
#   elif aj and W==1:
#    aj=False
#    aR=ticks_add(aR,ticks_diff(g,bW))
#    o.du('playing',g)
#    if G:
#     aa('RESUME',K)
#    m.hud_combo=None
#    bF(m,M,R)
#    bh=ticks_add(g,-aU)
#   elif aj and W==2:
#    ak(G)
#    return
#  bP=W
#  if aj:
#   sleep(18)
#   continue
#  F=ticks_diff(g,aR)
#  if F>=duration+900:
#   break
#  if G:
#   dg(g)
#   if not ap and(not any((A[2]==0 for A in z)))and(ticks_diff(g,at)>4000):
#    aa('STARVED',K)
#    ak(True)
#    return
#  else:
#   bk.update(F)
#   aY.dP()
#  if F<0:
#   aZ=min(3,max(1,(-F+999)//1000))
#   if aZ!=aG:
#    display.show(str(aZ))
#    aG=aZ
#  elif aG:
#   aG=0
#  if ticks_diff(g,be)>=0:
#   bi()
#   pin8.write_digital(0)
#  for A in z:
#   if A[2]==0 and F>A[0]+bK:
#    A[2]=3
#    ay+=1
#    M=0
#    aJ=True
#    be,bz=cq(2,g)
#  for ad in range(4):
#   bE=bt[ad].read_digital()==0
#   if bE and(not bO[ad]):
#    aD=None
#    ba=bK+1
#    for A in z:
#     X=abs(F-A[0])
#     if A[2]==0 and(G or A[1]==ad)and(X<ba):
#      aD=A
#      ba=X
#    if aD is not None:
#     if aD[1]!=ad:
#      t=2
#     elif ba<=cv:
#      t=0
#     else:
#      t=1
#     be,bz=cq(t,g)
#     if t==2:
#      aD[2]=3
#      ay+=1
#      M=0
#     else:
#      aD[2]=1 if t==0 else 2
#      if t==0:
#       bX+=1
#       R+=100
#      else:
#       bf+=1
#       R+=50
#      M+=1
#      aW=max(aW,M)
#     aJ=True
#   bO[ad]=bE
#  if ticks_diff(g,bh)>=aU:
#   bh=g
#   B.dW()
#   B.dN(32,35,10)
#   aw=128
#   av=-1
#   for A in z:
#    bl=A[3]
#    az=None
#    if A[2]in(0,3):
#     bG=A[0]-F
#     if bG<=bS:
#      f=32+bG*91//bS
#      if f>=-7:
#       az=f
#       B.dT(f,35,A[1],6)
#      elif A[2]==3:
#       A[2]=5
#    if bl is not None:
#     aw=min(aw,bl-8)
#     av=max(av,bl+8)
#    if az is not None:
#     aw=min(aw,az-8)
#     av=max(av,az+8)
#    A[3]=az
#   B.dZ(aw,av)
#   while z and z[0][0]<F-1600:
#    z.pop(0)
#  if aJ:
#   bF(m,M,R)
#   aJ=False
#  if F>=0:
#   aK=0 if ay else 1 if bf else 2
#   if aK!=bQ:
#    display.show(Image('99999:99999:99999:99999:99999' if aK==2 else '99999:90009:90009:90009:99999' if aK==1 else '00000:00000:00000:00000:00000'))
#    bQ=aK
#  sleep(1)
# if G:
#  aa('DONE',K,R,ay)
# else:
#  bk.stop()
#  L=None
#  gc.collect()
# o.du('results',ticks_ms())
# bi()
# pin8.write_digital(0)
# B.clear()
# B.dn('FINISH',29,14,2)
# B.show()
# ax(m,'RESULT',('SCORE '+str(R),'BEST '+str(aW),'P'+str(bX)+' G'+str(bf),'MISS '+str(ay)),0,'LS LEFT MENU')
# U=-1
# while True:
#  bn()
#  if G and o.dm!=Q:
#   return
#  W=ag(ab,ac)
#  if W==3 and U==-1:
#   break
#  U=W
#  sleep(25)
# ak(False)
#~
#for bA in bt:
# bA.set_pull(bA.PULL_UP)
#bV()
#i2c.init(freq=400000)
#B=ch(60)
#m=ch(61)
#uart.init(baudrate=115200)
#gc.collect()
#ab=pin0.read_analog()
#ac=pin1.read_analog()
#U=ag(ab,ac)
#bL=ticks_ms()
#~
#while True:
# bn()
# g=ticks_ms()
# D=ag(ab,ac)
# bZ=o.dm+C
# if bZ!=Y:
#  gc.collect()
#  if C=='MENU':
#   if o.dm==Q:
#    ax(m,'PC SONGS',[cB[1]for cB in T],Z,'LS RIGHT SELECT')
#   else:
#    ax(m,'MEGALOVANIA',('STANDALONE','LS RIGHT START'),0,'P12 SPEAKER')
#   B.clear()
#   B.dn('READY',24,20,2)
#   B.show()
#   display.show(Image.HAPPY)
#  elif C=='LOADING':
#   ax(m,'PC LOADING',('WAIT FOR CHART',),0,'')
#  elif C=='ARMED':
#   ax(m,'PC READY',('LS RIGHT PLAY','LS LEFT CANCEL'),0,'')
#  Y=bZ
# if D!=-1 and U==-1 and(ticks_diff(g,bL)>200):
#  bL=g
#  if C=='MENU':
#   if o.dm==Q:
#    if D==0:
#     Z=(Z-1)%len(T)
#     Y=''
#    elif D==2:
#     Z=(Z+1)%len(T)
#     Y=''
#    elif D==1:
#     z=[]
#     ap=False
#     aQ=False
#     ae=aM=0
#     K=(K+1)%65536
#     o.du('loading',g)
#     C='LOADING'
#     at=g
#     aa('SELECT',K,Z)
#   elif D==1:
#    cw(B,m)
#    Y=''
#    D=ag(ab,ac)
#  elif C=='ARMED':
#   if D==1:
#    cw(B,m)
#    Y=''
#    D=ag(ab,ac)
#   elif D==3:
#    ak(True)
# if C=='LOADING' and ticks_diff(g,at)>12000:
#  ak(True)
# U=D
# sleep(12)
#~END
