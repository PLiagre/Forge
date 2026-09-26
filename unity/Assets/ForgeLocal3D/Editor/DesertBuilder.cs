using System;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

namespace ForgeLocal3D
{
    // Le ksar du désert : même chaîne que la citadelle (catalogue, prefabs à trois LOD,
    // manifeste Blender, marche), avec son ciel, sa lumière et son vent de sable.
    public static class DesertBuilder
    {
        public const string Root="Assets/ForgeLocal3D/Desert";
        public static void Build()=>VillageV2Builder.BuildAt(Root,"../local3d/desert/sorties/villages/",true,false,true);
        static Vector3 P(float[] p)=>new Vector3(-p[0],p[2],-p[1]);

        public static void ConfigureMaterial(Material m,string name,Texture2D gloss)
        {
            bool foliage=name=="palme"||name=="palme_seche"||name=="feuillage_acacia";
            m.SetFloat("_Wind",foliage?1:0);
            m.SetFloat("_WindHeight",name=="feuillage_acacia"?6:12);
            m.SetFloat("_Foliage",0);
            m.SetFloat("_Banner",name=="tissu_etendard"?1:0);
            m.SetFloat("_SnowFactor",0);m.SetFloat("_SnowBase",0);
            m.SetColor("_EmissionColor",name=="lumiere"?new Color(1.5f,.72f,.28f):Color.black);
            m.SetFloat("_BumpScale",name.StartsWith("bois_")||name.StartsWith("tissu_")?.2f:name.StartsWith("sable")||name.StartsWith("dune_")?.55f:.4f);
            m.SetFloat("_Weathering",name=="pise"||name=="pise_clair"||name=="enduit_pise"||name=="brique_crue"?.12f:0);
            m.SetFloat("_HasGlossMap",gloss?1:0);
            m.SetFloat("_Metallic",name=="fer_noir"?.8f:name=="cuivre"?.7f:0);
        }

        public static void AddAssetCollision(GameObject go,string id)
        {
            if(id.StartsWith("palmier_")||id.StartsWith("acacia_"))
            {
                var trunk=go.AddComponent<CapsuleCollider>();trunk.radius=id.StartsWith("palmier_")?.3f:.22f;trunk.height=3;trunk.center=new Vector3(0,1.5f,0);return;
            }
            // Les petites pièces laissent passer ; les dunes lointaines n'ont pas besoin de sol.
            if(id=="etendard"||id=="garde"||id=="lanterne"||id=="dalles"||id=="souk_velum"||id.StartsWith("dune_")||id.StartsWith("butte_"))return;
            foreach(var mesh in go.GetComponentsInChildren<MeshFilter>().Where(f=>f.name.EndsWith("_LOD2")))
                mesh.gameObject.AddComponent<MeshCollider>().sharedMesh=mesh.sharedMesh;
        }

        public static Material ParticleMaterial(string name,Color color)
        {
            var path=Root+"/Materials/effet_"+name+".mat";var m=AssetDatabase.LoadAssetAtPath<Material>(path);
            if(!m){m=new Material(Shader.Find("Universal Render Pipeline/Particles/Unlit"));AssetDatabase.CreateAsset(m,path);}
            var texturePath=Root+"/Textures/particule_douce.png";
            if(!File.Exists(texturePath))
            {
                var texture=new Texture2D(64,64,TextureFormat.RGBA32,false);
                for(int y=0;y<64;y++)for(int x=0;x<64;x++)
                {float d=Vector2.Distance(new Vector2(x+.5f,y+.5f),new Vector2(32,32))/32;texture.SetPixel(x,y,new Color(1,1,1,Mathf.Pow(Mathf.Clamp01(1-d),1.8f)));}
                texture.Apply();File.WriteAllBytes(texturePath,texture.EncodeToPNG());UnityEngine.Object.DestroyImmediate(texture);AssetDatabase.ImportAsset(texturePath);
            }
            m.SetTexture("_BaseMap",AssetDatabase.LoadAssetAtPath<Texture2D>(texturePath));m.SetColor("_BaseColor",color);
            m.SetFloat("_Surface",1);m.SetFloat("_Blend",0);m.SetFloat("_SrcBlend",(float)BlendMode.SrcAlpha);m.SetFloat("_DstBlend",(float)BlendMode.OneMinusSrcAlpha);m.SetFloat("_ZWrite",0);m.SetFloat("_Cull",0);
            m.EnableKeyword("_SURFACE_TYPE_TRANSPARENT");m.renderQueue=3000;EditorUtility.SetDirty(m);return m;
        }

