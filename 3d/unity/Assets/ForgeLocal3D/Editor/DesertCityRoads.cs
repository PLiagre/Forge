using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Net.Http;
using Forge.Pont;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.SceneManagement;
using Object=UnityEngine.Object;

namespace ForgeLocal3D
{
    // Contrôle du lot 263, en Play : pose le jeu de gestes écrit par local3d/desert/routes.py sur
    // une copie du terrain, mesure, exporte, fait marcher le personnage, capture. Il ne juge
    // pas : routes.juger rejoue chaque route depuis hauteurs.f32 et décide. Ce qui s'écrit ici
    // est une mesure, ou la trace d'une contre-épreuve que le jugement doit voir rougir.
    [InitializeOnLoad] public static class DesertCityRoads
    {
        const string Flag="Forge.Desert.Routes",Ids="Forge.Desert.Routes.Ids",Index="Forge.Desert.Routes.Index",Failed="Forge.Desert.Routes.Echecs";
        const string PreviousDefault="Forge.Desert.Routes.Pipeline",PreviousQuality="Forge.Desert.Routes.Qualite";
        const string Output=DesertRoads.Sorties;
        const float Speed=2.8f,Dt=.04f;
        static int last=-1,settle;static bool loading;

        [Serializable] class Selection{public string[] implantations;}
        [Serializable] public class Marche{public bool faite;public double distance_fin=-1,pas_max=-1,pas_permis=-1;public int pas=-1;}
        [Serializable] public class Route
        {
            public string id="",famille="",revetement="",motif="",message="",avant="",apres="";
            public double largeur=-1,valeur=-1,position=-1,duree_s=-1;public bool acceptee;
            public double[] ax=new double[0],ay=new double[0],rendu=new double[0],collision=new double[0];
            public Marche marche=new Marche();
        }
        [Serializable] public class Decision{public string id="";public bool acceptee;public string motif="";}
        [Serializable] public class Empreinte{public string hauteurs="",couches="",touffes="";}
        [Serializable] public class Empreintes{public Empreinte a=new Empreinte(),b=new Empreinte(),autre_graine=new Empreinte();}
        [Serializable] public class Clic
        {
            public double[] voulus_x=new double[0],voulus_y=new double[0],obtenus_x=new double[0],obtenus_y=new double[0];
            public string empreinte_clic="",empreinte_gestes="";public bool acceptee;
        }
        [Serializable] public class Capture{public string nom;public double ecart=-1;}
        // Lot 251 : la caméra du joueur (DesertCityCamera) et son marcheur.
        [Serializable] public class Balayage{public int prevues=-1,mesurees=-1,sous_terrain=-1;public double marge_min=-1;}
        [Serializable] public class Zoom{public double distance_min=-1,distance_max=-1,hauteur_rue=-1;}
        [Serializable] public class Joueur
        {
            public bool branchee;public Balayage balayage=new Balayage(),releve=new Balayage(),sans_garde=new Balayage();public Zoom zoom=new Zoom();
            public double oeil=-1,retour=-1;public Marche marche=new Marche();public Route mur=new Route();
        }
        // Lot 293 : les deux clics passent par le service du monde, dont le contrôle fait passer les ticks.
        [Serializable] public class Raide{public bool clique,depose;public int rues_avant=-1,rues_apres=-1;}
        [Serializable] public class Plaine
        {
            public bool depose,recu_accepte;public long appliquee_au_tick=-1;public string recu="",empreinte_avant_tick="";public bool dessinee_avant_tick;
            public long tick_plan=-1;public int rues_neuves=-1;public double[] rue_x=new double[0],rue_y=new double[0];public double rue_largeur=-1;public bool rue_en_chantier;
        }
        [Serializable] public class Service{public long cell=-1;public int port=-1;public string empreinte_vierge="";public Raide raide=new Raide();public Plaine plaine=new Plaine();}
        [Serializable] public class Rapport
        {
            public string status="mesure",implantation,scene;public int graine,resolution=-1,couches_resolution=-1,details_resolution=-1;
            public double quantification=-1,@base,hauteur;
            public string[] couches=new string[0],touffes=new string[0];
            public Route[] routes=new Route[0];public Route profil_releve=new Route(),mur=new Route();public Decision pente_40=new Decision();
            public Empreintes empreintes=new Empreintes();public string asset_avant="",asset_apres="";
            public Clic clic=new Clic();public Capture[] captures=new Capture[0];public string[] defauts=new string[0];public double duree_s;
            public Joueur camera=new Joueur();public Capture[] captures_camera=new Capture[0];
            public Service service=new Service();
        }

        static DesertCityRoads(){EditorApplication.update+=Tick;}

        public static void Start()
        {
            var selection=JsonUtility.FromJson<Selection>(File.ReadAllText(Output+"selection.json"));
            if(selection?.implantations==null||selection.implantations.Length==0)
                throw new InvalidOperationException("Aucune implantation : lancer py local3d/atelier_desert.py routes");
            var pipeline=AssetDatabase.LoadAssetAtPath<RenderPipelineAsset>(DesertBuilder.Root+"/Settings/Pipeline.asset");
            if(!pipeline)throw new InvalidOperationException("Pipeline du désert absent : lancer d'abord py local3d/atelier_desert.py unity");
            SessionState.SetString(PreviousDefault,AssetDatabase.GetAssetPath(GraphicsSettings.defaultRenderPipeline));
            SessionState.SetString(PreviousQuality,AssetDatabase.GetAssetPath(QualitySettings.renderPipeline));
            GraphicsSettings.defaultRenderPipeline=pipeline;QualitySettings.renderPipeline=pipeline;
            SessionState.SetString(Ids,string.Join("|",selection.implantations));SessionState.SetInt(Index,0);SessionState.SetInt(Failed,0);
            EditorSceneManager.OpenScene(ScenePath(selection.implantations[0]));
            SessionState.SetBool(Flag,true);EditorApplication.EnterPlaymode();
        }
        [MenuItem("Forge/Désert/Ville : routes du joueur et contrôle")]
        public static void Menu()=>Start();
        static string ScenePath(string id)=>DesertBuilder.Root+"/Scenes/Forge_Desert_Ville_"+id+".unity";

        static void Tick()
        {
            if(!SessionState.GetBool(Flag,false)||!Application.isPlaying||last==Time.frameCount)return;last=Time.frameCount;
            try
            {
                var ids=SessionState.GetString(Ids,"").Split('|');int k=SessionState.GetInt(Index,0);
                if(SceneManager.GetActiveScene().name!="Forge_Desert_Ville_"+ids[k])
                {
                    if(!loading){loading=true;EditorSceneManager.LoadSceneInPlayMode(ScenePath(ids[k]),new LoadSceneParameters(LoadSceneMode.Single));}
                    return;
                }
                // Deux images pour que les composants de la scène aient fait leur Awake et leur Start.
                loading=false;if(settle++<2)return;settle=0;
                var report=Run(ids[k]);
                Directory.CreateDirectory(Output+ids[k]+"/routes");
                File.WriteAllText(Output+ids[k]+"/routes/unity-routes.json",JsonUtility.ToJson(report,true));
                UnityEngine.Debug.Log("DESERT_ROUTES "+ids[k]+" "+report.status+" "+string.Join(" | ",report.defauts));
                if(report.defauts.Length>0)SessionState.SetInt(Failed,SessionState.GetInt(Failed,0)+1);
                SessionState.SetInt(Index,k+1);
                if(k+1<ids.Length)return;
                Finish(SessionState.GetInt(Failed,0)==0?0:1);
            }
            catch(Exception e){UnityEngine.Debug.LogException(e);Finish(1);}
        }
        static void Finish(int code)
        {
            SessionState.SetBool(Flag,false);
            var a=AssetDatabase.LoadAssetAtPath<RenderPipelineAsset>(SessionState.GetString(PreviousDefault,""));
            var b=AssetDatabase.LoadAssetAtPath<RenderPipelineAsset>(SessionState.GetString(PreviousQuality,""));
            GraphicsSettings.defaultRenderPipeline=a;QualitySettings.renderPipeline=b;
            CitadelEditorBridge.Finish(code);
        }

        // ---------- Mesures ----------

        static Vector3 World(Terrain t,double x,double y)
        {var p=new Vector3((float)-x,0,(float)-y);p.y=t.SampleHeight(p)+t.transform.position.y;return p;}
        static Empreinte Copy(DesertRoads.Empreinte e)=>new Empreinte{hauteurs=e.hauteurs,couches=e.couches,touffes=e.touffes};

        static void Measure(Terrain t,Route r)
        {
            var collider=t.GetComponent<TerrainCollider>();Physics.SyncTransforms();
            r.rendu=new double[r.ax.Length];r.collision=new double[r.ax.Length];
            for(int k=0;k<r.ax.Length;k++)
            {
                var w=World(t,r.ax[k],r.ay[k]);r.rendu[k]=w.y;
                var ray=new Ray(new Vector3(w.x,t.transform.position.y+t.terrainData.size.y+50,w.z),Vector3.down);
                r.collision[k]=collider.Raycast(ray,out var hit,t.terrainData.size.y+200)?hit.point.y:double.NaN;
            }
        }
        static Route Record(DesertRoads.Geste g,DesertRoads.Resultat res,DesertRoads.Empreinte avant,DesertRoads.Empreinte apres,double seconds)
            =>new Route{id=g.id,famille=g.famille??"",revetement=g.revetement,largeur=g.largeur,acceptee=res.acceptee,motif=res.motif,message=res.message,
                valeur=res.valeur,position=res.position,ax=res.ax,ay=res.ay,avant=avant.hauteurs+avant.couches+avant.touffes,apres=apres.hauteurs+apres.couches+apres.touffes,duree_s=seconds};

        static void Export(DesertRoads roads,string id,string name)
        {
            var td=roads.Copie;int n=td.heightmapResolution;var h=td.GetHeights(0,0,n,n);var f=new float[n*n];
            double b=roads.terrain.transform.position.y,H=td.size.y;
            for(int j=0;j<n;j++)for(int i=0;i<n;i++)f[j*n+i]=(float)(h[j,i]*H+b);
            var bytes=new byte[f.Length*4];Buffer.BlockCopy(f,0,bytes,0,bytes.Length);File.WriteAllBytes(Output+id+"/routes_"+name+".f32",bytes);
        }
        static void ExportGround(DesertRoads roads,string id,string[] tufts)
        {
            var td=roads.Copie;int m=td.alphamapResolution;var a=td.GetAlphamaps(0,0,m,m);int k=a.GetLength(2);var b=new byte[m*m*k];
            for(int j=0;j<m;j++)for(int i=0;i<m;i++)for(int c=0;c<k;c++)b[(j*m+i)*k+c]=(byte)Math.Round(a[j,i,c]*255);
            File.WriteAllBytes(Output+id+"/routes_couches.u8",b);
            int dn=td.detailResolution;
            for(int l=0;l<td.detailPrototypes.Length;l++)
            {
                var g=td.GetDetailLayer(0,0,dn,dn,l);var d=new byte[dn*dn];
                for(int j=0;j<dn;j++)for(int i=0;i<dn;i++)d[j*dn+i]=(byte)Math.Min(255,g[j,i]);
                File.WriteAllBytes(Output+id+"/routes_details_"+tufts[l]+".u8",d);
            }
        }

        // Le personnage suit l'axe d'un bout à l'autre, un pas physique à la fois.
        public static Marche Walk(CitadelTraversal walk,Terrain t,Route r)
        {
            var pts=Enumerable.Range(0,r.ax.Length).Select(k=>World(t,r.ax[k],r.ay[k])).ToArray();int end=pts.Length-1;
            walk.Leave();walk.spawn=pts[0]+Vector3.up*.05f;walk.Enter();Physics.SyncTransforms();
            var m=new Marche{faite=true,pas_permis=Speed*Dt,pas_max=0,pas=0};
            int target=Math.Min(4,end),stall=0;float previous=float.MaxValue;
            int limit=(int)(pts.Length*.5f/(Speed*Dt)*3)+500;
            while(m.pas<limit)
            {
                var pos=walk.transform.position;var delta=pts[target]-pos;delta.y=0;float d=delta.magnitude;
                if(target<end&&d<.5f){target=Math.Min(target+4,end);previous=float.MaxValue;continue;}
                if(target==end&&d<.15f)break;
                walk.Step(delta/d*Speed,Dt);m.pas++;
                var moved=walk.transform.position-pos;moved.y=0;m.pas_max=Math.Max(m.pas_max,moved.magnitude);
                if(d>=previous-.002f){if(++stall>75)break;}else stall=0;
                previous=d;
            }
            var left=pts[end]-walk.transform.position;left.y=0;m.distance_fin=left.magnitude;
            walk.Leave();return m;
        }

        // Le mur de contre-épreuve, en travers du milieu de la route.
        static GameObject Wall(Terrain terrain,Route plain)
        {
            int q=plain.ax.Length/2;var at=World(terrain,plain.ax[q],plain.ay[q]);var along=World(terrain,plain.ax[q+1],plain.ay[q+1])-World(terrain,plain.ax[q-1],plain.ay[q-1]);along.y=0;
            var wall=GameObject.CreatePrimitive(PrimitiveType.Cube);wall.name="Mur de contre-épreuve";
            wall.transform.SetPositionAndRotation(at+Vector3.up*1.5f,Quaternion.LookRotation(along));wall.transform.localScale=new Vector3((float)plain.largeur+6,4,.6f);Physics.SyncTransforms();
            return wall;
        }

        static double Shot(Camera camera,DesertRoadTool tool,string path,Vector3 from,Vector3 to,float fov)
        {
            camera.transform.position=from;camera.transform.LookAt(to);camera.fieldOfView=fov;
            return Photo(camera,tool,path);
        }
        static double Photo(Camera camera,DesertRoadTool tool,string path)
        {
            camera.aspect=1600f/900;tool.Placer();
            var pixels=CitadelPlayCheck.Capture(camera,path,1600,900);
            // Écart moyen à la moyenne, comme les captures de la V0 : une image uniforme est un rendu raté.
            float mean=0,dev=0;foreach(var p in pixels)mean+=p.r+p.g+p.b;mean/=pixels.Length;
            foreach(var p in pixels)dev+=Mathf.Abs(p.r+p.g+p.b-mean);return dev/pixels.Length;
        }

        // ---------- Lot 293 : le service du monde ----------

        // L'horloge passée à la main (le service tourne à vitesse 0) : un tick, et le tick rendu ; -1 et un défaut sinon.
        static long Tick(int port,List<string> faults)
        {
            string url="http://127.0.0.1:"+port+"/tick?n=1";
            try
            {
                using var http=new HttpClient{Timeout=TimeSpan.FromSeconds(60)};
                using var reponse=http.PostAsync(url,new ByteArrayContent(new byte[0])).GetAwaiter().GetResult();
                string corps=reponse.Content.ReadAsStringAsync().GetAwaiter().GetResult();
                if((int)reponse.StatusCode!=200){faults.Add("service : POST "+url+" rend le statut "+(int)reponse.StatusCode+" ("+corps+")");return -1;}
                if(LecteurJson.LireObjet(corps).TryGetValue("tick",out var tick)&&tick is double t)return (long)t;
                faults.Add("service : POST "+url+" ne rend pas de tick ("+corps+")");return -1;
            }
            catch(Exception e){faults.Add("service : POST "+url+" a échoué ("+e.GetBaseException().Message+")");return -1;}
        }
        static int Rues(ClientPlan plan,long cell,List<string> faults)
        {
            var lu=plan.Lire(cell);if(lu.Presente)return lu.Plan.Rues.Count;
            faults.Add("service : "+lu.Absence);return -1;
        }

        // ---------- Lot 251 : la caméra du joueur ----------

        static Vector3[] Grid(Vector3 centre,float half,int n)
        {
            var v=new List<Vector3>();
            for(int j=0;j<n;j++)for(int i=0;i<n;i++)v.Add(centre+new Vector3(half*(2f*i/(n-1)-1),0,half*(2f*j/(n-1)-1)));
            return v.ToArray();
        }
        // Hauteur de la caméra au-dessus du sol, par un rayon vertical sur le collider lancé du dessus du
        // terrain : la mesure ne passe pas par la garde. NaN hors du terrain.
        static double Above(Terrain t,Vector3 at)
        {
            float top=t.transform.position.y+t.terrainData.size.y+50;
            return t.GetComponent<TerrainCollider>().Raycast(new Ray(new Vector3(at.x,top,at.z),Vector3.down),out var hit,t.terrainData.size.y+200)?at.y-hit.point.y:double.NaN;
        }
        // SC1 : chaque pose passe par DesertCityCamera.Poser, la méthode du joueur. Cap tous les 30°,
        // inclinaison au minimum, au milieu et au maximum, distance du maximum au minimum par pas de 0,75.
        static Balayage Sweep(DesertCityCamera cam,Terrain t,Vector3[] aims)
        {
            var distances=new List<float>();
            for(float d=DesertCityCamera.DistanceMax;d>DesertCityCamera.DistanceMin;d*=.75f)distances.Add(d);
            distances.Add(DesertCityCamera.DistanceMin);
            var pitches=new[]{DesertCityCamera.InclinaisonMin,(DesertCityCamera.InclinaisonMin+DesertCityCamera.InclinaisonMax)/2,DesertCityCamera.InclinaisonMax};
            var b=new Balayage{prevues=aims.Length*12*pitches.Length*distances.Count,mesurees=0,sous_terrain=0};double worst=double.MaxValue;
            Physics.SyncTransforms();
            foreach(var aim in aims)for(int cap=0;cap<360;cap+=30)foreach(var pitch in pitches)foreach(var d in distances)
            {
                cam.Poser(aim,cap,pitch,d);double m=Above(t,cam.transform.position);
                if(double.IsNaN(m))continue;
                b.mesurees++;if(m<0)b.sous_terrain++;worst=Math.Min(worst,m);
            }
            b.marge_min=b.mesurees>0?worst:-1;return b;
        }

        static Capture[] Player(DesertCityCamera cam,DesertRoads roads,DesertRoadTool tool,Route plain,Joueur j,string id,DesertRoads.Parametres P,int graine)
        {
            var terrain=roads.terrain;var view=cam.GetComponent<Camera>();var o=terrain.transform.position;var size=terrain.terrainData.size;
            view.aspect=1600f/900;
            int end=plain.ax.Length-1,q=plain.ax.Length/2;
            var start=World(terrain,plain.ax[0],plain.ay[0]);var mid=World(terrain,plain.ax[q],plain.ay[q]);
            var along=World(terrain,plain.ax[Math.Min(q+4,end)],plain.ay[Math.Min(q+4,end)])-World(terrain,plain.ax[Math.Max(q-4,0)],plain.ay[Math.Max(q-4,0)]);along.y=0;along.Normalize();
            var side=Vector3.Cross(Vector3.up,along);
            float Heading(Vector3 d)=>Mathf.Atan2(d.x,d.z)*Mathf.Rad2Deg;

            // SC1 — le terrain entier, moins 60 m de marge.
            j.balayage=Sweep(cam,terrain,Grid(new Vector3(o.x+size.x/2,0,o.z+size.z/2),size.x/2-60,9));

            // SC2 — le zoom, au milieu de la route de plaine ; la caméra se tient du côté du centre.
            var outward=mid-(o+size/2);outward.y=0;double near=double.MaxValue,far=0;
            foreach(var d in Enumerable.Range(0,60).Select(k=>100000*Mathf.Pow(.75f,k)).Append(0f))
            {
                cam.Poser(mid,Heading(outward),(DesertCityCamera.InclinaisonMin+DesertCityCamera.InclinaisonMax)/2,d);
                double got=Vector3.Distance(view.transform.position,cam.Vise);near=Math.Min(near,got);far=Math.Max(far,got);
            }
            j.zoom=new Zoom{distance_min=near,distance_max=far,hauteur_rue=Above(terrain,view.transform.position)};

            // SC4 — ce que voit le joueur.
            string folder=Output+id+"/camera/";Directory.CreateDirectory(folder);
            foreach(var old in Directory.GetFiles(folder,"*.png"))File.Delete(old);
            var shots=new List<Capture>();
            cam.VueEnsemble();shots.Add(new Capture{nom="ensemble",ecart=Photo(view,tool,folder+"ensemble.png")});
            cam.Poser(mid+side*(float)(plain.largeur/2),Heading(along),20,0);shots.Add(new Capture{nom="rue",ecart=Photo(view,tool,folder+"rue.png")});

            // SC3 — le marcheur du joueur : descendre au départ de la route, remonter, marcher, buter sur le mur.
            var first=World(terrain,plain.ax[Math.Min(4,end)],plain.ay[Math.Min(4,end)])-start;first.y=0;
            cam.Poser(start,Heading(first),30,25);
            var fromPos=view.transform.position;var fromAim=fromPos+view.transform.forward*cam.Distance;
            cam.Descendre();Physics.SyncTransforms();
            j.oeil=cam.Marcheur.walking?Above(terrain,view.transform.position):-1;
            if(cam.Marcheur.walking)shots.Add(new Capture{nom="marcheur",ecart=Photo(view,tool,folder+"marcheur.png")});
            cam.Remonter();
            j.retour=cam.Marcheur.walking?-1:Math.Max(Vector3.Distance(view.transform.position,fromPos),Vector3.Distance(view.transform.position+view.transform.forward*cam.Distance,fromAim));
            j.marche=Walk(cam.Marcheur,terrain,plain);
            var wall=Wall(terrain,plain);
            j.mur=new Route{id=plain.id,famille="mur",acceptee=true,ax=plain.ax,ay=plain.ay,marche=Walk(cam.Marcheur,terrain,plain)};
            Object.DestroyImmediate(wall);Physics.SyncTransforms();

            // Contre-épreuve : sur une copie fraîche, un disque de 30 m relevé de 40 m au milieu de la route.
            roads.Preparer(P,graine);var td=roads.Copie;int n=td.heightmapResolution;float step=td.size.x/(n-1);
            int i0=Mathf.Clamp(Mathf.FloorToInt((mid.x-o.x-31)/step),0,n-1),i1=Mathf.Clamp(Mathf.CeilToInt((mid.x-o.x+31)/step),0,n-1);
            int j0=Mathf.Clamp(Mathf.FloorToInt((mid.z-o.z-31)/step),0,n-1),j1=Mathf.Clamp(Mathf.CeilToInt((mid.z-o.z+31)/step),0,n-1);
            var h=td.GetHeights(i0,j0,i1-i0+1,j1-j0+1);
            for(int b=0;b<=j1-j0;b++)for(int a=0;a<=i1-i0;a++)
            {
                float dx=o.x+(i0+a)*step-mid.x,dz=o.z+(j0+b)*step-mid.z;
                if(dx*dx+dz*dz<=30*30)h[b,a]=Mathf.Min(1,h[b,a]+40/td.size.y);
            }
            td.SetHeights(i0,j0,h);Physics.SyncTransforms();
            var around=Grid(new Vector3(mid.x,0,mid.z),45,5);
            j.releve=Sweep(cam,terrain,around);
            cam.garde=false;j.sans_garde=Sweep(cam,terrain,around);cam.garde=true;
            return shots.ToArray();
        }

        static Rapport Run(string id)
        {
            var clock=Stopwatch.StartNew();var faults=new List<string>();
            var gestes=DesertRoads.Lire(id);var P=gestes.parametres;
            var report=new Rapport{implantation=id,scene=ScenePath(id),graine=gestes.graine};
            var roads=Object.FindFirstObjectByType<DesertRoads>();var tool=Object.FindFirstObjectByType<DesertRoadTool>();
            if(!roads||!tool)throw new InvalidOperationException("Scène sans routes du joueur : relancer py local3d/atelier_desert.py terrain");
            if(gestes.routes==null||gestes.routes.Length==0)throw new InvalidOperationException("Jeu de gestes vide : "+DesertRoads.CheminGestes(id));
            var sv=report.service;sv.cell=tool.Cellule;sv.port=tool.Port;
            using var plan=new ClientPlan(tool.Port,TimeSpan.FromSeconds(1));
            tool.automatique=true;var terrain=roads.terrain;var camera=tool.view;var env=Object.FindFirstObjectByType<DesertEnvironment>();
            // Lot 251 : la caméra du joueur s'est branchée seule au chargement ; le contrôle la pilote.
            var player=camera.GetComponent<DesertCityCamera>();report.camera.branchee=player;
            if(player){player.automatique=true;player.Poser(player.Vise,player.Cap,player.Inclinaison,player.Distance);}
            if(player&&player.Marcheur)player.Marcheur.automatic=true;
            else{faults.Add("caméra de la ville non branchée : DesertCityCamera absente ou sans marcheur");player=null;}
            var data=DesertCityTerrain.Load(id);
            report.asset_avant=DesertRoads.Empreintes(terrain.terrainData).Tout;

            // A — le jeu de gestes, dans l'ordre, sur une copie fraîche.
            roads.Preparer(P,gestes.graine);var td=roads.Copie;
            report.resolution=td.heightmapResolution;report.couches_resolution=td.alphamapResolution;report.details_resolution=td.detailResolution;
            report.hauteur=td.size.y;report.@base=terrain.transform.position.y;report.quantification=td.size.y/32766.0;
            report.couches=td.terrainLayers.Select(l=>l.name).ToArray();
            report.touffes=td.detailPrototypes.Length==data.touffes.Length?data.touffes:new string[0];
            if(td.detailPrototypes.Length>0&&report.touffes.Length==0)faults.Add("touffes de la copie sans nom");
            Export(roads,id,"avant");
            var routes=new List<Route>();
            foreach(var g in gestes.routes)
            {
                var before=roads.Empreintes();var t0=clock.Elapsed.TotalSeconds;
                var res=roads.Poser(g);
                routes.Add(Record(g,res,before,roads.Empreintes(),clock.Elapsed.TotalSeconds-t0));
            }
            report.routes=routes.ToArray();
            foreach(var r in routes.Where(r=>r.acceptee))Measure(terrain,r);
            Export(roads,id,"apres");ExportGround(roads,id,report.touffes);
            report.empreintes.a=Copy(roads.Empreintes());

            // Le marcheur : chaque route posée, puis la route de plaine barrée d'un mur.
            var body=new GameObject("Marcheur du contrôle").AddComponent<CharacterController>();
            body.height=1.8f;body.radius=.3f;body.center=new Vector3(0,.9f,0);
            var walk=body.gameObject.AddComponent<CitadelTraversal>();
            walk.body=body;walk.view=camera;walk.routes=new CitadelTraversal.Route[0];walk.plots=new CitadelTraversal.Plot[0];walk.automatic=true;
            if(!camera.GetComponent<VillageV2Visit>())camera.gameObject.AddComponent<VillageV2Visit>().enabled=false;
            foreach(var r in routes.Where(r=>r.acceptee))r.marche=Walk(walk,terrain,r);
            var plain=routes.FirstOrDefault(r=>r.famille=="plaine"&&r.acceptee);
            if(plain!=null)
            {
                var wall=Wall(terrain,plain);
                report.mur=new Route{id=plain.id,famille="mur",acceptee=true,ax=plain.ax,ay=plain.ay,marche=Walk(walk,terrain,plain)};
                Object.DestroyImmediate(wall);Physics.SyncTransforms();
            }
            else faults.Add("aucune route de plaine posée : contre-épreuve du mur impossible");
            Object.DestroyImmediate(body.gameObject);

            // Captures : plaine, flanc de dune, bord de près, refus à l'écran.
            string folder=Output+id+"/routes/captures/";Directory.CreateDirectory(folder);
            foreach(var old in Directory.GetFiles(folder,"*.png"))File.Delete(old);
            if(env){env.hour=16.5f;env.Apply();}
            var shots=new List<Capture>();
            void Around(Route r,out Vector3 mid,out Vector3 along,out Vector3 side)
            {
                int q=r.ax.Length/2;mid=World(terrain,r.ax[q],r.ay[q]);
                along=World(terrain,r.ax[Math.Min(q+4,r.ax.Length-1)],r.ay[Math.Min(q+4,r.ax.Length-1)])-World(terrain,r.ax[Math.Max(q-4,0)],r.ay[Math.Max(q-4,0)]);along.y=0;along.Normalize();
                side=Vector3.Cross(Vector3.up,along);
            }
            if(plain!=null)
            {
                Around(plain,out var mid,out var along,out var side);
                shots.Add(new Capture{nom="plaine",ecart=Shot(camera,tool,folder+"plaine.png",mid+side*40-along*30+Vector3.up*24,mid,40)});
                var edge=mid+side*(float)(plain.largeur/2)+along*3;
                var eye=mid+side*((float)plain.largeur/2+5)-along*4;eye.y=terrain.SampleHeight(eye)+terrain.transform.position.y+1.8f;
                shots.Add(new Capture{nom="bord",ecart=Shot(camera,tool,folder+"bord.png",eye,edge,55)});
            }
            var flank=routes.FirstOrDefault(r=>r.famille=="flanc"&&r.acceptee);
            if(flank!=null)
            {
                Around(flank,out var mid,out var along,out var side);
                // Depuis le côté aval et de haut, pour voir la chaussée, le déblai et le remblai.
                float up=World(terrain,-(mid+side*10).x,-(mid+side*10).z).y,down=World(terrain,-(mid-side*10).x,-(mid-side*10).z).y;
                var low=up<down?side:-side;
                shots.Add(new Capture{nom="flanc_de_dune",ecart=Shot(camera,tool,folder+"flanc_de_dune.png",mid+low*26-along*16+Vector3.up*24,mid,42)});
            }
            var steep=gestes.routes.FirstOrDefault(g=>g.famille=="raide_long");
            if(steep!=null)
            {
                // Le refus passe par l'outil du joueur : les points sont cliqués à l'écran.
                var centre=World(terrain,steep.x.Average(),steep.y.Average());
                var rt=new RenderTexture(1600,900,24);camera.targetTexture=rt;
                camera.transform.position=centre+new Vector3(28,70,28);camera.transform.LookAt(centre);camera.fieldOfView=45;
                tool.largeur=steep.largeur;tool.Annuler();
                sv.raide.rues_avant=Rues(plan,sv.cell,faults);bool clique=steep.x.Length>=2;
                for(int i=0;i<steep.x.Length;i++)clique&=tool.Clic(camera.WorldToScreenPoint(World(terrain,steep.x[i],steep.y[i])));
                var res=tool.Valider();camera.targetTexture=null;rt.Release();Object.DestroyImmediate(rt);
                if(res==null||res.acceptee)faults.Add("la route trop raide, cliquée à l'écran, n'est pas refusée");
                // Refusée par le relief, elle n'atteint pas le monde : un vrai tick n'ajoute aucune rue.
                sv.raide.clique=clique;sv.raide.depose=tool.Recu!=null;Tick(sv.port,faults);sv.raide.rues_apres=Rues(plan,sv.cell,faults);
                shots.Add(new Capture{nom="refus",ecart=Shot(camera,tool,folder+"refus.png",centre+new Vector3(28,70,28),centre,45)});
                tool.Annuler();
            }
            report.captures=shots.ToArray();

            // B et C — mêmes gestes, même graine ; puis une autre graine.
            roads.Preparer(P,gestes.graine);foreach(var g in gestes.routes)roads.Poser(g);report.empreintes.b=Copy(roads.Empreintes());
            roads.Preparer(P,gestes.graine+1);foreach(var g in gestes.routes)roads.Poser(g);report.empreintes.autre_graine=Copy(roads.Empreintes());

            // Contre-épreuves : profil relevé de 20 cm ; pente maximale portée à 40 %.
            var plainGeste=gestes.routes.FirstOrDefault(g=>g.famille=="plaine");
            if(plainGeste!=null)
            {
                roads.Preparer(P,gestes.graine);var res=roads.Poser(plainGeste,.2);
                report.profil_releve=Record(plainGeste,res,new DesertRoads.Empreinte(),new DesertRoads.Empreinte(),-1);
                if(res.acceptee)Measure(terrain,report.profil_releve);
            }
            if(steep!=null)
            {
                roads.Preparer(P,gestes.graine);var res=roads.Poser(steep,0,.40);
                report.pente_40=new Decision{id=steep.id,acceptee=res.acceptee,motif=res.motif};
            }

            // Le clic : les points de la route de plaine, projetés à l'écran puis cliqués.
            if(plainGeste!=null)
            {
                roads.Preparer(P,gestes.graine);sv.empreinte_vierge=roads.Empreintes().Tout;
                var centre=World(terrain,plainGeste.x.Average(),plainGeste.y.Average());
                var rt=new RenderTexture(1600,900,24);camera.targetTexture=rt;
                camera.transform.position=centre+new Vector3(0,120,-.5f);camera.transform.LookAt(centre);camera.fieldOfView=60;
                tool.largeur=plainGeste.largeur;tool.Annuler();
                for(int i=0;i<plainGeste.x.Length;i++)tool.Clic(camera.WorldToScreenPoint(World(terrain,plainGeste.x[i],plainGeste.y[i])));
                var res=tool.Valider();camera.targetTexture=null;rt.Release();Object.DestroyImmediate(rt);
                var c=report.clic;c.voulus_x=plainGeste.x;c.voulus_y=plainGeste.y;
                c.obtenus_x=tool.Derniers.Select(p=>p.x).ToArray();c.obtenus_y=tool.Derniers.Select(p=>p.y).ToArray();
                // Le dépôt : un reçu, et le terrain encore vierge ; la route ne se dessine qu'après un vrai tick.
                var pl=sv.plaine;var recu=tool.Recu;
                pl.depose=recu!=null;pl.recu_accepte=recu!=null&&recu.Acceptee;pl.appliquee_au_tick=recu?.AppliqueeAuTick??-1;
                pl.recu=recu==null?"":recu.Acceptee?"acceptée, appliquée au tick "+recu.AppliqueeAuTick:recu.Presente?"refusée ("+recu.Statut+") : "+recu.Erreur:"absente : "+recu.Absence;
                pl.empreinte_avant_tick=roads.Empreintes().Tout;pl.dessinee_avant_tick=tool.Attendre();
                Tick(sv.port,faults);
                if(!tool.Attendre())faults.Add("service : après le tick, l'outil n'a pas relu de plan plus récent que son dépôt");
                var lu=plan.Lire(sv.cell);
                if(lu.Presente)
                {
                    pl.tick_plan=lu.Plan.Tick;
                    var neuves=lu.Plan.Rues.Where(u=>tool.Posees.Any(p=>p.identifiant==u.Identifiant)).ToList();pl.rues_neuves=neuves.Count;
                    if(neuves.Count>0)
                    {
                        var rue=neuves[^1];pl.rue_x=rue.Points.Select(p=>p.X).ToArray();pl.rue_y=rue.Points.Select(p=>p.Y).ToArray();
                        pl.rue_largeur=rue.LargeurM;pl.rue_en_chantier=rue.EnChantier;
                    }
                }
                else faults.Add("service : "+lu.Absence);
                c.acceptee=res!=null&&res.acceptee;c.empreinte_clic=roads.Empreintes().Tout;
                // La référence (décision du propriétaire, issue #293) : la même route posée en terre battue.
                var terre=new DesertRoads.Geste{id=plainGeste.id,famille=plainGeste.famille,revetement="terre",largeur=plainGeste.largeur,x=plainGeste.x,y=plainGeste.y};
                roads.Preparer(P,gestes.graine);roads.Poser(terre);c.empreinte_gestes=roads.Empreintes().Tout;
            }

            // Lot 251 — la caméra du joueur, sur la ville aux routes posées.
            if(player)
            {
                roads.Preparer(P,gestes.graine);foreach(var g in gestes.routes)roads.Poser(g);
                if(plain!=null)report.captures_camera=Player(player,roads,tool,plain,report.camera,id,P,gestes.graine);
                else faults.Add("aucune route de plaine posée : caméra du joueur non contrôlée");
            }

            roads.Restaurer();
            report.asset_apres=DesertRoads.Empreintes(terrain.terrainData).Tout;
            report.defauts=faults.ToArray();report.duree_s=clock.Elapsed.TotalSeconds;
            return report;
        }
    }
}
