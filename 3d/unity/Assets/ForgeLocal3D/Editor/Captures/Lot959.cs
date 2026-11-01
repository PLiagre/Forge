using System;using System.Collections;using System.Collections.Generic;using System.Globalization;using System.IO;using System.Linq;using System.Net.Http;using System.Text;using System.Threading.Tasks;using Forge.Pont;using UnityEditor;using UnityEngine;using Object=UnityEngine.Object;
namespace ForgeLocal3D.Captures
{
    // Lot 959 : Biskra dense, 600 maisons, 80 passants, un chantier, le soir, mesurée sur quatre vues avant toute optimisation.
    // Rapport `lot959-ville-dense.json`, une ligne, réécrit à chaque étape ; `defaut` reste nommé jusqu'à la fin du scénario 5.
    static class Lot959
    {
        const string Siege="Biskra",Rapport="lot959-ville-dense.json",SansVille="-forge959SansVille",SansEffets="-forge959SansEffets";
        const long CelluleDense=10103,TickFin=4;const int MaisonsAttendues=600,Habitants=800,Passants=80;
        static readonly TimeSpan Delai=TimeSpan.FromSeconds(60);
        static readonly List<string> vues=new(),refus=new();static readonly List<EffetsDeMaison> effets=new();static readonly List<EtalDuBourg> etals=new();static readonly List<Renderer> comptoirs=new();
        static DesertRoadTool outil;static PassantsDeLaVille foule;static DesertCityCamera villeCam;static Terrain terrain;static Transform[] maisons=new Transform[0];
        static Transform piece,etiquette;static PlanLu plan;static Lecture<BourgLu> bourgLu;static Lecture<OccupationLue> occupation;static LecturePlan lecturePlan;static Vector2[] emprise;
        static Vector3 viseEtals;static long cellule=-1,tick=-1,bourgPop=-1,chantierId=-1;static int maisonsPosees=-1,foyers=-1,passProj=-1,passPoses=-1,passScene=-1,fumees=-1,lampes=-1;
        static double gx,gy,heure=-1;static string rapport,etape="aucune",drapeau="",chantierEtat,panierJson="{}",etalsJson="[]",machine;static bool monte,sansVille,sansEffets;
        static Exception Faux(string m)=>new InvalidOperationException(m);

        [ScenarioDeCapture(959,"1-montage")]static IEnumerator Montage(Camera camera)=>Derouler(Monter(camera));
        [ScenarioDeCapture(959,"2-survol")]static IEnumerator Survol(Camera camera)=>Derouler(Vue(camera,"survol"));
        [ScenarioDeCapture(959,"3-rue")]static IEnumerator Rue(Camera camera)=>Derouler(Vue(camera,"rue"));
        [ScenarioDeCapture(959,"4-place")]static IEnumerator Place(Camera camera)=>Derouler(Vue(camera,"place"));
        [ScenarioDeCapture(959,"5-chantier")]static IEnumerator Chantier(Camera camera)=>Derouler(Vue(camera,"chantier"));
        static IEnumerator Derouler(IEnumerator corps)
        {while(true){bool suite;try{suite=corps.MoveNext();}catch(Exception e){if(rapport!=null)Ecrire(etape+" : "+e.GetBaseException().Message);throw;}if(!suite)yield break;yield return null;}}

