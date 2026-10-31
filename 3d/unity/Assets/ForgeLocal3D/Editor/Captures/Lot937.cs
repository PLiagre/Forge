using System;using System.Collections;using System.Collections.Generic;using System.Globalization;using System.IO;using System.Linq;using System.Text;using Forge.Pont;using UnityEngine;using Object=UnityEngine.Object;
namespace ForgeLocal3D.Captures
{
    // Lot 937 : sur le service d'épreuve (-forgeTravailEnceinte), Biskra ; l'outil du joueur trace l'enceinte (E, quatre clics, Entrée),
    // puis la session la regarde passer des piquets à l'achèvement tick après tick, la caméra à l'ouest, dos à la porte. Chaque relevé
    // parcourt la scène, jamais Enceinte.Posees ni le panneau : tours, pans et portes dessinées contre les portes que le monde sert.
    // -forge937SansPorte retire les portes dessinées avant chaque relevé : le contrôle doit alors rougir. Rapport : `lot937-enceinte.json`.
    static class Lot937
    {
        const string Rapport="lot937-enceinte.json",SansPorte="-forge937SansPorte",Siege="Biskra",Tour="Enceinte tour ",Pan="Enceinte courtine ",Porte="Enceinte porte ";
        const int TicksMax=12,Images=10;
        static readonly (double x,double y)[] Coins={(-80,-80),(80,-80),(80,80),(-80,80)};
        static readonly List<string> releves=new();static DesertRoadTool outil;static long cellule=-1,acheve=-1;static int ticks;static bool sansPorte;
        static string rapport,etape="aucune",travail;static RecuIntention recu;static EnceinteDuPlan derniere;static (Vector3 vise,float cap,float dist)? cadre;
        static Exception Faux(string m)=>new InvalidOperationException(m);

        [ScenarioDeCapture(937,"1-enceinte-en-chantier")]static IEnumerator EnceinteEnChantier(Camera camera)=>Derouler(Chantier(camera));
        [ScenarioDeCapture(937,"2-enceinte-finie")]static IEnumerator EnceinteFinie(Camera camera)=>Derouler(Finie(camera));
        // Toute exception inscrit « étape : message » au rapport, puis fait échouer la capture.
        static IEnumerator Derouler(IEnumerator corps)
        {while(true){bool suite;try{suite=corps.MoveNext();}catch(Exception e){if(rapport!=null)Ecrire(etape+" : "+e.GetBaseException().Message);throw;}if(!suite)yield break;yield return null;}}

