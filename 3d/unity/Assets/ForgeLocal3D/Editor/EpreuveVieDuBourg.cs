using System;using System.Collections;using System.Collections.Generic;using System.Globalization;using System.IO;using System.Linq;using System.Net.Http;using System.Text;using System.Threading.Tasks;using Forge.Pont;using UnityEditor;using UnityEngine;using Object=UnityEngine.Object;
namespace ForgeLocal3D
{
    // Lot 781 : la session commune aux deux scénarios de `Captures/Lot781.cs`, sur le service d'épreuve (#777) que la capture lance avec
    // -forgeServiceEpreuve, graine 0, tick 0, horloge arrêtée. Biskra s'ouvre par son unique départ ; plan, bourg et occupation sont lus
    // au service, hors du fil d'Unity, jamais fabriqués. Les maisons de base dessinées reçoivent fumée et lampe (EffetsDeMaison, #779) ;
    // un comptoir temporaire, sur la place, reçoit les denrées (EtalDuBourg, #780), référence : la nourriture initiale lue.
    // 01 relève la place nourrie à 19,6 h ; 02 vide le panier une seule fois (POST /epreuve/vider-panier), relit les trois routes et
    // réapplique aux mêmes objets. -forgeGarderEtalPlein saute la seule seconde application de l'étal : l'anomalie est relevée, pas cachée.
    // Rapport : `vie-bourg.json` du dossier des captures, réécrit à chaque étape ; son défaut reste nommé tant que la session n'a pas fini.
    public static class EpreuveVieDuBourg
    {
        public const double Heure=19.6;public const string GarderEtalPlein="-forgeGarderEtalPlein";const string Siege="Biskra",Vivres="nourriture";
        const float Recul=3.5f;const int Images=60,ImagesMax=600;static readonly TimeSpan Delai=TimeSpan.FromSeconds(10);
        static readonly Dictionary<EffetsDeMaison,(long rang,long indice)> ids=new();static readonly Dictionary<EffetsDeMaison,float> soir=new();static readonly List<string> etats=new();
        static DesertRoadTool outil;static EffetsDeMaison temoin;static EtalDuBourg etal;static Renderer comptoir;static Transform racine;static long cellule=-1;static string etape="aucune",cadrage;
        static Vector3 visePose;static float capPose,incPose=22f,distPose;static Material ciel;
        // Apply écrit dans l'asset du ciel : on retire la marque avant la fermeture, le fichier du projet ne bouge pas.
        static EpreuveVieDuBourg(){EditorApplication.quitting+=()=>{if(ciel)EditorUtility.ClearDirty(ciel);};}
        static bool Contre=>Environment.GetCommandLineArgs().Contains(GarderEtalPlein);
        static Exception Faux(string m)=>new InvalidOperationException(m);

        public static IEnumerator Nourrie(Camera camera)=>Derouler(PlaceNourrie(camera));
        public static IEnumerator Affamee(Camera camera)=>Derouler(PlaceAffamee(camera));
        // Toute exception nomme son étape dans le rapport, puis fait échouer la capture.
        static IEnumerator Derouler(IEnumerator corps)
        {while(true){bool suite;try{suite=corps.MoveNext();}catch(Exception e){Ecrire(etape+" : "+e.GetBaseException().Message);throw;}if(!suite)yield break;yield return null;}}
        static void Etape(string nom){etape=nom;Ecrire("session interrompue pendant : "+nom);}