        static IEnumerator Monter(Camera camera)
        {
            vues.Clear();refus.Clear();effets.Clear();etals.Clear();comptoirs.Clear();monte=false;heure=-1;cellule=tick=bourgPop=chantierId=-1;
            maisonsPosees=foyers=passProj=passPoses=passScene=fumees=lampes=-1;panierJson="{}";etalsJson="[]";chantierEtat=null;piece=etiquette=null;machine=null;drapeau="";plan=null;
            etape="rapport";string chemin=Path.Combine(Capture.DossierDesCaptures,Rapport);if(File.Exists(chemin))throw Faux("rapport antérieur : "+chemin);rapport=chemin;
            var args=Environment.GetCommandLineArgs();sansVille=args.Contains(SansVille);sansEffets=args.Contains(SansEffets);
            if(sansVille&&sansEffets)throw Faux("les deux drapeaux ensemble : "+SansVille+" et "+SansEffets);
            drapeau=sansVille?SansVille.Substring(1):sansEffets?SansEffets.Substring(1):"";Ecrire("ouverture");
            etape="ouverture";outil=Object.FindFirstObjectByType<DesertRoadTool>()??throw Faux("pas d'outil des routes");
            villeCam=camera.GetComponent<DesertCityCamera>()??throw Faux("pas de caméra de ville");foule=outil.GetComponent<PassantsDeLaVille>()??throw Faux("foule absente");
            if(!outil.maillageCivil)throw Faux("maillage civil absent");if(!outil.roads||!outil.roads.terrain)throw Faux("terrain absent");terrain=outil.roads.terrain;
            outil.automatique=villeCam.automatique=true;if(villeCam.Marcheur)villeCam.Marcheur.automatic=true;
            var visite=camera.GetComponent<VillageV2Visit>();if(visite)visite.enabled=false;
            var env=Object.FindFirstObjectByType<DesertEnvironment>()??throw Faux("pas de DesertEnvironment");env.showPanel=false;
            var bandeau=GameObject.Find("/Panneau du lieu");if(bandeau)bandeau.SetActive(false);
            foreach(var tm in Object.FindObjectsByType<TextMesh>(FindObjectsSortMode.None))tm.gameObject.SetActive(false);
            int port=outil.Port;etape="départs";var departs=Task.Run(()=>{using(var d=new ClientDeparts(port,ClientDeparts.DelaiMinimal))return d.Lire();});
            while(!departs.IsCompleted)yield return null;
            if(departs.IsFaulted||!departs.Result.Presente)throw Faux(departs.IsFaulted?departs.Exception.GetBaseException().Message:departs.Result.Absence);
            var zab=departs.Result.Donnees.Fiches.Where(f=>f.Siege.Nom==Siege).ToArray();if(zab.Length!=1)throw Faux(zab.Length+" départ(s) au siège "+Siege);
            cellule=zab[0].CellId;if(cellule!=CelluleDense)throw Faux(Siege+" est la cellule "+L(cellule)+", "+L(CelluleDense)+" attendue");
            etape="gestes";Ecrire(etape);string c=L(cellule);
            Lot362.Deposer(port,"{\"type\":\"choisir_depart\",\"seigneurie\":"+L(zab[0].Id)+"}");Lot362.Tick(port);
            Lot362.Deposer(port,"{\"type\":\"tracer_route\",\"cell\":"+c+",\"points\":[[0,0],[40,0]],\"largeur_m\":4}");Lot362.Tick(port);
            var planRoute=Lot362.Lire(port,cellule);RueDuPlan rue=null;
            foreach(var u in planRoute.Rues)if(u.Points.Count==2&&Math.Abs(u.LargeurM-4)<1e-4&&Math.Abs(u.Points[0].X)<1e-4&&Math.Abs(u.Points[0].Y)<1e-4&&Math.Abs(u.Points[1].X-40)<1e-4&&Math.Abs(u.Points[1].Y)<1e-4)rue=u;
            if(rue==null)throw Faux("la route (0 ; 0)-(40 ; 0) n'est pas au plan du tick "+planRoute.Tick);
            var deja=new List<long>();foreach(var p in planRoute.Parcelles)deja.Add(p.Identifiant);
            Lot362.Deposer(port,"{\"type\":\"decouper_parcelle\",\"cell\":"+c+",\"rue\":"+L(rue.Identifiant)+",\"segment\":0,\"debut_m\":4,\"facade_m\":10,\"profondeur_m\":15,\"cote\":\"gauche\"}");Lot362.Tick(port);
            var planParcelle=Lot362.Lire(port,cellule);ParcelleDuPlan neuve=null;
            foreach(var p in planParcelle.Parcelles)if(!deja.Contains(p.Identifiant)){if(neuve!=null)throw Faux("plusieurs parcelles nouvelles");neuve=p;}
            if(neuve==null)throw Faux("parcelle absente après la découpe");
            Lot362.Deposer(port,"{\"type\":\"poser_batiment\",\"cell\":"+c+",\"parcelle\":"+L(neuve.Identifiant)+",\"nature\":\"maison\"}");Lot362.Tick(port);tick=TickFin;
            if(!sansVille)
            {
                etape="ville dense";Ecrire(etape);var post=Task.Run(()=>Poster(port,cellule));while(!post.IsCompleted)yield return null;
                if(post.IsFaulted)throw Faux(post.Exception.GetBaseException().Message);var (statut,corps)=post.Result;
                if(statut!=200)throw Faux("POST /epreuve/ville-dense?cell="+c+" a rendu "+statut+" : "+corps);
                var r=LecteurJson.LireObjet(corps);long Cle(string k)=>r.TryGetValue(k,out var v)&&v is double d?(long)d:throw Faux("POST : clé "+k+" absente ou non entière : "+corps);
                if(Cle("cell_id")!=CelluleDense||Cle("tick")!=TickFin)throw Faux("POST : rendu "+corps+" pour la cellule "+L(CelluleDense)+" au tick "+L(TickFin));
            }
            etape="dessin";Ecrire(etape);if(!outil.Ouvrir(cellule))throw Faux(outil.Message);foule.Retirer();
            etape="lectures";var lu=Lire(port);while(!lu.IsCompleted)yield return null;if(lu.IsFaulted)throw Faux(lu.Exception.GetBaseException().Message);Verifier(lu.Result);
            var dessinees=new List<Transform>();foreach(Transform t in outil.Maisons.Racine)dessinees.Add(t);maisons=dessinees.ToArray();
            maisonsPosees=outil.Maisons.Posees;foyers=outil.Maisons.Foyers;refus.Clear();refus.AddRange(outil.Maisons.Refus);etape="maisons";Ecrire(etape);
            if(maisonsPosees!=MaisonsAttendues||foyers!=MaisonsAttendues||refus.Count!=0)throw Faux("600 maisons attendues, "+maisonsPosees+" posée(s)"+(refus.Count==0?"":"\n"+string.Join("\n",refus)));
            etape="bourg";if(bourgPop!=Habitants)throw Faux("bourg à "+L(bourgPop)+", "+Habitants+" attendus");
            etape="chantier";BatimentDuPlan bat=null;foreach(var b in plan.Batiments)if(b.Nature=="maison")bat=b;if(bat==null)throw Faux("aucun bâtiment maison au plan");
            int idx=outil.Batiments.FindIndex(b=>b.identifiant==bat.Identifiant);if(idx<0)throw Faux("bâtiment "+L(bat.Identifiant)+" non dessiné");
            chantierEtat=outil.Batiments[idx].etat;chantierId=bat.Identifiant;
            if(chantierEtat!="piquets"&&chantierEtat!="murs")throw Faux("bâtiment "+L(chantierId)+" à l'état "+chantierEtat+", piquets ou murs attendu");
            piece=outil.RacineBatiments!=null?outil.RacineBatiments.Find("Bâtiment "+L(chantierId)):null;if(!piece)throw Faux("pas d'enfant « Bâtiment "+L(chantierId)+" »");
            etape="foule";Ecrire(etape);int scene=0;
            for(double fin=Time.realtimeSinceStartupAsDouble+30;Time.realtimeSinceStartupAsDouble<fin;)
            {scene=CompterPassants();if(foule.CelluleAppliquee==CelluleDense&&foule.TickApplique==TickFin&&foule.NombreProjete==Passants&&foule.NombrePose==Passants&&scene==Passants)break;yield return null;}
            scene=CompterPassants();passProj=(int)foule.NombreProjete;passPoses=(int)foule.NombrePose;passScene=scene;
            if(foule.CelluleAppliquee!=CelluleDense||foule.TickApplique!=TickFin||foule.NombreProjete!=Passants||foule.NombrePose!=Passants||scene!=Passants)
                throw Faux("foule "+foule.CelluleAppliquee+"/"+foule.TickApplique+" projetés "+foule.NombreProjete+" posés "+foule.NombrePose+" en scène "+scene+" : "+foule.Cause);
            etape="effets";Ecrire(etape);if(!sansEffets)MonterEffets();
            env.hour=(float)EpreuveVieDuBourg.Heure;heure=EpreuveVieDuBourg.Heure;env.Apply();if(env.sky)EditorUtility.ClearDirty(env.sky);
            foreach(var e in effets)if(!e.Appliquer(bourgLu,occupation,lecturePlan,(float)heure)||e.Cause!=null)throw Faux(e.name+" : "+e.Cause);
            foreach(var e in etals)if(!e.Appliquer(bourgLu,lecturePlan)||e.Cause!=null)throw Faux(e.name+" : "+e.Cause);
            etape="particules";for(int i=0;i<600&&(i<60||effets.Any(e=>e.Fumee.particleCount==0));i++)yield return null;
            if(effets.Any(e=>!e.Fumee.isEmitting||e.Fumee.particleCount==0))throw Faux("fumée sans particule");
            etape="relevé";ReleverEffets();var vise=Barycentre();villeCam.Poser(vise,180f,40f,DistanceSurvol(camera,vise,Centres()));monte=true;Ecrire("2-survol");
        }

