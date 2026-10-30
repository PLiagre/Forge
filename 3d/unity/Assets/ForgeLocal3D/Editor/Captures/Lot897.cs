using System;using System.Collections;using System.Collections.Generic;using System.Globalization;using System.IO;using System.Linq;using System.Net.Http;using System.Text;using System.Threading.Tasks;using Forge.Pont;using UnityEngine;using Object=UnityEngine.Object;
namespace ForgeLocal3D.Captures
{
    // Lot 897 : sur le service d'épreuve, Biskra au tick 5, trois routes en chantier tracées sur la place (01), puis la même rue au tick 6,
    // le bourg vidé par POST /epreuve/vider-bourg (#896) et un tick de plus (02). La foule est celle de PassantsDeLaVille, que la session
    // ne touche jamais, sauf par un drapeau de contre-épreuve ; le relevé parcourt la scène (MeshFilter actifs au maillage civil), jamais
    // le bilan du composant. Rapport : `passants-bourg.json`, réécrit à chaque relevé ; `defaut` nomme l'étape tant que 02 n'a pas relevé.
    static class Lot897
    {
        const string Siege="Biskra",Rapport="passants-bourg.json",EnTrop="-forge897PassantEnTrop",Ailleurs="-forge897OuvriersAilleurs",Anciens="-forge897GarderAnciens";
        const long TickChantier=5,TickVide=6;const int Images=10;const double AttenteS=30;static readonly TimeSpan Delai=TimeSpan.FromSeconds(10);
        // Les trois routes de la place, en mètres du plan : de (0 ; d) à (40 ; d), 4 m de large. La caméra vise (32 ; 8).
        static readonly double[] Ordonnees={0,8,16};const double Longueur=40,ViseX=32,ViseY=8;
        static readonly List<string> etats=new();static DesertRoadTool outil;static PassantsDeLaVille foule;static long cellule=-1;static string etape="aucune",drapeau="",rapport;
        static (Vector3 vise,float cap,float inc,float dist)? cadre;
        static Exception Faux(string m)=>new InvalidOperationException(m);

        [ScenarioDeCapture(897,"01-ouvriers-au-chantier")]static IEnumerator OuvriersAuChantier(Camera camera)=>Derouler(Chantier(camera));
        [ScenarioDeCapture(897,"02-bourg-vide")]static IEnumerator BourgVide(Camera camera)=>Derouler(Vide(camera));
        // Toute exception inscrit « étape : message » au rapport, puis fait échouer la capture.
        static IEnumerator Derouler(IEnumerator corps)
        {while(true){bool suite;try{suite=corps.MoveNext();}catch(Exception e){if(rapport!=null)Ecrire(etape+" : "+e.GetBaseException().Message);throw;}if(!suite)yield break;yield return null;}}

