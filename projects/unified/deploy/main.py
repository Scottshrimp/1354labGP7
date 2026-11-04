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
#aU='standalone'
#Q='pc'
#cj=('menu','loading','ready','playing','paused','results')
#cH=500
#bu=2500
#def cP(O,df):
# return O-df
#def cQ(v):
# return isinstance(v,str)and len(v)==16 and all((aW in '0123456789abcdef' for aW in v))
#class cO:
# def __init__(b,aR=bu,ticks_diff=None):
#  if aR<=0:
#   raise ValueError('Lease timeout must be positive')
#  b.dD=aR
#  b.dm=ticks_diff or cP
#  b.clear()
# def clear(b):
#  b.dj=None
#  b.dB=None
# def dE(b,O):
#  if b.dj is None:
#   return False
#  E=b.dm(O,b.dB)
#  return 0<=E<b.dD
# def dV(b,v,O):
#  if not cQ(v):
#   raise ValueError('Session must contain 16 lowercase hexadecimal characters')
#  if b.dj is not None:
#   return v==b.dj and b.dE(O)
#  b.dj=v
#  b.dB=O
#  return True
# def dR(b,v,O):
#  if v!=b.dj or not b.dE(O):
#   return False
#  b.dB=O
#  return True
#class cL:
# def __init__(b,aR=bu,ticks_diff=None):
#  b.dl=cO(aR,ticks_diff)
#  b.dn=aU
#  b.ds='menu'
#  b.dw=False
# def dW(b,v,O):
#  return b.dl.dV(v,O)
# def dR(b,v,O):
#  return b.dl.dR(v,O)
# def dZ(b,v,O):
#  if v!=b.dl.dj or not b.dl.dE(O):
#   return()
#  b.dw=True
#  return b.dL(O)
# def dT(b):
#  b.dl.clear()
#  b.dw=False
#  if b.dn!=Q:
#   return()
#  V=()
#  if b.ds in('loading','ready','playing','paused'):
#   V=('abort_pc_round',)
#  b.dn=aU
#  b.ds='menu'
#  return V+('enter_standalone',)
# def dL(b,O):
#  if b.dl.dj is not None and(not b.dl.dE(O)):
#   return b.dT()
#  if b.dw and b.dn==aU and(b.ds=='menu'):
#   b.dn=Q
#   return('enter_pc',)
#  return()
# def dv(b,af,O):
#  if af not in cj:
#   raise ValueError('Unknown game phase')
#  b.ds=af
#  return b.dL(O)
#'Bounded ASCII line framing for the RH1 serial protocol.\n\nCommand validation, handshakes, acknowledgments and serial I/O are handled by\nthe board adapter and pc_host.py.\n'
#cN='RH1'
#bv=60
#class cJ:
# def __init__(b,bi=bv):
#  if not 1<=bi<=bv:
#   raise ValueError('Line limit must be between 1 and 60 bytes')
#  b.dH=bi
#  b.dM()
# def dM(b):
#  b.du=bytearray()
#  b.dA=False
#  b.dF=False
# def dY(b,ar):
#  bU=[]
#  for F in ar or b'':
#   if F==10:
#    if not b.dA and b.du:
#     bU.append(b.du.decode('ascii'))
#    b.dM()
#   elif b.dA:
#    continue
#   elif F==13:
#    if b.dF:
#     b.du=bytearray()
#     b.dA=True
#    b.dF=True
#   elif b.dF or F<32 or F>126 or(len(b.du)>=b.dH):
#    b.du=bytearray()
#    b.dA=True
#   else:
#    b.du.append(F)
#  return bU
#from microbit import*
#import music
#import gc
#from utime import ticks_ms,ticks_diff,ticks_add
#~
#from random import getrandbits
#def cR(text):
# cl='ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/'
# ar=bytearray()
# F=am=0
# for aW in text:
#  F=F<<6|cl.index(aW)
#  am+=6
#  if am>=8:
#   am-=8
#   ar.append(F>>am&255)
#   F&=(1<<am)-1
# return ar
#def cE(text):
# aA=cR(text)
# az=bytearray()
# H=0
# while H<len(aA):
#  F=aA[H]
#  H+=1
#  if F:
#   az.append(F)
#  else:
#   bT=aA[H]
#   H+=1
#   if bT==0:
#    az.append(0)
#   else:
#    co=aA[H]|aA[H+1]<<8
#    H+=2
#    for by in range(bT):
#     az.append(az[-co])
# return az
#cI=3000
#cM=220
#cG=400
#aT=20
#bx=True
#bw=159196
#ch='AAAAAHUAAD6CAAB2AAA+gwAA6wAASgUBYAFFhwHrAABEBQHrAABDAAQFAEEFAQAHIwBBgwAAdQAAQ4IAAHUAADwABA8APAAgMgB1AABBAAQoAEMABDcAOwAECgA7ACwyADoABAoAOgAsMgAAHMgA6gAAQQQBAAUeAAAMMgAAHMgAABYyAAAcyAAAFjIAAAjIAOoAAEoEAWEBRYgAITIASgAECgBKAAQyAFYABDIAUQAEMgBQAAQtAE8EAesAAE0FAQAFHgB1AABNAAQoAE8ABAoASAAECgBIACwyAEcABDsBR4IAAOsAAFYFACYyAEYABDIARgAMMgDqAABQAAQtAE8ABM0AABQyAEoABDIASgAlMgB1AABPAAfDAAAFzQAAKjIARwAHzQAABTIAYAFRAASQAVAABC0AABkyAEYAB80AABkyAAAHgQFNAAQoAAAFMgAABUYATQAE9AFNAAQiAU0AByIBAAUDAksCSowCAAdpAE0ABIEBAAUeAAAFSwBQAAQUAAAFCQEABRMBAAiHAGABT4cABC0AABYyAOsAAFEABIIAVAAJmwBWAAQUAFYABBQAVgAERgBRAARGAFaCAAAhBFSWBHYABC0AAAUUAOoAAFEABEYAUQAHQQAABVAASwJPjAIABSMAdQAAUQAE8AAADR4AAAcKAAAFWgAABR4AAAUUAAAFbgAACiMAAAXwAFQADIEB6wAATAAEBQBGAAQ3AAAFdgJKAAcZACEEVKoIAAdoAQAPQAFQAApKAQAHFwI6AABQQQAAOgAAT0EAADsAAE1CAAA6AABKQQAEHQEFAasDT5YEAAUJAQAFlgAABQkBAAUKAAAURgB1AABMAAS5AAAFlgAACtIAVAAEBQBVAAdPAXUAAFAACY8CTQAENgEABV8AQQAJfwNFAAfMAdYBTAoC1gFKAAQFAEwKAtUBTQkC1gFPAAcPAKsDURMABG0BAARGAAAKUABOAASCAAAF2wFMAAQPAEsAB+UBNgNJkQMhBEupCAAKqgAACg4BAA+RAAAFMgAACg4BOgAATQAEEwFKQgAEHgAEAawACQ4BAAd9AAAIDgEAFEYAABkOAeoAAFUABOYAAAVGAAANRQEABQ4BAAWDBAAHVQVFAAfMAQAKDgHVAUwABAkBTQAEDwBPAAcPAKwDURQEABGVAU4ACYwAAAgOAQAF+gAACA4BlgSBBToeBtUBQQAEQQBAFASrAz4TBFYHQU4QgAU6HQbWAUEKAA0ZAD5OEAAHGQU+AATXAABOmgYADDIAACaaBgAyMgAAKJoGABYyAAAuYgeIAbAAAE2wAARNA1UABAgCAAQtAEgABCMATAAE/gFKAARjBkUACScGSgAtLQAABIIARgAJ8gMABTcFAAgPAAAFBQDqAABGAAQyAEYACSgASAAEFABIAAQUAEgABBQASAAHFAAAFhkASgAJcwAABWkAAAVMBEkABBQASQAElAJJAASyAkkABBkASQAYQQBHAAQUAEcABC0ARwAELQBHAAQZAAAFFABGAAQUAEYABBQAAAqbAAAIrwAADxkAAAVVAAAFUAAACloAAAoUAAARGQBKAAQZAEoAB1kGAArDAAAHvgAACBkAABQUAAAgLQAACKUAAAWbAAAKqgAAFhkAAA2bAAAPrwAAB9EBAAVJBwAIaAEAEW4AAAVUAQAFBQBJAAQtAEkABC0AAAhoAQARQQBHAAdtAQAFBQAAB3EHAAUPAAAcHAIAERkAABRaAAAXtAAAMvwDADIyAAAFlwkABaEJACoyADwAB50DACouBAAyXgsALjIA'
#~
#aS=cE('JwgAABMEAAAUBAETBAEUBAITBAIUBAMTBAMUBAAKGABiFAAWGAAABRUAAgAFFQADYRQAAAAFGwABAAUbAAAKGAAABS0AAAcYAGEAF0gAAAx4AGIUAByQAAAJSAAAFWAAABWQAAAz2AAADDAAACfYAAAMGAATBAAA')
#cg={58:233,59:247,60:262,62:294,64:330,65:349,67:392,68:415,69:440,70:466,71:494,72:523,73:554,74:587,75:622,76:659,77:698,78:740,79:784,80:831,81:880,84:1047,85:1109,86:1175}
#L=None
#def cY():
# global L
# if L is None:
#  gc.collect()
#  L=cE(ch)
#  gc.collect()
#bs=(pin13,pin11,pin15,pin5)
#bt='0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ-: >/'
#cf='7555726227717477171755711747177475771111757577571725755656563444365556746477464434553557557222711152556554444757755577752555265644255736565534216722225555755552557755525555222712470070002020000004212411244'
#~
#class ci:
# def __init__(b,aE):
#  b.dz=aE
#  b.dp=bytearray(1024)
#  b.dq=bytearray(1024)
#  b.dG=True
#  for an in(174,213,128,168,63,211,0,64,141,20,32,2,161,200,218,18,129,207,217,241,219,64,164,166,175):
#   i2c.write(aE,bytes((0,an)))
# def clear(b):
#  for H in range(1024):
#   b.dp[H]=0
# def dr(b,f,w):
#  if 0<=f<128 and 0<=w<64:
#   b.dp[f+(w>>3)*128]|=1<<(w&7)
# def dk(b,S,al,P,cd):
#  ba=abs(P-S)
#  bp=1 if S<P else-1
#  bb=-abs(cd-al)
#  bq=1 if al<cd else-1
#  X=ba+bb
#  while True:
#   b.dr(S,al)
#   if S==P and al==cd:
#    break
#   bG=2*X
#   if bG>=bb:
#    X+=bb
#    S+=bp
#   if bG<=ba:
#    X+=ba
#    al+=bq
# def dO(b,p,q,bZ):
#  f=bZ
#  w=0
#  bc=1-bZ
#  while f>=w:
#   b.dr(p+f,q+w)
#   b.dr(p+w,q+f)
#   b.dr(p-w,q+f)
#   b.dr(p-f,q+w)
#   b.dr(p-f,q-w)
#   b.dr(p-w,q-f)
#   b.dr(p+w,q-f)
#   b.dr(p+f,q-w)
#   w+=1
#   if bc<0:
#    bc+=2*w+1
#   else:
#    f-=1
#    bc+=2*(w-f)+1
# def dU(b,p,q,D,bZ=8):
#  t=bZ
#  if D==0:
#   b.dk(p,q-t,p-t,q+3)
#   b.dk(p,q-t,p+t,q+3)
#   b.dk(p,q-t,p,q+t)
#  elif D==1:
#   b.dk(p+t,q,p-3,q-t)
#   b.dk(p+t,q,p-3,q+t)
#   b.dk(p-t,q,p+t,q)
#  elif D==2:
#   b.dk(p,q+t,p-t,q-3)
#   b.dk(p,q+t,p+t,q-3)
#   b.dk(p,q-t,p,q+t)
#  else:
#   b.dk(p-t,q,p+3,q-t)
#   b.dk(p-t,q,p+3,q+t)
#   b.dk(p-t,q,p+t,q)
# def do(b,cZ,f,w,aN=1):
#  for an in str(cZ).upper():
#   u=bt.find(an)
#   if u<0:
#    u=bt.find(' ')
#   for ce in range(5):
#    cB=ord(cf[u*5+ce])-48
#    for cc in range(3):
#     if cB&1<<2-cc:
#      for bq in range(aN):
#       for bp in range(aN):
#        b.dr(f+cc*aN+bp,w+ce*aN+bq)
#   f+=4*aN
# def show(b):
#  b.dJ(0,127,0,7)
#  b.dG=False
# def ea(b,S,P):
#  if S<=P:
#   b.dJ(S,P,3,5)
# def dJ(b,S,P,dd,de):
#  S=max(0,S)
#  P=min(127,P)
#  for ai in range(dd,de+1):
#   I=ai*128
#   f=S
#   while f<=P:
#    while f<=P and(not b.dG)and(b.dp[I+f]==b.dq[I+f]):
#     f+=1
#    if f>P:
#     break
#    aB=f
#    bf=f
#    f+=1
#    while f<=P and f-aB<28:
#     if b.dG or b.dp[I+f]!=b.dq[I+f]:
#      bf=f
#     elif f-bf>6:
#      break
#     f+=1
#    aG=bf+1
#    i2c.write(b.dz,bytes((0,176|ai,aB&15,16|aB>>4)))
#    i2c.write(b.dz,b'@'+b.dp[I+aB:I+aG])
#    for ah in range(aB,aG):
#     b.dq[I+ah]=b.dp[I+ah]
#    if f<aG:
#     f=aG
# def dP(b,S,P,db,dc):
#  for ai in range(db,dc+1):
#   I=ai*128
#   for f in range(S,P+1):
#    b.dp[I+f]=0
# def dX(b):
#  for ai in(3,4,5):
#   I=ai*128
#   for f in range(128):
#    b.dp[I+f]=0
#~
#def bh():
# if bx:
#  pin9.write_digital(1)
#  pin14.write_digital(1)
#  pin16.write_digital(1)
#def cX(cA):
# if not bx:
#  return
# pin9.write_digital(0 if cA in(1,2)else 1)
# pin14.write_digital(0 if cA in(0,1)else 1)
# pin16.write_digital(1)
#z=[]
#C='MENU'
#def br(ar,cv):
# return ar[cv]|ar[cv+1]<<8
#class cK:
# def __init__(b):
#  cY()
#  b.index=0
#  b.dI=br(L,0)if L else bw
#  b.dK=-1
#  b.pitch=0
#  b.dC=False
# def stop(b):
#  music.stop(pin12)
#  b.dC=False
# def update(b,E):
#  if E<0:
#   return
#  bA=False
#  while b.index<len(L)and E>=b.dI:
#   b.dK=b.dI+br(L,b.index+2)
#   b.pitch=L[b.index+4]
#   b.index+=5
#   if b.index<len(L):
#    b.dI+=br(L,b.index)
#   bA=True
#  if E<b.dK:
#   if bA or not b.dC:
#    music.pitch(cg[b.pitch],duration=-1,pin=pin12,wait=False)
#    b.dC=True
#  elif b.dC:
#   b.stop()
#class cF:
# def __init__(b):
#  b.index=0
#  b.dN=0
# def dQ(b):
#  while len(z)<12 and b.index<len(aS):
#   b.dN+=br(aS,b.index)
#   z.append([b.dN,aS[b.index+2],0,None])
#   b.index+=3
#def ag(p,q):
# f=pin0.read_analog()-p
# w=pin1.read_analog()-q
# if abs(f)<230 and abs(w)<230:
#  return-1
# if abs(f)>=abs(w):
#  return 1 if f>0 else 3
# return 0 if w>0 else 2
#def cW(da,al,cU):
# for w in range(al,al+cU):
#  ck=(w>>3)*128
#  ct=1<<(w&7)
#  for f in range(6,122):
#   da.dp[ck+f]^=ct
#def ax(m,cV,aM,u,cT):
# m.hud_combo=None
# m.clear()
# m.do(cV[:18],4,2)
# for H in range(min(4,len(aM))):
#  cD=max(0,min(u-2,len(aM)-4))if len(aM)>4 else 0
#  ah=cD+H
#  if ah>=len(aM):
#   break
#  w=16+H*9
#  m.do(aM[ah][:25],10,w)
#  if ah==u:
#   cW(m,w-1,8)
# m.do(cT[:28],3,57)
# m.show()
#def bE(m,M,R):
# if getattr(m,'hud_combo',None)is None:
#  m.clear()
#  m.do('COMBO',23,3,2)
#  m.dk(8,39,119,39)
#  m.do('SCORE',8,48)
#  m.do(str(M),max(0,(128-(4*len(str(M))-1)*2)//2),22,2)
#  m.do(str(R),40,48)
#  m.show()
# else:
#  if M!=m.hud_combo:
#   m.dP(0,127,2,3)
#   bC=str(M)
#   m.do(bC,max(0,(128-(4*len(bC)-1)*2)//2),22,2)
#   m.dJ(0,127,2,3)
#  if R!=m.dS:
#   m.dP(40,127,6,6)
#   m.do(str(R),40,48)
#   m.dJ(40,127,6,6)
# m.hud_combo=M
# m.dS=R
#def cr(ad,g):
# cX(ad)
# pin8.write_digital(1 if ad==2 else 0)
# return(ticks_add(g,130),0)
#def cu():
# return '%04x%04x'%(getrandbits(16),getrandbits(16))
#o=cL(ticks_diff=ticks_diff)
#bI=cJ()
#aK=cu()
#bN=ticks_add(ticks_ms(),-1000)
#au=0
#T=[]
#ao=0
#Z=0
#K=0
#bn=0
#aL=0
#ae=0
#ap=False
#aP=False
#cb=0
#at=0
#bR=0
#Y=''
#N=[]
#aH=0
#bH=0
#bl=-1
#bM=ticks_ms()
#~
#def aD(*cS):
# line=','.join((str(F)for F in cS))
# if len(line)<=60:
#  uart.write(line+'\n')
#def aa(bB,*di):
# global aH
# if o.dl.dj:
#  if bB=='NEED' and any((X[1]=='NEED' for X in N)):
#   return
#  N.append((aH,bB)+di)
#  aH=(aH+1)%65536
#def bV():
# global L
# music.stop(pin12)
# L=None
# bh()
# pin8.write_digital(0)
#def ak(stop):
# global C,z,Y
# if stop and o.dn==Q:
#  aa('STOP',K)
# bV()
# z=[]
# o.dv('menu',ticks_ms())
# C='MENU'
# Y=''
#def cm(V):
# global aK,T,z,C,Y,Z
# if 'enter_standalone' in V or 'enter_pc' in V:
#  bV()
#  z=[]
#  C='MENU'
#  Y=''
#  Z=0
# if 'enter_standalone' in V:
#  T=[]
# if o.dl.dj is None:
#  bI.dM()
#  N[:]=[]
#  aK=cu()
#def bB(l,g):
# global T,ao,bn,aL,ae
# global ap,C,aP,cb,at,Y
# J=l[0]
# if J=='EA' and len(l)==2:
#  if N and int(l[1])==N[0][0]:
#   N.pop(0)
#  return
# if J=='HB' and len(l)==1:
#  return
# if J=='CATBEGIN' and len(l)==2 and(not o.dw):
#  aq=int(l[1])
#  if not 1<=aq<=12:
#   raise ValueError()
#  T=[]
#  ao=aq
#  return
# if J=='CAT' and len(l)==3 and(not o.dw):
#  u=int(l[1])
#  if u!=len(T)or u>=ao:
#   raise ValueError()
#  T.append((u,l[2][:18]))
#  return
# if J=='READY' and len(l)==1 and(len(T)==ao)and ao:
#  cm(o.dZ(o.dl.dj,g))
#  return
# if J=='BYE' and len(l)==1:
#  o.dl.dB=ticks_add(g,-3000)
#  return
# if o.dn!=Q or len(l)<2:
#  raise ValueError()
# if int(l[1])!=K or C=='MENU' or o.ds=='results':
#  return
# if J=='BEGIN' and len(l)==4 and(C=='LOADING'):
#  duration,aq=(int(l[2]),int(l[3]))
#  if not 0<duration<=3600000 or not 0<aq<=10000:
#   raise ValueError()
#  bn,aL,ae=(duration,aq,0)
#  ap=False
#  at=g
# elif J=='N' and len(l)==5 and(C in('LOADING','ARMED','PLAY')):
#  u,bo,D=(int(l[2]),int(l[3]),int(l[4]))
#  if u!=ae or u>=aL or len(z)>=48 or(not 0<=bo<bn)or(not 0<=D<4)or(z and bo<z[-1][0]):
#   raise ValueError()
#  z.append([bo,D,0,None])
#  ae+=1
#  at=g
# elif J=='END' and len(l)==2 and(ae==aL):
#  ap=True
# elif J=='ARM' and len(l)==2 and(C=='LOADING')and ae:
#  C='ARMED'
#  o.dv('ready',g)
# elif J=='SYNC' and len(l)==2 and(C=='PLAY')and(not aP):
#  cb=ticks_add(g,2700)
#  aP=True
#  aa('SYNCED',K)
# elif J=='ERROR' and len(l)==2:
#  ak(True)
# else:
#  raise ValueError()
#~
#def dg(line,g):
# global au,aH,bl,T,ao,Z
# l=line.split(',')
# if len(l)==4 and l[:2]==['RH1','ATTACH']and(l[2]==aK)and(len(l[3])==8)and all((an in '0123456789abcdef' for an in l[3])):
#  v=aK+l[3]
#  cp=o.dl.dj is None
#  if o.dW(v,g):
#   if cp:
#    au=aH=0
#    bl=-1
#    T=[]
#    ao=0
#    Z=0
#    N[:]=[]
#   aD('RH1','ACCEPT',v)
#  return
# if len(l)<4 or l[0]!='RH1' or l[1]!=o.dl.dj:
#  return
# try:
#  aO=int(l[2])
#  if aO==(au-1)%65536:
#   aD('RH1',l[1],'A',aO,'OK')
#   return
#  if aO!=au:
#   return
#  bB(l[3:],g)
#  o.dR(l[1],g)
#  au=(au+1)%65536
#  aD('RH1',l[1],'A',aO,'OK')
# except(ValueError,IndexError):
#  aD('RH1',l[1],'A',l[2],'BAD')
#def bm():
# global aK,bN,bH,bl,bM
# g=ticks_ms()
# cq=o.dl.dj is not None
# V=o.dL(g)
# if V or(cq and o.dl.dj is None):
#  cm(V)
# if ticks_diff(g,bM)>=1000:
#  gc.collect()
#  bM=g
# if uart.any():
#  for line in bI.dY(uart.read(64)):
#   dg(line,g)
# if N and(N[0][0]!=bl or ticks_diff(g,bH)>=600):
#  aD('RH1',o.dl.dj,'E',*N[0])
#  bl=N[0][0]
#  bH=g
# if o.dl.dj is None and ticks_diff(g,bN)>=800:
#  aD('RH1','HELLO',aK)
#  bN=g
#def dh(g):
# global bR
# if not ap and len(z)<32 and(ticks_diff(g,bR)>=500):
#  aa('NEED',K,ae,44-len(z))
#  bR=g
#~
#def cz(B,m):
# global C,z,L
# G=o.dn==Q
# o.dv('playing',ticks_ms())
# bS,cw,bK=(1700,100,210)if G else(3000,220,400)
# duration=bn if G else bw
# C='PLAY'
# M=0
# R=0
# aV=0
# bX=0
# bJ=0
# aJ=0
# if not G:
#  z=[]
# aX=None if G else cF()
# if aX:
#  aX.dQ()
# bj=None if G else cK()
# bW=0
# aj=False
# bO=[False]*4
# bd=ticks_ms()
# bg=ticks_add(ticks_ms(),-aT)
# bP=ag(ab,ac)
# aI=False
# bQ=-1
# bY=Image(5,5)
# B.clear()
# B.dk(1,18,126,18)
# B.dk(1,52,126,52)
# B.dO(32,35,10)
# B.show()
# m.hud_combo=None
# bE(m,0,0)
# if G:
#  aa('START',K)
#  cn=ticks_add(ticks_ms(),8000)
#  while not aP:
#   bm()
#   if o.dn!=Q or ticks_diff(ticks_ms(),cn)>=0:
#    ak(True)
#    return
#   sleep(2)
#  aQ=cb
# else:
#  aQ=ticks_add(ticks_ms(),3500)
# display.show('3')
# aF=3
# while True:
#  bm()
#  if G and o.dn!=Q:
#   return
#  g=ticks_ms()
#  W=ag(ab,ac)
#  if W!=-1 and bP==-1:
#   if not aj and W==3:
#    aj=True
#    bW=g
#    o.dv('paused',g)
#    if G:
#     aa('PAUSE',K)
#    else:
#     bj.stop()
#    bh()
#    pin8.write_digital(0)
#    ax(m,'PAUSED',('LS RIGHT RESUME','LS DOWN EXIT'),0,'LS R / LS DOWN')
#   elif aj and W==1:
#    aj=False
#    aQ=ticks_add(aQ,ticks_diff(g,bW))
#    o.dv('playing',g)
#    if G:
#     aa('RESUME',K)
#    m.hud_combo=None
#    bE(m,M,R)
#    bg=ticks_add(g,-aT)
#   elif aj and W==2:
#    ak(G)
#    return
#  bP=W
#  if aj:
#   sleep(18)
#   continue
#  E=ticks_diff(g,aQ)
#  if E>=duration+900:
#   break
#  if G:
#   dh(g)
#   if not ap and(not any((A[2]==0 for A in z)))and(ticks_diff(g,at)>4000):
#    aa('STARVED',K)
#    ak(True)
#    return
#  else:
#   bj.update(E)
#   aX.dQ()
#  if E<0:
#   aY=min(3,max(1,(-E+999)//1000))
#   if aY!=aF:
#    display.show(str(aY))
#    aF=aY
#  elif aF:
#   aF=0
#  if ticks_diff(g,bd)>=0:
#   bh()
#   pin8.write_digital(0)
#  for A in z:
#   if A[2]==0 and E>A[0]+bK:
#    A[2]=3
#    aJ+=1
#    M=0
#    aI=True
#    bd,by=cr(2,g)
#  for ad in range(4):
#   bD=bs[ad].read_digital()==0
#   if bD and(not bO[ad]):
#    aC=None
#    aZ=bK+1
#    for A in z:
#     X=abs(E-A[0])
#     if A[2]==0 and(G or A[1]==ad)and(X<aZ):
#      aC=A
#      aZ=X
#    if aC is not None:
#     if aC[1]!=ad:
#      t=2
#     elif aZ<=cw:
#      t=0
#     else:
#      t=1
#     bd,by=cr(t,g)
#     if t==2:
#      aC[2]=3
#      aJ+=1
#      M=0
#     else:
#      aC[2]=1 if t==0 else 2
#      if t==0:
#       bX+=1
#       R+=100
#      else:
#       bJ+=1
#       R+=50
#      M+=1
#      aV=max(aV,M)
#     aI=True
#   bO[ad]=bD
#  if ticks_diff(g,bg)>=aT:
#   bg=g
#   B.dX()
#   B.dO(32,35,10)
#   aw=128
#   av=-1
#   for A in z:
#    bk=A[3]
#    ay=None
#    if A[2]in(0,3):
#     bF=A[0]-E
#     if bF<=bS:
#      f=32+bF*91//bS
#      if f>=-7:
#       ay=f
#       B.dU(f,35,A[1],6)
#      elif A[2]==3:
#       A[2]=5
#    if bk is not None:
#     aw=min(aw,bk-8)
#     av=max(av,bk+8)
#    if ay is not None:
#     aw=min(aw,ay-8)
#     av=max(av,ay+8)
#    A[3]=ay
#   B.ea(aw,av)
#   while z and z[0][0]<E-1600:
#    z.pop(0)
#  if aI:
#   bE(m,M,R)
#   aI=False
#  if E>=0:
#   be=min(25,E*25//duration)
#   if be!=bQ:
#    for u in range(25):
#     bY.set_pixel(u%5,u//5,9 if u<be else 0)
#    display.show(bY)
#    bQ=be
#  sleep(1)
# if G:
#  aa('DONE',K,R,aJ)
# else:
#  bj.stop()
#  L=None
#  gc.collect()
# o.dv('results',ticks_ms())
# bh()
# pin8.write_digital(0)
# B.clear()
# B.do('FINISH',29,14,2)
# B.show()
# ax(m,'RESULT',('SCORE '+str(R),'BEST '+str(aV),'P'+str(bX)+' G'+str(bJ),'MISS '+str(aJ)),0,'LS LEFT MENU')
# U=-1
# while True:
#  bm()
#  if G and o.dn!=Q:
#   return
#  W=ag(ab,ac)
#  if W==3 and U==-1:
#   break
#  U=W
#  sleep(25)
# ak(False)
#~
#for bz in bs:
# bz.set_pull(bz.PULL_UP)
#bV()
#i2c.init(freq=400000)
#B=ci(60)
#m=ci(61)
#uart.init(baudrate=115200)
#gc.collect()
#ab=pin0.read_analog()
#ac=pin1.read_analog()
#U=ag(ab,ac)
#bL=ticks_ms()
#~
#while True:
# bm()
# g=ticks_ms()
# D=ag(ab,ac)
# ca=o.dn+C
# if ca!=Y:
#  gc.collect()
#  if C=='MENU':
#   if o.dn==Q:
#    ax(m,'PC SONGS',[cC[1]for cC in T],Z,'LS RIGHT SELECT')
#   else:
#    ax(m,'MEGALOVANIA',('STANDALONE','LS RIGHT START'),0,'P12 SPEAKER')
#   B.clear()
#   B.do('READY',24,20,2)
#   B.show()
#   display.show(Image.HAPPY)
#  elif C=='LOADING':
#   ax(m,'PC LOADING',('WAIT FOR CHART',),0,'')
#  elif C=='ARMED':
#   ax(m,'PC READY',('LS RIGHT PLAY','LS LEFT CANCEL'),0,'')
#  Y=ca
# if D!=-1 and U==-1 and(ticks_diff(g,bL)>200):
#  bL=g
#  if C=='MENU':
#   if o.dn==Q:
#    if D==0:
#     Z=(Z-1)%len(T)
#     Y=''
#    elif D==2:
#     Z=(Z+1)%len(T)
#     Y=''
#    elif D==1:
#     z=[]
#     ap=False
#     aP=False
#     ae=aL=0
#     K=(K+1)%65536
#     o.dv('loading',g)
#     C='LOADING'
#     at=g
#     aa('SELECT',K,Z)
#   elif D==1:
#    cz(B,m)
#    Y=''
#    D=ag(ab,ac)
#  elif C=='ARMED':
#   if D==1:
#    cz(B,m)
#    Y=''
#    D=ag(ab,ac)
#   elif D==3:
#    ak(True)
# if C=='LOADING' and ticks_diff(g,at)>12000:
#  ak(True)
# U=D
# sleep(12)
#~END