        static IEnumerator Vue(Camera camera,string nom)
        {
            etape=nom;if(!monte||plan==null||plan.Base==null)throw Faux("le scénario « 1-montage » n'a pas monté la ville");
            if(etiquette){Object.DestroyImmediate(etiquette.gameObject);etiquette=null;}Ecrire(nom);
            Vector3 vise;float cap,inc,dist;
            if(nom=="survol"){vise=Barycentre();cap=180f;inc=40f;dist=DistanceSurvol(camera,vise,Centres());}
            else if(nom=="rue")
            {
                RueDeBase longue=null;double meilleur=-1;
                foreach(var r in plan.Base.Rues){double longueur=0;for(int i=0;i+1<r.Points.Count;i++)longueur+=Dist(r.Points[i],r.Points[i+1]);if(longueur>meilleur){meilleur=longueur;longue=r;}}
                if(longue==null||longue.Points.Count<2)throw Faux("pas de rue de base");
                var but=LeLong(longue.Points,.6);vise=Monde(but.X,but.Y);cap=CapVers(vise,Monde(longue.Points[0].X,longue.Points[0].Y));inc=8f;dist=12f;
            }
            else if(nom=="place"){vise=sansEffets?Monde(gx,gy-12):viseEtals;cap=CapVers(Barycentre(),vise);inc=22f;dist=28f;}
            else{vise=BoiteDe(piece).center;cap=180f;inc=35f;dist=25f;}
            camera.aspect=1600f/900f;villeCam.Poser(vise,cap,inc,dist);for(int i=0;i<10;i++)yield return null;string controles=Controles(camera);
            ReleveDuBanc releve=null;var mes=BancDuTempsDImage.Mesurer(camera,60,300,x=>releve=x,true);while(mes.MoveNext())yield return null;
            if(releve==null||releve.nombre!=300)throw Faux("le banc n'a pas rendu 300 images");
            string texte=nom+" · médiane "+F1(releve.mediane_ms)+" ms · P95 "+F1(releve.p95_ms)+" ms · max "+F1(releve.maximum_ms)+" ms";
            PoserEtiquette(camera,texte);for(int i=0;i<10;i++)yield return null;
            var tm=etiquette.GetComponent<TextMesh>();if(!Huit(camera,tm.GetComponent<Renderer>().bounds,.01f))throw Faux("étiquette hors champ : "+tm.text);
            if(tm.text!=texte)throw Faux("étiquette « "+tm.text+" », attendu « "+texte+" »");
            AjouterVue(nom,villeCam.Vise,villeCam.Cap,villeCam.Inclinaison,villeCam.Distance,camera,controles,tm.text,releve);
            Debug.Log("CAPTURE_959 "+nom+" médiane "+F1(releve.mediane_ms)+" ms P95 "+F1(releve.p95_ms)+" ms");
            Ecrire(nom=="chantier"?null:nom=="survol"?"3-rue":nom=="rue"?"4-place":"5-chantier");
        }

