"""Palette alpine et sol continu, partagés par toutes les graines."""
import numpy as np
from PIL import Image
from local3d.atelier_v2.textures import prepare,save_material,noise,srgb,foliage
from local3d.atelier_v2.plan import path_distance
from .paysage import RECIPE,sample,river_x

def palette(folder):
    prepare(folder)
    save_material(folder,'chalet_wall',[.30,.16,.075],'wood',81)
    save_material(folder,'chalet_timber',[.20,.095,.035],'wood',82)
    save_material(folder,'chalet_roof',[.21,.24,.25],'tiles',83)
    save_material(folder,'chalet_stone',[.43,.42,.36],'stone',84)
    for i,col in enumerate([[.19,.30,.27],[.38,.095,.065],[.28,.32,.37]]):save_material(folder,'volet_'+str(i),col,'wood',90+i)
    for i,col in enumerate([[.82,.54,.10],[.47,.21,.52],[.80,.78,.61]]):save_material(folder,'fleur_'+str(i),col,'plaster',95+i)
    save_material(folder,'eau_alpine',[.065,.25,.245],'leaf',102,roughness=.2)
    save_material(folder,'lumiere',[1,.52,.12],'plaster',103)
    save_material(folder,'linge_0',[.63,.58,.43],'plaster',104)
    save_material(folder,'linge_1',[.31,.25,.18],'plaster',105)
    foliage(folder,'aiguilles_meleze',[.22,.29,.07],106)

def terrain(plan,h,path):
    n=1024;ext=RECIPE['extent_m'];axis=np.linspace(-ext/2,ext/2,n);x,y=np.meshgrid(axis,axis)
    grain=noise(np.random.default_rng(plan['seed']),n);z=sample(h,x,y)
    dy,dx=np.gradient(z,ext/(n-1));slope=np.hypot(dx,dy)
    col=np.ones((n,n,3))*[.20,.275,.09];col*= (.68+grain*.60)[...,None]
    patch=np.clip((grain-.51)*4,0,.35)
    col=col*(1-patch[...,None])+np.array([.36,.29,.12])*patch[...,None]
    rock=np.clip((slope-.40)*1.8+(z-24)/75,0,1)
    col=col*(1-rock[...,None])+np.array([.37,.39,.34])*(.75+grain*.45)[...,None]*rock[...,None]
    wd=abs(x-river_x(y,plan['seed']))-5.8
    shore=np.clip(1-np.maximum(wd,0)/4,0,1)
    col=col*(1-shore[...,None])+np.array([.30,.27,.19])*(.75+grain*.4)[...,None]*shore[...,None]
    d=path_distance(x,y,plan['roads']);cx,cy=plan['center'];d=np.minimum(d,np.hypot(x-cx,y-cy)-9)
    road=np.clip(.7-d+(.5-grain)*1.8,0,1)*np.clip(wd/2,0,1)
    col=col*(1-road[...,None])+np.array([.31,.25,.17])*(.9+grain*.2)[...,None]*road[...,None]
    snow=np.clip((z-55)/14,0,1)*np.clip(1-slope*.35,0,1)
    col=col*(1-snow[...,None])+np.array([.76,.80,.83])*snow[...,None]
    Image.fromarray((srgb(col[::-1])*255).astype(np.uint8)).save(path)
