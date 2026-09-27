using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEngine;
using UnityEngine.SceneManagement;
using UnityEngine.Rendering.Universal;
using UnityEngine.Profiling;
using UnityEngine.InputSystem;
using UnityEngine.InputSystem.LowLevel;

namespace ForgeLocal3D
{
    // Mesure facultative du vrai joueur, sans capture dans la fenêtre chronométrée.
    public sealed class CitadelBenchmark : MonoBehaviour
    {
        [Serializable] public class Measure
        {
            public string scene,vue;public int frames;public double mediane_ms,p95_ms,p99_ms,fps_moyen;
            public long memoire_unity_mo;public int pieces_construites;
        }
        [Serializable] public class Report
        {
            public string gpu,cpu,date_utc;public int largeur,hauteur;public float echelle_rendu;
            public string protocole="Joueur Windows, cadence libre, 3 s de chauffe puis 6 s par vue, caméra mobile. Huit vues par scène, avec huit maisons construites par le joueur. Neige sur les vues Foret et Passage.";
            public Measure[] mesures;public bool objectif_60;public bool images_non_vides;
        }
        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        static void Boot()
        {
            if(Application.isEditor||!Environment.GetCommandLineArgs().Any(a=>a=="-forge-benchmark"||a=="-forge-construction-check"))return;
            var go=new GameObject("Mesure de performance");DontDestroyOnLoad(go);go.AddComponent<CitadelBenchmark>();
        }
        [Serializable] class ConstructionReport { public string status="valide";public string[] controles;public int scenes; }
        IEnumerator ConstructionCheck(string folder)
        {
            var checks=new List<string>();
            // Des périphériques de contrôle isolés évitent que le pointeur du bureau
            // ne remplace un événement entre la pose et sa vérification.
            foreach(var device in InputSystem.devices.Where(d=>d is Keyboard||d is Mouse).ToArray())InputSystem.DisableDevice(device);
            InputSystem.AddDevice<Keyboard>();InputSystem.AddDevice<Mouse>();
            void Require(bool condition,string text)
            {if(!condition)throw new InvalidOperationException("Construction : "+text);checks.Add(SceneManager.GetActiveScene().name+" / "+text);}
            for(int scene=0;scene<SceneManager.sceneCountInBuildSettings;scene++)
            {
                yield return SceneManager.LoadSceneAsync(scene);yield return null;
                var build=FindFirstObjectByType<CitadelConstruction>();var env=FindFirstObjectByType<CitadelEnvironment>();
                Application.runInBackground=true;build.savePathOverride=Path.Combine(folder,"chantier_"+scene+".json");
                CitadelConstruction.Placement P(string id,float y)=>new CitadelConstruction.Placement{module="habitat_"+id,plot=0,anchor=new Vector3(0,y,0),turn=0};
                Require(!build.CanBatch(new[]{P("etage_enduit",3)},out _),"étage sans appui refusé");
                var basePiece=P("socle_pierre",0);Require(build.Place(new[]{basePiece},false),"socle posé");
                Require(!build.CanBatch(new[]{P("socle_pierre",0)},out _),"superposition refusée");
                Require(!build.CanBatch(new[]{P("toit_ardoise",6)},out _),"toiture suspendue refusée");
                Require(build.Place(new[]{P("etage_enduit",3)},false)&&build.Place(new[]{P("toit_ardoise",6)},false),"étage et toiture raccordés");
                Require(!build.Remove(new[]{basePiece},false),"suppression d’un appui refusée");
                Require(build.UndoLast(false)&&build.Pieces.Count==2,"annulation de la dernière pose");
                var outside=P("socle_pierre",0);outside.anchor.x=30;
                Require(!build.CanBatch(new[]{outside},out _),"sortie du terrain refusée");
                Require(build.Remove(build.Pieces.ToArray(),false),"démontage du chantier");
                Require(build.Place(build.House(1,0,Vector3.zero,0),false),"maison assemblée avec les pièces du kit");
                string identity=JsonUtility.ToJson(new ConstructionSaveIdentity{ids=build.Pieces.Select(p=>p.module+"/"+p.anchor+"/"+p.turn).ToArray()});
                Require(build.Save(build.SavePath),"sauvegarde réelle sur disque");
                Require(build.Remove(build.Pieces.ToArray(),false)&&build.Load(build.SavePath),"rechargement du chantier");
                Require(identity==JsonUtility.ToJson(new ConstructionSaveIdentity{ids=build.Pieces.Select(p=>p.module+"/"+p.anchor+"/"+p.turn).ToArray()}),"poses et rotations conservées");
                var stair=build.Pieces.Single(p=>p.module=="habitat_escalier").instance.transform;
                var walk=build.walk;walk.Enter();walk.automatic=true;walk.body.enabled=false;
                walk.transform.position=stair.TransformPoint(new Vector3(0,.10f,2));walk.body.enabled=true;
                Vector3 direction=stair.TransformDirection(Vector3.back);
                for(int step=0;step<100;step++){walk.Step(direction*2.2f,.02f);yield return null;}
                Require(walk.transform.position.y-stair.position.y>2.7f,"escalier et galerie parcourus avec les collisions réelles");
                walk.Leave();walk.automatic=false;
                Require(build.Remove(build.Pieces.ToArray(),false),"terrain libéré pour contrôle des entrées");
                foreach(int house in Enumerable.Range(0,build.kit.houses.Length))foreach(int rotation in Enumerable.Range(0,4))
                    Require(build.CanBatch(build.House(house,0,Vector3.zero,rotation),out _),"maison "+(house+1)+" assemblable à "+rotation*90+" degrés");
                InputSystem.QueueStateEvent(Keyboard.current,new KeyboardState(Key.B));yield return null;yield return null;
                InputSystem.QueueStateEvent(Keyboard.current,new KeyboardState());yield return null;
                Require(build.active,"touche B ouvre le chantier");
                InputSystem.QueueStateEvent(Keyboard.current,new KeyboardState(Key.R));yield return null;yield return null;
                InputSystem.QueueStateEvent(Keyboard.current,new KeyboardState());yield return null;
                Vector3 screen=build.view.WorldToScreenPoint(build.walk.plots[0].position);
                InputSystem.QueueStateEvent(Mouse.current,new MouseState{position=new Vector2(screen.x,screen.y)});yield return null;
                InputSystem.QueueStateEvent(Mouse.current,new MouseState{position=new Vector2(screen.x,screen.y),buttons=1});yield return null;yield return null;
                InputSystem.QueueStateEvent(Mouse.current,new MouseState{position=new Vector2(screen.x,screen.y)});yield return null;
                Debug.Log("CHANTIER_ENTREES "+build.Diagnostic+" cible="+screen+" souris="+Mouse.current.position.ReadValue());
                Require(build.Pieces.Count==1&&build.Pieces[0].turn==1,"clic dans la scène et rotation R placent un socle : "+build.Diagnostic);
                Require(build.UndoLast(false)&&build.Pieces.Count==0,"annulation de la pose par clic");
                Require(build.Place(build.House(1,0,new Vector3(-3,0,0),0),false)&&build.Place(build.House(2,0,new Vector3(3,0,0),0),false),"deux maisons mitoyennes assemblées");
                Require(build.WalkHere()&&walk.walking&&!build.active,"entrée en marche sur un sol libre du chantier");
                walk.Leave();build.Toggle();
                InputSystem.QueueStateEvent(Mouse.current,new MouseState{position=new Vector2(100,Screen.height-100)});
                env.ShowView("Chantier");yield return null;yield return new WaitForEndOfFrame();
                var image=new Texture2D(Screen.width,Screen.height,TextureFormat.RGB24,false);image.ReadPixels(new Rect(0,0,Screen.width,Screen.height),0,0);image.Apply();
                File.WriteAllBytes(Path.Combine(folder,"chantier_"+scene+".png"),image.EncodeToPNG());Destroy(image);
            }
            File.WriteAllText(Path.Combine(folder,"verification.json"),JsonUtility.ToJson(new ConstructionReport{controles=checks.ToArray(),scenes=SceneManager.sceneCountInBuildSettings},true));
        }
        [Serializable] class ConstructionSaveIdentity { public string[] ids; }
        IEnumerator Start()
        {
            var args=Environment.GetCommandLineArgs();int arg=Array.IndexOf(args,"-forge-output");
            string folder=arg>=0&&arg+1<args.Length?args[arg+1]:Application.persistentDataPath;
            Directory.CreateDirectory(folder);var results=new List<Measure>();
            if(File.Exists(Path.Combine(folder,"erreur.txt")))File.Delete(Path.Combine(folder,"erreur.txt"));
            Application.logMessageReceived+=(message,stack,type)=>
            {if(type==LogType.Exception||type==LogType.Error){File.WriteAllText(Path.Combine(folder,"erreur.txt"),message+"\n"+stack);Application.Quit(1);}};
            if(args.Contains("-forge-construction-check")){yield return ConstructionCheck(folder);Application.Quit(0);yield break;}
            for(int scene=0;scene<SceneManager.sceneCountInBuildSettings;scene++)
            {
                yield return SceneManager.LoadSceneAsync(scene);
                var env=FindFirstObjectByType<CitadelEnvironment>();
                if(!env){File.WriteAllText(Path.Combine(folder,"erreur.txt"),"Ambiance absente");Application.Quit(1);yield break;}
                env.showPanel=false;env.view.GetComponent<VillageV2Visit>().enabled=false;
                Application.targetFrameRate=-1;QualitySettings.vSyncCount=0;Application.runInBackground=true;
                var chantier=FindFirstObjectByType<CitadelConstruction>();
                for(int site=0;site<chantier.walk.plots.Length;site++)
                    foreach(int side in new[]{-1,1})
                        if(!chantier.Place(chantier.House(side<0?0:1,site,new Vector3(side*3,0,0),0),false))
                            throw new InvalidOperationException("Maisons de la mesure refusées");
                foreach(string name in new[]{"Citadelle","Vallee","Foret","Passage","Ilots","Forge","Habitat","Chantier","Marche","Etals"})
                {
                    var point=env.viewpoints.FirstOrDefault(p=>p.name.Equals(name,StringComparison.OrdinalIgnoreCase));
                    if(point==null)throw new InvalidOperationException("Vue absente : "+name);
                    env.ShowView(point.name);env.weather=name=="Foret"||name=="Passage"?1:0;env.Apply();
                    if(name=="Chantier")chantier.Toggle();
                    var startPosition=env.view.transform.position;var samples=new List<double>();
                    double start=Time.realtimeSinceStartupAsDouble,previous=start;
                    while(Time.realtimeSinceStartupAsDouble-start<9)
                    {
                        yield return null;
                        double now=Time.realtimeSinceStartupAsDouble;
                        if(now-start>3)samples.Add((now-previous)*1000);
                        previous=now;
                        env.view.transform.position=startPosition+env.view.transform.right*(Mathf.Sin((float)(now-start)*.3f)*2);
                        env.view.transform.LookAt(point.target);
                    }
                    if(samples.Count==0)throw new InvalidOperationException("Échantillon de performance vide");
                    samples.Sort();double Percent(float p)=>samples[Math.Min(samples.Count-1,(int)(samples.Count*p))];
                    results.Add(new Measure{scene=SceneManager.GetActiveScene().name,vue=name,frames=samples.Count,
                        mediane_ms=Percent(.5f),p95_ms=Percent(.95f),p99_ms=Percent(.99f),fps_moyen=1000/samples.Average(),
                        memoire_unity_mo=Profiler.GetTotalAllocatedMemoryLong()/(1024*1024),pieces_construites=chantier.Pieces.Count});
                    yield return new WaitForEndOfFrame();
                    var capture=new Texture2D(Screen.width,Screen.height,TextureFormat.RGB24,false);
                    capture.ReadPixels(new Rect(0,0,Screen.width,Screen.height),0,0);capture.Apply();
                    var pixels=capture.GetPixels32();
                    if(pixels.Max(p=>(int)p.r+p.g+p.b)-pixels.Min(p=>(int)p.r+p.g+p.b)<30)
                    {
                        File.WriteAllText(Path.Combine(folder,"erreur.txt"),"Capture uniforme : aucune mesure de rendu valide.");
                        Application.Quit(1);yield break;
                    }
                    File.WriteAllBytes(Path.Combine(folder,SceneManager.GetActiveScene().name+"_"+name+".png"),capture.EncodeToPNG());
                    Destroy(capture);
                }
            }
            var report=new Report{gpu=SystemInfo.graphicsDeviceName,cpu=SystemInfo.processorType,date_utc=DateTime.UtcNow.ToString("O"),
                largeur=Screen.width,hauteur=Screen.height,echelle_rendu=((UniversalRenderPipelineAsset)UnityEngine.Rendering.GraphicsSettings.currentRenderPipeline).renderScale,
                images_non_vides=true,mesures=results.ToArray(),objectif_60=results.Count>0&&results.All(r=>r.p95_ms<=1000.0/60)};
            File.WriteAllText(Path.Combine(folder,"performance.json"),JsonUtility.ToJson(report,true));
            Application.Quit(0);
        }
    }
}