        static IEnumerator PlaceNourrie(Camera camera)
        {
            etats.Clear();ids.Clear();soir.Clear();cellule=-1;cadrage=null;temoin=null;etal=null;if(racine)Object.Destroy(racine.gameObject);Etape("ouverture de "+Siege);
            outil=Object.FindFirstObjectByType<DesertRoadTool>()??throw Faux("pas d'outil des routes");var ville=camera.GetComponent<DesertCityCamera>()??throw Faux("pas de caméra de ville");
            var lieu=Object.FindFirstObjectByType<PanneauLieu>()??throw Faux("pas de panneau du lieu");var env=Object.FindFirstObjectByType<DesertEnvironment>()??throw Faux("pas de DesertEnvironment");
            // VillageV2Visit reprend la caméra à chaque image : sans ça, les deux photos ne cadrent plus la place.
            var visite=camera.GetComponent<VillageV2Visit>();if(visite)visite.enabled=false;
            outil.automatique=ville.automatique=true;if(ville.Marcheur)ville.Marcheur.automatic=true;env.showPanel=false;int port=outil.Port;
            var departs=Task.Run(()=>{using(var d=new ClientDeparts(port,ClientDeparts.DelaiMinimal))return d.Lire();});while(!departs.IsCompleted)yield return null;
            if(!departs.Result.Presente)throw Faux(departs.Result.Absence);
            var zab=departs.Result.Donnees.Fiches.Where(f=>f.Siege.Nom==Siege).ToArray();if(zab.Length!=1)throw Faux(zab.Length+" départ(s) au siège "+Siege);
            cellule=zab[0].CellId;if(!outil.Ouvrir(cellule))throw Faux(outil.Message);lieu.Ouvrir(cellule);
            Etape("première lecture");var t=Lire(port);while(!t.IsCompleted)yield return null;var l=Verifier(t.Result,true,-1);
            Etape("montage");Monter(l.p.Plan,l.b.Donnees.Stocks[Vivres],camera);env.hour=(float)Heure;env.Apply();Appliquer(l,true);Cadrer(camera);
            // Les particules se forment ; toutes les maisons habitées fument au panier garni.
            for(int i=0;i<ImagesMax&&(i<Images||ids.Keys.Any(e=>e.Fumee.particleCount==0));i++)yield return null;
            Etape("relevé de la place nourrie");Cadrer(camera);
            foreach(var e in ids.Keys){if(!e.Fumee.isEmitting||e.Fumee.particleCount==0||!e.Lampe.isActiveAndEnabled||!(e.Lampe.intensity>0))throw Faux(e.name+" : "+e.Fumee.particleCount+" particule(s), lampe "+e.Lampe.intensity);soir[e]=e.Lampe.intensity;}
            Champ(camera,true);cadrage=Matrice(camera);Relever("nourrie",l.b.Donnees,camera);
        }

        static IEnumerator PlaceAffamee(Camera camera)
        {
            if(!etal||!temoin||cadrage==null)throw Faux("le scénario « 01-place-nourrie » n'a pas relevé la place");
            Etape("retrait du panier");int port=outil.Port;long c=cellule;var post=Task.Run(()=>Vider(port,c));while(!post.IsCompleted)yield return null;
            var (statut,corps)=post.Result;if(statut!=200)throw Faux("POST /epreuve/vider-panier?cell="+L(c)+" a rendu "+statut+" : "+corps);
            var r=LecteurJson.LireObjet(corps);long Cle(string k)=>r.TryGetValue(k,out var v)&&v is double d?(long)d:throw Faux("POST : clé "+k+" absente ou non entière : "+corps);
            if(Cle("cell_id")!=c)throw Faux("POST : cellule "+L(Cle("cell_id"))+" rendue pour "+L(c));
            // #777 republie sans avancer le tick : les trois routes sont relues même au même numéro.
            Etape("seconde lecture");var t=Lire(port);while(!t.IsCompleted)yield return null;var l=Verifier(t.Result,false,Cle("tick"));
            var env=Object.FindFirstObjectByType<DesertEnvironment>()??throw Faux("pas de DesertEnvironment");env.hour=(float)Heure;env.Apply();
            Appliquer(l,!Contre);Cadrer(camera);for(int i=0;i<Images;i++)yield return null;
            Etape("relevé de la place affamée");Cadrer(camera);
            foreach(var e in ids.Keys)if(e.Fumee.isEmitting||e.Fumee.particleCount>0||!e.Lampe.isActiveAndEnabled||e.Lampe.intensity!=soir[e])throw Faux(e.name+" : "+e.Fumee.particleCount+" particule(s), lampe "+e.Lampe.intensity+" au lieu de "+soir[e]);
            if(Matrice(camera)!=cadrage)throw Faux("cadrage changé depuis la place nourrie");
            Champ(camera,Contre);Relever("affamee",l.b.Donnees,camera);
            if(Contre)Debug.Log("CAPTURE_781 contre-épreuve "+GarderEtalPlein+" : "+Visibles(camera)+" garniture(s) alimentaire(s) visible(s) au panier vide");
            Ecrire(null);
        }