        static IEnumerator Chantier(Camera camera)
        {
            releves.Clear();outil=null;cellule=-1;acheve=-1;ticks=0;recu=null;derniere=null;cadre=null;rapport=null;etape="ouverture";
            var args=Environment.GetCommandLineArgs();sansPorte=args.Contains(SansPorte);int i=Array.IndexOf(args,Capture.TRAVAIL_ENCEINTE);travail=i>=0&&i+1<args.Length?args[i+1]:null;
            string chemin=Path.Combine(Capture.DossierDesCaptures,Rapport);if(File.Exists(chemin))throw Faux("rapport antérieur : "+chemin);rapport=chemin;
            outil=Object.FindFirstObjectByType<DesertRoadTool>()??throw Faux("pas d'outil");var ville=camera.GetComponent<DesertCityCamera>()??throw Faux("pas de caméra de ville");
            var lieu=Object.FindFirstObjectByType<PanneauLieu>()??throw Faux("pas de panneau du lieu");outil.automatique=ville.automatique=true;if(ville.Marcheur)ville.Marcheur.automatic=true;
            var lus=System.Threading.Tasks.Task.Run(()=>{using(var d=new ClientDeparts(outil.Port,ClientDeparts.DelaiMinimal))return d.Lire();});while(!lus.IsCompleted)yield return null;
            if(lus.IsFaulted||!lus.Result.Presente)throw Faux(lus.IsFaulted?lus.Exception.GetBaseException().Message:lus.Result.Absence);
            var zab=lus.Result.Donnees.Fiches.Where(f=>f.Siege.Nom==Siege).ToArray();if(zab.Length!=1)throw Faux(zab.Length+" sièges "+Siege);
            long c=zab[0].CellId;cellule=c;string geste="\"maison\":\"seigneurie-"+zab[0].Id+"\",\"cell\":"+L(c);
            // Le choix au tick 0, un tick, la route vers l'ouest, un tick : la porte s'ouvrira sur elle.
            etape="gestes";Lot362.Deposer(outil.Port,"{\"type\":\"choisir_depart\",\"seigneurie\":"+zab[0].Id+"}");Lot362.Tick(outil.Port);
            Lot362.Deposer(outil.Port,"{\"type\":\"tracer_route\","+geste+",\"points\":[[-66,2.2],[-120,2.2]],\"largeur_m\":4}");Lot362.Tick(outil.Port);
            etape="ouverture de "+Siege;if(!outil.Ouvrir(c))throw Faux(outil.Message);lieu.Ouvrir(c);
            var enc=outil.Enceinte??throw Faux("pas d'enceinte dessinable : "+outil.Message);
            if(outil.Maisons.Posees!=33||outil.Rues1400.Dessinees!=7||enc.Posees!=0)throw Faux(outil.Maisons.Posees+" maisons, "+outil.Rues1400.Dessinees+" rues de 1400, "+enc.Posees+" pièces d'enceinte");
            // La route de l'ouest est au plan ; la 3D peut la refuser (pente du relief) : le journal dit ce que la photo en montrera.
            var route=Lot362.Lire(outil.Port,c).Rues.FirstOrDefault(u=>u.Points.Count==2&&u.Points[0].X==-66&&u.Points[1].X==-120)??throw Faux("la route de l'ouest n'est pas au plan");
            var posee=outil.Ouverture.FirstOrDefault(o=>o.identifiant==route.Identifiant);Debug.Log("CAPTURE_937 route "+route.Identifiant+" : "+(posee.resultat?.message??"jamais essayée"));
            // Les clics, de haut, sur une image de la taille de la photo : chaque coin au milieu de l'écran.
            etape="tracé";var t=outil.roads.terrain;outil.EntrerEnceinte();var rt=new RenderTexture(1600,900,24);camera.targetTexture=rt;
            try{foreach(var (x,y) in Coins){var m=Lot362.Monde(t,x,y);ville.Poser(m,ville.Cap,85f,60f);if(!outil.Clic(camera.WorldToScreenPoint(m)))throw Faux("clic en "+P(x,y)+" refusé : "+outil.Message);}}
            finally{camera.targetTexture=null;rt.Release();Object.DestroyImmediate(rt);}
            if(!Panneau().Split('\n').Contains("Enceinte · 4 coin(s)"))throw Faux("panneau : "+Panneau());
            etape="dépôt";recu=outil.ValiderEnceinte();
            if(recu==null||!recu.Acceptee||recu.AppliqueeAuTick!=2)throw Faux("reçu "+(recu==null?"absent":recu.Acceptee?"appliqué au tick "+recu.AppliqueeAuTick:recu.Erreur??recu.Absence)+" : "+Panneau());
            if(!outil.Derniers.SequenceEqual(Coins))throw Faux("coins déposés "+string.Join(" ",outil.Derniers.Select(p=>P(p.x,p.y))));
            etape="tick du dépôt";Lot362.Tick(outil.Port);ticks=1;if(!outil.Attendre())throw Faux("Attendre faux après le tick : "+Panneau());
            var plan=Relever();var e=plan.Enceinte;
            if(!e.EnChantier||e.Contour.Count!=4||!e.Contour.Select(p=>(p.X,p.Y)).SequenceEqual(Coins))throw Faux("enceinte du tick "+plan.Tick+" : chantier "+e.EnChantier+", contour "+string.Join(" ",e.Contour.Select(p=>P(p.X,p.Y))));
            // De l'ouest à 35°, dos à la porte : les tours (−80 ; ±80), la porte et la route qui y mène tiennent dans l'image.
            etape="cadrage";float cap=(float)PansDeLEnceinte.Decouper(e,plan.Portes).Pieces.Last(p=>p.Nature==NatureDePiece.Porte).LacetDegres+180f;
            camera.aspect=1600f/900f;var vise=Lot362.Monde(t,-80,0);var cibles=new[]{(-80.0,-80.0),(-80.0,80.0),(-80.0,2.2),(-95.0,2.2)}.Select(p=>Lot362.Monde(t,p.Item1,p.Item2)).ToArray();
            for(float d=40f;d<=DesertCityCamera.DistanceMax&&cadre==null;d*=1.06f){ville.Poser(vise,cap,35f,d);if(cibles.All(v=>Dans(camera,v))&&camera.transform.position.x>80f)cadre=(vise,cap,d);}
            if(cadre==null)throw Faux("cadrage impossible, caméra "+camera.transform.position);
            outil.Placer();for(int k=0;k<Images;k++)yield return null;
        }