        // Vent de sable : grains étirés filant à l'horizontale, voiles plus lents en hauteur.
        static ParticleSystem SandStorm(Material grains,Transform parent)
        {
            var ps=new GameObject("Vent de sable").AddComponent<ParticleSystem>();ps.transform.SetParent(parent);ps.transform.position=new Vector3(30,12,20);
            ps.Stop(true,ParticleSystemStopBehavior.StopEmittingAndClear);
            var main=ps.main;main.loop=true;main.prewarm=false;main.startLifetime=9;main.startSpeed=0;main.startSize=new ParticleSystem.MinMaxCurve(.03f,.09f);
            main.maxParticles=26000;main.simulationSpace=ParticleSystemSimulationSpace.World;
            var emission=ps.emission;emission.rateOverTime=0;
            var shape=ps.shape;shape.enabled=true;shape.shapeType=ParticleSystemShapeType.Box;shape.scale=new Vector3(330,26,330);
            var velocity=ps.velocityOverLifetime;velocity.enabled=true;velocity.space=ParticleSystemSimulationSpace.World;
            velocity.x=new ParticleSystem.MinMaxCurve(-24,-15);velocity.y=new ParticleSystem.MinMaxCurve(-.6f,.9f);velocity.z=new ParticleSystem.MinMaxCurve(-6,-2);
            var noise=ps.noise;noise.enabled=true;noise.strength=1.4f;noise.frequency=.12f;
            var r=ps.GetComponent<ParticleSystemRenderer>();r.sharedMaterial=grains;r.renderMode=ParticleSystemRenderMode.Stretch;r.lengthScale=7;r.velocityScale=.05f;
            ps.useAutoRandomSeed=false;ps.randomSeed=733;return ps;
        }
        static ParticleSystem DustVeil(Material veil,Transform parent)
        {
            var ps=new GameObject("Voiles de poussière").AddComponent<ParticleSystem>();ps.transform.SetParent(parent);ps.transform.position=new Vector3(30,8,20);
            ps.Stop(true,ParticleSystemStopBehavior.StopEmittingAndClear);
            var main=ps.main;main.loop=true;main.startLifetime=14;main.startSpeed=0;main.startSize=new ParticleSystem.MinMaxCurve(14,32);main.maxParticles=700;main.simulationSpace=ParticleSystemSimulationSpace.World;
            main.startRotation=new ParticleSystem.MinMaxCurve(0,Mathf.PI*2);
            var emission=ps.emission;emission.rateOverTime=0;
            var shape=ps.shape;shape.enabled=true;shape.shapeType=ParticleSystemShapeType.Box;shape.scale=new Vector3(360,14,360);
            var velocity=ps.velocityOverLifetime;velocity.enabled=true;velocity.space=ParticleSystemSimulationSpace.World;velocity.x=-9;velocity.y=.3f;velocity.z=-2.5f;
            var color=ps.colorOverLifetime;color.enabled=true;var gradient=new Gradient();
            gradient.SetKeys(new[]{new GradientColorKey(Color.white,0),new GradientColorKey(Color.white,1)},new[]{new GradientAlphaKey(0,0),new GradientAlphaKey(1,.3f),new GradientAlphaKey(0,1)});color.color=gradient;
            ps.GetComponent<ParticleSystemRenderer>().sharedMaterial=veil;ps.useAutoRandomSeed=false;ps.randomSeed=734;return ps;
        }

