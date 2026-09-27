using System;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;
using UnityEngine.SceneManagement;

namespace ForgeLocal3D
{
    // Captures de la scène réellement chargée en Play, puis changement de disposition.
    [InitializeOnLoad]
    public static class CitadelPlayCheck
    {
        const string Flag="Forge.Citadelle.PlayCheck";
        const string Folder="../local3d/citadelle/sorties/visite/";
        static int phase,frame,last=-1,wait,snowCount,flameCount;
        static CitadelEnvironment env;
        static float firstFire,fireDelta;
        static Color32[] initialPixels;
        static int changedPixels;
        [Serializable] public class Result
        {
            public string status="valide";
            public bool mode_play=true, changement_disposition;
            public int flocons,particules_flammes,images_animation,pixels_changes_camera_fixe;
            public float variation_lumiere_torche;
        }
        static CitadelPlayCheck(){EditorApplication.update+=Tick;}
        public static void Start()
        {
            phase=0;frame=0;last=-1;wait=0;snowCount=0;flameCount=0;
            env=null;firstFire=0;fireDelta=0;initialPixels=null;changedPixels=0;
            Directory.CreateDirectory(Folder+"frames");EditorSceneManager.OpenScene(CitadelBuilder.Root+"/Scenes/Forge_Citadelle_eperon_des_veilleurs.unity");SessionState.SetBool(Flag,true);EditorApplication.EnterPlaymode();
        }
        static void Tick()
        {
            if(!SessionState.GetBool(Flag,false)||!Application.isPlaying||last==Time.frameCount)return;last=Time.frameCount;
            try
            {
                if(!env)
                {
                    env=UnityEngine.Object.FindFirstObjectByType<CitadelEnvironment>();if(!env)return;
                    env.showPanel=false;env.view.GetComponent<VillageV2Visit>().enabled=false;
                    if(phase==0)
                    {
                        env.weather=1;env.Apply();env.snow.Simulate(25,true,true,false);env.snow.Play();
                        foreach(var ps in env.smoke){ps.Simulate(4,true,true,false);ps.Play();}
                        firstFire=env.fires[0].intensity;phase=1;wait=0;
                    }
                }
                if(phase==1)
                {
                    wait++;fireDelta=Mathf.Max(fireDelta,Mathf.Abs(env.fires[0].intensity-firstFire));
                    if(wait<20)return;
                    snowCount=env.snow.particleCount;flameCount=env.flames.Sum(p=>p.particleCount);
                    if(snowCount==0||flameCount==0||fireDelta<.1f)throw new InvalidOperationException("Effets immobiles ou vides en Play");
                    Capture(env.view,Folder+"neige.png",1600,900);
                    env.weather=0;env.snow.Clear();env.Apply();phase=2;wait=0;return;
                }
                if(phase==2)
                {
                    if(++wait<10)return;Capture(env.view,Folder+"eclaircie.png",1600,900);
                    var position=env.view.transform.position;var rotation=env.view.transform.rotation;float fov=env.view.fieldOfView;
                    if(env.viewpoints==null||env.viewpoints.Length==0)throw new InvalidOperationException("Cadrages de visite absents");
                    foreach(string name in new[]{"Passage","Parvis","Ilots"})
                    {
                        var point=env.viewpoints.First(p=>p.name==name);env.ShowView(name);
                        if(Vector3.Distance(env.view.transform.position,point.position)>.001f)throw new InvalidOperationException("Cadrage de visite inaccessible : "+name);
                        Capture(env.view,Folder+name.ToLowerInvariant()+".png",1600,900);
                    }
                    env.view.transform.SetPositionAndRotation(position,rotation);env.view.fieldOfView=fov;
                    env.hour=21;env.Apply();phase=3;wait=0;return;
                }
                if(phase==3)
                {
                    if(++wait<10)return;Capture(env.view,Folder+"nuit.png",1600,900);env.hour=16.8f;env.weather=2;env.Apply();phase=4;wait=0;return;
                }
                if(phase==4)
                {
                    if(++wait<10)return;Capture(env.view,Folder+"brume.png",1600,900);env.weather=1;env.Apply();env.snow.Simulate(25,true,true,false);env.snow.Play();phase=5;frame=0;Time.captureFramerate=24;
                    env.view.transform.position=new Vector3(-57,77,139);env.view.transform.LookAt(new Vector3(0,64,3));return;
                }
                if(phase==5)
                {
                    // Une seconde immobile pour mesurer une animation réelle dans les pixels.
                    if(frame>=24){float t=(frame-24)/168f;env.view.transform.position=Vector3.Lerp(new Vector3(-57,77,139),new Vector3(-91,98,176),t);env.view.transform.LookAt(new Vector3(0,67,-3));}
                    var pixels=Capture(env.view,Folder+"frames/image_"+frame.ToString("D4")+".png",1280,720);
                    if(frame==0)initialPixels=pixels;
                    if(frame==23)
                    {
                        changedPixels=pixels.Where((p,i)=>Mathf.Abs(p.r-initialPixels[i].r)+Mathf.Abs(p.g-initialPixels[i].g)+Mathf.Abs(p.b-initialPixels[i].b)>30).Count();
                        if(changedPixels<100)throw new InvalidOperationException("L'image animée reste identique à caméra fixe");
                    }
                    frame++;
                    if(frame==192){Time.captureFramerate=0;phase=6;wait=0;SceneManager.LoadScene(env.scenes[1]);env=null;}return;
                }
                if(phase==6)
                {
                    if(++wait<20)return;
                    if(env.seed!=2419)throw new InvalidOperationException("La deuxième disposition n'est pas chargée");
                    env.weather=0;env.Apply();env.snow.Clear();Capture(env.view,Folder+"col_des_cendres.png",1600,900);
                    var result=new Result{changement_disposition=true,flocons=snowCount,particules_flammes=flameCount,variation_lumiere_torche=fireDelta,images_animation=192,pixels_changes_camera_fixe=changedPixels};
                    File.WriteAllText(Folder+"verification-play.json",JsonUtility.ToJson(result,true));Debug.Log("CITADELLE_PLAY_OK "+JsonUtility.ToJson(result));SessionState.SetBool(Flag,false);CitadelEditorBridge.Finish(0);
                }
            }
            catch(Exception e){Debug.LogException(e);SessionState.SetBool(Flag,false);CitadelEditorBridge.Finish(1);}
        }
        public static Color32[] Capture(Camera camera,string path,int width,int height)
        {
            var target=new RenderTexture(width,height,24,RenderTextureFormat.ARGB32){antiAliasing=4};target.Create();
            RenderPipeline.SubmitRenderRequest(camera,new UniversalRenderPipeline.SingleCameraRequest{destination=target});
            var old=RenderTexture.active;RenderTexture.active=target;var texture=new Texture2D(width,height,TextureFormat.RGB24,false);
            texture.ReadPixels(new Rect(0,0,width,height),0,0);texture.Apply();File.WriteAllBytes(path,texture.EncodeToPNG());var pixels=texture.GetPixels32();
            RenderTexture.active=old;UnityEngine.Object.DestroyImmediate(texture);target.Release();UnityEngine.Object.DestroyImmediate(target);return pixels;
        }
    }
}
