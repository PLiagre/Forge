using System;
using System.IO;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;
using UnityEngine.SceneManagement;

namespace ForgeLocal3D
{
    // Contrôle dans le véritable mode Play, avec captures des effets à plusieurs instants.
    [InitializeOnLoad]
    public static class AlpinePlayCheck
    {
        const string Flag="Forge.Alpin.PlayCheck";
        const string Folder="../local3d/alpin/sorties/visite/";
        static int phase, frame, lastFrame=-1, waiting;
        static double next;
        static AlpineEnvironment env;
        static Quaternion initialWheel;
        static float rotation;
        static int rainCount,snowCount;
        static readonly string[] states={"clair","soir","couvert","brume","pluie","neige"};
        static readonly int[] weather={0,0,1,2,3,4};
        static readonly float[] hours={16.3f,20.1f,13,11,14,11};
        [Serializable] public class Result
        {
            public string status="valide";
            public bool mode_play=true, changement_disposition, fenetres_eclairees;
            public float roue_degres;
            public int gouttes, flocons, images_animation;
        }
        static AlpinePlayCheck() { EditorApplication.update+=Tick; }

        public static void Start()
        {
            Directory.CreateDirectory(Folder);Directory.CreateDirectory(Folder+"frames");
            EditorSceneManager.OpenScene("Assets/ForgeLocal3D/Alpin/Scenes/Forge_Alpin_combe_du_moulin.unity");
            SessionState.SetBool(Flag,true);
            EditorApplication.EnterPlaymode();
        }

        static void Tick()
        {
            if (!SessionState.GetBool(Flag,false) || !Application.isPlaying) return;
            try
            {
                if (Time.frameCount==lastFrame) return;lastFrame=Time.frameCount;
                if (!env)
                {
                    env=UnityEngine.Object.FindFirstObjectByType<AlpineEnvironment>();
                    if (!env)return;
                    if (phase==0)
                    {
                        env.view.GetComponent<VillageV2Visit>().enabled=false;env.showPanel=false;
                        env.view.transform.position=new Vector3(-99,100,145);env.view.transform.LookAt(new Vector3(-16,6,12));env.view.orthographicSize=55;
                        initialWheel=env.wheels[0].localRotation;next=EditorApplication.timeSinceStartup+1.5;phase=1;
                    }
                }
                if (phase==1 && EditorApplication.timeSinceStartup>=next)
                {
                    rotation=Quaternion.Angle(initialWheel,env.wheels[0].localRotation);
                    if(rotation<5)throw new InvalidOperationException("La roue reste immobile en Play");
                    phase=2;frame=0;waiting=0;
                }
                if(phase==2)
                {
                    if(waiting==0)
                    {
                        env.rain.Clear();env.snow.Clear();env.SetWeather(weather[frame],hours[frame]);
                        if(weather[frame]==3){env.rain.Simulate(1.8f,true,true,false);env.rain.Play();}
                        if(weather[frame]==4){env.snow.Simulate(13,true,true,false);env.snow.Play();}
                        foreach(var smoke in env.smoke){smoke.Simulate(4,true,true,false);smoke.Play();}
                    }
                    waiting++;
                    if(waiting<8)return;
                    if(weather[frame]==3)rainCount=env.rain.particleCount;
                    if(weather[frame]==4)snowCount=env.snow.particleCount;
                    Capture(env.view,Folder+states[frame]+".png",1600,1050);
                    Debug.Log("ALPIN_METEO_CAPTURE "+states[frame]);
                    frame++;waiting=0;
                    if(frame==states.Length)
                    {
                        if(rainCount==0||snowCount==0)throw new InvalidOperationException("Précipitations sans particules");
                        phase=3;frame=0;Time.captureFramerate=24;
                        var wheel=env.wheels[0].position;
                        env.view.transform.position=wheel+new Vector3(38,24,40);env.view.transform.LookAt(wheel+new Vector3(-4,2,0));env.view.orthographicSize=19;
                        env.SetWeather(0,16.3f);env.rain.Clear();env.snow.Clear();
                    }
                    return;
                }
                if(phase==3)
                {
                    if(frame==96){env.SetWeather(3,14);env.rain.Simulate(1.8f,true,true,false);env.rain.Play();}
                    if(frame==192){env.SetWeather(4,11);env.rain.Clear();env.snow.Simulate(13,true,true,false);env.snow.Play();}
                    Capture(env.view,Folder+"frames/image_"+frame.ToString("D4")+".png",960,630);frame++;
                    if(frame>=288){Time.captureFramerate=0;phase=4;frame=0;SceneManager.LoadScene(env.scenes[1]);env=null;waiting=0;}
                    return;
                }
                if(phase==4)
                {
                    waiting++;if(waiting<15)return;
                    if(env.seed!=8249)throw new InvalidOperationException("Changement de disposition sans nouvelle graine");
                    env.SetWeather(0,16.3f);Capture(env.view,Folder+"disposition_8249.png",1600,1050);
                    SceneManager.LoadScene(env.scenes[2]);env=null;waiting=0;phase=5;return;
                }
                if(phase==5)
                {
                    waiting++;if(waiting<15)return;
                    if(env.seed!=9359)throw new InvalidOperationException("Troisième disposition absente");
                    env.SetWeather(0,16.3f);Capture(env.view,Folder+"disposition_9359.png",1600,1050);
                    env.SetWeather(0,21);bool glow=Shader.GetGlobalFloat("_AlpineNight")>.2f;
                    if(!glow)throw new InvalidOperationException("Éclairage nocturne absent");
                    var result=new Result{roue_degres=rotation,gouttes=rainCount,flocons=snowCount,images_animation=288,changement_disposition=true,fenetres_eclairees=glow};
                    File.WriteAllText(Folder+"verification-play.json",JsonUtility.ToJson(result,true));
                    Debug.Log("ALPIN_PLAY_OK "+JsonUtility.ToJson(result));SessionState.SetBool(Flag,false);EditorApplication.Exit(0);
                }
            }
            catch(Exception exc){Debug.LogException(exc);SessionState.SetBool(Flag,false);EditorApplication.Exit(1);}
        }

        static void Capture(Camera camera,string path,int width,int height)
        {
            var target=new RenderTexture(width,height,24,RenderTextureFormat.ARGB32){antiAliasing=4};target.Create();
            RenderPipeline.SubmitRenderRequest(camera,new UniversalRenderPipeline.SingleCameraRequest{destination=target});
            var old=RenderTexture.active;RenderTexture.active=target;var texture=new Texture2D(width,height,TextureFormat.RGB24,false);
            texture.ReadPixels(new Rect(0,0,width,height),0,0);texture.Apply();File.WriteAllBytes(path,texture.EncodeToPNG());
            RenderTexture.active=old;UnityEngine.Object.DestroyImmediate(texture);target.Release();UnityEngine.Object.DestroyImmediate(target);
        }
    }
}