        static IEnumerator Chantier(Camera camera)
        {
            etats.Clear();cadre=null;cellule=-1;outil=null;foule=null;rapport=null;drapeau="";etape="ouverture";
            // Avant toute requête : un rapport antérieur reste tel quel, et deux drapeaux ensemble ne déposent rien.
            string chemin=Path.Combine(Capture.DossierDesCaptures,Rapport);if(File.Exists(chemin))throw Faux("rapport antérieur : "+chemin);rapport=chemin;
            var donnes=new[]{EnTrop,Ailleurs,Anciens}.Where(Environment.GetCommandLineArgs().Contains).ToArray();
            if(donnes.Length>1)throw Faux("un seul drapeau de contre-épreuve à la fois, reçu : "+string.Join(" ",donnes));if(donnes.Length==1)drapeau=donnes[0].Substring(1);
            outil=Object.FindFirstObjectByType<DesertRoadTool>()??throw Faux("pas d'outil des routes");var ville=camera.GetComponent<DesertCityCamera>()??throw Faux("pas de caméra de ville");
            foule=outil.GetComponent<PassantsDeLaVille>()??throw Faux("foule absente");if(!outil.maillageCivil)throw Faux("maillage civil absent");
            outil.automatique=ville.automatique=true;if(ville.Marcheur)ville.Marcheur.automatic=true;var visite=camera.GetComponent<VillageV2Visit>();if(visite)visite.enabled=false;
            var env=Object.FindFirstObjectByType<DesertEnvironment>();if(env)env.showPanel=false;var bandeau=GameObject.Find("/Panneau du lieu");if(bandeau)bandeau.SetActive(false);
            foreach(var tm in Object.FindObjectsByType<TextMesh>(FindObjectsSortMode.None))tm.gameObject.SetActive(false);
            int port=outil.Port;var departs=Task.Run(()=>{using(var d=new ClientDeparts(port,ClientDeparts.DelaiMinimal))return d.Lire();});while(!departs.IsCompleted)yield return null;
            if(departs.IsFaulted||!departs.Result.Presente)throw Faux(departs.IsFaulted?departs.Exception.GetBaseException().Message:departs.Result.Absence);
            var zab=departs.Result.Donnees.Fiches.Where(f=>f.Siege.Nom==Siege).ToArray();if(zab.Length!=1)throw Faux(zab.Length+" départ(s) au siège "+Siege);cellule=zab[0].CellId;
            // Le choix au tick 0, un tick, les trois routes, puis les ticks jusqu'au chantier.
            etape="gestes";Lot362.Deposer(port,"{\"type\":\"choisir_depart\",\"seigneurie\":"+zab[0].Id+"}");Lot362.Tick(port);
            string geste="{\"type\":\"tracer_route\",\"maison\":\"seigneurie-"+zab[0].Id+"\",\"cell\":"+L(cellule)+",\"points\":[[0,";
            Lot362.Deposer(port,Ordonnees.Select(d=>geste+N(d)+"],["+N(Longueur)+","+N(d)+"]],\"largeur_m\":4}").ToArray());for(long k=1;k<TickChantier;k++)Lot362.Tick(port);
            etape="ouverture de "+Siege;if(!outil.Ouvrir(cellule))throw Faux(outil.Message);
            for(double fin=Time.realtimeSinceStartupAsDouble+AttenteS;(foule.CelluleAppliquee!=cellule||foule.TickApplique!=TickChantier)&&Time.realtimeSinceStartupAsDouble<fin;)yield return null;
            if(foule.CelluleAppliquee!=cellule||foule.TickApplique!=TickChantier)throw Faux("foule de la cellule "+foule.CelluleAppliquee+" au tick "+foule.TickApplique+" : "+foule.Cause);
            var t=Lire();while(!t.IsCompleted)yield return null;var (lieu,plan)=Verifier(t,TickChantier);
            if(plan.Plan.ChantiersDuJour==null||!plan.Plan.ChantiersDuJour.Any(c=>c.Nature=="rue"&&c.Bras>0))throw Faux("aucun chantier de rue avec des bras au tick "+TickChantier+" : "+plan.Plan.AbsenceDesChantiersDuJour);
            // La plus petite distance, entre 25 et 40° d'inclinaison, qui tient les bouts des trois routes et de « base 0 » dans [0,05 ; 0,95].
            // Cap 180 d'abord : depuis le sud de la place, aucune maison ne se dresse entre la caméra et la sortie « base 0 ».
            etape="cadrage";var sol=outil.roads.terrain;var b0=plan.Plan.Base?.Rues?.FirstOrDefault()?.Points??throw Faux("pas de « base 0 » au plan");if(b0.Count<2)throw Faux("« base 0 » sans longueur");
            var bouts=Ordonnees.SelectMany(d=>new[]{Lot362.Monde(sol,0,d),Lot362.Monde(sol,Longueur,d)}).Concat(new[]{Lot362.Monde(sol,b0[0].X,b0[0].Y),Lot362.Monde(sol,b0[b0.Count-1].X,b0[b0.Count-1].Y)}).ToArray();
            camera.aspect=1600f/900f;var vise=Lot362.Monde(sol,ViseX,ViseY);
            for(float d=DesertCityCamera.DistanceMin;d<=DesertCityCamera.DistanceMax&&cadre==null;d*=1.02f)foreach(float cap in new[]{180f,0f})for(float inc=25;inc<=40&&cadre==null;inc+=5)
            {ville.Poser(vise,cap,inc,d);if(bouts.All(p=>Dans(camera,p,.05f)))cadre=(vise,cap,inc,d);}
            if(cadre==null)throw Faux("les trois routes et « base 0 » ne tiennent pas dans l'image");
            for(int i=0;i<Images;i++)yield return null;
            etape="relevé du chantier";Fausser(plan);Relever("chantier",lieu,plan,camera);Ecrire("02 : session interrompue après le relevé « chantier »");
        }

