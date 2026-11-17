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
#L='pc'
#ck=('menu','loading','ready','playing','paused','results')
#cI=500
#bx=2500
#def cO(P,dc):
# return P-dc
#def cP(u):
# return isinstance(u,str)and len(u)==16 and all((aY in '0123456789abcdef' for aY in u))
#class cN:
# def __init__(b,aS=bx,ticks_diff=None):
#  if aS<=0:
#   raise ValueError('Lease timeout must be positive')
#  b.dB=aS
#  b.dk=ticks_diff or cO
#  b.clear()
# def clear(b):
#  b.dg=None
#  b.dz=None
# def dC(b,P):
#  if b.dg is None:
#   return False
#  G=b.dk(P,b.dz)
#  return 0<=G<b.dB
# def dT(b,u,P):
#  if not cP(u):
#   raise ValueError('Session must contain 16 lowercase hexadecimal characters')
#  if b.dg is not None:
#   return u==b.dg and b.dC(P)
#  b.dg=u
#  b.dz=P
#  return True
# def dP(b,u,P):
#  if u!=b.dg or not b.dC(P):
#   return False
#  b.dz=P
#  return True
#class cL:
# def __init__(b,aS=bx,ticks_diff=None):
#  b.dj=cN(aS,ticks_diff)
#  b.dl=aV
#  b.dq='menu'
#  b.du=False
# def dU(b,u,P):
#  return b.dj.dT(u,P)
# def dP(b,u,P):
#  return b.dj.dP(u,P)
# def dX(b,u,P):
#  if u!=b.dj.dg or not b.dj.dC(P):
#   return()
#  b.du=True
#  return b.dJ(P)
# def dR(b):
#  b.dj.clear()
#  b.du=False
#  if b.dl!=L:
#   return()
#  M=()
#  if b.dq in('loading','ready','playing','paused'):
#   M=('abort_pc_round',)
#  b.dl=aV
#  b.dq='menu'
#  return M+('enter_standalone',)
# def dJ(b,P):
#  if b.dj.dg is not None and(not b.dj.dC(P)):
#   return b.dR()
#  if b.du and b.dl==aV and(b.dq=='menu'):
#   b.dl=L
#   return('enter_pc',)
#  return()
# def ds(b,ag,P):
#  if ag not in ck:
#   raise ValueError('Unknown game phase')
#  b.dq=ag
#  return b.dJ(P)
#'Bounded ASCII line framing for the RH1 serial protocol.\n\nCommand validation, handshakes, acknowledgments and serial I/O are handled by\nthe board adapter and pc_host.py.\n'
#cM='RH1'
#by=60
#class cJ:
# def __init__(b,bl=by):
#  if not 1<=bl<=by:
#   raise ValueError('Line limit must be between 1 and 60 bytes')
#  b.dF=bl
#  b.dK()
# def dK(b):
#  b.dr=bytearray()
#  b.dw=False
#  b.dD=False
# def dW(b,z):
#  bV=[]
#  for F in z or b'':
#   if F==10:
#    if not b.dw and b.dr:
#     bV.append(b.dr.decode('ascii'))
#    b.dK()
#   elif b.dw:
#    continue
#   elif F==13:
#    if b.dD:
#     b.dr=bytearray()
#     b.dw=True
#    b.dD=True
#   elif b.dD or F<32 or F>126 or(len(b.dr)>=b.dF):
#    b.dr=bytearray()
#    b.dw=True
#   else:
#    b.dr.append(F)
#  return bV
#from microbit import*
#import music
#import gc
#from utime import ticks_ms,ticks_diff,ticks_add
#~
#from random import getrandbits
#def cQ(text):
# cm='ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/'
# z=bytearray()
# F=ao=0
# for aY in text:
#  F=F<<6|cm.index(aY)
#  ao+=6
#  if ao>=8:
#   ao-=8
#   z.append(F>>ao&255)
#   F&=(1<<ao)-1
# return z
#def cG(text):
# aA=cQ(text)
# az=bytearray()
# H=0
# while H<len(aA):
#  F=aA[H]
#  H+=1
#  if F:
#   az.append(F)
#  else:
#   bU=aA[H]
#   H+=1
#   if bU==0:
#    az.append(0)
#   else:
#    cp=aA[H]|aA[H+1]<<8
#    H+=2
#    for aW in range(bU):
#     az.append(az[-cp])
# return az
#aT=20
#bz=True
#~
#aU=(('MEGALOVANIA',115370,'AAAAAHUAAD6CAAB2AAA+gwAA6wAASgUBYAFFhwHrAABEBQHrAABDAAQFAEEFAQAHIwBBgwAAdQAAQ4IAAHUAADwABA8APAAgMgB1AABBAAQoAEMABDcAOwAECgA7ACwyADoABAoAOgAsMgAAHMgA6gAAQQQBAAUeAAAMMgAAHMgAABYyAAAcyAAAFjIAAAjIAOoAAEoEAWEBRYgAITIASgAECgBKAAQyAFYABDIAUQAEMgBQAAQtAE8EAesAAE0FAQAFHgB1AABNAAQoAE8ABAoASAAECgBIACwyAEcABDsBR4IAAOsAAFYFACYyAEYABDIARgAMMgDqAABQAAQtAE8ABM0AABQyAEoABDIASgAlMgB1AABPAAfDAAAFzQAAKjIARwAHzQAABTIAYAFRAASQAVAABC0AABkyAEYAB80AABkyAAAHgQFNAAQoAAAFMgAABUYATQAE9AFNAAQiAU0AByIBAAUDAksCSowCAAdpAE0ABIEBAAUeAAAFSwBQAAQUAAAFCQEABRMBAAiHAGABT4cABC0AABYyAOsAAFEABIIAVAAJmwBWAAQUAFYABBQAVgAERgBRAARGAFaCAAAhBFSWBHYABC0AAAUUAOoAAFEABEYAUQAHQQAABVAASwJPjAIABSMAdQAAUQAE8AAADR4AAAcKAAAFWgAABR4AAAUUAAAFbgAACiMAAAXwAFQADIEB6wAATAAEBQBGAAQ3AAAFdgJKAAcZACEEVKoIAAdoAQAPQAFQAApKAQAHFwI6AABQQQAAOgAAT0EAADsAAE1CAAA6AABKQQAEHQEFAasDT5YEAAUJAQAFlgAABQkBAAUKAAAURgB1AABMAAS5AAAFlgAACtIAVAAEBQBVAAdPAXUAAFAACY8CTQAENgEABV8AQQAJfwNFAAfMAdYBTAoC1gFKAAQFAEwKAtUBTQkC1gFPAAcPAKsDURMABG0BAARGAAAKUABOAASCAAAF2wFMAAQPAEsAB+UBNgNJkQMhBEupCAAKqgAACg4BAA+RAAAFMgAACg4BOgAATQAEEwFKQgAEHgAEAawACQ4BAAd9AAAIDgEAFEYAABkOAeoAAFUABOYAAAVGAAANRQEABQ4BAAWDBAAHVQVFAAfMAQAKDgHVAUwABAkBTQAEDwBPAAcPAKwDURQEABGVAU4ACYwAAAgOAQAF+gAACA4BlgSBBToeBtUBQQAEQQBAFASrAz4TBFYHQU4QgAU6HQbWAUEKAA0ZAD5OEAAHGQU+AATXAABOmgYADDIAACaaBgAyMgAAKJoGABYyAAAuYgeIAbAAAE2wAARNA1UABAgCAAQtAEgABCMATAAE/gFKAARjBkUACScGSg','JwgAABMEAAAUBAETBAEUBAITBAIUBAMTBAMUBAAKGABiFAAWGAAABRUAAgAFFQADYRQAAAAFGwABAAUbAAAKGAAABS0AAAcYAGEAF0gAAAx4AGIUAByQAAAJSAAAFWAAABWQAAAb2AA'),('MARIO GROUND THEME',64820,'AAAAAHgAAEyWAAQFACwBAAUFAHgAAEgACQ8AT1gCeAAAQwAEBQBIwgFkAABDwgF4AABAAAQFAEUABB4ARwAEBQBGAAQtAAAFDwBDyAAENwAABAUATwAEBQBRAAQUAE0ABB4ATwAOWgBKAAQFAEcABEYAAFFVAO4CeAAATwAECgBOAAQFAAAFKABLAAkoAEQABVUAAAQFAEgABA8AAAYKAAAFPAAABH0AABk3AFQABQUAAAQUAFSEAwA5XwBLAAQFAAAFCgBI3AUAo6UAsAQABxkAAAUoAAAFBQAABigAAAVLAAAMQQBkAAchAgAULQAABUkCRgUAKEsAAAdsAgAmjwJ4AAQ6AmQAT48CAAVVAAAZjwJkADNVAAAK4QAABVoARAAJ6wBNAAk8AEUABNIARwAFUAAABQUAAAkKAAAFZABNAAVzAAAYJwEAJFoAAA4UAAAGUAAABAUASgAEBQAABa8AQAAEHgBAAAQKADwAKloAZAAOtABkACC0AA','CAcAABoEAACwBAFGBQGwBAIaBAKwBANGBQOwAAQVAAAAGgAIGAAABRsAA9wFA8oIAAQwAAAFFQAABzAA3AUDNAgDRgUABBgAYAkABDAAGgQCRgUABDAAAAVLAAAHSAAABWMAAAdIAAAYYAAABhgA'))
#cg=58
#ci=(233,247,262,277,294,311,330,349,370,392,415,440,466,494,523,554,587,622,659,698,740,784,831,880,932,988,1047,1109,1175)
#bv=(pin13,pin11,pin15,pin5)
#~
#bw='0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ-: >/'
#ch='7555726227717477171755711747177475771111757577571725755656563444365556746477464434553557557222711152556554444757755577752555265644255736565534216722225555755552557755525555222712470070002020000004212411244'
#~
#class cj:
# def __init__(b,aE):
#  b.dv=aE
#  b.dn=bytearray(1024)
#  b.do=bytearray(1024)
#  b.dE=True
#  for ap in(174,213,128,168,63,211,0,64,141,20,32,2,161,200,218,18,129,207,217,241,219,64,164,166,175):
#   i2c.write(aE,bytes((0,ap)))
# def clear(b):
#  for H in range(1024):
#   b.dn[H]=0
# def dp(b,f,v):
#  if 0<=f<128 and 0<=v<64:
#   b.dn[f+(v>>3)*128]|=1<<(v&7)
# def di(b,T,an,R,ce):
#  bc=abs(R-T)
#  bs=1 if T<R else-1
#  bd=-abs(ce-an)
#  bt=1 if an<ce else-1
#  X=bc+bd
#  while True:
#   b.dp(T,an)
#   if T==R and an==ce:
#    break
#   bI=2*X
#   if bI>=bd:
#    X+=bd
#    T+=bs
#   if bI<=bc:
#    X+=bc
#    an+=bt
# def dM(b,p,q,bZ):
#  f=bZ
#  v=0
#  be=1-bZ
#  while f>=v:
#   b.dp(p+f,q+v)
#   b.dp(p+v,q+f)
#   b.dp(p-v,q+f)
#   b.dp(p-f,q+v)
#   b.dp(p-f,q-v)
#   b.dp(p-v,q-f)
#   b.dp(p+v,q-f)
#   b.dp(p+f,q-v)
#   v+=1
#   if be<0:
#    be+=2*v+1
#   else:
#    f-=1
#    be+=2*(v-f)+1
# def dS(b,p,q,E,bZ=8):
#  t=bZ
#  if E==0:
#   b.di(p,q-t,p-t,q+3)
#   b.di(p,q-t,p+t,q+3)
#   b.di(p,q-t,p,q+t)
#  elif E==1:
#   b.di(p+t,q,p-3,q-t)
#   b.di(p+t,q,p-3,q+t)
#   b.di(p-t,q,p+t,q)
#  elif E==2:
#   b.di(p,q+t,p-t,q-3)
#   b.di(p,q+t,p+t,q-3)
#   b.di(p,q-t,p,q+t)
#  else:
#   b.di(p-t,q,p+3,q-t)
#   b.di(p-t,q,p+3,q+t)
#   b.di(p-t,q,p+t,q)
# def dm(b,cW,f,v,aO=1):
#  for ap in str(cW).upper():
#   w=bw.find(ap)
#   if w<0:
#    w=bw.find(' ')
#   for cf in range(5):
#    cE=ord(ch[w*5+cf])-48
#    for cd in range(3):
#     if cE&1<<2-cd:
#      for bt in range(aO):
#       for bs in range(aO):
#        b.dp(f+cd*aO+bs,v+cf*aO+bt)
#   f+=4*aO
# def show(b):
#  b.dH(0,127,0,7)
#  b.dE=False
# def dY(b,T,R):
#  if T<=R:
#   b.dH(T,R,3,5)
# def dH(b,T,R,da,db):
#  T=max(0,T)
#  R=min(127,R)
#  for ak in range(da,db+1):
#   I=ak*128
#   f=T
#   while f<=R:
#    while f<=R and(not b.dE)and(b.dn[I+f]==b.do[I+f]):
#     f+=1
#    if f>R:
#     break
#    aB=f
#    bi=f
#    f+=1
#    while f<=R and f-aB<28:
#     if b.dE or b.dn[I+f]!=b.do[I+f]:
#      bi=f
#     elif f-bi>6:
#      break
#     f+=1
#    aG=bi+1
#    i2c.write(b.dv,bytes((0,176|ak,aB&15,16|aB>>4)))
#    i2c.write(b.dv,b'@'+b.dn[I+aB:I+aG])
#    for ai in range(aB,aG):
#     b.do[I+ai]=b.dn[I+ai]
#    if f<aG:
#     f=aG
# def dN(b,T,R,cY,cZ):
#  for ak in range(cY,cZ+1):
#   I=ak*128
#   for f in range(T,R+1):
#    b.dn[I+f]=0
# def dV(b):
#  for ak in(3,4,5):
#   I=ak*128
#   for f in range(128):
#    b.dn[I+f]=0
#~
#def bk():
# if bz:
#  pin9.write_digital(1)
#  pin14.write_digital(1)
#  pin16.write_digital(1)
#def cV(cD):
# if not bz:
#  return
# pin9.write_digital(0 if cD in(1,2)else 1)
# pin14.write_digital(0 if cD in(0,1)else 1)
# pin16.write_digital(1)
#A=[]
#D='MENU'
#def bu(z,cz):
# return z[cz]|z[cz+1]<<8
#class cK:
# def __init__(b,cA):
#  b.dh=cG(cA)
#  b.index=0
#  b.dG=bu(b.dh,0)
#  b.dI=-1
#  b.pitch=0
#  b.dA=False
# def stop(b):
#  music.stop(pin12)
#  b.dA=False
# def update(b,G):
#  if G<0:
#   return
#  z=b.dh
#  bC=False
#  while b.index<len(z)and G>=b.dG:
#   b.dI=b.dG+bu(z,b.index+2)
#   b.pitch=z[b.index+4]
#   b.index+=5
#   if b.index<len(z):
#    b.dG+=bu(z,b.index)
#   bC=True
#  if G<b.dI:
#   if bC or not b.dA:
#    music.pitch(ci[b.pitch-cg],duration=-1,pin=pin12,wait=False)
#    b.dA=True
#  elif b.dA:
#   b.stop()
#class cH:
# def __init__(b,cA):
#  b.dh=cG(cA)
#  b.index=0
#  b.dL=0
# def dO(b):
#  z=b.dh
#  while len(A)<12 and b.index<len(z):
#   b.dL+=bu(z,b.index)
#   A.append([b.dL,z[b.index+2],0,None])
#   b.index+=3
#def ah(p,q):
# f=pin0.read_analog()-p
# v=pin1.read_analog()-q
# if abs(f)<230 and abs(v)<230:
#  return-1
# if abs(f)>=abs(v):
#  return 1 if f>0 else 3
# return 0 if v>0 else 2
#def cU(cX,an,cS):
# for v in range(an,an+cS):
#  cl=(v>>3)*128
#  cu=1<<(v&7)
#  for f in range(6,122):
#   cX.dn[cl+f]^=cu
#def aL(m,cT,af,w,bg):
# m.hud_combo=None
# m.clear()
# m.dm(cT[:18],4,2)
# for H in range(min(4,len(af))):
#  cF=max(0,min(w-2,len(af)-4))if len(af)>4 else 0
#  ai=cF+H
#  if ai>=len(af):
#   break
#  v=16+H*9
#  m.dm(af[ai][:25],10,v)
#  if ai==w:
#   cU(m,v-1,8)
# m.dm(bg[:28],3,57)
# m.show()
#def bG(m,N,S):
# if getattr(m,'hud_combo',None)is None:
#  m.clear()
#  m.dm('COMBO',23,3,2)
#  m.di(8,39,119,39)
#  m.dm('SCORE',8,48)
#  m.dm(str(N),max(0,(128-(4*len(str(N))-1)*2)//2),22,2)
#  m.dm(str(S),40,48)
#  m.show()
# else:
#  if N!=m.hud_combo:
#   m.dN(0,127,2,3)
#   bE=str(N)
#   m.dm(bE,max(0,(128-(4*len(bE)-1)*2)//2),22,2)
#   m.dH(0,127,2,3)
#  if S!=m.dQ:
#   m.dN(40,127,6,6)
#   m.dm(str(S),40,48)
#   m.dH(40,127,6,6)
# m.hud_combo=N
# m.dQ=S
#def ct(ac,g):
# cV(ac)
# pin8.write_digital(1 if ac==2 else 0)
# return(ticks_add(g,130),0)
#def cw():
# return '%04x%04x'%(getrandbits(16),getrandbits(16))
#o=cL(ticks_diff=ticks_diff)
#bK=cJ()
#aM=cw()
#bO=ticks_add(ticks_ms(),-1000)
#au=0
#V=[]
#aq=0
#aj=0
#K=0
#bq=0
#aN=0
#ae=0
#ar=False
#aQ=False
#cb=0
#at=0
#bS=0
#ad=''
#O=[]
#aH=0
#bJ=0
#bo=-1
#bN=ticks_ms()
#~
#def aD(*cR):
# line=','.join((str(F)for F in cR))
# if len(line)<=60:
#  uart.write(line+'\n')
#def Y(bD,*df):
# global aH
# if o.dj.dg:
#  if bD=='NEED' and any((X[1]=='NEED' for X in O)):
#   return
#  O.append((aH,bD)+df)
#  aH=(aH+1)%65536
#def bW():
# music.stop(pin12)
# bk()
# pin8.write_digital(0)
#def am(stop):
# global D,A,ad
# if stop and o.dl==L:
#  Y('STOP',K)
# bW()
# A=[]
# M=o.ds('menu',ticks_ms())
# if M:
#  bA(M)
# D='MENU'
# ad=''
#def bA(M):
# global aM,V,A,D,ad,aj
# if 'enter_standalone' in M or 'enter_pc' in M:
#  bW()
#  A=[]
#  D='MENU'
#  ad=''
#  aj=0
# if 'enter_standalone' in M:
#  V=[]
# if o.dj.dg is None:
#  bK.dK()
#  O[:]=[]
#  aM=cw()
#def bD(l,g):
# global V,aq,bq,aN,ae
# global ar,D,aQ,cb,at,ad
# J=l[0]
# if J=='EA' and len(l)==2:
#  if O and int(l[1])==O[0][0]:
#   O.pop(0)
#  return
# if J=='HB' and len(l)==1:
#  return
# if J=='CATBEGIN' and len(l)==2 and(not o.du):
#  ab=int(l[1])
#  if not 1<=ab<=12:
#   raise ValueError()
#  V=[]
#  aq=ab
#  return
# if J=='CAT' and len(l)==3 and(not o.du):
#  w=int(l[1])
#  if w!=len(V)or w>=aq:
#   raise ValueError()
#  V.append((w,l[2][:18]))
#  return
# if J=='READY' and len(l)==1 and(len(V)==aq)and aq:
#  bA(o.dX(o.dj.dg,g))
#  return
# if J=='BYE' and len(l)==1:
#  o.dj.dz=ticks_add(g,-3000)
#  return
# if o.dl!=L or len(l)<2:
#  raise ValueError()
# if int(l[1])!=K or D=='MENU' or o.dq=='results':
#  return
# if J=='BEGIN' and len(l)==4 and(D=='LOADING'):
#  duration,ab=(int(l[2]),int(l[3]))
#  if not 0<duration<=3600000 or not 0<ab<=10000:
#   raise ValueError()
#  bq,aN,ae=(duration,ab,0)
#  ar=False
#  at=g
# elif J=='N' and len(l)==5 and(D in('LOADING','ARMED','PLAY')):
#  w,br,E=(int(l[2]),int(l[3]),int(l[4]))
#  if w!=ae or w>=aN or len(A)>=48 or(not 0<=br<bq)or(not 0<=E<4)or(A and br<A[-1][0]):
#   raise ValueError()
#  A.append([br,E,0,None])
#  ae+=1
#  at=g
# elif J=='END' and len(l)==2 and(ae==aN):
#  ar=True
# elif J=='ARM' and len(l)==2 and(D=='LOADING')and ae:
#  D='ARMED'
#  o.ds('ready',g)
# elif J=='SYNC' and len(l)==2 and(D=='PLAY')and(not aQ):
#  cb=ticks_add(g,2700)
#  aQ=True
#  Y('SYNCED',K)
# elif J=='ERROR' and len(l)==2:
#  am(True)
# else:
#  raise ValueError()
#~
#def dd(line,g):
# global au,aH,bo,V,aq
# l=line.split(',')
# if len(l)==4 and l[:2]==['RH1','ATTACH']and(l[2]==aM)and(len(l[3])==8)and all((ap in '0123456789abcdef' for ap in l[3])):
#  u=aM+l[3]
#  cq=o.dj.dg is None
#  if o.dU(u,g):
#   if cq:
#    au=aH=0
#    bo=-1
#    V=[]
#    aq=0
#    O[:]=[]
#   aD('RH1','ACCEPT',u)
#  return
# if len(l)<4 or l[0]!='RH1' or l[1]!=o.dj.dg:
#  return
# try:
#  aP=int(l[2])
#  if aP==(au-1)%65536:
#   aD('RH1',l[1],'A',aP,'OK')
#   return
#  if aP!=au:
#   return
#  bD(l[3:],g)
#  o.dP(l[1],g)
#  au=(au+1)%65536
#  aD('RH1',l[1],'A',aP,'OK')
# except(ValueError,IndexError):
#  aD('RH1',l[1],'A',l[2],'BAD')
#def bp():
# global aM,bO,bJ,bo,bN
# g=ticks_ms()
# cr=o.dj.dg is not None
# M=o.dJ(g)
# if M or(cr and o.dj.dg is None):
#  bA(M)
# if ticks_diff(g,bN)>=1000:
#  gc.collect()
#  bN=g
# if uart.any():
#  for line in bK.dW(uart.read(64)):
#   dd(line,g)
# if O and(O[0][0]!=bo or ticks_diff(g,bJ)>=600):
#  aD('RH1',o.dj.dg,'E',*O[0])
#  bo=O[0][0]
#  bJ=g
# if o.dj.dg is None and ticks_diff(g,bO)>=800:
#  aD('RH1','HELLO',aM)
#  bO=g
#def de(g):
# global bS
# if not ar and len(A)<32 and(ticks_diff(g,bS)>=500):
#  Y('NEED',K,ae,44-len(A))
#  bS=g
#~
#def cC(C,m):
# global D,A
# Q=o.dl==L
# o.ds('playing',ticks_ms())
# bT,cB,bL=(1700,100,210)if Q else(3000,220,400)
# duration=bq
# D='PLAY'
# N=0
# S=0
# aX=0
# bY=0
# bh=0
# ax=0
# if not Q:
#  aW,duration,cv,cn=aU[aj]
#  A=[]
#  gc.collect()
#  aZ=cH(cn)
#  aZ.dO()
#  aK=cK(cv)
#  gc.collect()
# bX=0
# al=False
# bP=[False]*4
# bf=ticks_ms()
# bj=ticks_add(ticks_ms(),-aT)
# bQ=ah(Z,aa)
# aI=False
# bR=-1
# C.clear()
# C.di(1,18,126,18)
# C.di(1,52,126,52)
# C.dM(32,35,10)
# C.show()
# m.hud_combo=None
# bG(m,0,0)
# if Q:
#  Y('START',K)
#  co=ticks_add(ticks_ms(),8000)
#  while not aQ:
#   bp()
#   if o.dl!=L or ticks_diff(ticks_ms(),co)>=0:
#    am(True)
#    return
#   sleep(2)
#  aR=cb
# else:
#  aR=ticks_add(ticks_ms(),3500)
# display.show('3')
# aF=3
# while True:
#  bp()
#  if Q and o.dl!=L:
#   return
#  g=ticks_ms()
#  W=ah(Z,aa)
#  if W!=-1 and bQ==-1:
#   if not al and W==3:
#    al=True
#    bX=g
#    o.ds('paused',g)
#    if Q:
#     Y('PAUSE',K)
#    else:
#     aK.stop()
#    bk()
#    pin8.write_digital(0)
#    aL(m,'PAUSED',('LS RIGHT RESUME','LS DOWN EXIT'),0,'LS R / LS DOWN')
#   elif al and W==1:
#    al=False
#    aR=ticks_add(aR,ticks_diff(g,bX))
#    o.ds('playing',g)
#    if Q:
#     Y('RESUME',K)
#    m.hud_combo=None
#    bG(m,N,S)
#    bj=ticks_add(g,-aT)
#   elif al and W==2:
#    am(Q)
#    return
#  bQ=W
#  if al:
#   sleep(18)
#   continue
#  G=ticks_diff(g,aR)
#  if G>=duration+900:
#   break
#  if Q:
#   de(g)
#   if not ar and(not any((B[2]==0 for B in A)))and(ticks_diff(g,at)>4000):
#    Y('STARVED',K)
#    am(True)
#    return
#  else:
#   aK.update(G)
#   aZ.dO()
#  if G<0:
#   ba=min(3,max(1,(-G+999)//1000))
#   if ba!=aF:
#    display.show(str(ba))
#    aF=ba
#  elif aF:
#   aF=0
#  if ticks_diff(g,bf)>=0:
#   bk()
#   pin8.write_digital(0)
#  for B in A:
#   if B[2]==0 and G>B[0]+bL:
#    B[2]=3
#    ax+=1
#    N=0
#    aI=True
#    bf,aW=ct(2,g)
#  for ac in range(4):
#   bF=bv[ac].read_digital()==0
#   if bF and(not bP[ac]):
#    aC=None
#    bb=bL+1
#    for B in A:
#     X=abs(G-B[0])
#     if B[2]==0 and(Q or B[1]==ac)and(X<bb):
#      aC=B
#      bb=X
#    if aC is not None:
#     if aC[1]!=ac:
#      t=2
#     elif bb<=cB:
#      t=0
#     else:
#      t=1
#     bf,aW=ct(t,g)
#     if t==2:
#      aC[2]=3
#      ax+=1
#      N=0
#     else:
#      aC[2]=1 if t==0 else 2
#      if t==0:
#       bY+=1
#       S+=100
#      else:
#       bh+=1
#       S+=50
#      N+=1
#      aX=max(aX,N)
#     aI=True
#   bP[ac]=bF
#  if ticks_diff(g,bj)>=aT:
#   bj=g
#   C.dV()
#   C.dM(32,35,10)
#   aw=128
#   av=-1
#   for B in A:
#    bm=B[3]
#    ay=None
#    if B[2]in(0,3):
#     bH=B[0]-G
#     if bH<=bT:
#      f=32+bH*91//bT
#      if f>=-7:
#       ay=f
#       C.dS(f,35,B[1],6)
#      elif B[2]==3:
#       B[2]=5
#    if bm is not None:
#     aw=min(aw,bm-8)
#     av=max(av,bm+8)
#    if ay is not None:
#     aw=min(aw,ay-8)
#     av=max(av,ay+8)
#    B[3]=ay
#   C.dY(aw,av)
#   while A and A[0][0]<G-1600:
#    A.pop(0)
#  if aI:
#   bG(m,N,S)
#   aI=False
#  if G>=0:
#   aJ=0 if ax else 1 if bh else 2
#   if aJ!=bR:
#    display.show(Image('99999:99999:99999:99999:99999' if aJ==2 else '99999:90009:90009:90009:99999' if aJ==1 else '00000:00000:00000:00000:00000'))
#    bR=aJ
#  sleep(1)
# if Q:
#  Y('DONE',K,S,ax)
# else:
#  aK.stop()
#  aK=aZ=None
#  gc.collect()
# o.ds('results',ticks_ms())
# bk()
# pin8.write_digital(0)
# C.clear()
# C.dm('FINISH',29,14,2)
# C.show()
# aL(m,'RESULT',('SCORE '+str(S),'BEST '+str(aX),'P'+str(bY)+' G'+str(bh),'MISS '+str(ax)),0,'LS LEFT MENU')
# U=-1
# while True:
#  bp()
#  if Q and o.dl!=L:
#   return
#  W=ah(Z,aa)
#  if W==3 and U==-1:
#   break
#  U=W
#  sleep(25)
# am(False)
#~
#for bB in bv:
# bB.set_pull(bB.PULL_UP)
#bW()
#i2c.init(freq=400000)
#C=cj(60)
#m=cj(61)
#uart.init(baudrate=115200)
#gc.collect()
#Z=pin0.read_analog()
#aa=pin1.read_analog()
#U=ah(Z,aa)
#bM=ticks_ms()
#~
#while True:
# bp()
# g=ticks_ms()
# E=ah(Z,aa)
# ca=o.dl+D
# if ca!=ad:
#  gc.collect()
#  if D=='MENU':
#   if o.dl==L:
#    cc='PC SONGS'
#    af=[bn[1]for bn in V]
#    bg='LS RIGHT SELECT'
#   else:
#    cc='STANDALONE'
#    af=[bn[0]for bn in aU]
#    bg='LS RIGHT START'
#   aL(m,cc,af,aj,bg)
#   C.clear()
#   C.dm('READY',24,20,2)
#   C.show()
#   display.show(Image.HAPPY)
#  elif D=='LOADING':
#   aL(m,'PC LOADING',('WAIT FOR CHART',),0,'')
#  elif D=='ARMED':
#   aL(m,'PC READY',('LS RIGHT PLAY','LS LEFT CANCEL'),0,'')
#  ad=ca
# if E!=-1 and U==-1 and(ticks_diff(g,bM)>200):
#  bM=g
#  if D=='MENU':
#   if E in(0,2):
#    ab=len(V)if o.dl==L else len(aU)
#    aj=(aj+E-1)%ab
#    ad=''
#   elif E==1:
#    if o.dl==L:
#     A=[]
#     ar=False
#     aQ=False
#     ae=aN=0
#     K=(K+1)%65536
#     o.ds('loading',g)
#     D='LOADING'
#     at=g
#     Y('SELECT',K,aj)
#    else:
#     cC(C,m)
#     ad=''
#     E=ah(Z,aa)
#  elif D=='ARMED':
#   if E==1:
#    cC(C,m)
#    ad=''
#    E=ah(Z,aa)
#   elif E==3:
#    am(True)
# if D=='LOADING' and ticks_diff(g,at)>12000:
#  am(True)
# U=E
# sleep(12)
#~END
