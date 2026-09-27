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
    // Le même CharacterController que la visite parcourt chaque rue dans les scènes sauvegardées.
    [InitializeOnLoad] public static class CitadelTraversalCheck
    {
        const string Flag="Forge.Citadelle.Parcours";
        const string Folder="../local3d/citadelle/sorties/parcours/";
        static CitadelTraversal walk;static CitadelEnvironment env;static CitadelTree tree;
        static readonly List<Vector3> nodes=new();static readonly List<List<int>> links=new();
        static readonly List<int[]> routes=new();static readonly Queue<int> itinerary=new();
        static int variant,last=-1,steps,routeNumber,phase;static float stalled,previous=float.MaxValue,distance;
        static readonly List<Result> results=new();
        static string[] sceneNames;
        [Serializable] class Result
        {
            public string scene,status="valide";public int chemins,points,terrains,troncs_lisiere,pas_physiques;
            public float distance_marchee_m;public bool graphe_connexe,contre_epreuve_obstacle,abattage;
        }
        [Serializable] class Report { public string status="valide";public Result[] dispositions; }
        static Result result;
        static CitadelTraversalCheck(){EditorApplication.update+=Tick;}
        public static void Start()
        {
            walk=null;env=null;tree=null;variant=0;last=-1;phase=0;
            results.Clear();sceneNames=null;result=null;
            Directory.CreateDirectory(Folder);EditorSceneManager.OpenScene(CitadelBuilder.Root+"/Scenes/Forge_Citadelle_eperon_des_veilleurs.unity");
            SessionState.SetBool(Flag,true);EditorApplication.EnterPlaymode();
        }
        static int Node(Vector3 p)
        {
            int n=nodes.Count;nodes.Add(p);links.Add(new List<int>());return n;
        }
        static void Link(int a,int b){if(a==b)return;links[a].Add(b);links[b].Add(a);}
        static IEnumerable<int> Path(int from,int to)
        {
            var previous=Enumerable.Repeat(-1,nodes.Count).ToArray();var q=new Queue<int>();q.Enqueue(from);previous[from]=from;
            while(q.Count>0 && previous[to]<0)
            {int a=q.Dequeue();foreach(int b in links[a])if(previous[b]<0){previous[b]=a;q.Enqueue(b);}}
            if(previous[to]<0)throw new InvalidOperationException("Chemin déconnecté : "+nodes[to]);
            var path=new List<int>();for(int p=to;p!=from;p=previous[p])path.Add(p);path.Reverse();return path;
        }
        static void Prepare()
        {
            nodes.Clear();links.Clear();routes.Clear();itinerary.Clear();steps=0;distance=0;stalled=0;previous=float.MaxValue;routeNumber=0;
            walk=UnityEngine.Object.FindFirstObjectByType<CitadelTraversal>();env=UnityEngine.Object.FindFirstObjectByType<CitadelEnvironment>();
            if(!walk||walk.routes.Length==0||walk.plots.Length==0)throw new InvalidOperationException("Échantillon de parcours vide");
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
            // Toutes les branches doivent pouvoir être rejointes depuis la citadelle.
            int current=0;foreach(var route in routes)
            {foreach(int n in Path(current,route[0]))itinerary.Enqueue(n);foreach(int n in route)itinerary.Enqueue(n);current=route[^1];}
            result=new Result{scene=SceneManager.GetActiveScene().name,chemins=routes.Count,points=nodes.Count,terrains=walk.plots.Length,graphe_connexe=true};
            // Contre-épreuve : un mur ajouté sur la première rue doit arrêter le personnage.
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
        static void Capture(string name,Vector3 target)
        {
            walk.Face(target);CitadelPlayCheck.Capture(walk.view,Folder+result.scene+"_"+name+".png",1600,900);
        }
        static void Tick()
        {
            if(!SessionState.GetBool(Flag,false)||!Application.isPlaying||last==Time.frameCount)return;last=Time.frameCount;
            try
            {
                if(!walk){Prepare();return;}
                if(phase==1)
                {
                    // Pas de téléportation entre les branches : retour par le réseau lui-même.
                    for(int j=0;j<220 && itinerary.Count>0;j++)
                    {
                        Vector3 target=nodes[itinerary.Peek()],delta=target-walk.transform.position;delta.y=0;
                        float d=delta.magnitude;
                        if(d<.18f)
                        {
                            if(Mathf.Abs(walk.transform.position.y-target.y)>.7f)throw new InvalidOperationException("Niveau du chemin inaccessible : "+target+" pied="+walk.transform.position);
                            int reached=itinerary.Dequeue();previous=float.MaxValue;stalled=0;
                            for(int r=0;r<routes.Count;r++)if(reached==routes[r][^1])
                            {
                                routeNumber++;
                                if(walk.routes[r].id=="descente_village"||walk.routes[r].id=="lisiere_bois"||walk.routes[r].id.StartsWith("acces_terrain"))
                                    Capture(walk.routes[r].id,r==1?new Vector3(0,55,30):walk.transform.position+new Vector3(0,0,-20));
                            }
                            continue;
                        }
                        Move(delta.normalized);
                        if(d>=previous-.008f)stalled+=.04f;else stalled=0;previous=d;
                        if(stalled>3||steps>150000)
                        {
                            Capture("obstruction",target);
                            var near=Physics.OverlapSphere(walk.transform.position+Vector3.up,2).Select(c=>c.name).Distinct();
                            throw new InvalidOperationException("Passage bloqué vers "+target+" depuis "+walk.transform.position+" : "+string.Join(",",near));
                        }
                    }
                    if(itinerary.Count>0)return;
                    // Rejoindre la lisière par le graphe avant l'essai d'abattage.
                    int from=Enumerable.Range(0,nodes.Count).OrderBy(i=>Vector3.Distance(nodes[i],walk.transform.position)).First();
                    int to=routes[Array.FindIndex(walk.routes,r=>r.id=="lisiere_bois")][^1];
                    foreach(int n in Path(from,to))itinerary.Enqueue(n);
                    phase=2;return;
                }
                if(phase==2)
                {
                    for(int j=0;j<220 && itinerary.Count>0;j++)
                    {
                        Vector3 delta=nodes[itinerary.Peek()]-walk.transform.position;delta.y=0;
                        if(delta.magnitude<.18f){itinerary.Dequeue();continue;}
                        Vector3 before=walk.transform.position;Move(delta.normalized);
                        if(Vector3.Distance(before,walk.transform.position)<.008f)stalled+=.04f;else stalled=0;
                        if(stalled>3)throw new InvalidOperationException("Retour à la lisière obstrué");
                    }
                    if(itinerary.Count>0)return;
                    var trees=UnityEngine.Object.FindObjectsByType<CitadelTree>(FindObjectsSortMode.None).Where(t=>Vector3.Distance(t.transform.position,walk.forest)<25).OrderBy(t=>Vector3.Distance(t.transform.position,walk.transform.position)).ToArray();
                    if(trees.Length==0)throw new InvalidOperationException("La lisière n'a aucun tronc accessible");
                    result.troncs_lisiere=trees.Length;tree=trees[0];phase=3;stalled=0;previous=float.MaxValue;return;
                }
                if(phase==3)
                {
                    for(int j=0;j<80;j++)
                    {
                        Vector3 delta=tree.transform.position-walk.transform.position;delta.y=0;
                        if(walk.NearestTree()==tree)
                        {Capture("foret_avant_abattage",tree.transform.position);tree.Fell(walk.transform.position);phase=4;return;}
                        float d=delta.magnitude;Move(delta.normalized);
                        if(d>=previous-.008f)stalled+=.04f;else stalled=0;previous=d;
                        if(stalled>3)throw new InvalidOperationException("Impossible d'approcher le tronc depuis la clairière");
                    }
                }
                if(phase==4 && tree.landed)
                {
                    result.abattage=tree.felled && !tree.GetComponent<CapsuleCollider>().enabled;
                    if(!result.abattage)throw new InvalidOperationException("Abattage sans effet");
                    Capture("foret_apres_abattage",tree.transform.position);result.pas_physiques=steps;result.distance_marchee_m=distance;
                    results.Add(result);File.WriteAllText(Folder+"verification.json",JsonUtility.ToJson(new Report{status=results.Count==sceneNames.Length?"valide":"en_cours",dispositions=results.ToArray()},true));
                    if(++variant<sceneNames.Length){walk=null;env=null;tree=null;phase=0;SceneManager.LoadScene(sceneNames[variant]);}
                    else{if(File.Exists(Folder+"echec.txt"))File.Delete(Folder+"echec.txt");SessionState.SetBool(Flag,false);Debug.Log("CITADELLE_PARCOURS_OK "+results.Count);CitadelEditorBridge.Finish(0);}
                }
            }
            catch(Exception e)
            {
                File.WriteAllText(Folder+"echec.txt",e.ToString());Debug.LogException(e);SessionState.SetBool(Flag,false);CitadelEditorBridge.Finish(1);
            }
        }
    }
}