        static IEnumerator Vide(Camera camera)
        {
            if(cadre==null||etats.Count!=1)throw Faux("le scénario « 01-ouvriers-au-chantier » n'a pas relevé la rue");
            var ville=camera.GetComponent<DesertCityCamera>()??throw Faux("pas de caméra de ville");etape="vider-bourg";
            // Le maintien indu : la foule passe sous un autre parent, avec ses identifiants, avant que le monde ne la vide.
            if(drapeau==Anciens.Substring(1)){var garde=new GameObject("Anciens gardés").transform;foreach(var e in foule.Racine.Cast<Transform>().ToArray())e.SetParent(garde,true);}
            int port=outil.Port;long c=cellule;var post=Task.Run(()=>Poster(port,c));while(!post.IsCompleted)yield return null;if(post.IsFaulted)throw Faux(post.Exception.GetBaseException().Message);
            var (statut,corps)=post.Result;if(statut!=200)throw Faux("POST /epreuve/vider-bourg?cell="+L(c)+" a rendu "+statut+" : "+corps);
            var r=LecteurJson.LireObjet(corps);long Cle(string k)=>r.TryGetValue(k,out var v)&&v is double d?(long)d:throw Faux("POST : clé "+k+" absente ou non entière : "+corps);
            if(Cle("cell_id")!=c||Cle("tick")!=TickChantier)throw Faux("POST : rendu "+corps+" pour la cellule "+L(c)+" au tick "+TickChantier);
            var t=Lire();while(!t.IsCompleted)yield return null;Bourg0(Verifier(t,TickChantier).lieu);
            // #896 republie sans avancer le tick, et le composant ignore un tick déjà appliqué : un tick de plus, il remplace la foule de lui-même.
            etape="tick après le bourg vidé";Lot362.Tick(port);
            for(double fin=Time.realtimeSinceStartupAsDouble+AttenteS;foule.TickApplique!=TickVide&&Time.realtimeSinceStartupAsDouble<fin;)yield return null;
            if(foule.TickApplique!=TickVide)throw Faux("foule au tick "+foule.TickApplique+" : "+foule.Cause);
            t=Lire();while(!t.IsCompleted)yield return null;var (lieu,plan)=Verifier(t,TickVide);Bourg0(lieu);
            var k=cadre.Value;camera.aspect=1600f/900f;ville.Poser(k.vise,k.cap,k.inc,k.dist);for(int i=0;i<Images;i++)yield return null;
            etape="relevé du bourg vide";Relever("vide",lieu,plan,camera);Ecrire(null);
        }
        static void Bourg0(LectureLieu l){if(l.Lieu.Bourg?.Population!=0)throw Faux("bourg à "+(l.Lieu.Bourg?.Population?.ToString()??"?")+" au tick "+l.Lieu.Tick+" après vider-bourg");}

        static Task<(LectureLieu lieu,LecturePlan plan)> Lire(){int port=outil.Port;long c=cellule;return Task.Run(()=>{using(var a=new ClientLieu(port,Delai))using(var b=new ClientPlan(port,Delai))return (a.Lire(c),b.Lire(c));});}
        static (LectureLieu lieu,LecturePlan plan) Verifier(Task<(LectureLieu lieu,LecturePlan plan)> t,long tick)
        {
            if(t.IsFaulted)throw Faux(t.Exception.GetBaseException().Message);var (l,p)=t.Result;if(!l.Presente)throw Faux("lieu absent : "+l.Absence);if(!p.Presente)throw Faux("plan absent : "+p.Absence);
            if(l.Lieu.CellId!=cellule||p.Plan.CellId!=cellule||l.Lieu.Tick!=tick||p.Plan.Tick!=tick)throw Faux("lieu "+l.Lieu.CellId+"/"+l.Lieu.Tick+", plan "+p.Plan.CellId+"/"+p.Plan.Tick+" pour "+cellule+"/"+tick);
            return (l,p);
        }
        static (int,string) Poster(int port,long c)
        {
            using(var http=new HttpClient{Timeout=Delai})using(var vide=new StringContent(""))
            using(var r=http.PostAsync("http://127.0.0.1:"+port.ToString(CultureInfo.InvariantCulture)+"/epreuve/vider-bourg?cell="+L(c),vide).GetAwaiter().GetResult())
                return ((int)r.StatusCode,r.Content.ReadAsStringAsync().GetAwaiter().GetResult());
        }

