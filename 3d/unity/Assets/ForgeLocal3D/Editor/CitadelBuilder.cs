using System;
using System.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

namespace ForgeLocal3D
{
    public static class CitadelBuilder
    {
        public const string Root="Assets/ForgeLocal3D/Citadelle";
        public static void Build()=>VillageV2Builder.BuildAt(Root,"../local3d/citadelle/sorties/villages/",true,true);
        public static void ConfigureRenderer(UniversalRendererData renderer,UniversalRenderPipelineAsset pipeline)
        {
            // L'occlusion assombrit les petits contacts à partir de la profondeur rendue.
            var ao=renderer.rendererFeatures.OfType<ScreenSpaceAmbientOcclusion>().FirstOrDefault();
            if(!ao)
            {
                ao=ScriptableObject.CreateInstance<ScreenSpaceAmbientOcclusion>();ao.name="Contacts de la pierre";
                AssetDatabase.AddObjectToAsset(ao,renderer);renderer.rendererFeatures.Add(ao);
            }
            var serialized=new SerializedObject(ao);
            void F(string n,float v)=>serialized.FindProperty("m_Settings."+n).floatValue=v;
            void I(string n,int v)=>serialized.FindProperty("m_Settings."+n).intValue=v;
            I("Source",0);I("NormalSamples",2);I("Samples",0);I("AOMethod",1);
            F("Intensity",1.25f);F("Radius",.75f);F("DirectLightingStrength",.28f);F("Falloff",420);
            serialized.FindProperty("m_Settings.Downsample").boolValue=true;
            serialized.ApplyModifiedPropertiesWithoutUndo();ao.Create();ao.SetActive(true);renderer.SetDirty();
            pipeline.supportsCameraDepthTexture=true;pipeline.maxAdditionalLightsCount=4;
            pipeline.shadowDistance=180;pipeline.mainLightShadowmapResolution=2048;pipeline.shadowCascadeCount=2;
            pipeline.msaaSampleCount=2;pipeline.renderScale=.9f;
            EditorUtility.SetDirty(renderer);EditorUtility.SetDirty(ao);
        }
        static Vector3 P(float[] p)=>new Vector3(-p[0],p[2],-p[1]);
        public static void AddAssetCollision(GameObject go,string id)
        {
            if(id.StartsWith("sapin_"))
            {
                var trunk=go.AddComponent<CapsuleCollider>();trunk.radius=.20f;trunk.height=3;trunk.center=new Vector3(0,1.5f,0);
                go.AddComponent<CitadelTree>();return;
            }
            if(id=="banniere"||id=="garde"||id=="torche"||id=="lucarne_gothique")return;
            // Un seul maillage de collision, indépendant du niveau de détail affiché.
            foreach(var mesh in go.GetComponentsInChildren<MeshFilter>().Where(f=>f.name.EndsWith("_LOD2")))
                mesh.gameObject.AddComponent<MeshCollider>().sharedMesh=mesh.sharedMesh;
        }
        public static void Configure(VillageV2Builder.SceneSpec spec,Camera camera,Light sun,string[] names,string[] labels)
        {
            camera.orthographic=false;camera.fieldOfView=26.4f;camera.farClipPlane=2200;camera.transform.position=P(spec.camera_position);camera.transform.LookAt(P(spec.camera_target));
            var visit=camera.GetComponent<VillageV2Visit>();visit.minPitch=5;visit.focusLimit=330;visit.focus=P(spec.camera_target);visit.distance=Vector3.Distance(camera.transform.position,visit.focus);visit.pitch=camera.transform.eulerAngles.x;visit.yaw=camera.transform.eulerAngles.y;
            var sky=AssetDatabase.LoadAssetAtPath<Material>(Root+"/Settings/Ciel.mat");
            if(!sky){sky=new Material(Shader.Find("Forge/StormSky"));AssetDatabase.CreateAsset(sky,Root+"/Settings/Ciel.mat");}
            var profile=AssetDatabase.LoadAssetAtPath<VolumeProfile>(Root+"/Settings/Ambiance.asset");
            if(!profile)
            {
                profile=ScriptableObject.CreateInstance<VolumeProfile>();AssetDatabase.CreateAsset(profile,Root+"/Settings/Ambiance.asset");
                var tone=profile.Add<Tonemapping>(true);tone.mode.Override(TonemappingMode.ACES);AssetDatabase.AddObjectToAsset(tone,profile);
                var color=profile.Add<ColorAdjustments>(true);color.postExposure.Override(.35f);color.contrast.Override(12);color.saturation.Override(-10);AssetDatabase.AddObjectToAsset(color,profile);
                var bloom=profile.Add<Bloom>(true);bloom.intensity.Override(.24f);bloom.threshold.Override(.9f);AssetDatabase.AddObjectToAsset(bloom,profile);
                var vignette=profile.Add<Vignette>(true);vignette.intensity.Override(.18f);AssetDatabase.AddObjectToAsset(vignette,profile);
            }
            // Les réglages sont réappliqués aussi aux profils existants à la reconstruction.
            if(profile.TryGet<ColorAdjustments>(out var grading))
            {grading.postExposure.Override(.25f);grading.contrast.Override(16);grading.saturation.Override(-8);}
            if(profile.TryGet<Bloom>(out var bloomExisting))
            {bloomExisting.intensity.Override(.18f);bloomExisting.threshold.Override(1.1f);}
            var volume=new GameObject("Ambiance de la citadelle").AddComponent<Volume>();volume.isGlobal=true;volume.sharedProfile=profile;camera.GetUniversalAdditionalCameraData().renderPostProcessing=true;
            var env=new GameObject("Météo et feux").AddComponent<CitadelEnvironment>();env.village=spec.label;env.seed=spec.seed;env.scenes=names;env.labels=labels;env.view=camera;env.sun=sun;env.sky=sky;
            env.viewpoints=spec.cameras.Select(c=>new CitadelEnvironment.Viewpoint{name=c.name,position=P(c.position),target=P(c.target),fieldOfView=2*Mathf.Atan(36f/(2*c.lens)/(1600f/900f))*Mathf.Rad2Deg}).ToArray();
            var snowMat=AlpineBuilder.ParticleMaterial("neige",new Color(.94f,.96f,1,.88f));env.snow=AlpineBuilder.Precipitation("Neige de la citadelle",snowMat,true,env.transform);env.snow.transform.position=new Vector3(0,140,0);
            var shape=env.snow.shape;shape.scale=new Vector3(310,22,330);var main=env.snow.main;main.startLifetime=38;main.maxParticles=24000;main.startSize=new ParticleSystem.MinMaxCurve(.025f,.085f);
            var smokeMat=AlpineBuilder.ParticleMaterial("fumee",new Color(.70f,.75f,.76f,.20f));env.smoke=spec.smokes.Where((s,i)=>i%3==0).Select((p,i)=>AlpineBuilder.Smoke(p.position,smokeMat,env.transform,i)).ToArray();
            var flameMat=AlpineBuilder.ParticleMaterial("flamme",new Color(3,1.7f,.35f,.8f));
            env.fires=spec.torches.Select((p,i)=>
            {
                var light=new GameObject("Torche "+i).AddComponent<Light>();light.transform.position=P(p.position);light.transform.SetParent(env.transform);light.type=LightType.Point;light.color=new Color(1,.50f,.12f);light.intensity=2.6f;light.range=12;return light;
            }).ToArray();
            env.flames=spec.torches.Select((p,i)=>
            {
                var ps=new GameObject("Flamme "+i).AddComponent<ParticleSystem>();ps.transform.SetParent(env.transform);ps.transform.position=P(p.position);ps.Stop(true,ParticleSystemStopBehavior.StopEmittingAndClear);
                var mm=ps.main;mm.startLifetime=.65f;mm.startSpeed=.65f;mm.startSize=new ParticleSystem.MinMaxCurve(.16f,.36f);mm.maxParticles=40;mm.prewarm=true;
                var sh=ps.shape;sh.shapeType=ParticleSystemShapeType.Sphere;sh.radius=.09f;var vel=ps.velocityOverLifetime;vel.enabled=true;vel.y=1.0f;
                var emission=ps.emission;emission.rateOverTime=24;var size=ps.sizeOverLifetime;size.enabled=true;size.size=new ParticleSystem.MinMaxCurve(1,AnimationCurve.Linear(0,1,1,0));
                ps.GetComponent<ParticleSystemRenderer>().sharedMaterial=flameMat;ps.useAutoRandomSeed=false;ps.randomSeed=(uint)(400+i);ps.Play();return ps;
            }).ToArray();
            env.Apply();sun.shadows=LightShadows.Soft;sun.shadowBias=.045f;sun.shadowNormalBias=.22f;
            if(spec.routes==null||spec.routes.Length==0||spec.plots==null||spec.plots.Length==0)
                throw new InvalidOperationException("Parcours ou clairières absents");
            var walk=new GameObject("Marche dans la citadelle et la vallée").AddComponent<CitadelTraversal>();
            walk.view=camera;walk.spawn=P(spec.spawn);walk.forest=P(spec.forest);
            walk.routes=spec.routes.Select(r=>new CitadelTraversal.Route{id=r.id,width=r.width,points=r.points.Select(p=>P(p.position)).ToArray()}).ToArray();
            walk.plots=spec.plots.Select(p=>new CitadelTraversal.Plot{id=p.id,position=P(p.position),size=new Vector2(p.size[0],p.size[1])}).ToArray();
            walk.body=walk.gameObject.AddComponent<CharacterController>();walk.body.height=1.8f;walk.body.radius=.3f;walk.body.center=new Vector3(0,.9f,0);
            walk.body.stepOffset=.32f;walk.body.slopeLimit=42;walk.body.skinWidth=.025f;walk.body.minMoveDistance=0;walk.body.enabled=false;
            // Le décor tiers se pose après les rues et les clairières, qu'il doit laisser libres.
            CitadelDecor.Place(spec,walk);
            CitadelTerrainSample.Apply(spec,walk);
            CitadelArchitecture.Apply();
            CitadelHabitatBuilder.Configure(camera,walk);
            camera.gameObject.AddComponent<CitadelPerformance>();
            CitadelQuality.PrepareScene();
            CitadelDecor.AddForgeView(env);
            EditorUtility.SetDirty(profile);EditorUtility.SetDirty(sky);
        }
        [MenuItem("Forge/Citadelle/Ouvrir la visite")]
        public static void OpenPlay(){EditorSceneManager.OpenScene(Root+"/Scenes/Forge_Citadelle_eperon_des_veilleurs.unity");EditorApplication.ExecuteMenuItem("Window/General/Game");EditorApplication.EnterPlaymode();}
    }
}