        static Task<(LecturePlan p,Lecture<BourgLu> b,Lecture<OccupationLue> o)> Lire(int port)
        {long c=cellule;return Task.Run(()=>{using(var plan=new ClientPlan(port,Delai))using(var vie=new ClientVieDuBourg(port,Delai))return (plan.Lire(c),vie.LireBourg(c),vie.LireOccupation(c));});}
        static (int,string) Vider(int port,long c)
        {
            using(var http=new HttpClient{Timeout=Delai})using(var vide=new StringContent(""))
            using(var r=http.PostAsync("http://127.0.0.1:"+port.ToString(CultureInfo.InvariantCulture)+"/epreuve/vider-panier?cell="+L(c),vide).GetAwaiter().GetResult())
                return ((int)r.StatusCode,r.Content.ReadAsStringAsync().GetAwaiter().GetResult());
        }
        // Absence, cellule ou tick discordants, population nulle, base vide : refus nommé. Nourrie : vivres > 0 et faim nulle ; affamée : 0 et faim > 0.
        static (LecturePlan p,Lecture<BourgLu> b,Lecture<OccupationLue> o) Verifier((LecturePlan p,Lecture<BourgLu> b,Lecture<OccupationLue> o) l,bool nourrie,long tick)
        {
            if(!l.p.Presente)throw Faux(l.p.Absence);if(!l.b.Presente)throw Faux(l.b.Absence);if(!l.o.Presente)throw Faux(l.o.Absence);var p=l.p.Plan;var b=l.b.Donnees;var o=l.o.Donnees;
            if(p.CellId!=cellule||b.CellId!=cellule||o.CellId!=cellule)throw Faux("cellules discordantes : plan "+L(p.CellId)+", bourg "+L(b.CellId)+", occupation "+L(o.CellId)+" pour "+L(cellule));
            if(b.Tick!=p.Tick||b.TickLocal!=p.Tick||o.Tick!=p.Tick||tick>=0&&p.Tick!=tick)throw Faux("ticks discordants : plan "+L(p.Tick)+", bourg "+L(b.Tick)+" (local "+L(b.TickLocal)+"), occupation "+L(o.Tick)+", POST "+L(tick));
            if(b.Population<=0)throw Faux("population nulle au bourg "+L(cellule));if(p.Base==null||p.Base.Maisons.Count==0)throw Faux("base vide ou non servie");
            if(!b.Stocks.TryGetValue(Vivres,out double kg))throw Faux(Vivres+" absente du bourg "+L(cellule));
            if(nourrie?!(kg>0)||b.DureeFaimTicks!=0:kg!=0||b.DureeFaimTicks<=0)throw Faux("place "+(nourrie?"nourrie":"affamée")+" attendue : "+N(kg)+" kg, faim "+L(b.DureeFaimTicks)+" tick(s)");
            return l;
        }
        static void Appliquer((LecturePlan p,Lecture<BourgLu> b,Lecture<OccupationLue> o) l,bool etalAussi)
        {
            foreach(var e in ids.Keys)if(!e.Appliquer(l.b,l.o,l.p,(float)Heure))throw Faux(e.name+" : "+e.Cause);
            if(etalAussi&&!etal.Appliquer(l.b,l.p))throw Faux(etal.name+" : "+etal.Cause);
        }