        // Les drapeaux faussent la scène après le tick appliqué, jamais le rapport : une copie de trop, ou des ouvriers figés sur une sortie.
        static void Fausser(LecturePlan plan)
        {
            var enfants=foule.Racine?foule.Racine.Cast<Transform>().ToArray():new Transform[0];
            if(drapeau==EnTrop.Substring(1)){var e=enfants.FirstOrDefault(x=>x.name.StartsWith("paysans|",StringComparison.Ordinal))??throw Faux("aucun paysan à copier");Copier(e,e.position+e.right*.6f);}
            if(drapeau!=Ailleurs.Substring(1))return;
            var sortie=TrajetsDesMetiers.Calculer(plan,"paysans").Trajets.FirstOrDefault(x=>x.Points!=null&&x.Points.Count>1)??throw Faux("aucun trajet paysan accessible");var m=Milieu(sortie.Points);
            foreach(var e in enfants.Where(x=>x.name.StartsWith("ouvriers|",StringComparison.Ordinal))){Copier(e,Lot362.Monde(outil.roads.terrain,m.X,m.Y));e.gameObject.SetActive(false);}
        }
        static void Copier(Transform e,Vector3 ou){var c=Object.Instantiate(e.gameObject,ou,e.rotation,foule.Racine);c.name=e.name;var b=new MaterialPropertyBlock();e.GetComponent<Renderer>().GetPropertyBlock(b);c.GetComponent<Renderer>().SetPropertyBlock(b);}
        static PointLocal Milieu(IReadOnlyList<PointLocal> l)
        {
            double total=0;for(int k=0;k+1<l.Count;k++)total+=Dist(l[k],l[k+1]);double reste=total/2;
            for(int k=0;k+1<l.Count;k++){double s=Dist(l[k],l[k+1]);if(s>0&&reste<=s)return new PointLocal(l[k].X+(l[k+1].X-l[k].X)*reste/s,l[k].Y+(l[k+1].Y-l[k].Y)*reste/s);reste-=s;}return l[l.Count-1];
        }
        static double Dist(PointLocal a,PointLocal b)=>Math.Sqrt((b.X-a.X)*(b.X-a.X)+(b.Y-a.Y)*(b.Y-a.Y));
        // Distance horizontale d'un point du plan à une polyligne ; -1 sans segment.
        static double Ecart(double x,double y,IReadOnlyList<PointLocal> l)
        {
            double m=double.PositiveInfinity;
            for(int k=0;k+1<l.Count;k++){double ax=l[k].X,ay=l[k].Y,dx=l[k+1].X-ax,dy=l[k+1].Y-ay,q=dx*dx+dy*dy,s=q>0?Math.Clamp(((x-ax)*dx+(y-ay)*dy)/q,0,1):0;m=Math.Min(m,Dist(new PointLocal(x,y),new PointLocal(ax+s*dx,ay+s*dy)));}
            return double.IsInfinity(m)?-1:m;
        }
        static bool Dans(Camera c,Vector3 p,float marge){var v=c.WorldToViewportPoint(p);return v.z>0f&&v.x>=marge&&v.x<=1-marge&&v.y>=marge&&v.y<=1-marge;}
        static bool Entier(Camera c,Renderer r)
        {if(!r)return false;var b=r.bounds;for(int i=0;i<8;i++)if(!Dans(c,b.center+Vector3.Scale(b.extents,new Vector3((i&1)*2-1,((i>>1)&1)*2-1,((i>>2)&1)*2-1)),.03f))return false;return true;}

