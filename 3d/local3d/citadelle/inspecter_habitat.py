"""Vue de contrôle rapide des volumes, sans réenregistrer les scènes."""
import sys
from pathlib import Path
import bpy
from mathutils import Vector

OUT=Path(__file__).parent/'sorties'
name=sys.argv[sys.argv.index('--')+1]
bpy.ops.wm.open_mainfile(filepath=str(OUT/'villages'/name/(name+'.blend')))
sc=bpy.context.scene;sc.render.engine='BLENDER_WORKBENCH'
sc.display.shading.light='STUDIO';sc.display.shading.color_type='OBJECT'
sc.display.shading.show_shadows=True;sc.display.shading.show_cavity=True;sc.display.shading.cavity_type='BOTH'
sc.render.resolution_x=1200;sc.render.resolution_y=900;sc.render.resolution_percentage=100
sc.render.image_settings.file_format='PNG'
folder=OUT/'diagnostic/habitat';folder.mkdir(parents=True,exist_ok=True)
camera=bpy.data.objects.new('Contrôle des îlots',bpy.data.cameras.new('Contrôle des îlots'));sc.collection.objects.link(camera)
for label,position,target,lens in [('ville',(8,-74,145),(0,1,44),48),('hameau',(-173,-134,115),(-108,-49,14),45)]:
    camera.location=position;camera.rotation_euler=(Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.lens=lens;sc.camera=camera
    sc.render.filepath=str(folder/(name+'_'+label+'.png'));bpy.ops.render.render(write_still=True)