        // Chaque maison de base dessinée, associée à sa seule case (rang, indice) de MaisonsDeLaBase.Poser, reçoit fumée et lampe ;
        // le comptoir va sur la place, près du bord qui fait face à la maison témoin, son devant vers la caméra.
        static void Monter(PlanLu plan,double reference,Camera camera)
        {
            var fumee=AssetDatabase.LoadAssetAtPath<Material>("Assets/ForgeLocal3D/Desert/Materials/effet_fumee.mat")??throw Faux("matériau de fumée absent");
            var pose=MaisonsDeLaBase.Poser(plan.Base);if(!pose.Presente)throw Faux(pose.Absence);var terrain=outil.roads.terrain;
            var dessinees=outil.Maisons.Racine.Cast<Transform>().ToArray();if(dessinees.Length==0)throw Faux("aucune maison de base dessinée : "+outil.Maisons.Absence);
            var place=plan.Base.Place.Select(q=>new Vector2(-(float)q.X,-(float)q.Y)).ToArray();if(place.Length<3)throw Faux("place sans emprise");
            float mieux=float.MaxValue;Vector2 a0=default,b0=default,vu=default;
            foreach(var c in pose.Cases)
            {
                string nom="Maison "+L(c.Maison)+" indice "+L(c.Indice);var t=dessinees.Where(x=>x.name==nom).ToArray();if(t.Length==0)continue; // refusée au dessin : rien à animer
                var m=t[0];var centre=new Vector2(-(float)c.CentreX,-(float)c.CentreY);
                if(t.Length>1||Vector2.Distance(centre,new Vector2(m.position.x,m.position.z))>c.LargeurM+c.ProfondeurM)throw Faux(nom+" : "+t.Length+" pièce(s), ou loin de sa case");
                if(!DesertMaisons1400.Boite(m.gameObject,out var lb))throw Faux(nom+" : mesure absente");
                // La fumée au-dessus du toit, dense comme #779 pour se lire au crépuscule ; la lampe devant la façade (+Z de la pièce).
                var f=AlpineBuilder.Smoke(new float[3],fumee,m,ids.Count);f.transform.position=m.TransformPoint(new Vector3(lb.center.x,lb.max.y,lb.center.z))+Vector3.up*.3f;
                var fm=f.main;fm.startSize=new ParticleSystem.MinMaxCurve(1.1f,1.8f);fm.startColor=new Color(.62f,.6f,.57f);fm.maxParticles=320;fm.scalingMode=ParticleSystemScalingMode.Local;fm.cullingMode=ParticleSystemCullingMode.AlwaysSimulate;var fe=f.emission;fe.rateOverTime=40;
                var l=new GameObject("Lampe").AddComponent<Light>();l.transform.SetParent(m,false);l.transform.position=m.TransformPoint(new Vector3(lb.center.x,lb.min.y,lb.max.z))+m.forward*.9f+Vector3.up*1.8f;
                l.type=LightType.Point;l.color=new Color(1f,.62f,.28f);l.range=11f;l.intensity=8f;
                var e=m.gameObject.AddComponent<EffetsDeMaison>();e.PourLaBase(f,l,cellule,c.Maison,c.Indice);ids.Add(e,(c.Maison,c.Indice));
                for(int k=0;k<place.Length;k++){var a=place[k];var b=place[(k+1)%place.Length];float d=Vector2.Distance(centre,Proche(a,b,centre));if(d<mieux){mieux=d;temoin=e;a0=a;b0=b;vu=centre;}}
            }
            if(ids.Count!=dessinees.Length||!temoin)throw Faux(L(dessinees.Length)+" maisons dessinées, "+L(ids.Count)+" associées à une case");
            Vector2 g=place.Aggregate(Vector2.zero,(s,q)=>s+q)/place.Length,pied=Proche(a0,b0,vu),n=Vector2.Perpendicular(b0-a0).normalized;if(Vector2.Dot(n,g-pied)<0)n=-n;
            // La façade donne sur la rue, pas vers le centre : on se place en trois-quarts, côté porte, le comptoir dans la place.
            Vector2 face=new Vector2(temoin.transform.forward.x,temoin.transform.forward.z).normalized,versCentre=(g-vu).normalized,ici=pied+n*Recul+face*2f;
            Vector2 cam=vu+versCentre*16f+face*8f;if(!Dedans(place,cam))cam=pied+n*14f+face*6f;if(!Dedans(place,cam))cam=g;
            Vector2 devant=(cam-ici).normalized;if(devant.sqrMagnitude<1e-4f)devant=n;var droite=new Vector2(devant.y,-devant.x);
            for(int s=0;s<4;s++)if(!Dedans(place,ici+devant*((s&1)==0?-.8f:.8f)+droite*((s&2)==0?-1.5f:1.5f)))throw Faux("comptoir hors de l'emprise de la place");
            var regard=(vu-cam).normalized;visePose=new Vector3(vu.x,0,vu.y);capPose=Mathf.Atan2(regard.x,regard.y)*Mathf.Rad2Deg;distPose=Vector2.Distance(cam,vu)/Mathf.Cos(incPose*Mathf.Deg2Rad);
            racine=new GameObject("Lot 781 : comptoir du bourg").transform;var et=new GameObject("Étal nourriture").transform;et.SetParent(racine);
            var pos=new Vector3(ici.x,0,ici.y);pos.y=terrain.SampleHeight(pos)+terrain.transform.position.y;et.SetPositionAndRotation(pos,Quaternion.LookRotation(new Vector3(devant.x,0,devant.y)));
            comptoir=Bloc(PrimitiveType.Cube,et,"comptoir",new Vector3(0,.45f,0),new Vector3(2.6f,.9f,1.2f),"bois_sombre");
            // L'auvent haut, au fond, et ses deux poteaux : il n'ombre que l'arrière et ne cache pas les denrées.
            Bloc(PrimitiveType.Cube,et,"auvent",new Vector3(0,2.5f,-.45f),new Vector3(2.8f,.05f,.8f),"tissu_garance");
            for(int s=-1;s<=1;s+=2){Bloc(PrimitiveType.Cube,et,"poteau",new Vector3(s*1.25f,1.25f,-.8f),new Vector3(.08f,2.5f,.08f),"bois_palmier");Bloc(PrimitiveType.Cylinder,et,"contenant vide",new Vector3(s*1.12f,.98f,.35f),new Vector3(.3f,.08f,.3f),"poterie");}
            var gar=new GameObject("garniture").transform;gar.SetParent(et,false);gar.localPosition=new Vector3(0,.9f,0);
            for(int i=0;i<3;i++)Bloc(PrimitiveType.Cube,gar,"denrée",new Vector3((i-1)*.6f,.5f,0),new Vector3(.55f,1f,.9f),new[]{"dattes","epices_rouge","epices_jaune"}[i]);
            etal=et.gameObject.AddComponent<EtalDuBourg>();etal.Configurer(cellule,Vivres,reference,gar);Cadrer(camera);
        }
        // Même vise, cap, inclinaison et distance aux deux photos : DesertCityCamera.Poser est la seule entrée.
        static void Cadrer(Camera c){c.aspect=1600f/900f;(c.GetComponent<DesertCityCamera>()??throw Faux("pas de caméra de ville")).Poser(visePose,capPose,incPose,distPose);var env=Object.FindFirstObjectByType<DesertEnvironment>()??throw Faux("pas de DesertEnvironment");env.hour=(float)Heure;env.showPanel=false;env.Apply();if(env.sky){ciel=env.sky;EditorUtility.ClearDirty(ciel);}if(outil)outil.Placer();}
        static Renderer Bloc(PrimitiveType t,Transform parent,string nom,Vector3 pos,Vector3 taille,string matiere)
        {
            var g=GameObject.CreatePrimitive(t);g.name=nom;g.transform.SetParent(parent,false);g.transform.localPosition=pos;g.transform.localScale=taille;var r=g.GetComponent<Renderer>();
            if(nom!="denrée")Object.DestroyImmediate(g.GetComponent<Collider>()); // Seules les denrées arrêtent le rayon qui prouve qu'on les voit.
            r.sharedMaterial=AssetDatabase.LoadAssetAtPath<Material>("Assets/ForgeLocal3D/Desert/Materials/"+matiere+".mat")??throw Faux("matériau "+matiere+" absent du projet");return r;
        }
        static Vector2 Proche(Vector2 a,Vector2 b,Vector2 p){var ab=b-a;return a+ab*Mathf.Clamp01(Vector2.Dot(p-a,ab)/Mathf.Max(ab.sqrMagnitude,1e-6f));}
        static bool Dedans(Vector2[] poly,Vector2 p)
        {bool d=false;for(int i=0,j=poly.Length-1;i<poly.Length;j=i++)if((poly[i].y>p.y)!=(poly[j].y>p.y)&&p.x<(poly[j].x-poly[i].x)*(p.y-poly[i].y)/(poly[j].y-poly[i].y)+poly[i].x)d=!d;return d;}