        static IEnumerator Finie(Camera camera)
        {
            if(outil==null||cadre==null||releves.Count==0||derniere==null)throw Faux("le scénario « 1-enceinte-en-chantier » n'a pas joué");
            var ville=camera.GetComponent<DesertCityCamera>()??throw Faux("pas de caméra de ville");
            while(derniere.EnChantier)
            {
                etape="chantier";if(ticks>=TicksMax)throw Faux("enceinte inachevée après "+TicksMax+" ticks : fourni "+derniere.TravailFourni+"/"+derniere.TravailRequis);
                Lot362.Tick(outil.Port);ticks++;if(!outil.Rafraichir())throw Faux("rafraîchir : "+outil.Message);Relever();yield return null;
            }
            if(PansDeLEnceinte.Etape(derniere)!=EtapeDuBatiment.Fini)throw Faux("enceinte achevée à l'étape "+PansDeLEnceinte.Etape(derniere));
            etape="cadrage";var k=cadre.Value;camera.aspect=1600f/900f;ville.Poser(k.vise,k.cap,35f,k.dist);
            outil.Placer();for(int n=0;n<Images;n++)yield return null;
            Debug.Log("CAPTURE_937 "+Ecrire(null));
        }

        // Le relevé, après chaque dessin. Les tours, pans et portes sont les Transform actifs de la scène, où qu'ils soient rangés.
        static PlanLu Relever()
        {
            etape="relevé";
            if(sansPorte)foreach(var enfant in outil.Enceinte.Racine.Cast<Transform>().Where(x=>x.name.StartsWith(Porte,StringComparison.Ordinal)).ToArray())Object.DestroyImmediate(enfant.gameObject);
            var lignes=Panneau().Split('\n');string vue=new[]{"piquets","murs","fini"}.FirstOrDefault(s=>lignes.Contains("Enceinte : "+s+" · 4 tour(s), 63 pan(s), 1 porte(s)."))??throw Faux("panneau : "+Panneau());
            var plan=Lot362.Lire(outil.Port,cellule);var e=plan.Enceinte??throw Faux("pas d'enceinte au plan du tick "+plan.Tick);
            string et=PansDeLEnceinte.Etape(e).ToString().ToLowerInvariant();if(et!=vue)throw Faux("panneau à l'étape "+vue+", plan du tick "+plan.Tick+" à "+et);
            var scene=Object.FindObjectsByType<Transform>(FindObjectsInactive.Exclude,FindObjectsSortMode.None);bool A(Transform x,string p)=>x.name.StartsWith(p,StringComparison.Ordinal);
            var portes=scene.Where(x=>A(x,Porte)).OrderBy(x=>x.name,StringComparer.Ordinal).ToArray();
            double Ecart(PointLocal p)=>portes.Length==0?-1:portes.Min(x=>Math.Sqrt((-x.position.x-p.X)*(-x.position.x-p.X)+(-x.position.z-p.Y)*(-x.position.z-p.Y)));
            releves.Add("{\"tick\":"+L(plan.Tick)+",\"en_chantier\":"+B(e.EnChantier)+",\"travail_fourni\":"+L(e.TravailFourni)+",\"travail_requis\":"+L(e.TravailRequis)+",\"etape\":"+Q(et)
                +",\"portes_servies\":["+string.Join(",",plan.Portes.Select(p=>"{\"x\":"+N(p.Point.X)+",\"y\":"+N(p.Point.Y)+",\"rue\":"+Q(p.Rue)+",\"identifiant\":"+L(p.Identifiant)+"}"))+"]"
                +",\"tours\":"+scene.Count(x=>A(x,Tour))+",\"pans\":"+scene.Count(x=>A(x,Pan))
                +",\"portes_dessinees\":["+string.Join(",",portes.Select(x=>"{\"nom\":"+Q(x.name)+",\"x\":"+N(-x.position.x)+",\"y\":"+N(-x.position.z)+",\"lacet\":"+N(x.eulerAngles.y)+"}"))+"]"
                +",\"ecart_porte_m\":["+string.Join(",",plan.Portes.Select(p=>N(Ecart(p.Point))))+"]}");
            derniere=e;if(!e.EnChantier&&acheve<0)acheve=plan.Tick;
            Ecrire(e.EnChantier?"session interrompue après le relevé du tick "+L(plan.Tick):null);
            Debug.Log("CAPTURE_937 relevé du tick "+L(plan.Tick)+" : "+et+", "+e.TravailFourni+"/"+e.TravailRequis+", "+portes.Length+" porte(s) dessinée(s)");
            return plan;
        }

