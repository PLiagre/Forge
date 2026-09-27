"""Maillages assemblés en mémoire, UV métriques et niveaux de détail explicites."""
import math
from pathlib import Path
import bpy
import bmesh
from mathutils import Vector

MATS={}
def material(name,texture_root,color=(1,1,1),rough=.85,alpha=False):
    if name in MATS:return MATS[name]
    m=bpy.data.materials.new(name);m.use_nodes=True
    m.diffuse_color=(*color,1)
    bs=m.node_tree.nodes.get('Principled BSDF')
    bs.inputs['Base Color'].default_value=(*color,1)
    bs.inputs['Roughness'].default_value=rough
    m['alpha_clip']=alpha
    m['texture_id']=name
    for suffix,input_name in [('BaseColor','Base Color'),('Normal','Normal')]:
        path=Path(texture_root)/(name+'_'+suffix+'.png')
        if not path.exists():continue
        image=bpy.data.images.load(str(path),check_existing=True)
        image.colorspace_settings.name='sRGB' if suffix=='BaseColor' else 'Non-Color'
        tex=m.node_tree.nodes.new('ShaderNodeTexImage');tex.image=image
        if suffix=='Normal':
            normal=m.node_tree.nodes.new('ShaderNodeNormalMap')
            m.node_tree.links.new(tex.outputs['Color'],normal.inputs['Color'])
            m.node_tree.links.new(normal.outputs[0],bs.inputs[input_name])
        else:
            m.node_tree.links.new(tex.outputs['Color'],bs.inputs[input_name])
            if alpha:m.node_tree.links.new(tex.outputs['Alpha'],bs.inputs['Alpha'])
    MATS[name]=m
    return m

def tri_count(obj):
    obj.data.calc_loop_triangles()
    return len(obj.data.loop_triangles)

class Mesh:
    def __init__(self):
        self.verts=[];self.faces=[];self.materials=[];self.indices=[];self.levels=[];self.uv=[];self.detail=2
    def surface(self,verts,faces,mat,uv=None):
        offset=len(self.verts);self.verts.extend(verts)
        if mat not in self.materials:self.materials.append(mat)
        idx=self.materials.index(mat)
        for face in faces:
            self.faces.append(tuple(i+offset for i in face));self.indices.append(idx);self.levels.append(self.detail)
            if uv is not None:self.uv.append([uv[i] for i in face])
            else:
                a,b,c=[Vector(verts[i]) for i in face[:3]];normal=(b-a).cross(c-a)
                axis=max(range(3),key=lambda i:abs(normal[i]));axes=[i for i in range(3) if i!=axis]
                self.uv.append([(verts[i][axes[0]]/2,verts[i][axes[1]]/2) for i in face])
    def box(self,loc,size,mat,angle=0):
        x,y,z=loc;w,d,h=[v/2 for v in size];c,s=math.cos(angle),math.sin(angle)
        vs=[(x+a*c-b*s,y+a*s+b*c,z+zz) for a,b,zz in [(-w,-d,-h),(w,-d,-h),(w,d,-h),(-w,d,-h),(-w,-d,h),(w,-d,h),(w,d,h),(-w,d,h)]]
        self.surface(vs,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],mat)
    def beam(self,a,b,width,mat,depth=None):
        a,b=Vector(a),Vector(b);delta=b-a;length=delta.length
        if length<1e-5:return
        q=delta.to_track_quat('Z','Y');center=(a+b)/2;d=depth or width
        vs=[tuple(center+q@Vector((x,y,z))) for x,y,z in [(-width/2,-d/2,-length/2),(width/2,-d/2,-length/2),(width/2,d/2,-length/2),(-width/2,d/2,-length/2),(-width/2,-d/2,length/2),(width/2,-d/2,length/2),(width/2,d/2,length/2),(-width/2,d/2,length/2)]]
        self.surface(vs,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],mat)
    def cylinder(self,a,b,r1,r2,mat,n=10):
        a,b=Vector(a),Vector(b);q=(b-a).to_track_quat('Z','Y')
        vs=[tuple(center+q@Vector((r*math.cos(i*math.tau/n),r*math.sin(i*math.tau/n),0))) for center,r in ((a,r1),(b,r2)) for i in range(n)]
        fs=[tuple(reversed(range(n))),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
        self.surface(vs,fs,mat)
    def ico(self,loc,scale,mat,sub=1):
        bm=bmesh.new();bmesh.ops.create_icosphere(bm,subdivisions=sub,radius=1)
        bm.verts.ensure_lookup_table();bm.verts.index_update()
        vs=[tuple(loc[i]+v.co[i]*scale[i] for i in range(3)) for v in bm.verts]
        fs=[tuple(v.index for v in f.verts) for f in bm.faces]
        self.surface(vs,fs,mat);bm.free()
    def foliage_card(self,center,size,rotation,mat):
        q=rotation
        vs=[tuple(Vector(center)+q@Vector((x*size[0],y*size[1],0))) for x,y in [(-.5,-.5),(.5,-.5),(.5,.5),(-.5,.5)]]
        self.surface(vs,[(0,1,2,3)],mat,[(0,0),(1,0),(1,1),(0,1)])
    def object(self,name,lod=0):
        indices=[i for i,level in enumerate(self.levels) if level>=lod]
        mesh=bpy.data.meshes.new(name)
        # Retirer les sommets devenus orphelins au LOD lointain.
        used=sorted({v for i in indices for v in self.faces[i]});mapping={v:i for i,v in enumerate(used)}
        mesh.from_pydata([self.verts[v] for v in used],[],[tuple(mapping[v] for v in self.faces[i]) for i in indices])
        for m in self.materials:mesh.materials.append(m)
        uv=mesh.uv_layers.new(name='UVMap')
        for p,i in zip(mesh.polygons,indices):
            p.material_index=self.indices[i]
            for li,coord in zip(p.loop_indices,self.uv[i]):uv.data[li].uv=coord
        mesh.update()
        o=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(o)
        return o

def export_fbx(path,objects):
    bpy.ops.object.select_all(action='DESELECT')
    originals={o:o.data for o in objects}
    try:
        for o in objects:o.data=o.data.copy();o.select_set(True)
        bpy.context.view_layer.objects.active=objects[0]
        bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'MESH'},
            axis_forward='-Z',axis_up='Y',apply_scale_options='FBX_SCALE_ALL',bake_space_transform=True,
            add_leaf_bones=False,mesh_smooth_type='FACE',path_mode='RELATIVE')
    finally:
        for o,original in originals.items():
            temp=o.data;o.data=original;bpy.data.meshes.remove(temp)