        // Avant chaque photo : toit, fumée (ou sa place), lampe de la maison témoin et comptoir dans le champ, sans obstacle ; les denrées aussi si garnie.
        static void Champ(Camera camera,bool garnie)
        {
            Physics.SyncTransforms();var o=camera.transform.position;bool Dans(Vector3 p){var v=camera.WorldToViewportPoint(p);return v.z>0f&&v.x>.02f&&v.x<.98f&&v.y>.02f&&v.y<.98f;}
            bool Libre(Vector3 p,Transform de)=>!Physics.Raycast(o,p-o,out var h,Vector3.Distance(o,p)-.05f)||h.transform.IsChildOf(de);
            var mb=temoin.GetComponentsInChildren<MeshRenderer>().Select(r=>r.bounds).Aggregate((a,x)=>{a.Encapsulate(x);return a;});var toit=new Vector3(mb.center.x,mb.max.y,mb.center.z);
            var f=temoin.Fumee.transform.position;var lampe=temoin.Lampe.transform.position;var cb=comptoir.bounds;
            string bilan=temoin.name+" : toit "+camera.WorldToViewportPoint(toit).ToString("F2")+", fumée "+camera.WorldToViewportPoint(f).ToString("F2")+", lampe "+camera.WorldToViewportPoint(lampe).ToString("F2")+", comptoir "+camera.WorldToViewportPoint(cb.center).ToString("F2");
            if(!Dans(toit)||!Dans(mb.center)||!Dans(f)||!Dans(f+Vector3.up*1.5f)||!Dans(lampe)||!Dans(cb.min)||!Dans(cb.max)||!comptoir.enabled||!Libre(toit,temoin.transform)||!Libre(cb.center+Vector3.up*cb.extents.y,etal.transform))
                throw Faux("hors du champ ou caché, "+bilan);
            if(garnie)
            {
                var gb=etal.Garniture.GetComponentsInChildren<Renderer>().Select(r=>r.bounds).Aggregate((a,x)=>{a.Encapsulate(x);return a;});var haut=new Vector3(gb.center.x,gb.max.y-.02f,gb.center.z);
                if(Visibles(camera)==0||!Dans(gb.min)||!Dans(gb.max)||!Physics.Raycast(o,haut-o,out var h,500f)||!h.transform.IsChildOf(etal.Garniture))throw Faux("denrées cachées ou hors du champ, "+bilan);
            }
            Debug.Log("CAPTURE_781 "+bilan);
        }