        static string Ecrire(string defaut)
        {
            string r="{\"cellule\":"+L(cellule)+",\"port\":"+L(outil?outil.Port:-1)+",\"contre_epreuve\":"+Q(sansPorte?SansPorte.Substring(1):"")+",\"travail_enceinte\":"+Q(travail)
                +",\"coins\":["+string.Join(",",Coins.Select(p=>P(p.x,p.y)))+"],\"recu\":"+(recu==null?"null":"{\"acceptee\":"+B(recu.Acceptee)+",\"tick\":"+(recu.AppliqueeAuTick.HasValue?L(recu.AppliqueeAuTick.Value):"null")+"}")
                +",\"releves\":["+string.Join(",",releves)+"],\"acheve_au_tick\":"+(acheve<0?"null":L(acheve))+",\"defaut\":"+Q(defaut)+"}";
            File.WriteAllText(rapport,r+"\n",new UTF8Encoding(false));return r;
        }
        static string Panneau(){var p=outil.view.transform.Find("Panneau des routes")?.GetComponent<TextMesh>();if(!p)throw Faux("la caméra de l'outil n'a pas de panneau");return p.text;}
        static bool Dans(Camera camera,Vector3 v){var q=camera.WorldToViewportPoint(v);return q.z>camera.nearClipPlane&&q.x>.02f&&q.x<.98f&&q.y>.02f&&q.y<.98f;}
        static string Q(string s)=>s==null?"null":"\""+s.Replace("\\","\\\\").Replace("\"","\\\"").Replace("\n","\\n").Replace("\r","\\r").Replace("\t","\\t")+"\"";
        static string B(bool b)=>b?"true":"false";static string L(long n)=>n.ToString(CultureInfo.InvariantCulture);static string N(double v)=>v.ToString("R",CultureInfo.InvariantCulture);
        static string P(double x,double y)=>"["+N(x)+","+N(y)+"]";
    }
}