        static void MonterEffets()
        {
            var fumee=Mat("effet_fumee");var pose=MaisonsDeLaBase.Poser(plan.Base);if(!pose.Presente)throw Faux(pose.Absence);
            var parNom=new Dictionary<string,Transform>();
            foreach(var m in maisons){if(parNom.ContainsKey(m.name))throw Faux(m.name+" : plusieurs pièces");parNom.Add(m.name,m);}
            foreach(var cas in pose.Cases)
            {
                string nom="Maison "+L(cas.Maison)+" indice "+L(cas.Indice);if(!parNom.TryGetValue(nom,out var m))throw Faux(nom+" : maison dessinée absente");
                if(!DesertMaisons1400.Boite(m.gameObject,out var lb))throw Faux(nom+" : mesure absente");
                var f=AlpineBuilder.Smoke(new float[3],fumee,m,effets.Count);f.transform.position=m.TransformPoint(new Vector3(lb.center.x,lb.max.y,lb.center.z))+Vector3.up*.3f;
                var fm=f.main;fm.startSize=new ParticleSystem.MinMaxCurve(.55f,.9f);fm.startColor=new Color(.62f,.6f,.57f);fm.maxParticles=320;fm.scalingMode=ParticleSystemScalingMode.Local;fm.cullingMode=ParticleSystemCullingMode.AlwaysSimulate;
                var fe=f.emission;fe.rateOverTime=40;var lampe=new GameObject("Lampe").AddComponent<Light>();lampe.transform.SetParent(m,false);
                lampe.transform.position=m.TransformPoint(new Vector3(lb.center.x,lb.min.y,lb.max.z))+m.forward*.9f+Vector3.up*1.8f;
                lampe.type=LightType.Point;lampe.color=new Color(1f,.62f,.28f);lampe.range=11f;lampe.intensity=8f;
                var e=m.gameObject.AddComponent<EffetsDeMaison>();e.PourLaBase(f,lampe,cellule,cas.Maison,cas.Indice);effets.Add(e);
            }
            if(effets.Count!=maisons.Length)throw Faux(maisons.Length+" maisons dessinées, "+effets.Count+" effets");
            var stocks=bourgLu.Donnees.Stocks.Where(kv=>kv.Value>0).Select(kv=>kv.Key).OrderBy(k=>k,StringComparer.Ordinal).ToList();
            if(stocks.Count==0)throw Faux("panier sans stock positif");if(emprise==null||emprise.Length<3)throw Faux("place sans emprise");
            var racine=new GameObject("Étals du bourg").transform;double largeur=(stocks.Count-1)*5.0;var poses=new List<Vector3>();
            for(int i=0;i<stocks.Count;i++)
            {
                string nom=stocks[i];double kg=bourgLu.Donnees.Stocks[nom],x=gx+(i*5.0-largeur/2.0),y=gy-12;var et=new GameObject("Étal "+nom);et.transform.SetParent(racine,false);
                var pos=Monde(x,y);et.transform.SetPositionAndRotation(pos,Quaternion.LookRotation(Vector3.back));poses.Add(pos);
                var comptoir=Bloc(et.transform,"comptoir",new Vector3(0,.45f,0),new Vector3(2.6f,.9f,1.2f),"bois_sombre");
                if(!HuitDansPlace(comptoir.bounds))throw Faux("comptoir hors de l'emprise de la place ("+nom+")");comptoirs.Add(comptoir);
                var gar=new GameObject("garniture").transform;gar.SetParent(et.transform,false);gar.localPosition=new Vector3(0,.9f,0);
                Bloc(gar,"denrée",new Vector3(-.6f,.5f,0),new Vector3(.55f,1f,.9f),"dattes");Bloc(gar,"denrée",new Vector3(0,.5f,0),new Vector3(.55f,1f,.9f),"epices_rouge");Bloc(gar,"denrée",new Vector3(.6f,.5f,0),new Vector3(.55f,1f,.9f),"epices_jaune");
                var eb=et.AddComponent<EtalDuBourg>();eb.Configurer(cellule,nom,kg,gar);etals.Add(eb);
            }
            viseEtals=Vector3.zero;foreach(var p in poses)viseEtals+=p;viseEtals/=poses.Count;
        }
        static Renderer Bloc(Transform parent,string nom,Vector3 pos,Vector3 taille,string matiere)
        {var g=GameObject.CreatePrimitive(PrimitiveType.Cube);g.name=nom;g.transform.SetParent(parent,false);g.transform.localPosition=pos;g.transform.localScale=taille;var r=g.GetComponent<Renderer>();r.sharedMaterial=Mat(matiere);return r;}