        // Les mesures se prennent sur les objets de la session, jamais sur ce qu'on attend : -1 non calculé, 0 est une mesure.
        static bool Montre(Renderer r,Camera c)=>r.enabled&&r.gameObject.activeInHierarchy&&r.bounds.size.y>1e-4f&&GeometryUtility.TestPlanesAABB(GeometryUtility.CalculateFrustumPlanes(c),r.bounds);
        static int Visibles(Camera c)=>racine.GetComponentsInChildren<EtalDuBourg>().Where(e=>e.Marchandise==Vivres&&e.Garniture).SelectMany(e=>e.Garniture.GetComponentsInChildren<Renderer>(true)).Count(r=>Montre(r,c));
        static float Haut(Transform g)
        {
            float h=0;foreach(var f in g.GetComponentsInChildren<MeshFilter>(true))if(f.sharedMesh){var b=f.sharedMesh.bounds;
                for(int k=0;k<8;k++)h=Mathf.Max(h,f.transform.TransformPoint(new Vector3((k&1)==0?b.min.x:b.max.x,(k&2)==0?b.min.y:b.max.y,(k&4)==0?b.min.z:b.max.z)).y-g.position.y);}
            return h;
        }
        static string Matrice(Camera c){var m=c.projectionMatrix*c.worldToCameraMatrix;return "["+string.Join(",",Enumerable.Range(0,16).Select(i=>Nf(m[i])))+"]";}
        static void Relever(string nom,BourgLu b,Camera camera)
        {
            var env=Object.FindFirstObjectByType<DesertEnvironment>();var s=new StringBuilder("{\"nom\":"+Q(nom));
            s.Append(",\"tick\":"+L(b.Tick)+",\"tick_local\":"+L(b.TickLocal)+",\"heure\":"+(!env?"-1":env.hour==(float)Heure?N(Heure):Nf(env.hour))+",\"population\":"+L(b.Population));
            s.Append(",\"nourriture_kg\":"+(b.Stocks.TryGetValue(Vivres,out double kg)?N(kg):"-1")+",\"faim_ticks\":"+L(b.DureeFaimTicks)+",\"camera\":"+Matrice(camera));
            var maisons=outil.Maisons.Racine.GetComponentsInChildren<EffetsDeMaison>();var etals=racine.GetComponentsInChildren<EtalDuBourg>();
            s.Append(",\"maisons\":["+string.Join(",",maisons.Select(e=>"{\"rang\":"+L(ids[e].rang)+",\"indice\":"+L(ids[e].indice)+",\"emission\":"+B(e.Fumee.isEmitting)+",\"particules\":"+L(e.Fumee.particleCount)
                +",\"lampe_active\":"+B(e.Lampe.isActiveAndEnabled)+",\"intensite\":"+Nf(e.Lampe.intensity)+",\"cause\":"+Q(e.Cause)+"}"))+"]");
            s.Append(",\"etals\":["+string.Join(",",etals.Select(e=>"{\"marchandise\":"+Q(e.Marchandise)+",\"reference_kg\":"+N(e.ReferenceKg)+",\"rapport\":"+N(e.Rapport)+",\"hauteur\":"+Nf(Haut(e.Garniture))
                +",\"visible\":"+B(e.Garniture.GetComponentsInChildren<Renderer>(true).Any(r=>Montre(r,camera)))+",\"comptoir\":"+B(e.GetComponentsInChildren<Renderer>().Any(r=>r.name=="comptoir"&&r.enabled))+",\"cause\":"+Q(e.Cause)+"}"))+"]");
            s.Append(",\"garnitures_visibles\":"+L(Visibles(camera))+",\"causes\":["+string.Join(",",maisons.Select(e=>e.Cause).Concat(etals.Select(e=>e.Cause)).Where(x=>x!=null).Distinct().Select(Q))+"]}");
            etats.Add(s.ToString());Ecrire("session interrompue après le relevé « "+nom+" »");
        }
        static void Ecrire(string defaut)=>File.WriteAllText(Path.Combine(Capture.DossierDesCaptures,"vie-bourg.json"),"{\"cellule\":"+L(cellule)+",\"port\":"+L(outil?outil.Port:-1)
            +",\"contre_epreuve\":"+B(Contre)+",\"defaut\":"+Q(defaut)+",\"etats\":["+string.Join(",",etats)+"]}",new UTF8Encoding(false));
        static string Q(string t)=>t==null?"null":"\""+t.Replace("\\","\\\\").Replace("\"","\\\"").Replace("\n","\\n").Replace("\r","\\r").Replace("\t","\\t")+"\"";
        static string B(bool b)=>b?"true":"false";static string L(long n)=>n.ToString(CultureInfo.InvariantCulture);
        static string N(double v)=>v.ToString("R",CultureInfo.InvariantCulture);static string Nf(float v)=>v.ToString("R",CultureInfo.InvariantCulture);
    }
}