        // Le relevé de la scène : chaque MeshFilter actif au maillage civil est un passant, où qu'il soit rangé. -1 : non calculé.
        static void Relever(string nom,LectureLieu lieu,LecturePlan plan,Camera camera)
        {
            var proj=PassantsDuBourg.Projeter(lieu);if(!proj.Presente)throw Faux("effectifs : "+proj.Absence);var p=plan.Plan;
            List<TrajetDuMetier> Acces(string metier)=>TrajetsDesMetiers.Calculer(plan,metier).Trajets.Where(x=>x.Points!=null&&x.Points.Count>1).ToList();
            var bras=(p.ChantiersDuJour??new ChantierDuJour[0]).Where(c=>c.Nature=="rue"&&c.Bras>0).Select(c=>p.Rues.FirstOrDefault(u=>u.Identifiant==c.Identifiant)).Where(u=>u!=null).ToList();
            var gens=Object.FindObjectsByType<MeshFilter>(FindObjectsInactive.Exclude,FindObjectsSortMode.None).Where(f=>f.sharedMesh==outil.maillageCivil)
                .OrderBy(f=>f.name,StringComparer.Ordinal).ThenBy(f=>f.GetInstanceID()).ToArray();
            int hors=gens.Count(f=>!foule.Racine||!f.transform.IsChildOf(foule.Racine));if(hors>0)Debug.Log("CAPTURE_897 "+nom+" : "+hors+" objet(s) au maillage civil hors de la foule");
            var liste=new List<string>();var parMetier=new SortedDictionary<string,long>(StringComparer.Ordinal);
            foreach(var f in gens)
            {
                var parts=f.name.Split('|');string metier=parts.Length==3?parts[0]:"",dest=parts.Length==3?parts[1]:"";var pos=f.transform.position;double x=-pos.x,y=-pos.z;
                parMetier[metier]=parMetier.TryGetValue(metier,out long n)?n+1:1;var trajet=metier==""?null:Acces(metier).FirstOrDefault(u=>u.Destination==dest);
                liste.Add("{\"id\":"+L(f.GetInstanceID())+",\"nom\":"+Q(f.name)+",\"metier\":"+Q(metier)+",\"destination\":"+Q(dest)+",\"x\":"+N(x)+",\"y\":"+N(y)
                    +",\"ecart_trajet_m\":"+N(trajet==null?-1:Ecart(x,y,trajet.Points))+",\"ecart_chantier_m\":"+N(bras.Count==0?-1:bras.Min(u=>Ecart(x,y,u.Points)))+",\"visible\":"+B(Entier(camera,f.GetComponent<Renderer>()))+"}");
            }
            string Dico(IEnumerable<KeyValuePair<string,long>> d)=>"{"+string.Join(",",d.OrderBy(kv=>kv.Key,StringComparer.Ordinal).Select(kv=>Q(kv.Key)+":"+L(kv.Value)))+"}";
            var metiers=(lieu.Lieu.Foyers?.Keys??Enumerable.Empty<string>()).Concat(proj.ParMetier.Keys).Distinct().OrderBy(m=>m,StringComparer.Ordinal);
            var m4=camera.projectionMatrix*camera.worldToCameraMatrix;var s=new StringBuilder("{\"nom\":"+Q(nom));
            s.Append(",\"tick_lieu\":"+L(lieu.Lieu.Tick)+",\"tick_plan\":"+L(p.Tick)+",\"tick_applique\":"+L(foule.TickApplique)+",\"bourg\":"+L(lieu.Lieu.Bourg?.Population??-1));
            s.Append(",\"projete\":"+L(foule.NombreProjete)+",\"pose\":"+L(foule.NombrePose)+",\"attendu\":"+Dico(proj.ParMetier));
            s.Append(",\"trajets\":{"+string.Join(",",metiers.Select(m=>Q(m)+":["+string.Join(",",Acces(m).Select(u=>Q(u.Destination)))+"]"))+"}");
            s.Append(",\"chantiers\":["+string.Join(",",(p.ChantiersDuJour??new ChantierDuJour[0]).Select(c=>"{\"nature\":"+Q(c.Nature)+",\"identifiant\":"+L(c.Identifiant)+",\"bras\":"+L(c.Bras)+"}"))+"]");
            s.Append(",\"passants\":"+L(gens.Length)+",\"par_metier\":"+Dico(parMetier)+",\"liste\":["+string.Join(",",liste)+"],\"camera\":["+string.Join(",",Enumerable.Range(0,16).Select(i=>N(m4[i])))+"]}");
            etats.Add(s.ToString());Debug.Log("CAPTURE_897 "+nom+" : "+gens.Length+" passant(s) relevé(s), "+Dico(parMetier)+", tick "+foule.TickApplique);
        }
        static void Ecrire(string defaut)=>File.WriteAllText(rapport,"{\"cellule\":"+L(cellule)+",\"port\":"+L(outil?outil.Port:-1)+",\"contre_epreuve\":"+Q(drapeau)+",\"defaut\":"+Q(defaut)+",\"etats\":["+string.Join(",",etats)+"]}\n",new UTF8Encoding(false));
        static string Q(string t)=>t==null?"null":"\""+t.Replace("\\","\\\\").Replace("\"","\\\"").Replace("\n","\\n").Replace("\r","\\r").Replace("\t","\\t")+"\"";
        static string B(bool b)=>b?"true":"false";static string L(long n)=>n.ToString(CultureInfo.InvariantCulture);static string N(double v)=>v.ToString("R",CultureInfo.InvariantCulture);
    }
}
