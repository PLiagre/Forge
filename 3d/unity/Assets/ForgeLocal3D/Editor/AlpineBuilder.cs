using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

namespace ForgeLocal3D
{
    public static class AlpineBuilder
    {
        const string Root="Assets/ForgeLocal3D/Alpin";
        [MenuItem("Forge/Alpin/Reconstruire les dispositions")]
        public static void Build() => VillageV2Builder.BuildAt(Root,"../local3d/alpin/sorties/villages/",true);

        public static void Configure(VillageV2Builder.SceneSpec spec, Camera camera, Light sun, string[] names, string[] labels, Dictionary<string,Material> materials)
        {
            var sky=AssetDatabase.LoadAssetAtPath<Material>(Root+"/Settings/Ciel.mat");
            if (!sky) { sky=new Material(Shader.Find("Skybox/Procedural"));AssetDatabase.CreateAsset(sky,Root+"/Settings/Ciel.mat"); }
            var profile=AssetDatabase.LoadAssetAtPath<VolumeProfile>(Root+"/Settings/Lumiere.asset");
            if (!profile)
            {
                profile=ScriptableObject.CreateInstance<VolumeProfile>();AssetDatabase.CreateAsset(profile,Root+"/Settings/Lumiere.asset");
                var tone=profile.Add<Tonemapping>(true);tone.mode.Override(TonemappingMode.ACES);AssetDatabase.AddObjectToAsset(tone,profile);
                var color=profile.Add<ColorAdjustments>(true);color.postExposure.Override(.15f);color.contrast.Override(8);color.saturation.Override(7);AssetDatabase.AddObjectToAsset(color,profile);
                var bloom=profile.Add<Bloom>(true);bloom.intensity.Override(.24f);bloom.threshold.Override(1);AssetDatabase.AddObjectToAsset(bloom,profile);
            }
            var volume=new GameObject("Lumière et couleurs").AddComponent<Volume>();volume.isGlobal=true;volume.sharedProfile=profile;
            camera.GetUniversalAdditionalCameraData().renderPostProcessing=true;
            camera.clearFlags=CameraClearFlags.SolidColor;
            var env=new GameObject("Atmosphère alpine").AddComponent<AlpineEnvironment>();
            env.village=spec.label;env.culture=spec.culture;env.typologie=spec.typologie;env.seed=spec.seed;env.year=spec.annee;
            env.sun=sun;env.sky=sky;env.view=camera;env.scenes=names;env.labels=labels;
            env.wheels=spec.wheels.Select(n=>GameObject.Find(n).transform).ToArray();
            var smokeMat=ParticleMaterial("fumee",new Color(.70f,.75f,.76f,.20f));
            var rainMat=ParticleMaterial("pluie",new Color(.65f,.77f,.86f,.48f));
            var snowMat=ParticleMaterial("neige",new Color(.94f,.96f,1,.88f));
            env.rain=Precipitation("Pluie",rainMat,false,env.transform);
            env.snow=Precipitation("Neige",snowMat,true,env.transform);
            env.smoke=spec.smokes.Where((s,i)=>i%3==0).Select((point,i)=>Smoke(point.position,smokeMat,env.transform,i)).ToArray();
            env.Apply(true);
            sun.shadowBias=.07f;sun.shadowNormalBias=.35f;
            EditorUtility.SetDirty(sky);EditorUtility.SetDirty(profile);
        }

        public static Material ParticleMaterial(string name, Color color)
        {
            var path=Root+"/Materials/effet_"+name+".mat";var m=AssetDatabase.LoadAssetAtPath<Material>(path);
            if (!m) { m=new Material(Shader.Find("Universal Render Pipeline/Particles/Unlit"));AssetDatabase.CreateAsset(m,path); }
            var texturePath=Root+"/Textures/particule_douce.png";
            if (!File.Exists(texturePath))
            {
                var texture=new Texture2D(64,64,TextureFormat.RGBA32,false);
                for (int y=0;y<64;y++) for(int x=0;x<64;x++)
                { float d=Vector2.Distance(new Vector2(x+.5f,y+.5f),new Vector2(32,32))/32;texture.SetPixel(x,y,new Color(1,1,1,Mathf.Pow(Mathf.Clamp01(1-d),1.8f))); }
                texture.Apply();File.WriteAllBytes(texturePath,texture.EncodeToPNG());UnityEngine.Object.DestroyImmediate(texture);AssetDatabase.ImportAsset(texturePath);
            }
            m.SetTexture("_BaseMap",AssetDatabase.LoadAssetAtPath<Texture2D>(texturePath));m.SetColor("_BaseColor",color);
            m.SetFloat("_Surface",1);m.SetFloat("_Blend",0);m.SetFloat("_SrcBlend",(float)BlendMode.SrcAlpha);m.SetFloat("_DstBlend",(float)BlendMode.OneMinusSrcAlpha);m.SetFloat("_ZWrite",0);m.SetFloat("_Cull",0);
            m.EnableKeyword("_SURFACE_TYPE_TRANSPARENT");m.renderQueue=3000;EditorUtility.SetDirty(m);return m;
        }

