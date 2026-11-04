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
#cg=('menu','loading','ready','playing','paused','results')
#cE=500
#bt=2500
#def cM(O,dc):
# return O-dc
#def cN(u):
# return isinstance(u,str)and len(u)==16 and all((aW in '0123456789abcdef' for aW in u))
#class cL:
# def __init__(b,aR=bt,ticks_diff=None):
#  if aR<=0:
#   raise ValueError('Lease timeout must be positive')
#  b.dA=aR
#  b.dj=ticks_diff or cM
#  b.clear()
# def clear(b):
#  b.dg=None
#  b.dw=None
# def dB(b,O):
#  if b.dg is None:
#   return False
#  H=b.dj(O,b.dw)
#  return 0<=H<b.dA
# def dS(b,u,O):
#  if not cN(u):
#   raise ValueError('Session must contain 16 lowercase hexadecimal characters')
#  if b.dg is not None:
#   return u==b.dg and b.dB(O)
#  b.dg=u
#  b.dw=O
#  return True
# def dO(b,u,O):
#  if u!=b.dg or not b.dB(O):
#   return False
#  b.dw=O
#  return True
#class cI:
# def __init__(b,aR=bt,ticks_diff=None):
#  b.di=cL(aR,ticks_diff)
#  b.dk=aU
#  b.dp='menu'
#  b.ds=False
# def dT(b,u,O):
#  return b.di.dS(u,O)
# def dO(b,u,O):
#  return b.di.dO(u,O)
# def dW(b,u,O):
#  if u!=b.di.dg or not b.di.dB(O):
#   return()
#  b.ds=True
#  return b.dI(O)
# def dQ(b):
#  b.di.clear()
#  b.ds=False
#  if b.dk!=Q:
#   return()
#  V=()
#  if b.dp in('loading','ready','playing','paused'):
#   V=('abort_pc_round',)
#  b.dk=aU
#  b.dp='menu'
#  return V+('enter_standalone',)
# def dI(b,O):
#  if b.di.dg is not None and(not b.di.dB(O)):
#   return b.dQ()
#  if b.ds and b.dk==aU and(b.dp=='menu'):
#   b.dk=Q
#   return('enter_pc',)
#  return()
# def dr(b,af,O):
#  if af not in cg:
#   raise ValueError('Unknown game phase')
#  b.dp=af
#  return b.dI(O)
#'Bounded ASCII line framing for the RH1 serial protocol.\n\nCommand validation, handshakes, acknowledgments and serial I/O are handled by\nthe board adapter and pc_host.py.\n'
#cK='RH1'
#bu=60
#class cG:
# def __init__(b,bh=bu):
#  if not 1<=bh<=bu:
#   raise ValueError('Line limit must be between 1 and 60 bytes')
#  b.dE=bh
#  b.dJ()
# def dJ(b):
#  b.dq=bytearray()
#  b.dv=False
#  b.dC=False
# def dV(b,ar):
#  bS=[]
#  for E in ar or b'':
#   if E==10:
#    if not b.dv and b.dq:
#     bS.append(b.dq.decode('ascii'))
#    b.dJ()
#   elif b.dv:
#    continue
#   elif E==13:
#    if b.dC:
#     b.dq=bytearray()
#     b.dv=True
#    b.dC=True
#   elif b.dC or E<32 or E>126 or(len(b.dq)>=b.dE):
#    b.dq=bytearray()
#    b.dv=True
#   else:
#    b.dq.append(E)
#  return bS
#from microbit import*
#import music
#import gc
#from utime import ticks_ms,ticks_diff,ticks_add
#~
#from random import getrandbits
#def cO(text):
# ci='ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/'
# ar=bytearray()
# E=am=0
# for aW in text:
#  E=E<<6|ci.index(aW)
#  am+=6
#  if am>=8:
#   am-=8
#   ar.append(E>>am&255)
#   E&=(1<<am)-1
# return ar
#def cB(text):
# aA=cO(text)
# az=bytearray()
# I=0
# while I<len(aA):
#  E=aA[I]
#  I+=1
#  if E:
#   az.append(E)
#  else:
#   bR=aA[I]
#   I+=1
#   if bR==0:
#    az.append(0)
#   else:
#    cl=aA[I]|aA[I+1]<<8
#    I+=2
#    for bx in range(bR):
#     az.append(az[-cl])
# return az
#cF=3000
#cJ=220
#cD=400
#aT=20
#bw=True
#bv=159196
#ce='AAAAAHUAAD6CAAB2AAA+gwAA6wAASgUBYAFFhwHrAABEBQHrAABDAAQFAEEFAQAHIwBBgwAAdQAAQ4IAAHUAADwABA8APAAgMgB1AABBAAQoAEMABDcAOwAECgA7ACwyADoABAoAOgAsMgAAHMgA6gAAQQQBAAUeAAAMMgAAHMgAABYyAAAcyAAAFjIAAAjIAOoAAEoEAWEBRYgAITIASgAECgBKAAQyAFYABDIAUQAEMgBQAAQtAE8EAesAAE0FAQAFHgB1AABNAAQoAE8ABAoASAAECgBIACwyAEcABDsBR4IAAOsAAFYFACYyAEYABDIARgAMMgDqAABQAAQtAE8ABM0AABQyAEoABDIASgAlMgB1AABPAAfDAAAFzQAAKjIARwAHzQAABTIAYAFRAASQAVAABC0AABkyAEYAB80AABkyAAAHgQFNAAQoAAAFMgAABUYATQAE9AFNAAQiAU0AByIBAAUDAksCSowCAAdpAE0ABIEBAAUeAAAFSwBQAAQUAAAFCQEABRMBAAiHAGABT4cABC0AABYyAOsAAFEABIIAVAAJmwBWAAQUAFYABBQAVgAERgBRAARGAFaCAAAhBFSWBHYABC0AAAUUAOoAAFEABEYAUQAHQQAABVAASwJPjAIABSMAdQAAUQAE8AAADR4AAAcKAAAFWgAABR4AAAUUAAAFbgAACiMAAAXwAFQADIEB6wAATAAEBQBGAAQ3AAAFdgJKAAcZACEEVKoIAAdoAQAPQAFQAApKAQAHFwI6AABQQQAAOgAAT0EAADsAAE1CAAA6AABKQQAEHQEFAasDT5YEAAUJAQAFlgAABQkBAAUKAAAURgB1AABMAAS5AAAFlgAACtIAVAAEBQBVAAdPAXUAAFAACY8CTQAENgEABV8AQQAJfwNFAAfMAdYBTAoC1gFKAAQFAEwKAtUBTQkC1gFPAAcPAKsDURMABG0BAARGAAAKUABOAASCAAAF2wFMAAQPAEsAB+UBNgNJkQMhBEupCAAKqgAACg4BAA+RAAAFMgAACg4BOgAATQAEEwFKQgAEHgAEAawACQ4BAAd9AAAIDgEAFEYAABkOAeoAAFUABOYAAAVGAAANRQEABQ4BAAWDBAAHVQVFAAfMAQAKDgHVAUwABAkBTQAEDwBPAAcPAKwDURQEABGVAU4ACYwAAAgOAQAF+gAACA4BlgSBBToeBtUBQQAEQQBAFASrAz4TBFYHQU4QgAU6HQbWAUEKAA0ZAD5OEAAHGQU+AATXAABOmgYADDIAACaaBgAyMgAAKJoGABYyAAAuYgeIAbAAAE2wAARNA1UABAgCAAQtAEgABCMATAAE/gFKAARjBkUACScGSgAtLQAABIIARgAJ8gMABTcFAAgPAAAFBQDqAABGAAQyAEYACSgASAAEFABIAAQUAEgABBQASAAHFAAAFhkASgAJcwAABWkAAAVMBEkABBQASQAElAJJAASyAkkABBkASQAYQQBHAAQUAEcABC0ARwAELQBHAAQZAAAFFABGAAQUAEYABBQAAAqbAAAIrwAADxkAAAVVAAAFUAAACloAAAoUAAARGQBKAAQZAEoAB1kGAArDAAAHvgAACBkAABQUAAAgLQAACKUAAAWbAAAKqgAAFhkAAA2bAAAPrwAAB9EBAAVJBwAIaAEAEW4AAAVUAQAFBQBJAAQtAEkABC0AAAhoAQARQQBHAAdtAQAFBQAAB3EHAAUPAAAcHAIAERkAABRaAAAXtAAAMvwDADIyAAAFlwkABaEJACoyADwAB50DACouBAAyXgsALjIA'
#~
#aS=cB('JwgAABMEAAAUBAETBAEUBAITBAIUBAMTBAMUBAAKGABiFAAWGAAABRUAAgAFFQADYRQAAAAFGwABAAUbAAAKGAAABS0AAAcYAGEAF0gAAAx4AGIUAByQAAAJSAAAFWAAABWQAAAz2AAADDAAACfYAAAMGAATBAAA')
#cd={58:233,59:247,60:262,62:294,64:330,65:349,67:392,68:415,69:440,70:466,71:494,72:523,73:554,74:587,75:622,76:659,77:698,78:740,79:784,80:831,81:880,84:1047,85:1109,86:1175}
#M=None
#def cV():
# global M
# if M is None:
#  gc.collect()
#  M=cB(ce)
#  gc.collect()
#br=(pin13,pin11,pin15,pin5)
#bs='0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ-: >/'
#cc='7555726227717477171755711747177475771111757577571725755656563444365556746477464434553557557222711152556554444757755577752555265644255736565534216722225555755552557755525555222712470070002020000004212411244'
#~
#class cf:
# def __init__(b,aE):
#  b.du=aE
#  b.dm=bytearray(1024)
#  b.dn=bytearray(1024)
#  b.dD=True
#  for an in(174,213,128,168,63,211,0,64,141,20,32,2,161,200,218,18,129,207,217,241,219,64,164,166,175):
#   i2c.write(aE,bytes((0,an)))
# def clear(b):
#  for I in range(1024):
#   b.dm[I]=0
# def do(b,f,v):
#  if 0<=f<128 and 0<=v<64:
#   b.dm[f+(v>>3)*128]|=1<<(v&7)
# def dh(b,S,al,P,ca):
#  ba=abs(P-S)
#  bo=1 if S<P else-1
#  bb=-abs(ca-al)
#  bp=1 if al<ca else-1
#  X=ba+bb
#  while True:
#   b.do(S,al)
#   if S==P and al==ca:
#    break
#   bF=2*X
#   if bF>=bb:
#    X+=bb
#    S+=bo
#   if bF<=ba:
#    X+=ba
#    al+=bp
# def dL(b,p,q,bW):
#  f=bW
#  v=0
#  bc=1-bW
#  while f>=v:
#   b.do(p+f,q+v)
#   b.do(p+v,q+f)
#   b.do(p-v,q+f)
#   b.do(p-f,q+v)
#   b.do(p-f,q-v)
#   b.do(p-v,q-f)
#   b.do(p+v,q-f)
#   b.do(p+f,q-v)
#   v+=1
#   if bc<0:
#    bc+=2*v+1
#   else:
#    f-=1
#    bc+=2*(v-f)+1
# def dR(b,p,q,D,bW=8):
#  t=bW
#  if D==0:
#   b.dh(p,q-t,p-t,q+3)
#   b.dh(p,q-t,p+t,q+3)
#   b.dh(p,q-t,p,q+t)
#  elif D==1:
#   b.dh(p+t,q,p-3,q-t)
#   b.dh(p+t,q,p-3,q+t)
#   b.dh(p-t,q,p+t,q)
#  elif D==2:
#   b.dh(p,q+t,p-t,q-3)
#   b.dh(p,q+t,p+t,q-3)
#   b.dh(p,q-t,p,q+t)
#  else:
#   b.dh(p-t,q,p+3,q-t)
#   b.dh(p-t,q,p+3,q+t)
#   b.dh(p-t,q,p+t,q)
# def dl(b,cW,f,v,aN=1):
#  for an in str(cW).upper():
#   w=bs.find(an)
#   if w<0:
#    w=bs.find(' ')
#   for cb in range(5):
#    cw=ord(cc[w*5+cb])-48
#    for bZ in range(3):
#     if cw&1<<2-bZ:
#      for bp in range(aN):
#       for bo in range(aN):
#        b.do(f+bZ*aN+bo,v+cb*aN+bp)
#   f+=4*aN
# def show(b):
#  b.dG(0,127,0,7)
#  b.dD=False
# def dX(b,S,P):
#  if S<=P:
#   b.dG(S,P,3,5)
# def dG(b,S,P,da,db):
#  S=max(0,S)
#  P=min(127,P)
#  for ai in range(da,db+1):
#   J=ai*128
#   f=S
#   while f<=P:
#    while f<=P and(not b.dD)and(b.dm[J+f]==b.dn[J+f]):
#     f+=1
#    if f>P:
#     break
#    aB=f
#    be=f
#    f+=1
#    while f<=P and f-aB<28:
#     if b.dD or b.dm[J+f]!=b.dn[J+f]:
#      be=f
#     elif f-be>6:
#      break
#     f+=1
#    aG=be+1
#    i2c.write(b.du,bytes((0,176|ai,aB&15,16|aB>>4)))
#    i2c.write(b.du,b'@'+b.dm[J+aB:J+aG])
#    for ah in range(aB,aG):
#     b.dn[J+ah]=b.dm[J+ah]
#    if f<aG:
#     f=aG
# def dM(b,S,P,cY,cZ):
#  for ai in range(cY,cZ+1):
#   J=ai*128
#   for f in range(S,P+1):
#    b.dm[J+f]=0
# def dU(b):
#  for ai in(3,4,5):
#   J=ai*128
#   for f in range(128):
#    b.dm[J+f]=0
#~
#def bg():
# if bw:
#  pin9.write_digital(1)
#  pin14.write_digital(1)
#  pin16.write_digital(1)
#def cU(cv):
# if not bw:
#  return
# pin9.write_digital(0 if cv in(1,2)else 1)
# pin14.write_digital(0 if cv in(0,1)else 1)
# pin16.write_digital(1)
#z=[]
#C='MENU'
#def bq(ar,cr):
# return ar[cr]|ar[cr+1]<<8
#class cH:
# def __init__(b):
#  cV()
#  b.index=0
#  b.dF=bq(M,0)if M else bv
#  b.dH=-1
#  b.pitch=0
#  b.dz=False
# def stop(b):
#  music.stop(pin12)
#  b.dz=False
# def update(b,H):
#  if H<0:
#   return
#  bz=False
#  while b.index<len(M)and H>=b.dF:
#   b.dH=b.dF+bq(M,b.index+2)
#   b.pitch=M[b.index+4]
#   b.index+=5
#   if b.index<len(M):
#    b.dF+=bq(M,b.index)
#   bz=True
#  if H<b.dH:
#   if bz or not b.dz:
#    music.pitch(cd[b.pitch],duration=-1,pin=pin12,wait=False)
#    b.dz=True
#  elif b.dz:
#   b.stop()
#class cC:
# def __init__(b):
#  b.index=0
#  b.dK=0
# def dN(b):
#  while len(z)<12 and b.index<len(aS):
#   b.dK+=bq(aS,b.index)
#   z.append([b.dK,aS[b.index+2],0,None])
#   b.index+=3
#def ag(p,q):
# f=pin0.read_analog()-p
# v=pin1.read_analog()-q
# if abs(f)<230 and abs(v)<230:
#  return-1
# if abs(f)>=abs(v):
#  return 1 if f>0 else 3
# return 0 if v>0 else 2
#def cT(cX,al,cR):
# for v in range(al,al+cR):
#  ch=(v>>3)*128
#  cp=1<<(v&7)
#  for f in range(6,122):
#   cX.dm[ch+f]^=cp
#def ax(m,cS,aM,w,cQ):
# m.hud_combo=None
# m.clear()
# m.dl(cS[:18],4,2)
# for I in range(min(4,len(aM))):
#  cA=max(0,min(w-2,len(aM)-4))if len(aM)>4 else 0
#  ah=cA+I
#  if ah>=len(aM):
#   break
#  v=16+I*9
#  m.dl(aM[ah][:25],10,v)
#  if ah==w:
#   cT(m,v-1,8)
# m.dl(cQ[:28],3,57)
# m.show()
#def bD(m,G,R):
# if getattr(m,'hud_combo',None)is None:
#  m.clear()
#  m.dl('COMBO',23,3,2)
#  m.dh(8,39,119,39)
#  m.dl('SCORE',8,48)
#  m.dl(str(G),max(0,(128-(4*len(str(G))-1)*2)//2),22,2)
#  m.dl(str(R),40,48)
#  m.show()
# else:
#  if G!=m.hud_combo:
#   m.dM(0,127,2,3)
#   bB=str(G)
#   m.dl(bB,max(0,(128-(4*len(bB)-1)*2)//2),22,2)
#   m.dG(0,127,2,3)
#  if R!=m.dP:
#   m.dM(40,127,6,6)
#   m.dl(str(R),40,48)
#   m.dG(40,127,6,6)
# m.hud_combo=G
# m.dP=R
#def co(ad,g):
# cU(ad)
# pin8.write_digital(1 if ad==2 else 0)
# return(ticks_add(g,130),0)
#def cq():
# return '%04x%04x'%(getrandbits(16),getrandbits(16))
#o=cI(ticks_diff=ticks_diff)
#bH=cG()
#aK=cq()
#bM=ticks_add(ticks_ms(),-1000)
#au=0
#T=[]
#ao=0
#Z=0
#L=0
#bm=0
#aL=0
#ae=0
#ap=False
#aP=False
#bY=0
#at=0
#bP=0
#Y=''
#N=[]
#aH=0
#bG=0
#bk=-1
#bL=ticks_ms()
#~
#def aD(*cP):
# line=','.join((str(E)for E in cP))
# if len(line)<=60:
#  uart.write(line+'\n')
#def aa(bA,*df):
# global aH
# if o.di.dg:
#  if bA=='NEED' and any((X[1]=='NEED' for X in N)):
#   return
#  N.append((aH,bA)+df)
#  aH=(aH+1)%65536
#def bT():
# global M
# music.stop(pin12)
# M=None
# bg()
# pin8.write_digital(0)
#def ak(stop):
# global C,z,Y
# if stop and o.dk==Q:
#  aa('STOP',L)
# bT()
# z=[]
# o.dr('menu',ticks_ms())
# C='MENU'
# Y=''
#def cj(V):
# global aK,T,z,C,Y,Z
# if 'enter_standalone' in V or 'enter_pc' in V:
#  bT()
#  z=[]
#  C='MENU'
#  Y=''
#  Z=0
# if 'enter_standalone' in V:
#  T=[]
# if o.di.dg is None:
#  bH.dJ()
#  N[:]=[]
#  aK=cq()
#def bA(l,g):
# global T,ao,bm,aL,ae
# global ap,C,aP,bY,at,Y
# K=l[0]
# if K=='EA' and len(l)==2:
#  if N and int(l[1])==N[0][0]:
#   N.pop(0)
#  return
# if K=='HB' and len(l)==1:
#  return
# if K=='CATBEGIN' and len(l)==2 and(not o.ds):
#  aq=int(l[1])
#  if not 1<=aq<=12:
#   raise ValueError()
#  T=[]
#  ao=aq
#  return
# if K=='CAT' and len(l)==3 and(not o.ds):
#  w=int(l[1])
#  if w!=len(T)or w>=ao:
#   raise ValueError()
#  T.append((w,l[2][:18]))
#  return
# if K=='READY' and len(l)==1 and(len(T)==ao)and ao:
#  cj(o.dW(o.di.dg,g))
#  return
# if K=='BYE' and len(l)==1:
#  o.di.dw=ticks_add(g,-3000)
#  return
# if o.dk!=Q or len(l)<2:
#  raise ValueError()
# if int(l[1])!=L or C=='MENU' or o.dp=='results':
#  return
# if K=='BEGIN' and len(l)==4 and(C=='LOADING'):
#  duration,aq=(int(l[2]),int(l[3]))
#  if not 0<duration<=3600000 or not 0<aq<=10000:
#   raise ValueError()
#  bm,aL,ae=(duration,aq,0)
#  ap=False
#  at=g
# elif K=='N' and len(l)==5 and(C in('LOADING','ARMED','PLAY')):
#  w,bn,D=(int(l[2]),int(l[3]),int(l[4]))
#  if w!=ae or w>=aL or len(z)>=48 or(not 0<=bn<bm)or(not 0<=D<4)or(z and bn<z[-1][0]):
#   raise ValueError()
#  z.append([bn,D,0,None])
#  ae+=1
#  at=g
# elif K=='END' and len(l)==2 and(ae==aL):
#  ap=True
# elif K=='ARM' and len(l)==2 and(C=='LOADING')and ae:
#  C='ARMED'
#  o.dr('ready',g)
# elif K=='SYNC' and len(l)==2 and(C=='PLAY')and(not aP):
#  bY=ticks_add(g,2700)
#  aP=True
#  aa('SYNCED',L)
# elif K=='ERROR' and len(l)==2:
#  ak(True)
# else:
#  raise ValueError()
#~
#def dd(line,g):
# global au,aH,bk,T,ao,Z
# l=line.split(',')
# if len(l)==4 and l[:2]==['RH1','ATTACH']and(l[2]==aK)and(len(l[3])==8)and all((an in '0123456789abcdef' for an in l[3])):
#  u=aK+l[3]
#  cm=o.di.dg is None
#  if o.dT(u,g):
#   if cm:
#    au=aH=0
#    bk=-1
#    T=[]
#    ao=0
#    Z=0
#    N[:]=[]
#   aD('RH1','ACCEPT',u)
#  return
# if len(l)<4 or l[0]!='RH1' or l[1]!=o.di.dg:
#  return
# try:
#  aO=int(l[2])
#  if aO==(au-1)%65536:
#   aD('RH1',l[1],'A',aO,'OK')
#   return
#  if aO!=au:
#   return
#  bA(l[3:],g)
#  o.dO(l[1],g)
#  au=(au+1)%65536
#  aD('RH1',l[1],'A',aO,'OK')
# except(ValueError,IndexError):
#  aD('RH1',l[1],'A',l[2],'BAD')
#def bl():
# global aK,bM,bG,bk,bL
# g=ticks_ms()
# cn=o.di.dg is not None
# V=o.dI(g)
# if V or(cn and o.di.dg is None):
#  cj(V)
# if ticks_diff(g,bL)>=1000:
#  gc.collect()
#  bL=g
# if uart.any():
#  for line in bH.dV(uart.read(64)):
#   dd(line,g)
# if N and(N[0][0]!=bk or ticks_diff(g,bG)>=600):
#  aD('RH1',o.di.dg,'E',*N[0])
#  bk=N[0][0]
#  bG=g
# if o.di.dg is None and ticks_diff(g,bM)>=800:
#  aD('RH1','HELLO',aK)
#  bM=g
#def de(g):
# global bP
# if not ap and len(z)<32 and(ticks_diff(g,bP)>=500):
#  aa('NEED',L,ae,44-len(z))
#  bP=g
#~
#def cu(B,m):
# global C,z,M
# F=o.dk==Q
# o.dr('playing',ticks_ms())
# bQ,ct,bJ=(1700,100,210)if F else(3000,220,400)
# duration=bm if F else bv
# C='PLAY'
# G=0
# R=0
# aV=0
# bV=0
# bI=0
# aJ=0
# if not F:
#  z=[]
# aX=None if F else cC()
# if aX:
#  aX.dN()
# bi=None if F else cH()
# bU=0
# aj=False
# bN=[False]*4
# bd=ticks_ms()
# bf=ticks_add(ticks_ms(),-aT)
# bO=ag(ab,ac)
# aI=False
# B.clear()
# B.dh(1,18,126,18)
# B.dh(1,52,126,52)
# B.dL(32,35,10)
# B.show()
# m.hud_combo=None
# bD(m,0,0)
# if F:
#  aa('START',L)
#  ck=ticks_add(ticks_ms(),8000)
#  while not aP:
#   bl()
#   if o.dk!=Q or ticks_diff(ticks_ms(),ck)>=0:
#    ak(True)
#    return
#   sleep(2)
#  aQ=bY
# else:
#  aQ=ticks_add(ticks_ms(),3500)
# display.show('3')
# aF=3
# while True:
#  bl()
#  if F and o.dk!=Q:
#   return
#  g=ticks_ms()
#  W=ag(ab,ac)
#  if W!=-1 and bO==-1:
#   if not aj and W==3:
#    aj=True
#    bU=g
#    o.dr('paused',g)
#    if F:
#     aa('PAUSE',L)
#    else:
#     bi.stop()
#    bg()
#    pin8.write_digital(0)
#    ax(m,'PAUSED',('LS RIGHT RESUME','LS DOWN EXIT'),0,'LS R / LS DOWN')
#    display.show(Image.SQUARE)
#   elif aj and W==1:
#    aj=False
#    aQ=ticks_add(aQ,ticks_diff(g,bU))
#    o.dr('playing',g)
#    if F:
#     aa('RESUME',L)
#    m.hud_combo=None
#    bD(m,G,R)
#    display.show(str(G%10))
#    bf=ticks_add(g,-aT)
#   elif aj and W==2:
#    ak(F)
#    return
#  bO=W
#  if aj:
#   sleep(18)
#   continue
#  H=ticks_diff(g,aQ)
#  if H>=duration+900:
#   break
#  if F:
#   de(g)
#   if not ap and(not any((A[2]==0 for A in z)))and(ticks_diff(g,at)>4000):
#    aa('STARVED',L)
#    ak(True)
#    return
#  else:
#   bi.update(H)
#   aX.dN()
#  if H<0:
#   aY=min(3,max(1,(-H+999)//1000))
#   if aY!=aF:
#    display.show(str(aY))
#    aF=aY
#  elif aF:
#   display.show('0')
#   aF=0
#  if ticks_diff(g,bd)>=0:
#   bg()
#   pin8.write_digital(0)
#  for A in z:
#   if A[2]==0 and H>A[0]+bJ:
#    A[2]=3
#    aJ+=1
#    G=0
#    aI=True
#    bd,bx=co(2,g)
#  for ad in range(4):
#   bC=br[ad].read_digital()==0
#   if bC and(not bN[ad]):
#    aC=None
#    aZ=bJ+1
#    for A in z:
#     X=abs(H-A[0])
#     if A[2]==0 and(F or A[1]==ad)and(X<aZ):
#      aC=A
#      aZ=X
#    if aC is not None:
#     if aC[1]!=ad:
#      t=2
#     elif aZ<=ct:
#      t=0
#     else:
#      t=1
#     bd,bx=co(t,g)
#     if t==2:
#      aC[2]=3
#      aJ+=1
#      G=0
#     else:
#      aC[2]=1 if t==0 else 2
#      if t==0:
#       bV+=1
#       R+=100
#      else:
#       bI+=1
#       R+=50
#      G+=1
#      aV=max(aV,G)
#     aI=True
#   bN[ad]=bC
#  if ticks_diff(g,bf)>=aT:
#   bf=g
#   B.dU()
#   B.dL(32,35,10)
#   aw=128
#   av=-1
#   for A in z:
#    bj=A[3]
#    ay=None
#    if A[2]in(0,3):
#     bE=A[0]-H
#     if bE<=bQ:
#      f=32+bE*91//bQ
#      if f>=-7:
#       ay=f
#       B.dR(f,35,A[1],6)
#      elif A[2]==3:
#       A[2]=5
#    if bj is not None:
#     aw=min(aw,bj-8)
#     av=max(av,bj+8)
#    if ay is not None:
#     aw=min(aw,ay-8)
#     av=max(av,ay+8)
#    A[3]=ay
#   B.dX(aw,av)
#   while z and z[0][0]<H-1600:
#    z.pop(0)
#  if aI:
#   display.show(str(G%10))
#   bD(m,G,R)
#   aI=False
#  sleep(1)
# if F:
#  aa('DONE',L,R,aJ)
# else:
#  bi.stop()
#  M=None
#  gc.collect()
# o.dr('results',ticks_ms())
# bg()
# pin8.write_digital(0)
# B.clear()
# B.dl('FINISH',29,14,2)
# B.show()
# ax(m,'RESULT',('SCORE '+str(R),'BEST '+str(aV),'P'+str(bV)+' G'+str(bI),'MISS '+str(aJ)),0,'LS LEFT MENU')
# U=-1
# while True:
#  bl()
#  if F and o.dk!=Q:
#   return
#  W=ag(ab,ac)
#  if W==3 and U==-1:
#   break
#  U=W
#  sleep(25)
# ak(False)
#~
#for by in br:
# by.set_pull(by.PULL_UP)
#bT()
#i2c.init(freq=400000)
#B=cf(60)
#m=cf(61)
#uart.init(baudrate=115200)
#gc.collect()
#ab=pin0.read_analog()
#ac=pin1.read_analog()
#U=ag(ab,ac)
#bK=ticks_ms()
#~
#while True:
# bl()
# g=ticks_ms()
# D=ag(ab,ac)
# bX=o.dk+C
# if bX!=Y:
#  gc.collect()
#  if C=='MENU':
#   if o.dk==Q:
#    ax(m,'PC SONGS',[cz[1]for cz in T],Z,'LS RIGHT SELECT')
#   else:
#    ax(m,'MEGALOVANIA',('STANDALONE','LS RIGHT START'),0,'P12 SPEAKER')
#   B.clear()
#   B.dl('READY',24,20,2)
#   B.show()
#   display.show(Image.HAPPY)
#  elif C=='LOADING':
#   ax(m,'PC LOADING',('WAIT FOR CHART',),0,'')
#  elif C=='ARMED':
#   ax(m,'PC READY',('LS RIGHT PLAY','LS LEFT CANCEL'),0,'')
#  Y=bX
# if D!=-1 and U==-1 and(ticks_diff(g,bK)>200):
#  bK=g
#  if C=='MENU':
#   if o.dk==Q:
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
#     L=(L+1)%65536
#     o.dr('loading',g)
#     C='LOADING'
#     at=g
#     aa('SELECT',L,Z)
#   elif D==1:
#    cu(B,m)
#    Y=''
#    D=ag(ab,ac)
#  elif C=='ARMED':
#   if D==1:
#    cu(B,m)
#    Y=''
#    D=ag(ab,ac)
#   elif D==3:
#    ak(True)
# if C=='LOADING' and ticks_diff(g,at)>12000:
#  ak(True)
# U=D
# sleep(12)
#~END
