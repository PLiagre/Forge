using System;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace ForgeLocal3D
{
    // Captures de la scène réellement chargée en Play : ambiances, cadrages, vidéo, changement de disposition.
    [InitializeOnLoad]
    public static class DesertPlayCheck
    {
        const string Flag="Forge.Desert.PlayCheck";
        const string Folder="../local3d/desert/sorties/visite/";
        static int phase,frame,last=-1,wait,sandCount,flameCount;
        static DesertEnvironment env;
        static float firstFire,fireDelta;
        static int firstSeed;static string expectedScene;
        static Color32[] initialPixels;
        static int changedPixels;
        [Serializable] public class Result
        {
            public string status="valide";
            public bool mode_play=true,changement_disposition;
            public int grains_de_sable,particules_flammes,images_animation,pixels_changes_camera_fixe;
            public float variation_lumiere_lanterne;
        }
        static DesertPlayCheck(){EditorApplication.update+=Tick;}
        public static void Start()
        {
            phase=0;frame=0;last=-1;wait=0;sandCount=0;flameCount=0;
            env=null;firstFire=0;fireDelta=0;initialPixels=null;changedPixels=0;
            Directory.CreateDirectory(Folder+"frames");
            foreach(var old in Directory.GetFiles(Folder+"frames","image_*.png"))File.Delete(old);
            EditorSceneManager.OpenScene(DesertBuilder.Root+"/Scenes/Forge_Desert_ksar_des_sept_puits.unity");SessionState.SetBool(Flag,true);EditorApplication.EnterPlaymode();
        }
        static void Capture(string name)=>CitadelPlayCheck.Capture(env.view,Folder+name+".png",1600,900);
        static void Tick()
        {
            if(!SessionState.GetBool(Flag,false)||!Application.isPlaying||last==Time.frameCount)return;last=Time.frameCount;
            try
            {
                if(!env)
                {
                    env=UnityEngine.Object.FindFirstObjectByType<DesertEnvironment>();if(!env)return;
                    env.showPanel=false;env.view.GetComponent<VillageV2Visit>().enabled=false;
                    if(phase==0)
                    {
                        env.hour=17;env.weather=0;env.Apply();
                        foreach(var ps in env.smoke){ps.Simulate(4,true,true,false);ps.Play();}
                        phase=1;wait=0;
                    }
                }
                if(phase==1)
                {
                    if(++wait<10)return;Capture("soleil");
                    env.weather=1;env.hour=18.4f;env.Apply();env.sand.Simulate(8,true,true,false);env.sand.Play();env.veil.Simulate(10,true,true,false);env.veil.Play();
                    firstFire=env.fires[0].intensity;phase=2;wait=0;return;
                }
                if(phase==2)
                {
                    wait++;fireDelta=Mathf.Max(fireDelta,Mathf.Abs(env.fires[0].intensity-firstFire));
                    if(wait<20)return;
                    sandCount=env.sand.particleCount;flameCount=env.flames.Sum(p=>p.particleCount);
                    if(sandCount==0||flameCount==0||fireDelta<.05f)throw new InvalidOperationException("Effets immobiles ou vides en Play");
                    Capture("vent_de_sable");env.weather=0;env.sand.Clear();env.veil.Clear();env.hour=17;env.Apply();phase=3;wait=0;return;
                }
                if(phase==3)
                {
                    if(++wait<10)return;
                    var position=env.view.transform.position;var rotation=env.view.transform.rotation;float fov=env.view.fieldOfView;
                    if(env.viewpoints==null||env.viewpoints.Length==0)throw new InvalidOperationException("Cadrages de visite absents");
                    foreach(string name in new[]{"Passage","Parvis","Souk","Oasis"})
                    {
                        var point=env.viewpoints.First(p=>p.name==name);env.ShowView(name);
                        if(Vector3.Distance(env.view.transform.position,point.position)>.001f)throw new InvalidOperationException("Cadrage de visite inaccessible : "+name);
                        Capture(name.ToLowerInvariant());
                    }
                    env.view.transform.SetPositionAndRotation(position,rotation);env.view.fieldOfView=fov;
                    env.hour=18.7f;env.Apply();phase=4;wait=0;return;
                }
                if(phase==4)
                {
                    if(++wait<10)return;Capture("crepuscule");env.hour=21.5f;env.Apply();phase=5;wait=0;return;
                }
                if(phase==5)
                {
                    if(++wait<10)return;Capture("nuit");env.hour=16.5f;env.weather=2;env.Apply();phase=6;wait=0;return;
                }
                if(phase==6)
                {
                    if(++wait<10)return;Capture("brume");env.weather=1;env.hour=17.4f;env.Apply();env.sand.Simulate(8,true,true,false);env.sand.Play();
                    phase=7;frame=0;Time.captureFramerate=24;
                    env.view.transform.position=new Vector3(-57,65,139);env.view.transform.LookAt(new Vector3(0,52,3));return;
                }
                if(phase==7)
                {
                    // Une seconde à caméra fixe pour mesurer une animation réelle dans les pixels.
                    if(frame>=24){float t=(frame-24)/168f;env.view.transform.position=Vector3.Lerp(new Vector3(-57,65,139),new Vector3(-91,86,176),t);env.view.transform.LookAt(new Vector3(0,55,-3));}
                    var pixels=CitadelPlayCheck.Capture(env.view,Folder+"frames/image_"+frame.ToString("D4")+".png",1280,720);
                    if(frame==0)initialPixels=pixels;
                    if(frame==23)
                    {
                        changedPixels=pixels.Where((p,i)=>Mathf.Abs(p.r-initialPixels[i].r)+Mathf.Abs(p.g-initialPixels[i].g)+Mathf.Abs(p.b-initialPixels[i].b)>30).Count();
                        if(changedPixels<100)throw new InvalidOperationException("L'image animée reste identique à caméra fixe");
                    }
                    frame++;
                    if(frame==192){Time.captureFramerate=0;phase=8;wait=0;firstSeed=env.seed;expectedScene=env.scenes[1];SceneManager.LoadScene(expectedScene);env=null;}return;
                }
                if(phase==8)
                {
                    if(++wait<20)return;
                    // Référence dérivée de la scène quittée : autre graine, scène annoncée par la première.
                    if(env.seed==firstSeed||SceneManager.GetActiveScene().name!=expectedScene)throw new InvalidOperationException("La deuxième disposition n'est pas chargée");
                    env.weather=0;env.hour=17;env.Apply();env.sand.Clear();Capture(expectedScene.Replace("Forge_Desert_",""));
                    var result=new Result{changement_disposition=true,grains_de_sable=sandCount,particules_flammes=flameCount,variation_lumiere_lanterne=fireDelta,images_animation=192,pixels_changes_camera_fixe=changedPixels};
                    File.WriteAllText(Folder+"verification-play.json",JsonUtility.ToJson(result,true));Debug.Log("DESERT_PLAY_OK "+JsonUtility.ToJson(result));SessionState.SetBool(Flag,false);CitadelEditorBridge.Finish(0);
                }
            }
            catch(Exception e){Debug.LogException(e);SessionState.SetBool(Flag,false);CitadelEditorBridge.Finish(1);}
        }
    }
}
