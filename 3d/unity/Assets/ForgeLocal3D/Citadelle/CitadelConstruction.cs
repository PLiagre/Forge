using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEngine;
using UnityEngine.InputSystem;
using UnityEngine.SceneManagement;

namespace ForgeLocal3D
{
    // Chantier local de la visite : les poses sont les seules données sauvegardées.
    public sealed class CitadelConstruction : MonoBehaviour
    {
        [Serializable] public class Placement
        {
            public string module;public int plot,turn;public Vector3 anchor;
            [NonSerialized] public GameObject instance;
        }
        [Serializable] class SaveData { public int schema=1;public string scene;public Placement[] pieces; }
        public CitadelHabitatKit kit;public Camera view;public CitadelTraversal walk;
        public bool active;public const int Limit=120;
        public static CitadelConstruction Current {get;private set;}
        public bool BlocksPointer=>active&&Mouse.current!=null&&Panel.Contains(new Vector2(Mouse.current.position.ReadValue().x,Screen.height-Mouse.current.position.ReadValue().y));
        public IReadOnlyList<Placement> Pieces=>pieces;
        public string Diagnostic=>"actif="+active+" rotation="+turn+" pointeur="+hasPointer+" valide="+valid+" ancre="+anchor+" motif="+verdict+" pièces="+pieces.Count;
        [NonSerialized] public string savePathOverride;
        public string SavePath=>savePathOverride??Path.Combine(Application.persistentDataPath,"habitat_"+SceneManager.GetActiveScene().name+".json");
        readonly List<Placement> pieces=new List<Placement>();
        readonly Stack<Placement[]> history=new Stack<Placement[]>();
        int selected,plot,turn,preset=-1;float elevation;
        GameObject preview,grid;Vector3 anchor;bool valid,hasPointer,oldPanel;
        CitadelEnvironment environment;VillageV2Visit orbit;string hint="Choisis une maison ou commence par un socle en pierre.";
        string verdict="";float noticeUntil;Material lineMaterial;
        MaterialPropertyBlock tint;
        void Awake(){tint=new MaterialPropertyBlock();}
        Vector2 scroll;
        Rect Panel=>new Rect(16,16,344,Mathf.Min(Screen.height-32,820));
        void OnEnable(){Current=this;}
        void OnDisable(){if(Current==this)Current=null;}
        void Start()
        {
            environment=FindFirstObjectByType<CitadelEnvironment>();orbit=view.GetComponent<VillageV2Visit>();
            // Les contrôles automatisés travaillent dans un fichier distinct et ne
            // chargent jamais les constructions personnelles pendant une mesure.
            bool measurement=Environment.GetCommandLineArgs().Any(a=>a=="-forge-benchmark"||a=="-forge-construction-check");
            if(measurement)savePathOverride=Path.Combine(Application.temporaryCachePath,"forge-mesures","habitat_"+SceneManager.GetActiveScene().name+".json");
            else Load(SavePath);
        }
        public void Toggle()
        {
            if(!active)
            {
                walk.Leave();oldPanel=environment.showPanel;environment.showPanel=false;active=true;FocusPlot();MakePreview();
            }
            else
            {
                active=false;environment.showPanel=oldPanel;ClearPreview();if(grid)Destroy(grid);
            }
        }
        void FocusPlot()
        {
            var p=walk.plots[plot];orbit.focus=p.position+Vector3.up*3;orbit.yaw=38;orbit.pitch=35;orbit.minPitch=10;orbit.distance=43;
            view.fieldOfView=42;view.transform.SetPositionAndRotation(orbit.focus+Quaternion.Euler(orbit.pitch,orbit.yaw,0)*Vector3.back*orbit.distance,Quaternion.Euler(orbit.pitch,orbit.yaw,0));
            elevation=0;DrawGrid();
        }
        void ClearPreview(){if(preview){preview.SetActive(false);Destroy(preview);}preview=null;}
        void MakePreview()
        {
            ClearPreview();preview=Instantiate(preset>=0?kit.houses[preset]:kit.modules[selected].prefab,transform);
            preview.name="Aperçu du chantier";
            foreach(var c in preview.GetComponentsInChildren<Collider>(true))c.enabled=false;
            foreach(var r in preview.GetComponentsInChildren<Renderer>(true))r.shadowCastingMode=UnityEngine.Rendering.ShadowCastingMode.Off;
        }
        void DrawGrid()
        {
            if(grid)Destroy(grid);grid=new GameObject("Grille de la clairière");grid.transform.SetParent(transform);
            if(!lineMaterial)lineMaterial=new Material(kit.gridMaterial);
            var p=walk.plots[plot];float hx=Mathf.Floor(p.size.x/2/kit.grid)*kit.grid,hz=Mathf.Floor(p.size.y/2/kit.grid)*kit.grid;
            void Line(Vector3 a,Vector3 b)
            {
                var go=new GameObject("Trame 0,75 m");go.transform.SetParent(grid.transform);var r=go.AddComponent<LineRenderer>();
                r.sharedMaterial=lineMaterial;r.startWidth=r.endWidth=.028f;r.positionCount=2;r.useWorldSpace=true;
                r.SetPositions(new[]{p.position+a+Vector3.up*.08f,p.position+b+Vector3.up*.08f});r.shadowCastingMode=UnityEngine.Rendering.ShadowCastingMode.Off;
            }
            for(float x=-hx;x<=hx+.01f;x+=kit.grid)Line(new Vector3(x,0,-hz),new Vector3(x,0,hz));
            for(float z=-hz;z<=hz+.01f;z+=kit.grid)Line(new Vector3(-hx,0,z),new Vector3(hx,0,z));
        }
        CitadelHabitatKit.Module Module(string id)=>kit.modules.FirstOrDefault(m=>m.id==id);
        Vector3 Size(Placement p)
        {
            Vector3 v=Module(p.module).size;return p.turn%2==0?v:new Vector3(v.z,v.y,v.x);
        }
        Bounds Volume(Placement p)
        {
            Vector3 s=Size(p);return new Bounds(p.anchor+Vector3.up*s.y/2,s-Vector3.one*.035f);
        }
        bool Covers(Placement p,Vector3 point,float inset=0)
        {
            Vector3 s=Size(p);return Mathf.Abs(point.x-p.anchor.x)<=s.x/2-inset+.02f&&Mathf.Abs(point.z-p.anchor.z)<=s.z/2-inset+.02f;
        }
        public bool CanPlace(Placement p,IReadOnlyList<Placement> context,out string reason)
        {
            reason="";var m=Module(p.module);
            if(m==null||p.plot<0||p.plot>=walk.plots.Length){reason="Module ou terrain inconnu.";return false;}
            if(!float.IsFinite(p.anchor.x)||!float.IsFinite(p.anchor.y)||!float.IsFinite(p.anchor.z)||p.turn<0||p.turn>3)
            {reason="Coordonnées invalides.";return false;}
            Vector3 s=Size(p);var land=walk.plots[p.plot];
            if(Mathf.Abs(p.anchor.x)+s.x/2>land.size.x/2+.01f||Mathf.Abs(p.anchor.z)+s.z/2>land.size.y/2+.01f)
            {reason="La pièce doit rester dans la clairière.";return false;}
            if(p.anchor.y<-.01f||p.anchor.y>12){reason="Hauteur autorisée : de 0 à 12 m.";return false;}
            foreach(float coordinate in new[]{p.anchor.x,p.anchor.y,p.anchor.z})
                if(Mathf.Abs(coordinate/kit.grid-Mathf.Round(coordinate/kit.grid))>.001f)
                {reason="Pose hors de la grille.";return false;}
            var neighbors=context.Where(q=>q.plot==p.plot&&!ReferenceEquals(q,p)).ToArray();
            foreach(var q in neighbors)
            {
                bool decorative=(m.kind=="ornement")!=(Module(q.module).kind=="ornement");
                if(!decorative&&Volume(p).Intersects(Volume(q))||p.module==q.module&&(p.anchor-q.anchor).sqrMagnitude<.001f)
                {reason="Une pièce occupe déjà cet emplacement.";return false;}
            }
            if(m.kind=="ornement")
            {
                if(!neighbors.Any(q=>Module(q.module).kind=="toit"&&Covers(q,p.anchor)&&p.anchor.y>=q.anchor.y&&p.anchor.y<=q.anchor.y+Size(q).y))
                {reason="Pose cet élément dans une toiture existante.";return false;}
                return true;
            }
            if(p.anchor.y<.01f)
            {
                if(m.kind!="base"){reason="Commence par un rez-de-chaussée en pierre.";return false;}
                return true;
            }
            bool Support(Vector3 point)=>neighbors.Any(q=>Module(q.module).kind!="ornement"&&Module(q.module).kind!="toit"&&
                Mathf.Abs(q.anchor.y+Size(q).y-p.anchor.y)<.03f&&Covers(q,point));
            // Les quatre coins empêchent une pièce suspendue ou un étage posé sur une seule marche.
            foreach(float x in new[]{-1f,1f})foreach(float z in new[]{-1f,1f})
                if(!Support(p.anchor+new Vector3(x*(s.x/2-.08f),0,z*(s.z/2-.08f))))
                {reason="Il faut un appui sous les quatre coins, à cette hauteur.";return false;}
            return true;
        }
        Placement[] Candidates(string module,int site,Vector3 position,int rotation,int house=-1)
        {
            if(house<0)return new[]{new Placement{module=module,plot=site,anchor=position,turn=rotation}};
            return kit.houses[house].GetComponent<LODGroup>().GetLODs()[0].renderers.Select(r=>new Placement{
                module=r.name,plot=site,anchor=position+Quaternion.Euler(0,rotation*90,0)*r.transform.localPosition,
                turn=((Mathf.RoundToInt(r.transform.localEulerAngles.y/90)+rotation)%4+4)%4}).ToArray();
        }
        public bool CanBatch(Placement[] batch,out string reason)
        {
            reason="";if(batch.Length==0||pieces.Count+batch.Length>Limit){reason="Budget du chantier : "+Limit+" pièces maximum.";return false;}
            var draft=new List<Placement>(pieces);
            foreach(var p in batch){if(!CanPlace(p,draft,out reason))return false;draft.Add(p);}
            return true;
        }
        void Spawn(Placement p)
        {
            p.instance=Instantiate(Module(p.module).prefab,walk.plots[p.plot].position+p.anchor,Quaternion.Euler(0,p.turn*90,0),transform);
            p.instance.name=Module(p.module).label;
            var marker=p.instance.AddComponent<CitadelBuiltPiece>();marker.module=p.module;marker.plot=p.plot;marker.turn=p.turn;marker.anchor=p.anchor;
            pieces.Add(p);
        }
        public bool Place(Placement[] batch,bool persist=true)
        {
            if(!CanBatch(batch,out var reason)){Notice(reason);return false;}
            foreach(var p in batch)Spawn(p);history.Push(batch);if(persist&&!Save(SavePath))return true;
            Notice(batch.Length==1?"Pièce posée.":"Maison assemblée : "+batch.Length+" pièces modifiables.");return true;
        }
        public Placement[] House(int index,int site,Vector3 position,int rotation)=>Candidates(null,site,position,rotation,index);
        public bool Remove(Placement[] removed,bool persist=true)
        {
            if(removed.Length==0||removed.Any(p=>!pieces.Contains(p)))return false;
            var remaining=pieces.Except(removed).ToArray();
            foreach(var p in remaining)if(!CanPlace(p,remaining,out _)){Notice("Retire d’abord les pièces qui reposent dessus.");return false;}
            foreach(var p in removed){pieces.Remove(p);if(p.instance){p.instance.SetActive(false);Destroy(p.instance);}}
            if(persist&&!Save(SavePath))return true;Notice("Pièce retirée.");return true;
        }
        public bool UndoLast(bool persist=true)
        {
            if(history.Count==0)return false;var batch=history.Peek();if(!Remove(batch,persist))return false;history.Pop();return true;
        }
        public bool WalkHere()
        {
            var land=walk.plots[plot];Physics.SyncTransforms();
            // Chercher un vrai sol libre à l'intérieur de la terrasse. Son bord
            // extérieur peut être un talus ; une position fixe y ferait chuter le visiteur.
            for(int side=0;side<4;side++)for(float t=-1;t<=1.01f;t+=.25f)
            {
                Vector3 local=side<2?new Vector3(t*(land.size.x/2-.65f),0,(side==0?1:-1)*(land.size.y/2-.65f)):
                    new Vector3((side==2?1:-1)*(land.size.x/2-.65f),0,t*(land.size.y/2-.65f));
                Vector3 point=land.position+local;
                if(!Physics.Raycast(point+Vector3.up*2,Vector3.down,out var hit,3)||hit.normal.y<.75f||Mathf.Abs(hit.point.y-land.position.y)>.5f)continue;
                point=hit.point+Vector3.up*.05f;
                if(Physics.CheckCapsule(point+Vector3.up*.34f,point+Vector3.up*1.5f,.30f))continue;
                Vector3 original=walk.spawn;if(active)Toggle();walk.spawn=point;walk.Enter();walk.spawn=original;return true;
            }
            Notice("Libère un passage au bord du chantier pour y marcher.");return false;
        }
        public bool Save(string path)
        {
            try
            {
                Directory.CreateDirectory(Path.GetDirectoryName(path));string temp=path+".tmp";
                File.WriteAllText(temp,JsonUtility.ToJson(new SaveData{scene=SceneManager.GetActiveScene().name,pieces=pieces.ToArray()},true));
                if(File.Exists(path))File.Replace(temp,path,path+".bak");else File.Move(temp,path);
                return true;
            }
            catch(Exception e)when(e is IOException||e is UnauthorizedAccessException){Notice("Sauvegarde impossible : "+e.Message);return false;}
        }
        public bool Load(string path)
        {
            if(!File.Exists(path))return true;
            try
            {
                var data=JsonUtility.FromJson<SaveData>(File.ReadAllText(path));
                if(data==null||data.schema!=1||data.pieces==null||data.scene!=SceneManager.GetActiveScene().name)throw new InvalidDataException("Format ou scène incompatible.");
                var draft=new List<Placement>();
                foreach(var p in data.pieces)
                {
                    if(p==null||draft.Count>=Limit||!CanPlace(p,draft,out _))throw new InvalidDataException("Une pièce ne respecte plus les appuis du kit.");
                    draft.Add(p);
                }
                foreach(var p in pieces)if(p.instance){p.instance.SetActive(false);Destroy(p.instance);}pieces.Clear();history.Clear();
                foreach(var p in draft)Spawn(p);return true;
            }
            catch(Exception e)when(e is IOException||e is ArgumentException||e is UnauthorizedAccessException)
            {Notice("Construction non chargée : "+e.Message);return false;}
        }
        void Notice(string text){hint=text;noticeUntil=Time.unscaledTime+5;}
        void Update()
        {
            var k=Keyboard.current;var mouse=Mouse.current;if(k==null||mouse==null)return;
            if(k.bKey.wasPressedThisFrame)Toggle();if(!active)return;
            if(k.escapeKey.wasPressedThisFrame||k.tabKey.wasPressedThisFrame){Toggle();return;}
            if(k.rKey.wasPressedThisFrame)turn=(turn+1)%4;
            if(k.pageUpKey.wasPressedThisFrame)elevation=Mathf.Min(12,elevation+kit.storey/2);
            if(k.pageDownKey.wasPressedThisFrame)elevation=Mathf.Max(0,elevation-kit.storey/2);
            if((k.leftCtrlKey.isPressed||k.rightCtrlKey.isPressed)&&k.zKey.wasPressedThisFrame)UndoLast();
            Vector2 pointer=mouse.position.ReadValue();bool overPanel=Panel.Contains(new Vector2(pointer.x,Screen.height-pointer.y));
            hasPointer=false;Ray ray=view.ScreenPointToRay(pointer);
            if(!overPanel&&new Plane(Vector3.up,walk.plots[plot].position+Vector3.up*elevation).Raycast(ray,out float distance))
            {
                Vector3 local=ray.GetPoint(distance)-walk.plots[plot].position;
                anchor=new Vector3(Mathf.Round(local.x/kit.grid)*kit.grid,elevation,Mathf.Round(local.z/kit.grid)*kit.grid);
                hasPointer=true;
            }
            if(preview)
            {
                preview.SetActive(hasPointer);preview.transform.SetPositionAndRotation(walk.plots[plot].position+anchor,Quaternion.Euler(0,turn*90,0));
                var batch=Candidates(kit.modules[selected].id,plot,anchor,turn,preset);valid=hasPointer&&CanBatch(batch,out verdict);
                tint.SetColor("_BaseColor",valid?new Color(.35f,1,.68f):new Color(1,.22f,.18f));
                foreach(var r in preview.GetComponentsInChildren<Renderer>())r.SetPropertyBlock(tint);
                if(hasPointer&&mouse.leftButton.wasPressedThisFrame&&valid)Place(batch);
            }
            if(!overPanel&&k.deleteKey.wasPressedThisFrame&&Physics.Raycast(ray,out var hit,600))
            {
                var marker=hit.collider.GetComponentInParent<CitadelBuiltPiece>();
                var p=marker?pieces.FirstOrDefault(x=>x.instance==marker.gameObject):null;
                if(p!=null&&Remove(new[]{p}))history.Clear();
            }
        }
        void OnDestroy(){if(lineMaterial)Destroy(lineMaterial);}
        void OnGUI()
        {
            if(!active)return;
            var previous=GUI.matrix;
            // Le panneau reste assez court pour une fenêtre 720p ; aucune information cachée sous la scène.
            var content=GUI.contentColor;GUI.color=new Color(.025f,.045f,.055f,.96f);GUI.DrawTexture(Panel,Texture2D.whiteTexture);GUI.color=Color.white;
            GUI.contentColor=new Color(.94f,.92f,.86f);
            GUILayout.BeginArea(new Rect(28,26,320,Panel.height-20));scroll=GUILayout.BeginScrollView(scroll);
            GUILayout.Label("ATELIER DES HABITATIONS",new GUIStyle(GUI.skin.label){fontSize=19,fontStyle=FontStyle.Bold});
            GUILayout.Label("Pierre · colombages · ardoise et tuile");
            GUILayout.BeginHorizontal();
            if(GUILayout.Button("‹",GUILayout.Width(30))){plot=(plot+walk.plots.Length-1)%walk.plots.Length;FocusPlot();}
            GUILayout.Label("Clairière "+(plot+1)+" / "+walk.plots.Length);
            if(GUILayout.Button("›",GUILayout.Width(30))){plot=(plot+1)%walk.plots.Length;FocusPlot();}GUILayout.EndHorizontal();
            GUILayout.Space(6);GUILayout.Label("MAISONS PRÉASSEMBLÉES");
            for(int row=0;row<2;row++)
            {
                GUILayout.BeginHorizontal();for(int col=0;col<3;col++){int i=row*3+col;
                    if(GUILayout.Toggle(preset==i,"Maison "+(i+1),"Button")&&preset!=i){preset=i;MakePreview();}}
                GUILayout.EndHorizontal();
            }
            GUILayout.Space(6);GUILayout.Label("PIÈCES À ASSEMBLER");
            for(int i=0;i<kit.modules.Length;i++)
                if(GUILayout.Toggle(preset<0&&selected==i,kit.modules[i].label,"Button",GUILayout.Height(23))&&(preset>=0||selected!=i))
                {preset=-1;selected=i;MakePreview();}
            GUILayout.Space(6);GUILayout.BeginHorizontal();
            if(GUILayout.Button("− 1,5 m"))elevation=Mathf.Max(0,elevation-kit.storey/2);
            GUILayout.Label("Niveau "+elevation.ToString("0.0")+" m");
            if(GUILayout.Button("+ 1,5 m"))elevation=Mathf.Min(12,elevation+kit.storey/2);GUILayout.EndHorizontal();
            if(GUILayout.Button("R · Rotation : "+turn*90+"°"))turn=(turn+1)%4;
            GUILayout.BeginHorizontal();if(GUILayout.Button("Annuler la pose"))UndoLast();
            if(GUILayout.Button("Enregistrer"))if(Save(SavePath))Notice("Construction enregistrée.");GUILayout.EndHorizontal();
            GUILayout.Label(pieces.Count+" / "+Limit+" pièces · sauvegarde automatique");
            GUILayout.Label(Time.unscaledTime<noticeUntil?hint:hasPointer?(valid?"Clic gauche : poser ici.":verdict):"Pointe la grille pour placer la sélection.",new GUIStyle(GUI.skin.label){wordWrap=true});
            GUILayout.Label("Clic : poser · R : tourner · Suppr : retirer\nPg préc./suiv. : hauteur · Ctrl+Z : annuler\nClic droit : orbite · Molette : zoom",new GUIStyle(GUI.skin.label){fontSize=11});
            if(GUILayout.Button("Marcher près de la construction"))
                WalkHere();
            if(GUILayout.Button("B / Échap · Revenir à la visite"))Toggle();
            GUILayout.EndScrollView();GUILayout.EndArea();GUI.matrix=previous;GUI.contentColor=content;
        }
    }
}