        static void ReleverEffets()
        {
            fumees=0;lampes=0;foreach(var e in Object.FindObjectsByType<EffetsDeMaison>(FindObjectsSortMode.None)){if(e.Fumee&&e.Fumee.isEmitting&&e.Fumee.particleCount>0)fumees++;if(e.Lampe&&e.Lampe.isActiveAndEnabled&&e.Lampe.intensity>0f)lampes++;}
            etalsJson="["+string.Join(",",Object.FindObjectsByType<EtalDuBourg>(FindObjectsSortMode.None).OrderBy(e=>e.Marchandise??"",StringComparer.Ordinal).Select(e=>"{\"marchandise\":"+Q(e.Marchandise)+",\"reference_kg\":"+N(e.ReferenceKg)+",\"rapport\":"+N(e.Rapport)+",\"cause\":"+Q(e.Cause)+"}"))+"]";
        }
        static void Verifier((LectureLieu lieu,LecturePlan plan,Lecture<BourgLu> bourg,Lecture<OccupationLue> occupation) l)
        {
            if(!l.lieu.Presente)throw Faux("lieu absent : "+l.lieu.Absence);if(!l.plan.Presente)throw Faux("plan absent : "+l.plan.Absence);
            if(!l.bourg.Presente)throw Faux("bourg absent : "+l.bourg.Absence);if(!l.occupation.Presente)throw Faux("occupation absente : "+l.occupation.Absence);
            long[] cells={l.lieu.Lieu.CellId,l.plan.Plan.CellId,l.bourg.Donnees.CellId,l.occupation.Donnees.CellId};
            long[] ticks={l.lieu.Lieu.Tick,l.plan.Plan.Tick,l.bourg.Donnees.Tick,l.bourg.Donnees.TickLocal,l.occupation.Donnees.Tick};
            if(cells.Any(x=>x!=cellule)||ticks.Any(x=>x!=TickFin))throw Faux("lectures discordantes pour "+L(cellule)+"/"+L(TickFin)+" : cellules "+string.Join(",",cells.Select(L))+", ticks "+string.Join(",",ticks.Select(L)));
            plan=l.plan.Plan;lecturePlan=l.plan;bourgLu=l.bourg;occupation=l.occupation;bourgPop=bourgLu.Donnees.Population;tick=TickFin;
            if(plan.Base==null||plan.Base.Place.Count<3)throw Faux("place absente");gx=0;gy=0;foreach(var p in plan.Base.Place){gx+=p.X;gy+=p.Y;}gx/=plan.Base.Place.Count;gy/=plan.Base.Place.Count;
            emprise=plan.Base.Place.Select(p=>new Vector2((float)p.X,(float)p.Y)).ToArray();
            panierJson="{"+string.Join(",",bourgLu.Donnees.Stocks.Keys.OrderBy(k=>k,StringComparer.Ordinal).Select(k=>Q(k)+":"+N(bourgLu.Donnees.Stocks[k])))+"}";
        }
        static Task<(LectureLieu lieu,LecturePlan plan,Lecture<BourgLu> bourg,Lecture<OccupationLue> occupation)> Lire(int port)
        {long c=cellule;return Task.Run(()=>{using(var a=new ClientLieu(port,Delai))using(var b=new ClientPlan(port,Delai))using(var v=new ClientVieDuBourg(port,Delai))return(a.Lire(c),b.Lire(c),v.LireBourg(c),v.LireOccupation(c));});}
        static (int statut,string corps) Poster(int port,long c)
        {using(var http=new HttpClient{Timeout=Delai})using(var vide=new StringContent(""))using(var r=http.PostAsync("http://127.0.0.1:"+port.ToString(CultureInfo.InvariantCulture)+"/epreuve/ville-dense?cell="+L(c),vide).GetAwaiter().GetResult())return((int)r.StatusCode,r.Content.ReadAsStringAsync().GetAwaiter().GetResult());}
        static int CompterPassants(){if(!foule.Racine)return 0;int n=0;foreach(var f in foule.Racine.GetComponentsInChildren<MeshFilter>(false))if(f.sharedMesh==outil.maillageCivil&&f.gameObject.activeInHierarchy)n++;return n;}
        static Vector3 Monde(double x,double y)=>Lot362.Monde(terrain,x,y);static Vector3 Barycentre()=>Monde(gx,gy);
        static Vector3[] Centres(){var c=new Vector3[maisons.Length];for(int i=0;i<maisons.Length;i++)c[i]=BoiteDe(maisons[i]).center;return c;}
        static float DistanceSurvol(Camera camera,Vector3 vise,Vector3[] centres)
        {for(float d=100f;;d=Mathf.Min(d*1.05f,450f)){camera.aspect=1600f/900f;villeCam.Poser(vise,180f,40f,d);bool ok=true;for(int i=0;i<centres.Length&&ok;i++)if(!Dans(camera,centres[i],.02f))ok=false;if(ok)return d;if(d>=450f)throw Faux("les 600 maisons ne tiennent pas dans l'image, de 100 m à 450 m");}}
        static float CapVers(Vector3 de,Vector3 vers){var d=vers-de;d.y=0f;if(d.sqrMagnitude<1e-8f)throw Faux("visée et origine confondues");return Mathf.Atan2(d.x,d.z)*Mathf.Rad2Deg;}
        static PointLocal LeLong(IReadOnlyList<PointLocal> pts,double part)
        {double total=0;for(int i=0;i+1<pts.Count;i++)total+=Dist(pts[i],pts[i+1]);if(!(total>0))throw Faux("rue sans longueur");double reste=total*part;for(int i=0;i+1<pts.Count;i++){double s=Dist(pts[i],pts[i+1]);if(s>0&&reste<=s)return new PointLocal(pts[i].X+(pts[i+1].X-pts[i].X)*reste/s,pts[i].Y+(pts[i+1].Y-pts[i].Y)*reste/s);reste-=s;}return pts[pts.Count-1];}
        static double Dist(PointLocal a,PointLocal b){double dx=b.X-a.X,dy=b.Y-a.Y;return Math.Sqrt(dx*dx+dy*dy);}
        static Bounds BoiteDe(Transform m){bool vu=false;var b=new Bounds(m.position,Vector3.zero);foreach(var r in m.GetComponentsInChildren<Renderer>(true)){if(!vu){b=r.bounds;vu=true;}else b.Encapsulate(r.bounds);}return b;}
        static bool Dans(Camera c,Vector3 p,float marge){var v=c.WorldToViewportPoint(p);return v.z>0f&&v.x>=marge&&v.x<=1f-marge&&v.y>=marge&&v.y<=1f-marge;}
        static bool Huit(Camera c,Bounds b,float marge){for(int k=0;k<8;k++){var p=b.center+Vector3.Scale(b.extents,new Vector3((k&1)*2-1,((k>>1)&1)*2-1,((k>>2)&1)*2-1));if(!Dans(c,p,marge))return false;}return true;}
        static bool HuitDansPlace(Bounds b){for(int k=0;k<8;k++){var p=b.center+Vector3.Scale(b.extents,new Vector3((k&1)*2-1,((k>>1)&1)*2-1,((k>>2)&1)*2-1));if(!Dedans(new Vector2(-p.x,-p.z)))return false;}return true;}
        static bool Dedans(Vector2 p){bool d=false;for(int i=0,j=emprise.Length-1;i<emprise.Length;j=i++)if((emprise[i].y>p.y)!=(emprise[j].y>p.y)&&p.x<(emprise[j].x-emprise[i].x)*(p.y-emprise[i].y)/(emprise[j].y-emprise[i].y)+emprise[i].x)d=!d;return d;}
        static string Controles(Camera camera)
        {
            var planes=GeometryUtility.CalculateFrustumPlanes(camera);int champ=0,cone=0;
            foreach(var m in maisons){var b=BoiteDe(m);if(Dans(camera,b.center,.02f))champ++;if(GeometryUtility.TestPlanesAABB(planes,b))cone++;}
            int pass=0;if(foule.Racine)foreach(var f in foule.Racine.GetComponentsInChildren<MeshFilter>(false))if(f.sharedMesh==outil.maillageCivil&&f.TryGetComponent<Renderer>(out var rd)&&GeometryUtility.TestPlanesAABB(planes,rd.bounds))pass++;
            int et=0;foreach(var c in comptoirs)if(c&&Huit(camera,c.bounds,.02f))et++;bool ch=piece&&Huit(camera,BoiteDe(piece),.03f);
            float haut=camera.transform.position.y-(terrain.SampleHeight(camera.transform.position)+terrain.transform.position.y);
            return "\"maisons_dans_le_champ\":"+L(champ)+",\"maisons_dans_le_cone\":"+L(cone)+",\"passants_dans_le_cone\":"+L(pass)+",\"etals_dans_le_champ\":"+L(et)+",\"chantier_dans_le_champ\":"+(ch?"true":"false")+",\"hauteur_m\":"+N(haut);
        }
        static void PoserEtiquette(Camera camera,string texte)
        {
            float z=1f,h=2f*z*Mathf.Tan(camera.fieldOfView*Mathf.Deg2Rad/2f),w=h*camera.aspect;var font=Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf")??throw Faux("police LegacyRuntime.ttf absente");
            var go=new GameObject("Étiquette");go.transform.SetParent(camera.transform,false);var tm=go.AddComponent<TextMesh>();tm.font=font;tm.GetComponent<MeshRenderer>().sharedMaterial=font.material;
            tm.fontSize=64;tm.characterSize=1f;tm.anchor=TextAnchor.UpperLeft;tm.alignment=TextAlignment.Left;tm.color=Color.white;tm.text=texte;var r=tm.GetComponent<MeshRenderer>();
            if(r.localBounds.size.x<=0f||r.localBounds.size.y<=0f)throw Faux("étiquette sans bornes");
            float echelle=Mathf.Min(.62f*w/r.localBounds.size.x,.1f*h/r.localBounds.size.y);go.transform.localScale=Vector3.one*echelle;go.transform.localRotation=Quaternion.identity;
            go.transform.localPosition=new Vector3(-w/2f+.08f*w,h/2f-.08f*h,z);etiquette=go.transform;
        }
        static void AjouterVue(string nom,Vector3 vise,float cap,float inc,float dist,Camera camera,string controles,string eti,ReleveDuBanc releve)
        {var m=camera.projectionMatrix*camera.worldToCameraMatrix;vues.Add("{\"nom\":"+Q(nom)+",\"vise\":["+N(vise.x)+","+N(vise.y)+","+N(vise.z)+"],\"cap\":"+N(cap)+",\"inclinaison\":"+N(inc)+",\"distance\":"+N(dist)+",\"camera\":["+string.Join(",",Enumerable.Range(0,16).Select(i=>N(m[i])))+"],"+controles+",\"etiquette\":"+Q(eti)+",\"releve\":"+JsonUtility.ToJson(releve)+"}");}
        static void Ecrire(string defaut)
        {
            if(machine==null)machine="{\"gpu\":"+Q(SystemInfo.graphicsDeviceName)+",\"api\":"+Q(SystemInfo.graphicsDeviceType.ToString())+",\"cpu\":"+Q(SystemInfo.processorType)+",\"memoire_mo\":"+L(SystemInfo.systemMemorySize)+",\"unity\":"+Q(Application.unityVersion)+",\"qualite\":"+Q(QualitySettings.names[QualitySettings.GetQualityLevel()])+"}";
            var s=new StringBuilder();s.Append("{\"cellule\":").Append(L(cellule)).Append(",\"port\":").Append(L(outil?outil.Port:-1)).Append(",\"tick\":").Append(L(tick)).Append(",\"bourg\":").Append(L(bourgPop));
            s.Append(",\"contre_epreuve\":").Append(Q(drapeau)).Append(",\"defaut\":").Append(Q(defaut)).Append(",\"panier\":").Append(panierJson);
            s.Append(",\"maisons_posees\":").Append(L(maisonsPosees)).Append(",\"foyers\":").Append(L(foyers)).Append(",\"refus\":[").Append(string.Join(",",refus.Select(Q))).Append("],\"passants_projetes\":").Append(L(passProj)).Append(",\"passants_poses\":").Append(L(passPoses)).Append(",\"passants_scene\":").Append(L(passScene));
            s.Append(",\"chantier\":").Append(chantierId<0?"null":"{\"identifiant\":"+L(chantierId)+",\"nature\":\"maison\",\"etat\":"+Q(chantierEtat)+"}");
            s.Append(",\"heure\":").Append(heure<0?"-1":N(heure)).Append(",\"fumees\":").Append(L(fumees)).Append(",\"lampes\":").Append(L(lampes)).Append(",\"etals\":").Append(etalsJson);
            s.Append(",\"optimisations\":").Append(OptimisationsDeLaVille.Actives?"true":"false").Append(",\"machine\":").Append(machine).Append(",\"vues\":[").Append(string.Join(",",vues)).Append("]}");
            File.WriteAllText(rapport,s.ToString(),new UTF8Encoding(false));
        }
        static Material Mat(string nom)=>AssetDatabase.LoadAssetAtPath<Material>("Assets/ForgeLocal3D/Desert/Materials/"+nom+".mat")??throw Faux("matériau "+nom+" absent");
        static string Q(string t)=>t==null?"null":"\""+t.Replace("\\","\\\\").Replace("\"","\\\"").Replace("\n","\\n").Replace("\r","\\r").Replace("\t","\\t")+"\"";
        static string F1(double v)=>v.ToString("F1",CultureInfo.InvariantCulture).Replace('.',',');
        static string L(long n)=>n.ToString(CultureInfo.InvariantCulture);static string N(double v)=>v.ToString("R",CultureInfo.InvariantCulture);
    }
}
