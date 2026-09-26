using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace ForgeLocal3D
{
    // Le personnage de la visite parcourt chaque rue du ksar et du bourg dans les scènes
    // sauvegardées, sans téléportation entre les branches, puis rejoint la lisière de la palmeraie.
    [InitializeOnLoad] public static class DesertTraversalCheck
    {
        const string Flag="Forge.Desert.Parcours";
        const string Folder="../local3d/desert/sorties/parcours/";
        static CitadelTraversal walk;static DesertEnvironment env;
        static readonly List<Vector3> nodes=new();static readonly List<List<int>> links=new();
        static readonly List<int[]> routes=new();static readonly Queue<int> itinerary=new();
        static int variant,last=-1,steps,phase;static float stalled,previous=float.MaxValue,distance;
        static readonly List<Result> results=new();
        static string[] sceneNames;
        [Serializable] class Result
        {
            public string scene,status="valide";public int chemins,points,jardins,palmiers_lisiere,pas_physiques;
            public float distance_marchee_m;public bool graphe_connexe,contre_epreuve_obstacle,lisiere_atteinte;
        }
        [Serializable] class Report { public string status="valide";public Result[] dispositions; }
        static Result result;
        static DesertTraversalCheck(){EditorApplication.update+=Tick;}
        public static void Start()
        {
            walk=null;env=null;variant=0;last=-1;phase=0;results.Clear();sceneNames=null;result=null;
            Directory.CreateDirectory(Folder);EditorSceneManager.OpenScene(DesertBuilder.Root+"/Scenes/Forge_Desert_ksar_des_sept_puits.unity");
            SessionState.SetBool(Flag,true);EditorApplication.EnterPlaymode();
        }
        static int Node(Vector3 p){int n=nodes.Count;nodes.Add(p);links.Add(new List<int>());return n;}
        static void Link(int a,int b){if(a==b)return;links[a].Add(b);links[b].Add(a);}
        static IEnumerable<int> Path(int from,int to)
        {
            var before=Enumerable.Repeat(-1,nodes.Count).ToArray();var q=new Queue<int>();q.Enqueue(from);before[from]=from;
            while(q.Count>0 && before[to]<0){int a=q.Dequeue();foreach(int b in links[a])if(before[b]<0){before[b]=a;q.Enqueue(b);}}
            if(before[to]<0)throw new InvalidOperationException("Chemin déconnecté : "+nodes[to]);
            var path=new List<int>();for(int p=to;p!=from;p=before[p])path.Add(p);path.Reverse();return path;
        }
        static void Prepare()
        {
            nodes.Clear();links.Clear();routes.Clear();itinerary.Clear();steps=0;distance=0;stalled=0;previous=float.MaxValue;
            walk=UnityEngine.Object.FindFirstObjectByType<CitadelTraversal>();env=UnityEngine.Object.FindFirstObjectByType<DesertEnvironment>();
            if(!walk||!env||walk.routes.Length==0||walk.plots.Length==0)throw new InvalidOperationException("Échantillon de parcours vide");
            env.showPanel=false;walk.automatic=true;walk.Enter();Physics.SyncTransforms();
            sceneNames=env.scenes;
            foreach(var route in walk.routes)
            {
                if(route.points.Length<2||route.width<2)throw new InvalidOperationException("Rue sans largeur ou sans profil : "+route.id);
                int[] ids=route.points.Select(Node).ToArray();routes.Add(ids);
                for(int i=1;i<ids.Length;i++)Link(ids[i-1],ids[i]);
            }
            for(int a=0;a<nodes.Count;a++)for(int b=a+1;b<nodes.Count;b++)
                if(Vector3.Distance(nodes[a],nodes[b])<1.45f)Link(a,b);
            // Toutes les branches doivent pouvoir être rejointes depuis la place du ksar.
            int current=0;foreach(var route in routes)
            {foreach(int n in Path(current,route[0]))itinerary.Enqueue(n);foreach(int n in route)itinerary.Enqueue(n);current=route[^1];}
            result=new Result{scene=SceneManager.GetActiveScene().name,chemins=routes.Count,points=nodes.Count,jardins=walk.plots.Length,graphe_connexe=true};
            // Contre-épreuve : un mur posé devant le point de départ doit arrêter le personnage.
            var wall=GameObject.CreatePrimitive(PrimitiveType.Cube);wall.name="Obstacle de contre-épreuve";
            wall.transform.position=walk.spawn+new Vector3(0,1,2);wall.transform.localScale=new Vector3(8,4,.6f);Physics.SyncTransforms();
            Vector3 start=walk.transform.position;for(int i=0;i<70;i++)walk.Step(Vector3.forward*2.8f,.04f);
            result.contre_epreuve_obstacle=walk.transform.position.z-start.z<1.8f;
            UnityEngine.Object.DestroyImmediate(wall);
            if(!result.contre_epreuve_obstacle)throw new InvalidOperationException("Le personnage traverse le mur de contre-épreuve");
            walk.Leave();walk.Enter();Physics.SyncTransforms();phase=1;
        }
        static void Move(Vector3 direction)
        {Vector3 before=walk.transform.position;walk.Step(direction*2.8f,.04f);steps++;distance+=Vector3.Distance(before,walk.transform.position);}
        static void Capture(string name,Vector3 target){walk.Face(target);CitadelPlayCheck.Capture(walk.view,Folder+result.scene+"_"+name+".png",1600,900);}
        static bool Follow()
        {
            for(int j=0;j<220 && itinerary.Count>0;j++)
            {
                Vector3 target=nodes[itinerary.Peek()],delta=target-walk.transform.position;delta.y=0;
                float d=delta.magnitude;
                if(d<.18f)
                {
                    if(Mathf.Abs(walk.transform.position.y-target.y)>.7f)throw new InvalidOperationException("Niveau du chemin inaccessible : "+target+" pied="+walk.transform.position);
                    int reached=itinerary.Dequeue();previous=float.MaxValue;stalled=0;
                    for(int r=0;r<routes.Count;r++)if(reached==routes[r][^1]&&phase==1)
                    {
                        string id=walk.routes[r].id;
                        if(id=="descente_oasis"||id=="place_souk"||id.StartsWith("acces_jardin"))Capture(id,walk.transform.position+walk.transform.forward*20+Vector3.up);
                    }
                    continue;
                }
                Move(delta.normalized);
                if(d>=previous-.008f)stalled+=.04f;else stalled=0;previous=d;
                if(stalled>3||steps>200000)
                {
                    Capture("obstruction",target);
                    var near=Physics.OverlapSphere(walk.transform.position+Vector3.up,2).Select(c=>c.name).Distinct();
                    throw new InvalidOperationException("Passage bloqué vers "+target+" depuis "+walk.transform.position+" : "+string.Join(",",near));
                }
            }
            return itinerary.Count==0;
        }
        static void Tick()
        {
            if(!SessionState.GetBool(Flag,false)||!Application.isPlaying||last==Time.frameCount)return;last=Time.frameCount;
            try
            {
                if(!walk){Prepare();return;}
                if(phase==1)
                {
                    if(!Follow())return;
                    // Rejoindre la lisière de la palmeraie par le réseau lui-même.
                    int from=Enumerable.Range(0,nodes.Count).OrderBy(i=>Vector3.Distance(nodes[i],walk.transform.position)).First();
                    int to=routes[Array.FindIndex(walk.routes,r=>r.id=="lisiere_palmeraie")][^1];
                    foreach(int n in Path(from,to))itinerary.Enqueue(n);
                    phase=2;return;
                }
                if(phase==2)
                {
                    if(!Follow())return;
                    var palms=UnityEngine.Object.FindObjectsByType<LODGroup>(FindObjectsSortMode.None).Where(g=>g.name.StartsWith("palmier_")&&Vector3.Distance(g.transform.position,walk.forest)<30).ToArray();
                    if(palms.Length==0)throw new InvalidOperationException("La lisière n'a aucun palmier proche");
                    result.palmiers_lisiere=palms.Length;result.lisiere_atteinte=Vector3.Distance(walk.transform.position,walk.forest)<3;
                    if(!result.lisiere_atteinte)throw new InvalidOperationException("Lisière de la palmeraie non atteinte");
                    Capture("palmeraie",palms.OrderBy(p=>Vector3.Distance(p.transform.position,walk.transform.position)).First().transform.position+Vector3.up*4);
                    result.pas_physiques=steps;result.distance_marchee_m=distance;results.Add(result);
                    File.WriteAllText(Folder+"verification.json",JsonUtility.ToJson(new Report{status=results.Count==sceneNames.Length?"valide":"en_cours",dispositions=results.ToArray()},true));
                    if(++variant<sceneNames.Length){walk=null;env=null;phase=0;SceneManager.LoadScene(sceneNames[variant]);}
                    else{if(File.Exists(Folder+"echec.txt"))File.Delete(Folder+"echec.txt");SessionState.SetBool(Flag,false);Debug.Log("DESERT_PARCOURS_OK "+results.Count);CitadelEditorBridge.Finish(0);}
                }
            }
            catch(Exception e)
            {
                File.WriteAllText(Folder+"echec.txt",e.ToString());Debug.LogException(e);SessionState.SetBool(Flag,false);CitadelEditorBridge.Finish(1);
            }
        }
    }
}