        public static ParticleSystem Precipitation(string name,Material material,bool snow,Transform parent)
        {
            var ps=new GameObject(name).AddComponent<ParticleSystem>();ps.transform.SetParent(parent);ps.transform.position=new Vector3(0,55,0);ps.Stop(true,ParticleSystemStopBehavior.StopEmittingAndClear);
            var main=ps.main;main.loop=true;main.prewarm=false;main.startLifetime=snow?18:2.5f;main.startSpeed=0;main.startSize=snow?.23f:.075f;main.maxParticles=20000;main.simulationSpace=ParticleSystemSimulationSpace.World;
            var emission=ps.emission;emission.rateOverTime=0;
            var shape=ps.shape;shape.enabled=true;shape.shapeType=ParticleSystemShapeType.Box;shape.scale=new Vector3(220,18,210);
            var velocity=ps.velocityOverLifetime;velocity.enabled=true;velocity.space=ParticleSystemSimulationSpace.World;velocity.x=snow?-.9f:-3.5f;velocity.y=snow?-3.8f:-28;velocity.z=.25f;
            var noise=ps.noise;noise.enabled=snow;noise.strength=.65f;noise.frequency=.2f;
            var r=ps.GetComponent<ParticleSystemRenderer>();r.sharedMaterial=material;r.renderMode=snow?ParticleSystemRenderMode.Billboard:ParticleSystemRenderMode.Stretch;r.lengthScale=snow?1:13;r.velocityScale=snow?0:.06f;
            ps.useAutoRandomSeed=false;ps.randomSeed=snow?511u:512u;return ps;
        }

        public static ParticleSystem Smoke(float[] position,Material material,Transform parent,int i)
        {
            var ps=new GameObject("Fumée cheminée "+i).AddComponent<ParticleSystem>();ps.transform.SetParent(parent);ps.transform.position=new Vector3(-position[0],position[2],-position[1]);ps.Stop(true,ParticleSystemStopBehavior.StopEmittingAndClear);
            var main=ps.main;main.loop=true;main.prewarm=true;main.startLifetime=7;main.startSpeed=.35f;main.startSize=new ParticleSystem.MinMaxCurve(.45f,.8f);main.maxParticles=80;main.simulationSpace=ParticleSystemSimulationSpace.World;
            var emission=ps.emission;emission.rateOverTime=4;
            var shape=ps.shape;shape.enabled=true;shape.shapeType=ParticleSystemShapeType.Sphere;shape.radius=.12f;
            var velocity=ps.velocityOverLifetime;velocity.enabled=true;velocity.space=ParticleSystemSimulationSpace.World;velocity.x=-.3f;velocity.y=1.0f;velocity.z=.1f;
            var size=ps.sizeOverLifetime;size.enabled=true;size.size=new ParticleSystem.MinMaxCurve(1,AnimationCurve.Linear(0,.65f,1,3.8f));
            var color=ps.colorOverLifetime;color.enabled=true;var gradient=new Gradient();gradient.SetKeys(new[]{new GradientColorKey(Color.white,0),new GradientColorKey(Color.white,1)},new[]{new GradientAlphaKey(0,0),new GradientAlphaKey(.7f,.15f),new GradientAlphaKey(0,1)});color.color=gradient;
            var noise=ps.noise;noise.enabled=true;noise.strength=.25f;noise.frequency=.3f;
            ps.GetComponent<ParticleSystemRenderer>().sharedMaterial=material;ps.useAutoRandomSeed=false;ps.randomSeed=(uint)(800+i);return ps;
        }

        [MenuItem("Forge/Alpin/Ouvrir Combe du Moulin")]
        public static void Open()
        {
            EditorSceneManager.OpenScene(Root+"/Scenes/Forge_Alpin_combe_du_moulin.unity");
            if (SceneView.lastActiveSceneView) SceneView.lastActiveSceneView.LookAt(new Vector3(-14,8,12),Quaternion.Euler(33,143,0),130);
        }
        [MenuItem("Forge/Alpin/Lancer la visite")]
        public static void OpenPlay()
        {
            Open();EditorApplication.ExecuteMenuItem("Window/General/Game");EditorApplication.EnterPlaymode();
        }
    }
}