        public static void Configure(VillageV2Builder.SceneSpec spec,Camera camera,Light sun,string[] names,string[] labels)
        {
            camera.orthographic=false;camera.fieldOfView=26.4f;camera.farClipPlane=2200;camera.transform.position=P(spec.camera_position);camera.transform.LookAt(P(spec.camera_target));
            var visit=camera.GetComponent<VillageV2Visit>();visit.minPitch=5;visit.focusLimit=330;visit.focus=P(spec.camera_target);visit.distance=Vector3.Distance(camera.transform.position,visit.focus);visit.pitch=camera.transform.eulerAngles.x;visit.yaw=camera.transform.eulerAngles.y;
            var sky=AssetDatabase.LoadAssetAtPath<Material>(Root+"/Settings/Ciel.mat");
            if(!sky){sky=new Material(Shader.Find("Forge/DesertSky"));AssetDatabase.CreateAsset(sky,Root+"/Settings/Ciel.mat");}
            sky.shader=Shader.Find("Forge/DesertSky");
            var profile=AssetDatabase.LoadAssetAtPath<VolumeProfile>(Root+"/Settings/Ambiance.asset");
            if(!profile)
            {
                profile=ScriptableObject.CreateInstance<VolumeProfile>();AssetDatabase.CreateAsset(profile,Root+"/Settings/Ambiance.asset");
                AssetDatabase.AddObjectToAsset(profile.Add<Tonemapping>(true),profile);AssetDatabase.AddObjectToAsset(profile.Add<ColorAdjustments>(true),profile);
                AssetDatabase.AddObjectToAsset(profile.Add<Bloom>(true),profile);AssetDatabase.AddObjectToAsset(profile.Add<Vignette>(true),profile);
                AssetDatabase.AddObjectToAsset(profile.Add<WhiteBalance>(true),profile);
            }
            // Les réglages sont réappliqués à chaque reconstruction, profil existant compris.
            if(profile.TryGet<Tonemapping>(out var tone))tone.mode.Override(TonemappingMode.ACES);
            if(profile.TryGet<ColorAdjustments>(out var grading)){grading.postExposure.Override(.05f);grading.contrast.Override(14);grading.saturation.Override(6);}
            if(profile.TryGet<Bloom>(out var bloom)){bloom.intensity.Override(.2f);bloom.threshold.Override(1.05f);}
            if(profile.TryGet<Vignette>(out var vignette))vignette.intensity.Override(.2f);
            if(profile.TryGet<WhiteBalance>(out var balance)){balance.temperature.Override(8);balance.tint.Override(2);}
            var volume=new GameObject("Ambiance du désert").AddComponent<Volume>();volume.isGlobal=true;volume.sharedProfile=profile;camera.GetUniversalAdditionalCameraData().renderPostProcessing=true;
            var env=new GameObject("Soleil, vent et lanternes").AddComponent<DesertEnvironment>();env.village=spec.label;env.seed=spec.seed;env.scenes=names;env.labels=labels;env.view=camera;env.sun=sun;env.sky=sky;
            env.viewpoints=spec.cameras.Select(c=>new DesertEnvironment.Viewpoint{name=c.name,position=P(c.position),target=P(c.target),fieldOfView=2*Mathf.Atan(36f/(2*c.lens)/(1600f/900f))*Mathf.Rad2Deg}).ToArray();
            env.sand=SandStorm(ParticleMaterial("sable",new Color(.93f,.74f,.52f,.75f)),env.transform);
            env.veil=DustVeil(ParticleMaterial("poussiere",new Color(.86f,.66f,.46f,.10f)),env.transform);
            var smokeMat=ParticleMaterial("fumee",new Color(.72f,.70f,.66f,.18f));
            env.smoke=spec.smokes.Where((s,i)=>i%4==0).Select((p,i)=>AlpineBuilder.Smoke(p.position,smokeMat,env.transform,i)).ToArray();
            var flameMat=ParticleMaterial("flamme",new Color(3,1.6f,.4f,.8f));
            env.fires=spec.torches.Select((p,i)=>
            {
                var light=new GameObject("Lanterne "+i).AddComponent<Light>();light.transform.position=P(p.position);light.transform.SetParent(env.transform);light.type=LightType.Point;light.color=new Color(1,.58f,.22f);light.intensity=2.2f;light.range=11;return light;
            }).ToArray();
            env.flames=spec.torches.Select((p,i)=>
            {
                var ps=new GameObject("Flamme "+i).AddComponent<ParticleSystem>();ps.transform.SetParent(env.transform);ps.transform.position=P(p.position);ps.Stop(true,ParticleSystemStopBehavior.StopEmittingAndClear);
                var mm=ps.main;mm.startLifetime=.5f;mm.startSpeed=.25f;mm.startSize=new ParticleSystem.MinMaxCurve(.08f,.16f);mm.maxParticles=20;mm.prewarm=true;
                var sh=ps.shape;sh.shapeType=ParticleSystemShapeType.Sphere;sh.radius=.04f;var vel=ps.velocityOverLifetime;vel.enabled=true;vel.y=.35f;
                var emission=ps.emission;emission.rateOverTime=18;var size=ps.sizeOverLifetime;size.enabled=true;size.size=new ParticleSystem.MinMaxCurve(1,AnimationCurve.Linear(0,1,1,0));
                ps.GetComponent<ParticleSystemRenderer>().sharedMaterial=flameMat;ps.useAutoRandomSeed=false;ps.randomSeed=(uint)(600+i);ps.Play();return ps;
            }).ToArray();
            env.Apply();sun.shadows=LightShadows.Soft;sun.shadowBias=.045f;sun.shadowNormalBias=.22f;
            if(spec.routes==null||spec.routes.Length==0||spec.plots==null||spec.plots.Length==0)
                throw new InvalidOperationException("Parcours ou jardins absents");
            var walk=new GameObject("Marche dans le ksar et l'oasis").AddComponent<CitadelTraversal>();
            walk.view=camera;walk.spawn=P(spec.spawn);walk.forest=P(spec.forest);
            walk.routes=spec.routes.Select(r=>new CitadelTraversal.Route{id=r.id,width=r.width,points=r.points.Select(p=>P(p.position)).ToArray()}).ToArray();
            walk.plots=spec.plots.Select(p=>new CitadelTraversal.Plot{id=p.id,position=P(p.position),size=new Vector2(p.size[0],p.size[1])}).ToArray();
            walk.body=walk.gameObject.AddComponent<CharacterController>();walk.body.height=1.8f;walk.body.radius=.3f;walk.body.center=new Vector3(0,.9f,0);
            walk.body.stepOffset=.32f;walk.body.slopeLimit=42;walk.body.skinWidth=.025f;walk.body.minMoveDistance=0;walk.body.enabled=false;
            DesertDecor.Place(spec,walk);
            EditorUtility.SetDirty(profile);EditorUtility.SetDirty(sky);
        }

        [MenuItem("Forge/Désert/Reconstruire le ksar")]
        public static void BuildMenu()=>Build();
        [MenuItem("Forge/Désert/Ouvrir la visite")]
        public static void OpenPlay(){EditorSceneManager.OpenScene(Root+"/Scenes/Forge_Desert_ksar_des_sept_puits.unity");EditorApplication.ExecuteMenuItem("Window/General/Game");EditorApplication.EnterPlaymode();}
    }
}
